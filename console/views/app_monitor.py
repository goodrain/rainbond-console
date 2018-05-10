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
from console.services.app_config import port_service

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
        result_list = []
        try:
            """
            1. 获取组下所有的服务
            2. 查询所有服务对应的pod信息，找出ip信息
            3. 根据pod信息和ip信息 查询出 响应时间和吞吐率
            4. 查询对外的服务的信息
            5. ip信息为public，查询出响应时间和吞吐率
            6. 综合查到的信息，组合为返回参数
            [{"is_web":True,"source":"服务名称","target":"服务名称","data":{"response_time":0.9,"throughput_rate":10}}]
            """
            if group_id is None:
                return Response(general_message(400, "group id is none", "请指明要查询的组名称"), status=400)
            prefix = "?query="
            services = group_service.get_group_services(group_id)
            service_id_list = []
            id_service_map = {}
            id_name_map = {}
            for s in services:
                service_id_list.append(s.service_id)
                id_service_map[s.service_id] = s
                id_name_map[s.service_id] = s.service_cname

            pods_info = region_api.get_services_pods(self.response_region, self.tenant.tenant_name, service_id_list,
                                                     self.tenant.enterprise_id)
            pod_info_list = pods_info["list"]
            ip_service_map = {}
            all_ips = []
            for pod_info in pod_info_list:
                pod_ip = pod_info["PodIP"]
                service_id = pod_info["ServiceID"]
                service = id_service_map.get(service_id, None)
                no_dot_ip = pod_ip.replace(".", "")
                if service:
                    ip_service_map[no_dot_ip] = service
                all_ips.append(no_dot_ip)
            response_time, throughput_rate = self.get_query_statements(service_id_list, all_ips)
            try:
                res, response_body = region_api.get_query_data(self.response_region, self.tenant.tenant_name,
                                                               prefix + response_time)

                res, throughput_body = region_api.get_query_data(self.response_region, self.tenant.tenant_name,
                                                                 prefix + throughput_rate)

                response_data = response_body["data"]["result"]
                throughput_data = throughput_body["data"]["result"]

                for r in response_data:
                    res_union_key = r["metric"]["client"] + "+" + r["metric"]["service_id"]
                    for t in throughput_data:
                        thr_union_key = t["metric"]["client"] + "+" + t["metric"]["service_id"]
                        if res_union_key == thr_union_key:
                            result_bean = {"is_web": False}
                            source = res_union_key.split("+")[0]
                            target = res_union_key.split("+")[1]
                            source_service = ip_service_map.get(source, None)
                            target_service = id_service_map.get(target, None)

                            if source_service and target_service:
                                result_bean["target"] = target_service.service_cname
                                result_bean["source"] = source_service.service_cname
                            elif target_service and not source_service:
                                if source == "public":
                                    result_bean["is_web"] = True
                                    result_bean["target"] = target_service.service_cname
                                    result_bean["source"] = None
                            else:
                                continue

                            result_bean["data"] = {"response_time": float(r["value"][1]),
                                                   "throughput_rate": float(t["value"][1])}
                            result_list.append(result_bean)

            except region_api.CallApiError as e:
                logger.exception(e)

            result = general_message(200, "success", "成功", list=result_list)

        except Exception as e:
            logger.exception(e)
            result = general_message(400, e.message, "查询失败")
        return Response(result, status=result["code"])

    def get_query_statements(self, service_id_list, all_pod_ips):
        # 响应时间语句： avg(app_client_requesttime{client="17216189100", service_id=~"968f6919a1bb4cc988d48fd4ebf6303f"}) by (service_id,client)
        # 吞吐率 avg(ceil(increase(app_client_request{service_id=~"968f6919a1bb4cc988d48fd4ebf6303f",client=~"17216189100"}[1m])/12)) by (service_id,client)

        query_service_ids = "|".join(service_id_list)
        query_pod_ips = "|".join(all_pod_ips)
        response_time = 'avg(app_client_requesttime{service_id=~"' + query_service_ids + '",client=~"public|' + query_pod_ips + '"}) by (service_id,client)'
        logger.debug(" 1 ======> raw response_time {0}".format(response_time))
        response_time = urlencode({"1": response_time})[2:]

        throughput_rate = 'avg(ceil(increase(app_client_request{service_id=~"' + query_service_ids + '",client=~"public|' + query_pod_ips + '"}[1m])/12)) by (service_id,client)'
        logger.debug(" 2 ======> raw throughput_rate {0}".format(throughput_rate))
        throughput_rate = urlencode({"1": throughput_rate})[2:]
        return response_time, throughput_rate
