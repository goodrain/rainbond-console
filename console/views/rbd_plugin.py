# -*- coding: utf8 -*-
from rest_framework.response import Response
from django.http import HttpResponse

from console.views.base import EnterpriseAdminView, JWTAuthApiView
from console.services.plugin_service import rbd_plugin_service
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class RainbondPluginLView(JWTAuthApiView):
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
        plugins, _ = rbd_plugin_service.list_plugins(enterprise_id, region_name)
        return Response(general_message(200, "success", "查询成功", list=plugins))


class RainbondPluginStaticView(JWTAuthApiView):
    def get(self, request, region_name, plugin_name, *args, **kwargs):
        path = "/v2/platform/static/plugins/" + plugin_name
        resp = region_api.get_proxy(region_name, path, check_status=False)
        return HttpResponse(resp, content_type="application/javascript")

class RainbondPluginBackendView(JWTAuthApiView):
    def get(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        resp = region_api.get_proxy(region_name, path)
        return Response(resp)

    def post(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        resp = region_api.post_proxy(region_name, path, request.data)
        return Response(resp)

    def put(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        resp = region_api.put_proxy(region_name, path, request.data)
        return Response(resp)

    def delete(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        path = "/v2/platform/backend/plugins/" + plugin_name + "/" + file_path
        # 传递查询参数
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            path = path + "?" + query_string
        # DELETE 请求可能携带请求体（虽然不常见，但有些 API 需要）
        data = request.data if request.data else None
        resp = region_api.delete_proxy(region_name, path, data)
        return Response(resp)

class RainbondPluginStatusView(EnterpriseAdminView):
    def post(self, request, region_name, plugin_name, *args, **kwargs):
        path = "/v2/platform/plugins/" + plugin_name + "/status"
        resp = region_api.post_proxy(region_name, path, request.data)
        result = general_message(200, "success", "更新成功", bean=resp['bean'], list=resp['list'])
        return Response(result, status=result["code"])

class RainbondOfficialPluginLView(JWTAuthApiView):
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
        plugins, need_authz = rbd_plugin_service.list_plugins(enterprise_id, region_name, official=True)
        return Response(general_message(200, "success", "查询成功", bean={"need_authz": need_authz}, list=plugins))


class RainbondObservablePluginLView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        regions = region_services.get_regions_by_enterprise_id(enterprise_id)
        res = []
        for region in regions:
            plugins = rbd_plugin_service.list_plugins(enterprise_id, region.region_name, official=True)
            for plugin in plugins:
                if plugin["name"] == "observability":
                    res.append({"region_name": region.region_name, "urls": plugin["urls"], "name": "observability"})
                elif plugin["name"] == "rainbond-large-screen":
                    res.append({"region_name": region.region_name, "urls": plugin["urls"], "name": "rainbond-large-screen"})
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

    def _handle_proxy(self, request, region_name, plugin_name, file_path):
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

    def get(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def post(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def put(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def delete(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        return self._handle_proxy(request, region_name, plugin_name, file_path)

    def patch(self, request, region_name, plugin_name, file_path, *args, **kwargs):
        return self._handle_proxy(request, region_name, plugin_name, file_path)
