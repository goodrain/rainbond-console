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
        resp = region_api.get_proxy(region_name, path)
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
