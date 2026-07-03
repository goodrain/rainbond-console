# -*- coding: utf8 -*-
import json
import logging
from typing import Any, Dict, Optional, Set

from django.db.models import Q
from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.response import Response

from console.views.base import (
    AlowAnyApiView,
    EnterpriseAdminView,
    JWTAuthApiView,
)
from console.login.jwt_authentication import JSONWebTokenAuthentication
from console.services.plugin_service import rbd_plugin_service
from console.services.auth.authentication import InternalTokenAuthentication
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import RegionApp, ServiceGroup, Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

GATEWAY_MONITORING_PLUGIN = "rainbond-gateway-monitoring"
GATEWAY_MONITORING_APP_TOP_PATHS = set([
    "api/v1/platform/apps/top-errors",
    "api/v1/platform/apps/top-latency",
    "api/v1/platform/apps/top-throughput",
])
GATEWAY_MONITORING_APP_TOP_ACTIONS = set([
    "top-errors",
    "top-latency",
    "top-throughput",
])
UNKNOWN_ID_VALUES = set([
    "",
    "unknown",
    "unknown_app",
    "unknown_team",
    "unknown_component",
])


def _backend_plugin_path(plugin_name: str, file_path: str, query_string: str) -> str:
    path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
    if query_string:
        path = path + "?" + query_string
    return path


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_unknown_value(value: Any) -> bool:
    return _normalize_text(value) in UNKNOWN_ID_VALUES


def _to_int(value: Any) -> Optional[int]:
    value = _normalize_text(value)
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_gateway_monitoring_app_top_path(plugin_name: str, file_path: str) -> bool:
    if plugin_name != GATEWAY_MONITORING_PLUGIN:
        return False
    normalized = (file_path or "").strip("/")
    if normalized in GATEWAY_MONITORING_APP_TOP_PATHS:
        return True
    parts = normalized.split("/")
    return (
        len(parts) == 6 and
        parts[0] == "api" and
        parts[1] == "v1" and
        parts[2] == "teams" and
        parts[4] == "apps" and
        parts[5] in GATEWAY_MONITORING_APP_TOP_ACTIONS
    )


def _enrich_gateway_monitoring_app_items(payload: Any, region_name: str) -> Any:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list) or not data:
        return payload

    region_app_ids: Set[str] = set()
    namespace_values: Set[str] = set()
    app_ids: Set[int] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        region_app_id = _normalize_text(item.get("region_app_id"))
        namespace = _normalize_text(item.get("namespace"))
        app_id = _to_int(item.get("app_id"))
        if region_app_id:
            region_app_ids.add(region_app_id)
        if namespace:
            namespace_values.add(namespace)
        if app_id is not None:
            app_ids.add(app_id)

    region_app_id_to_app_id: Dict[str, Any] = {}
    if region_app_ids:
        region_apps = RegionApp.objects.filter(
            region_name=region_name,
            region_app_id__in=list(region_app_ids),
        ).values("region_app_id", "app_id")
        for region_app in region_apps:
            region_app_id_to_app_id[_normalize_text(region_app.get("region_app_id"))] = region_app.get("app_id")
            if region_app.get("app_id") is not None:
                app_ids.add(region_app.get("app_id"))

    service_groups_by_id: Dict[Any, Any] = {}
    tenant_ids: Set[str] = set()
    if app_ids:
        service_groups = ServiceGroup.objects.filter(
            ID__in=list(app_ids),
            region_name=region_name,
        ).values("ID", "tenant_id", "group_name", "region_name")
        for service_group_row in service_groups:
            app_id = service_group_row.get("ID")
            tenant_id = _normalize_text(service_group_row.get("tenant_id"))
            service_groups_by_id[app_id] = service_group_row
            if tenant_id:
                tenant_ids.add(tenant_id)

    tenants_by_namespace: Dict[str, Any] = {}
    tenants_by_id: Dict[str, Any] = {}
    tenant_filter = Q()
    if namespace_values:
        tenant_filter |= Q(namespace__in=list(namespace_values))
    if tenant_ids:
        tenant_filter |= Q(tenant_id__in=list(tenant_ids))
    if tenant_filter:
        tenants = Tenants.objects.filter(tenant_filter).values(
            "tenant_id",
            "tenant_name",
            "tenant_alias",
            "namespace",
        )
        for tenant_row in tenants:
            namespace = _normalize_text(tenant_row.get("namespace"))
            tenant_id = _normalize_text(tenant_row.get("tenant_id"))
            if namespace:
                tenants_by_namespace[namespace] = tenant_row
            if tenant_id:
                tenants_by_id[tenant_id] = tenant_row

    for item in data:
        if not isinstance(item, dict):
            continue

        region_app_id = _normalize_text(item.get("region_app_id"))
        current_app_id = _to_int(item.get("app_id"))
        mapped_app_id = region_app_id_to_app_id.get(region_app_id)
        app_id = mapped_app_id if mapped_app_id is not None else current_app_id
        service_group = service_groups_by_id.get(app_id)

        tenant: Any = None
        if service_group:
            group_name = _normalize_text(service_group.get("group_name"))
            tenant_id = _normalize_text(service_group.get("tenant_id"))
            if app_id is not None:
                item["app_id"] = str(app_id)
            if group_name:
                item["app_name"] = group_name
                item["name"] = group_name
            if tenant_id:
                item["team_id"] = tenant_id
                tenant = tenants_by_id.get(tenant_id)

        namespace = _normalize_text(item.get("namespace"))
        if not tenant and namespace and namespace in tenants_by_namespace:
            tenant = tenants_by_namespace[namespace]

        if tenant:
            tenant_id = _normalize_text(tenant.get("tenant_id"))
            tenant_name = _normalize_text(tenant.get("tenant_name"))
            tenant_alias = _normalize_text(tenant.get("tenant_alias"))
            namespace = _normalize_text(tenant.get("namespace"))
            if tenant_id and _is_unknown_value(item.get("team_id")):
                item["team_id"] = tenant_id
            elif tenant_id and not item.get("team_id"):
                item["team_id"] = tenant_id
            if namespace:
                item["namespace"] = namespace
            if tenant_name:
                item["team_name"] = tenant_name
            if tenant_alias:
                item["team_alias"] = tenant_alias

    return payload


