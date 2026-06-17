# -*- coding: utf8 -*-
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response
from django.http import HttpResponse

from console.views.base import AlowAnyApiView, EnterpriseAdminView, JWTAuthApiView
from console.services.plugin_service import rbd_plugin_service
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


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
    # 流式代理插件后端 API：支持 SSE / 长响应，转发 body 与请求头（含 Cookie/JWT），
    # 不缓冲、不走 proxy() 的固定 20s 超时。
    def get(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
            **kwargs: Any) -> HttpResponse:
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        return region_api.stream_proxy(request, path, region_name)

    def post(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
             **kwargs: Any) -> HttpResponse:
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        return region_api.stream_proxy(request, path, region_name)

    def put(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
            **kwargs: Any) -> HttpResponse:
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        return region_api.stream_proxy(request, path, region_name)

    def delete(self, request: Request, region_name: str, plugin_name: str, file_path: str, *args: Any,
               **kwargs: Any) -> HttpResponse:
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        return region_api.stream_proxy(request, path, region_name)

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
        return region_api.proxy(request, path, region_name)

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
