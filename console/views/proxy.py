# -*- coding: utf8 -*-
import logging

from django.views import View
from django.views.decorators.cache import never_cache

from rest_framework.response import Response

from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi

from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class ProxySSEView(View):
    @never_cache
    def get(self, request, *args, **kwargs):
        path = request.get_full_path().replace("/console/sse", "")
        return region_api.sse_proxy(request.GET.get("region_name"), path)


class ProxyPassView(JWTAuthApiView):
    @never_cache
    def post(self, request, *args, **kwargs):
        path = request.get_full_path().replace("/console", "")
        app_id = request.GET.get("appID")
        region_name = request.GET.get("region_name")
        if app_id and "routes/tcp?" in path:
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
            path = path.replace("appID=" + str(app_id), "appID=" + region_app_id) + "&intID=" + str(app_id)
        resp = region_api.post_proxy(request.GET.get("region_name"), path, request.data)
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])
        return Response(result, status=result["code"])

    @never_cache
    def get(self, request, *args, **kwargs):
        path = request.get_full_path().replace("/console", "")
        resp = region_api.get_proxy(request.GET.get("region_name"), path, app_id=request.GET.get("appID"))
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])
        return Response(result, status=result["code"])

    @never_cache
    def delete(self, request, *args, **kwargs):
        path = request.get_full_path().replace("/console", "")
        resp = region_api.delete_proxy(request.GET.get("region_name"), path)
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])
        return Response(result, status=result["code"])
