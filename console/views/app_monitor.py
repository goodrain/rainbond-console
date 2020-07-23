# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
import logging
from urllib import urlencode

from rest_framework.response import Response

from console.services.app_config import env_var_service
from console.services.group_service import group_service
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

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
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        sufix = get_sufix_path(request.get_full_path())
        try:
            res, body = region_api.get_query_data(self.service.service_region, self.tenant.tenant_name, sufix)
            result = general_message(200, "success", "查询成功", bean=body["data"])
        except Exception as e:
            logger.debug(e)
            result = general_message(200, "success", "查询成功", bean=[])
        return Response(result, status=result["code"])


class AppMonitorQueryRangeView(AppBaseView):
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
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        sufix = get_sufix_path(request.get_full_path())
        try:
            res, body = region_api.get_query_range_data(self.service.service_region, self.tenant.tenant_name, sufix)
            result = general_message(200, "success", "查询成功", bean=body["data"])
        except Exception as e:
            logger.exception(e)
            result = general_message(200, "success", "查询成功", bean=[])
        return Response(result, status=result["code"])


class AppResourceQueryView(AppBaseView):
    def get(self, request, *args, **kwargs):
        """
        组件资源查询
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        data = {"service_ids": [self.service.service_id]}
        body = region_api.get_service_resources(self.tenant.tenant_name, self.service.service_region, data)
        bean = body["bean"]
        result = bean.get(self.service.service_id)
        resource = dict()
        resource["memory"] = result.get("memory", 0) if result else 0
        resource["disk"] = result.get("disk", 0) if result else 0
        resource["cpu"] = result.get("cpu", 0) if result else 0
        result = general_message(200, "success", "查询成功", bean=resource)
        return Response(result, status=result["code"])


class BatchAppMonitorQueryView(RegionTenantHeaderView):
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
        """
        1. 获取组下所有的组件
        2. 查询所有组件对应的pod信息，找出ip信息
        3. 根据pod信息和ip信息 查询出 响应时间和吞吐率
        4. 查询对外的组件的信息
        5. ip信息为public，查询出响应时间和吞吐率
        6. 综合查到的信息，组合为返回参数
        [{"is_web":True,"source":"组件名称","target":"组件名称","data":{"response_time":0.9,"throughput_rate":10}}]
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
        if pod_info_list:
            for pod_info in pod_info_list:
                pod_ip = pod_info["pod_ip"]
                service_id = pod_info["service_id"]
                service = id_service_map.get(service_id, None)
                no_dot_ip = pod_ip.replace(".", "")
                if service:
                    ip_service_map[no_dot_ip] = service
                all_ips.append(no_dot_ip)

        response_time, throughput_rate = self.get_query_statements(service_id_list, all_ips)
        res, response_body = region_api.get_query_data(self.response_region, self.tenant.tenant_name, prefix + response_time)

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
                        result_bean["target"] = target_service.service_id
                        result_bean["source"] = source_service.service_id
                    elif target_service and not source_service:
                        if source == "public":
                            result_bean["is_web"] = True
                            result_bean["target"] = target_service.service_id
                            result_bean["source"] = None
                    else:
                        continue

                    result_bean["data"] = {"response_time": float(r["value"][1]), "throughput_rate": float(t["value"][1])}
                    result_list.append(result_bean)

        result = general_message(200, "success", "成功", list=result_list)

        return Response(result, status=result["code"])

    def get_query_statements(self, service_id_list, all_pod_ips):
        # 响应时间语句： avg(app_client_requesttime{client="17216189100",
        # service_id=~"968f6919a1bb4cc988d48fd4ebf6303f"}) by (service_id,client)
        # 吞吐率 sum(ceil(increase(app_client_request{service_id=~"968f6919a1bb4cc988d48fd4ebf6303f",
        # client=~"17216189100"}[1m])/12)) by (service_id,client)

        query_service_ids = "|".join(service_id_list)
        query_pod_ips = "|".join(all_pod_ips)
        response_time = 'avg(app_client_requesttime{service_id=~"' + query_service_ids + \
            '",client=~"public|' + query_pod_ips + '"}) by (service_id,client)'
        response_time = urlencode({"1": response_time})[2:]

        throughput_rate = 'sum(ceil(increase(app_client_request{service_id=~"' + query_service_ids + \
            '",client=~"public|' + query_pod_ips + '"}[1m])/12)) by (service_id,client)'
        throughput_rate = urlencode({"1": throughput_rate})[2:]
        return response_time, throughput_rate


class AppTraceView(AppBaseView):
    def get(self, request, *args, **kwargs):
        envs = env_var_service.get_all_envs_incloud_depend_env(self.tenant, self.service)
        trace_status = {"collector_host": "", "collector_port": "", "enable_apm": False}
        for env in envs:
            if env.attr_name == "COLLECTOR_TCP_HOST":
                trace_status["collector_host"] = env.attr_value
            if env.attr_name == "COLLECTOR_TCP_PORT":
                trace_status["collector_host"] = env.attr_value
            if env.attr_name == "ES_ENABLE_APM" and env.attr_value == "true":
                trace_status["enable_apm"] = True
        result = general_message(200, "success", "查询成功", bean=trace_status)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        enable_env = env_var_service.get_env_by_attr_name(self.tenant, self.service, "ES_ENABLE_APM")
        if enable_env:
            enable_env.attr_value = "true"
            enable_env.save
        else:
            env_var_service.add_service_env_var(self.tenant, self.service, 0, "ES_ENABLE_APM", "ES_ENABLE_APM", "true", True,
                                                "inner")
            env_var_service.add_service_env_var(self.tenant, self.service, 0, "ES_TRACE_APP_NAME", "ES_TRACE_APP_NAME",
                                                self.service.service_cname, True, "inner")
        result = general_message(200, "success", "设置成功")
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        enable_env = env_var_service.get_env_by_attr_name(self.tenant, self.service, "ES_ENABLE_APM")
        if enable_env:
            env_var_service.delete_env_by_attr_name(self.tenant, self.service, "ES_ENABLE_APM")
        trace_name_env = env_var_service.get_env_by_attr_name(self.tenant, self.service, "ES_TRACE_APP_NAME")
        if trace_name_env:
            env_var_service.delete_env_by_attr_name(self.tenant, self.service, "ES_TRACE_APP_NAME")
        result = general_message(200, "success", "关闭成功")
        return Response(result, status=result["code"])
