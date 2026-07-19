# -*- coding: utf-8 -*-
import logging
from typing import Any, Iterator, Optional

import yaml
from django.http.response import StreamingHttpResponse
from rest_framework.request import Request
from rest_framework.response import Response

from console.repositories.app import service_repo
from console.repositories.helm import helm_repo
from console.repositories.helm_release_source import helm_release_source_repo
from console.services.app_actions import ws_service
from console.services.enterprise_first_deploy_service import enterprise_first_deploy_service
from console.views.base import TenantHeaderView
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


def get_team_resource_namespace(view: Any, fallback: Optional[str] = None) -> Any:
    tenant = getattr(view, "tenant", None)
    if tenant is not None:
        namespace = getattr(tenant, "namespace", None)
        if namespace:
            return namespace
        tenant_name = getattr(tenant, "tenant_name", None)
        if tenant_name:
            return tenant_name
    return fallback


def build_helm_install_body(body: Optional[dict], namespace: Optional[str] = None) -> dict:
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


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value:
            return value
    return ""


def get_request_operator(request: Any) -> Any:
    try:
        user = getattr(request, "user", None)
    except Exception:
        return ""
    return first_non_empty(
        getattr(user, "nick_name", ""),
        getattr(user, "username", ""),
        getattr(user, "user_id", ""),
    )


def normalize_helm_values_yaml(*candidates: Any) -> str:
    for value in candidates:
        if value in (None, ""):
            continue
        if isinstance(value, (dict, list)):
            return yaml.safe_dump(value, default_flow_style=False, allow_unicode=True)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)
    return ""


def build_helm_release_source_info(record: Optional[dict] = None, release: Optional[dict] = None) -> dict:
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


def persist_helm_release_source(request: Any, team_name: str, region_name: str, namespace: Optional[str],
                                raw_body: dict, install_body: dict, response_body: Optional[dict]) -> None:
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


def enrich_helm_release_list(bean: Optional[dict], region_name: str, namespace: Optional[str]) -> Any:
    releases = (bean or {}).get("list") or []
    release_names = [item.get("name") for item in releases if item.get("name")]
    source_map = {}
    try:
        # NOTE: namespace is Optional[str] but repo expects str (systemic mismatch; backlog).
        source_map = helm_release_source_repo.list_by_releases(region_name, namespace, release_names)  # type: ignore[arg-type]
    except Exception as e:
        logger.exception("list helm release source failed: %s", e)
    for item in releases:
        item_namespace = item.get("namespace") or namespace
        key = "{}/{}".format(item_namespace, item.get("name"))
        item["source_info"] = build_helm_release_source_info(source_map.get(key), item)
    return bean


def enrich_helm_release_detail(bean: Optional[dict], region_name: str, namespace: Optional[str],
                               release_name: str) -> Any:
    summary = ((bean or {}).get("summary")) or {}
    item_namespace = summary.get("namespace") or namespace
    record = None
    try:
        record = helm_release_source_repo.get_by_release(region_name, item_namespace, release_name)  # type: ignore[arg-type]
    except Exception as e:
        logger.exception("get helm release source failed: %s", e)
    values_yaml = normalize_helm_values_yaml((record or {}).get("values_yaml"))
    if values_yaml:
        summary["values"] = values_yaml
    summary["source_info"] = build_helm_release_source_info(record, summary)
    # NOTE: bean may be None; indexed assignment is a latent risk (backlog).
    bean["summary"] = summary  # type: ignore[index]
    return bean