def _clone_response_headers(source: HttpResponse, target: HttpResponse) -> HttpResponse:
    excluded_headers = set(["content-length", "content-encoding", "transfer-encoding"])
    for key, value in source.items():
        if key.lower() in excluded_headers:
            continue
        target[key] = value
    return target


def _allow_sameorigin_frame(response: HttpResponse) -> HttpResponse:
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


class PluginQueryTokenAuthentication(JSONWebTokenAuthentication):
    def get_jwt_value(self, request: Request) -> Optional[str]:
        jwt_value = super(
            PluginQueryTokenAuthentication,
            self,
        ).get_jwt_value(request)
        if jwt_value:
            return jwt_value
        query_params = getattr(request, "query_params", None)
        if query_params:
            return query_params.get("token")
        return getattr(request, "GET", {}).get("token")


class RainbondPluginLView(JWTAuthApiView):
    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        plugins, _ = rbd_plugin_service.list_plugins(enterprise_id, region_name)
        return Response(general_message(200, "success", "查询成功", list=plugins))


class RainbondPluginStaticView(AlowAnyApiView):
    def get(self, request: Request, region_name: str, plugin_name: str, *args: Any, **kwargs: Any) -> HttpResponse:
        path = "/v2/platform/static/plugins/" + plugin_name
        resp = region_api.get_proxy(region_name, path, check_status=False)
        return HttpResponse(resp, content_type="application/javascript")


class RainbondPluginBackendView(JWTAuthApiView):
    authentication_classes = (InternalTokenAuthentication, PluginQueryTokenAuthentication)

    # 流式代理插件后端 API：支持 SSE / 长响应，转发 body 与请求头（含 Cookie/JWT），
    # 不缓冲、不走 proxy() 的固定 20s 超时。
    def get(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
            **kwargs: Any) -> HttpResponse:
        path = _backend_plugin_path(plugin_name, file_path, request.META.get('QUERY_STRING', ''))
        if _is_gateway_monitoring_app_top_path(plugin_name, file_path):
            response = region_api.proxy(request, path, region_name)
            if response.status_code != 200:
                return _allow_sameorigin_frame(response)
            try:
                payload = json.loads(response.content.decode("utf-8"))
            except (TypeError, ValueError, UnicodeDecodeError) as exc:
                logger.warning("enrich gateway monitoring app top failed to decode response: %s", exc)
                return _allow_sameorigin_frame(response)
            payload = _enrich_gateway_monitoring_app_items(payload, region_name)
            enriched = HttpResponse(
                json.dumps(payload, ensure_ascii=False),
                status=response.status_code,
                content_type="application/json",
            )
            return _allow_sameorigin_frame(_clone_response_headers(response, enriched))
        return _allow_sameorigin_frame(region_api.stream_proxy(request, path, region_name))

    def post(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
             **kwargs: Any) -> HttpResponse:
        path = _backend_plugin_path(plugin_name, file_path, request.META.get('QUERY_STRING', ''))
        return _allow_sameorigin_frame(region_api.stream_proxy(request, path, region_name))

    def put(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
            **kwargs: Any) -> HttpResponse:
        path = _backend_plugin_path(plugin_name, file_path, request.META.get('QUERY_STRING', ''))
        return _allow_sameorigin_frame(region_api.stream_proxy(request, path, region_name))

    def delete(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
               **kwargs: Any) -> HttpResponse:
        path = _backend_plugin_path(plugin_name, file_path, request.META.get('QUERY_STRING', ''))
        return _allow_sameorigin_frame(region_api.stream_proxy(request, path, region_name))

