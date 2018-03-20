# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import general_message
import logging
from rest_framework.response import Response

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


def get_sufix_path(full_url):
    """获取get请求参数路径部分的数据"""
    index = full_url.find("?")
    sufix = ""
    if index != -1:
        sufix = full_url[index:]
    return sufix


class AppMonitorQueryView(AppBaseView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        监控信息查询
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        sufix = get_sufix_path(request.get_full_path())
        logger.debug("service.monitor", "{0}".format(sufix))
        try:
            res, body = region_api.get_query_data(self.service.service_region, self.tenant.tenant_name, sufix)
            result = general_message(200, "success", "查询成功", bean=body["data"])
        except Exception as e:
            logger.exception(e)
            result = general_message(400, e.message, "查询失败")
        return Response(result, status=result["code"])


class AppMonitorQueryRangeView(AppBaseView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        监控信息范围查询
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        sufix = get_sufix_path(request.get_full_path())
        logger.debug("service.monitor", "{0}".format(sufix))
        try:
            res, body = region_api.get_query_range_data(self.service.service_region,self.tenant.tenant_name, sufix)
            result = general_message(200, "success", "查询成功", bean=body["data"])
        except Exception as e:
            logger.exception(e)
            result = general_message(400, e.message, "查询失败")
        return Response(result, status=result["code"])


class AppResourceQueryView(AppBaseView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        应用资源查询
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        try:
            data = {"service_ids": [self.service.service_id]}
            body = region_api.get_service_resources(self.tenant.tenant_name, self.service.service_region,
                                                    data)
            bean = body["bean"]
            result = bean.get(self.service.service_id)
            resource = dict()
            resource["memory"] = result.get("memory", 0)
            resource["disk"] = result.get("disk", 0)
            resource["cpu"] = result.get("cpu", 0)
            result = general_message(200, "success", "查询成功", bean=resource)
        except Exception as e:
            logger.exception(e)
            result = general_message(400, e.message, "查询失败")
        return Response(result, status=result["code"])
