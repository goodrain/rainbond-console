# -*- coding: utf-8 -*-
import logging

import yaml
from django.http.response import StreamingHttpResponse
from rest_framework.response import Response

from console.repositories.app import service_repo
from console.repositories.helm import helm_repo
from console.repositories.helm_release_source import helm_release_source_repo
from console.services.app_actions import ws_service
from console.views.base import TenantHeaderView
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


def get_team_resource_namespace(view, fallback=None):
    tenant = getattr(view, "tenant", None)
    if tenant is not None:
        namespace = getattr(tenant, "namespace", None)
        if namespace:
            return namespace
        tenant_name = getattr(tenant, "tenant_name", None)
        if tenant_name:
            return tenant_name
    return fallback


def build_helm_install_body(body, namespace=None):
    payload = dict(body or {})
    if namespace and not payload.get("namespace"):
        payload["namespace"] = namespace
    source_type = payload.get("source_type") or "store"
    if source_type != "store":
        return payload

    repo_name = payload.get("repo_name")
    if not repo_name:
        return payload

    repo = helm_repo.get_helm_repo_by_name(repo_name)
    if not repo:
        return payload

    chart_name = payload.get("chart_name") or payload.get("chart")
    payload["source_type"] = "repo"
    payload["repo_url"] = payload.get("repo_url") or repo.get("repo_url")
    if chart_name:
        payload["chart_name"] = chart_name
    payload["username"] = payload.get("username") or repo.get("username", "")
    payload["password"] = payload.get("password") or repo.get("password", "")
    return payload


def first_non_empty(*values):
    for value in values:
        if value:
            return value
    return ""


def get_request_operator(request):
    try:
        user = getattr(request, "user", None)
    except Exception:
        return ""
    return first_non_empty(
        getattr(user, "nick_name", ""),
        getattr(user, "username", ""),
        getattr(user, "user_id", ""),
    )


def normalize_helm_values_yaml(*candidates):
    for value in candidates:
        if value in (None, ""):
            continue
        if isinstance(value, (dict, list)):
            return yaml.safe_dump(value, default_flow_style=False, allow_unicode=True)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)
    return ""


def build_helm_release_source_info(record=None, release=None):
    release = release or {}
    record = record or {}
    source_type = record.get("source_type") or "legacy"
    return {
        "source_type": source_type,
        "repo_name": record.get("repo_name") or "",
        "repo_url": record.get("repo_url") or "",
        "chart_name": record.get("chart_name") or release.get("chart") or "",
        "chart_version": record.get("chart_version") or release.get("chart_version") or "",
        "upgrade_mode": "store_locked" if source_type == "store" else "manual_select",
    }


def persist_helm_release_source(request, team_name, region_name, namespace, raw_body, install_body, response_body):
    release_name = first_non_empty(
        (response_body or {}).get("release_name"),
        install_body.get("release_name"),
        raw_body.get("release_name"),
        raw_body.get("name"),
    )
    if not release_name:
        return
    source_type = (raw_body.get("source_type") or "store").strip() or "store"
    helm_release_source_repo.save_or_update(
        team_name=team_name,
        region_name=region_name,
        namespace=namespace,
        release_name=release_name,
        source_type=source_type,
        repo_name=first_non_empty(raw_body.get("repo_name"), install_body.get("repo_name")),
        repo_url=first_non_empty(raw_body.get("repo_url"), install_body.get("repo_url")),
        chart_name=first_non_empty(
            raw_body.get("chart_name"),
            raw_body.get("chart"),
            install_body.get("chart_name"),
            install_body.get("chart"),
        ),
        chart_version=first_non_empty(raw_body.get("version"), install_body.get("version")),
        values_yaml=normalize_helm_values_yaml(raw_body.get("values"), install_body.get("values")),
        creator=get_request_operator(request),
    )


