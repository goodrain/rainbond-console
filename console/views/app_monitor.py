# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import general_message
import logging
from rest_framework.response import Response
from console.services.group_service import group_service
from urllib import urlencode
import json

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
            res, body = region_api.get_query_range_data(self.service.service_region, self.tenant.tenant_name, sufix)
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


class BatchAppMonitorQueryView(RegionTenantHeaderView):
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
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path

        """
        group_id = kwargs.get("group_id", None)

        try:
            group_id = int(group_id)
            if not group_id:
                return Response(general_message(400, "group id is null", "参数错误"), status=400)
            if group_id == -1:
                return Response(general_message(400, "undefine group", "未分组不能查询"), status=400)
            services = group_service.get_group_services(group_id)
            service_ids = [s.service_id for s in services]
            id_name_map = {s.service_id: s.service_cname for s in services}
            query_service_ids = "|".join(service_ids)
            prefix = "?query="
            # 响应时间
            response_time = 'avg(app_requesttime{mode="avg",service_id=~"'+query_service_ids+'"}) by (service_id)'
            response_time = urlencode({"1": response_time})[2:]
            # 吞吐率
            throughput_rate = 'avg(ceil(delta(app_request{method="total",service_id=~"' + query_service_ids + '"}[1m])/12)) by (service_id)'
            throughput_rate = urlencode({"1": throughput_rate})[2:]
            all_bean = dict()
            try:
                # 响应时间
                res, response_body = region_api.get_query_data(self.response_region, self.tenant.tenant_name, prefix+response_time)
                # 吞吐率
                res, throughput_body = region_api.get_query_data(self.response_region, self.tenant.tenant_name, prefix+throughput_rate)

                response_data = response_body["data"]["result"]
                throughput_data = throughput_body["data"]["result"]
                response_bean = dict()
                for r in response_data:
                    service_id = r["metric"]["service_id"]
                    service_cname = id_name_map[service_id]
                    response_bean[service_cname] = float(r["value"][1])
                throughput_bean = dict()
                for t in throughput_data:
                    service_id = t["metric"]["service_id"]
                    service_cname = id_name_map[service_id]
                    throughput_bean[service_cname] = float(t["value"][1])

                for k, v in response_bean.iteritems():
                    throughput = throughput_bean.get(k, 0)
                    all_bean[k] = {"response_time": v, "throughput_rate": throughput}
                result = general_message(200, "success", "查询成功", bean=all_bean)
            except region_api.CallApiError as ce:
                logger.error("api query error")
                logger.exception(ce)
                result = general_message(400, "api invoke error", "查询失败", bean=all_bean)
            except Exception as oe:
                logger.error("process error")
                logger.exception(oe)
                result = general_message(400, "process error", "系统异常", bean=all_bean)
        except Exception as e:
            logger.exception(e)
            result = general_message(400, e.message, "查询失败")
        return Response(result, status=result["code"])