class NsResourceTypesView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        res, data = region_api.get_tenant_ns_resource_types(region_name, team_name)
        # NOTE: region API result may be None; .get access is a latent risk (backlog).
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class NsResourcesView(TenantHeaderView):
    @staticmethod
    def _ns_resource_source(params: dict) -> str:
        return str(params.get("source") or "").strip().lower()

    def _build_ns_resource_tracker(self,
                                   request: Request,
                                   params: dict,
                                   team_name: str,
                                   region_name: str) -> Optional[dict]:
        try:
            source = self._ns_resource_source(params)
            deploy_type = (
                enterprise_first_deploy_service.DEPLOY_TYPE_YAML
                if source == "yaml" else enterprise_first_deploy_service.DEPLOY_TYPE_K8S_RESOURCE)
            source_language = "yaml" if deploy_type == enterprise_first_deploy_service.DEPLOY_TYPE_YAML else "k8s-resource"
            trigger = (
                "ns_resource_yaml_create"
                if deploy_type == enterprise_first_deploy_service.DEPLOY_TYPE_YAML else "ns_resource_create")
            workload_context = enterprise_first_deploy_service.build_k8s_resource_workload_context(
                self._decode_request_body(request.body))
            workload_context["source_type"] = (
                "yaml" if deploy_type == enterprise_first_deploy_service.DEPLOY_TYPE_YAML else "k8s_resource")
            return enterprise_first_deploy_service.safe_begin_deploy_tracking(
                enterprise_id=getattr(self.tenant, "enterprise_id", ""),
                tenant_name=getattr(self.tenant, "tenant_name", "") or team_name,
                region_name=region_name,
                deploy_type=deploy_type,
                operator=get_request_operator(request),
                source_language=source_language,
                trigger=trigger,
                app_context={"component_count": 0},
                workload_context=workload_context)
        except Exception as exc:
            logger.debug("begin ns resource deploy diagnostic tracking failed: %s", exc)
            return None

    @staticmethod
    def _decode_request_body(body: Any) -> Any:
        if isinstance(body, bytes):
            return body.decode("utf-8", "ignore")
        return body

    @staticmethod
    def _ns_resource_failure_reason(data: Any, status_code: int) -> str:
        body = data or {}
        bean = ((body.get("data") or {}).get("bean") or {}) if isinstance(body, dict) else {}
        summary = bean.get("summary") or {}
        if isinstance(summary, dict):
            failure_count = summary.get("failure_count") or 0
            partial_success = bool(summary.get("partial_success"))
            if failure_count or partial_success:
                return body.get("msg_show") or body.get("msg") or "K8S 资源部分创建失败"
        if status_code < 200 or status_code >= 300:
            if not isinstance(body, dict):
                return "K8S 资源创建失败"
            return body.get("msg_show") or body.get("msg") or "K8S 资源创建失败"
        return ""

    def get(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resources(region_name, team_name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]

    def post(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        content_type = request.META.get("CONTENT_TYPE")
        tracker = self._build_ns_resource_tracker(request, params, team_name, region_name)
        try:
            res, data = region_api.post_tenant_ns_resource(
                region_name, team_name, request.body, params=params, content_type=content_type)
        except Exception as exc:
            enterprise_first_deploy_service.safe_mark_failure(
                tracker, reason=str(exc), failure_stage=enterprise_first_deploy_service.FAILURE_STAGE_PREFLIGHT)
            raise
        status_code = getattr(res, "status", 200)
        failure_reason = self._ns_resource_failure_reason(data, status_code)
        if failure_reason:
            enterprise_first_deploy_service.safe_mark_failure(
                tracker,
                reason=failure_reason,
                failure_stage=enterprise_first_deploy_service.FAILURE_STAGE_PREFLIGHT)
        else:
            enterprise_first_deploy_service.safe_mark_success(tracker)
        return Response(data, status=status_code)


class TeamComponentsView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        components = service_repo.list_basic_infos_by_team_and_region(self.tenant.tenant_id, region_name)
        return Response(general_message(200, "success", "OK", list=components))


class NsResourceDetailView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]

    def put(self, request: Request, team_name: str, region_name: str, name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        content_type = request.META.get("CONTENT_TYPE")
        res, data = region_api.put_tenant_ns_resource(
            region_name, team_name, name, request.body, params=params, content_type=content_type)
        return Response(general_message(200, "success", "更新成功", bean=data.get("bean")))  # type: ignore[union-attr]

    def delete(self, request: Request, team_name: str, region_name: str, name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        region_api.delete_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "删除成功"))


class HelmReleasesView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        namespace = get_team_resource_namespace(self, team_name)
        res, data = region_api.get_tenant_helm_releases(region_name, team_name, namespace=namespace)
        bean = enrich_helm_release_list(data.get("bean") or {}, region_name, namespace)  # type: ignore[union-attr]
        return Response(general_message(200, "success", "OK", bean=bean))

    def post(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        namespace = get_team_resource_namespace(self, team_name)
        raw_body = dict(request.data or {})
        body = build_helm_install_body(raw_body, namespace=namespace)
        res, data = region_api.install_tenant_helm_release(region_name, team_name, body)
        try:
            persist_helm_release_source(
                request, team_name, region_name, namespace,
                raw_body, body, data.get("bean") or {})  # type: ignore[union-attr]
        except Exception as e:
            logger.exception("persist helm release source failed: %s", e)
        return Response(general_message(200, "success", "安装成功", bean=data.get("bean")))  # type: ignore[union-attr]


class HelmChartPreviewView(TenantHeaderView):
    def post(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        namespace = get_team_resource_namespace(self, team_name)
        body = build_helm_install_body(request.data or {}, namespace=namespace)
        res, data = region_api.preview_tenant_helm_chart(region_name, team_name, body)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class HelmReleaseDetailView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, release_name: str, *args: Any, **kwargs: Any) -> Response:
        namespace = get_team_resource_namespace(self, team_name)
        res, data = region_api.get_tenant_helm_release_detail(region_name, team_name, release_name, namespace=namespace)
        bean = enrich_helm_release_detail(
            data.get("bean") or {}, region_name, namespace, release_name)  # type: ignore[union-attr]
        return Response(general_message(200, "success", "OK", bean=bean))

    def put(self, request: Request, team_name: str, region_name: str, release_name: str, *args: Any, **kwargs: Any) -> Response:
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
        return Response(general_message(200, "success", "升级成功", bean=data.get("bean")))  # type: ignore[union-attr]

    def delete(self, request: Request, team_name: str, region_name: str, release_name: str, *args: Any,
               **kwargs: Any) -> Response:
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
    def get(self, request: Request, team_name: str, region_name: str, release_name: str, *args: Any, **kwargs: Any) -> Response:
        namespace = get_team_resource_namespace(self, team_name)
        res, data = region_api.get_tenant_helm_release_history(region_name, team_name, release_name, namespace=namespace)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class HelmReleaseRollbackView(TenantHeaderView):
    def post(self, request: Request, team_name: str, region_name: str, release_name: str, *args: Any, **kwargs: Any) -> Response:
        namespace = get_team_resource_namespace(self, team_name)
        body = dict(request.data or {})
        if namespace and not body.get("namespace"):
            body["namespace"] = namespace
        res, data = region_api.rollback_tenant_helm_release(region_name, team_name, release_name, body)
        return Response(general_message(200, "success", "回滚成功", bean=data.get("bean")))  # type: ignore[union-attr]


class ResourceCenterWorkloadDetailView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, resource: str, name: str, *args: Any,
            **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_resource_center_workload_detail(region_name, team_name, resource, name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class ResourceCenterPodDetailView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, pod_name: str, *args: Any,
            **kwargs: Any) -> Response:
        res, data = region_api.get_resource_center_pod_detail(region_name, team_name, pod_name)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class ResourceCenterEventsView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_resource_center_events(region_name, team_name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class ResourceCenterPodLogsView(TenantHeaderView):
    def get(self, request: Request, team_name: str, region_name: str, pod_name: str, *args: Any,
            **kwargs: Any) -> StreamingHttpResponse:
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

        def iter_stream() -> Iterator[Any]:
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
    def get(self, request: Request, team_name: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        bean = {
            "event_websocket_url": ws_service.get_event_log_ws(request, region_name),
            "namespace": self.tenant.namespace or self.tenant.tenant_name,
            "tenant_name": self.tenant.tenant_name,
        }
        return Response(general_message(200, "success", "OK", bean=bean))
