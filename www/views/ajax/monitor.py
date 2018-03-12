# -*- coding: utf8 -*-
"""
  Created on 18/1/11.
"""
from django.http import JsonResponse

from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.views import AuthedView
import logging
from www.utils.return_message import general_message, error_message

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


def get_sufix_path(full_url):
    """获取get请求参数路径部分的数据"""
    index = full_url.find("?")
    sufix = ""
    if index != -1:
        sufix = full_url[index:]
    return sufix


class QueryMonitorView(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        sufix = get_sufix_path(request.get_full_path())
        region = self.request.COOKIES.get('region')
        try:
            res, body = region_api.get_query_data(region,self.tenantName, sufix)
            result = general_message(200, "success", "查询成功", bean=body["data"])
        except Exception as e:
            logger.exception(e)
            result = general_message(400,"query error","查询一次")
        return JsonResponse(result, status=result["code"])


class QueryRangeMonitorView(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        sufix = get_sufix_path(request.get_full_path())
        region = self.request.COOKIES.get('region')
        try:
            res, body = region_api.get_query_range_data(region,self.tenantName, sufix)
            result = general_message(200, "success", "查询成功", bean=body["data"])
        except Exception as e:
            logger.exception(e)
            result = general_message(400,"query error","查询一次")
        return JsonResponse(result, status=result["code"])