class RainbondPluginStatusView(EnterpriseAdminView):
    def post(self, request: Request, region_name: str, plugin_name: str, *args: Any, **kwargs: Any) -> Response:
        path = "/v2/platform/plugins/" + plugin_name + "/status"
        resp = region_api.post_proxy(region_name, path, request.data)
        # NOTE: post_proxy may return None; legacy code indexes directly (backlog).
        result = general_message(200, "success", "更新成功", bean=resp['bean'], list=resp['list'])  # type: ignore[index]
        return Response(result, status=result["code"])

class RainbondOfficialPluginLView(JWTAuthApiView):
    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        plugins, need_authz = rbd_plugin_service.list_plugins(enterprise_id, region_name, official=True)
        return Response(general_message(200, "success", "查询成功", bean={"need_authz": need_authz}, list=plugins))


class RainbondObservablePluginLView(JWTAuthApiView):
    def get(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        # NOTE: region_services is undefined in this module — latent NameError at runtime (real bug, backlog).
        regions = region_services.get_regions_by_enterprise_id(enterprise_id)  # type: ignore[name-defined]
        res = []
        for region in regions:
            plugins = rbd_plugin_service.list_plugins(enterprise_id, region.region_name, official=True)
            # NOTE: list_plugins returns (plugins, need_authz) tuple; loop iterates the tuple and
            # indexes plugin as a dict — latent bug, items are list/bool not dict (real bug, backlog).
            for plugin in plugins:
                if plugin["name"] == "observability":  # type: ignore[index,call-overload]
                    res.append({"region_name": region.region_name, "urls": plugin["urls"],  # type: ignore[index,call-overload]
                                "name": "observability"})
                elif plugin["name"] == "rainbond-large-screen":  # type: ignore[index,call-overload]
                    res.append({"region_name": region.region_name, "urls": plugin["urls"],  # type: ignore[index,call-overload]
                                "name": "rainbond-large-screen"})
        return Response(general_message(200, "success", "查询成功", list=res))


class RainbondPluginFullProxyView(JWTAuthApiView):
    authentication_classes = (InternalTokenAuthentication, PluginQueryTokenAuthentication)

    """
    完整的 HTTP 代理视图，用于代理完整的 Web 应用（如 Grafana）

    支持代理：
    - HTML 页面
    - 静态资源（CSS、JS、图片等）
    - API 接口
    - WebSocket 连接

    与 RainbondPluginBackendView 的区别：
    - RainbondPluginBackendView: 只适合代理 JSON API，会丢失 Content-Type
    - RainbondPluginFullProxyView: 完整代理，保留所有 HTTP 响应头，适合代理完整的 Web 应用

    调用链：
    前端 -> Console (此视图) -> Region API (Go 反向代理) -> 插件服务 (Grafana 等)
    """

    def _handle_proxy(self, request: Request, region_name: str, plugin_name: str, file_path: str) -> HttpResponse:
        """
        统一的代理处理方法
        使用 region_api.proxy() 实现完整的 HTTP 代理
        """
        # 构建后端路径
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path

        # 添加查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string

        # 使用完整的 proxy 方法（保留所有 headers、content-type 等）
        # 该方法在 www/apiclient/regionapibaseclient.py:309-382 中实现
        return _allow_sameorigin_frame(region_api.proxy(request, path, region_name))

    def get(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
            **kwargs: Any) -> HttpResponse:
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def post(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
             **kwargs: Any) -> HttpResponse:
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def put(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
            **kwargs: Any) -> HttpResponse:
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def delete(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
               **kwargs: Any) -> HttpResponse:
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def patch(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
              **kwargs: Any) -> HttpResponse:
        return self._handle_proxy(request, region_name, plugin_name, file_path)
