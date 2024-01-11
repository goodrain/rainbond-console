# -*- coding: utf8 -*-
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi

from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()

class ProxyPassView(JWTAuthApiView):
    @never_cache
    def post(self, request, *args, **kwargs):
        path = request.get_full_path().replace("/console", "")
        resp = region_api.post_proxy(request.GET.get("region"), path, request.data)
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])
        return Response(result, status=result["code"])

    @never_cache
    def get(self, request, *args, **kwargs):
        path = request.get_full_path().replace("/console", "")
        resp = region_api.get_proxy(request.GET.get("region"), path)
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])
        return Response(result, status=result["code"])