def enrich_helm_release_list(bean, region_name, namespace):
    releases = (bean or {}).get("list") or []
    release_names = [item.get("name") for item in releases if item.get("name")]
    source_map = {}
    try:
        source_map = helm_release_source_repo.list_by_releases(region_name, namespace, release_names)
    except Exception as e:
        logger.exception("list helm release source failed: %s", e)
    for item in releases:
        item_namespace = item.get("namespace") or namespace
        key = "{}/{}".format(item_namespace, item.get("name"))
        item["source_info"] = build_helm_release_source_info(source_map.get(key), item)
    return bean


def enrich_helm_release_detail(bean, region_name, namespace, release_name):
    summary = ((bean or {}).get("summary")) or {}
    item_namespace = summary.get("namespace") or namespace
    record = None
    try:
        record = helm_release_source_repo.get_by_release(region_name, item_namespace, release_name)
    except Exception as e:
        logger.exception("get helm release source failed: %s", e)
    values_yaml = normalize_helm_values_yaml((record or {}).get("values_yaml"))
    if values_yaml:
        summary["values"] = values_yaml
    summary["source_info"] = build_helm_release_source_info(record, summary)
    bean["summary"] = summary
    return bean


class NsResourceTypesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        res, data = region_api.get_tenant_ns_resource_types(region_name, team_name)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class NsResourcesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resources(region_name, team_name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))

    def post(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        content_type = request.META.get("CONTENT_TYPE")
        res, data = region_api.post_tenant_ns_resource(
            region_name, team_name, request.body, params=params, content_type=content_type)
        status_code = getattr(res, "status", 200)
        return Response(data, status=status_code)


class TeamComponentsView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        components = service_repo.list_basic_infos_by_team_and_region(self.tenant.tenant_id, region_name)
        return Response(general_message(200, "success", "OK", list=components))


class NsResourceDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))

    def put(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        content_type = request.META.get("CONTENT_TYPE")
        res, data = region_api.put_tenant_ns_resource(
            region_name, team_name, name, request.body, params=params, content_type=content_type)
        return Response(general_message(200, "success", "更新成功", bean=data.get("bean")))

    def delete(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        region_api.delete_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "删除成功"))


class HelmReleasesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        res, data = region_api.get_tenant_helm_releases(region_name, team_name, namespace=namespace)
        bean = enrich_helm_release_list(data.get("bean") or {}, region_name, namespace)
        return Response(general_message(200, "success", "OK", bean=bean))

    def post(self, request, team_name, region_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        raw_body = dict(request.data or {})
        body = build_helm_install_body(raw_body, namespace=namespace)
        res, data = region_api.install_tenant_helm_release(region_name, team_name, body)
        try:
            persist_helm_release_source(request, team_name, region_name, namespace, raw_body, body, data.get("bean") or {})
        except Exception as e:
            logger.exception("persist helm release source failed: %s", e)
        return Response(general_message(200, "success", "安装成功", bean=data.get("bean")))


class HelmChartPreviewView(TenantHeaderView):
    def post(self, request, team_name, region_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        body = build_helm_install_body(request.data or {}, namespace=namespace)
        res, data = region_api.preview_tenant_helm_chart(region_name, team_name, body)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class HelmReleaseDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, release_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        res, data = region_api.get_tenant_helm_release_detail(region_name, team_name, release_name, namespace=namespace)
        bean = enrich_helm_release_detail(data.get("bean") or {}, region_name, namespace, release_name)
        return Response(general_message(200, "success", "OK", bean=bean))

    def put(self, request, team_name, region_name, release_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        raw_body = dict(request.data or {})
        body = build_helm_install_body(request.data or {}, namespace=namespace)
        res, data = region_api.upgrade_tenant_helm_release(region_name, team_name, release_name, body)
        try:
            persist_helm_release_source(
                request=request,
                team_name=team_name,
                region_name=region_name,
                namespace=namespace,
                raw_body=raw_body,
                install_body=body,
                response_body=dict((data or {}).get("bean") or {}, release_name=release_name),
            )
        except Exception as e:
            logger.exception("persist helm release source failed: %s", e)
        return Response(general_message(200, "success", "升级成功", bean=data.get("bean")))

    def delete(self, request, team_name, region_name, release_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        region_api.uninstall_tenant_helm_release(region_name, team_name, release_name, namespace=namespace)
        try:
            helm_release_source_repo.delete_by_release(
                region_name=region_name,
                namespace=namespace,
                release_name=release_name,
            )
        except Exception as e:
            logger.exception("delete helm release source failed: %s", e)
        return Response(general_message(200, "success", "卸载成功"))


class HelmReleaseHistoryView(TenantHeaderView):
    def get(self, request, team_name, region_name, release_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        res, data = region_api.get_tenant_helm_release_history(region_name, team_name, release_name, namespace=namespace)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class HelmReleaseRollbackView(TenantHeaderView):
    def post(self, request, team_name, region_name, release_name, *args, **kwargs):
        namespace = get_team_resource_namespace(self, team_name)
        body = dict(request.data or {})
        if namespace and not body.get("namespace"):
            body["namespace"] = namespace
        res, data = region_api.rollback_tenant_helm_release(region_name, team_name, release_name, body)
        return Response(general_message(200, "success", "回滚成功", bean=data.get("bean")))


class ResourceCenterWorkloadDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, resource, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_resource_center_workload_detail(region_name, team_name, resource, name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class ResourceCenterPodDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, pod_name, *args, **kwargs):
        res, data = region_api.get_resource_center_pod_detail(region_name, team_name, pod_name)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class ResourceCenterEventsView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_resource_center_events(region_name, team_name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class ResourceCenterPodLogsView(TenantHeaderView):
    def get(self, request, team_name, region_name, pod_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        logger.info(
            "resource center pod logs request user_id=%s team=%s region=%s pod=%s params=%s",
            getattr(getattr(request, "user", None), "user_id", ""),
            team_name,
            region_name,
            pod_name,
            params,
        )
        stream = region_api.get_resource_center_pod_log(region_name, team_name, pod_name, params=params)

        logger.info(
            "resource center pod logs upstream connected team=%s region=%s pod=%s "
            "status=%s content_type=%s transfer_encoding=%s",
            team_name,
            region_name,
            pod_name,
            getattr(stream, "status", None),
            getattr(getattr(stream, "headers", None), "get", lambda *x: None)("Content-Type"),
            getattr(getattr(stream, "headers", None), "get", lambda *x: None)("Transfer-Encoding"),
        )

        def iter_stream():
            chunk_count = 0
            try:
                # Flush one SSE comment frame immediately so EventSource can
                # establish the stream even when the workload is currently silent.
                yield b": heartbeat\n\n"
                for chunk in stream.stream(1024):
                    chunk_count += 1
                    if chunk_count == 1:
                        logger.info(
                            "resource center pod logs first chunk team=%s region=%s pod=%s chunk_size=%s",
                            team_name,
                            region_name,
                            pod_name,
                            len(chunk) if chunk else 0,
                        )
                    yield chunk
                logger.info(
                    "resource center pod logs stream completed team=%s region=%s pod=%s chunk_count=%s",
                    team_name,
                    region_name,
                    pod_name,
                    chunk_count,
                )
            except Exception as e:
                logger.exception(
                    "resource center pod logs stream failed team=%s region=%s pod=%s error=%s",
                    team_name,
                    region_name,
                    pod_name,
                    e,
                )
                raise
            finally:
                try:
                    if hasattr(stream, "close"):
                        stream.close()
                except Exception as e:
                    logger.warning(
                        "resource center pod logs stream close failed team=%s region=%s pod=%s error=%s",
                        team_name,
                        region_name,
                        pod_name,
                        e,
                    )

        response = StreamingHttpResponse(iter_stream(), content_type="text/event-stream")
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        response['Content-Encoding'] = 'identity'
        return response


class ResourceCenterWSInfoView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        bean = {
            "event_websocket_url": ws_service.get_event_log_ws(request, region_name),
            "namespace": self.tenant.namespace or self.tenant.tenant_name,
            "tenant_name": self.tenant.tenant_name,
        }
        return Response(general_message(200, "success", "OK", bean=bean))
