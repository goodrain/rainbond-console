# -*- coding: utf8 -*-
"""
  Created by leon on 19/2/13.
"""
import base64
import logging
import os
import pickle

from console.exception.bcode import ErrK8sComponentNameExists
from console.exception.main import ServiceHandleException
from console.repositories.app_config import service_endpoints_repo
from console.repositories.deploy_repo import deploy_repo
from console.services.app import app_service
from console.services.app_config import endpoint_service, port_service
from console.services.group_service import group_service
from console.utils.validation import (validate_endpoint_address, validate_endpoints_info)
from console.views.app_config.base import AppBaseView
from console.views.base import AlowAnyApiView, RegionTenantHeaderView
from django.db.transaction import atomic
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants, TenantServiceInfo
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class ThirdPartyServiceCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        创建第三方组件

        """

        group_id = request.data.get("group_id", -1)
        service_cname = request.data.get("service_cname", None)
        static = request.data.get("static", None)
        endpoints_type = request.data.get("endpoints_type", None)
        service_name = request.data.get("serviceName", "")
        k8s_component_name = request.data.get("k8s_component_name", "")
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            raise ErrK8sComponentNameExists
        if not service_cname:
            return Response(general_message(400, "service_cname is null", "组件名未指明"), status=400)
        if endpoints_type == "static":
            validate_endpoints_info(static)
        source_config = {}
        if endpoints_type == "kubernetes":
            if not service_name:
                return Response(general_message(400, "kubernetes service name is null", "Kubernetes Service名称必须指定"), status=400)
            source_config = {"service_name": service_name, "namespace": request.data.get("namespace", "")}
        new_service = app_service.create_third_party_app(
            self.response_region,
            self.tenant,
            self.user,
            service_cname,
            static,
            endpoints_type,
            source_config,
            k8s_component_name=k8s_component_name)
        # 添加组件所在组
        code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id, new_service.service_id)
        if code != 200:
            new_service.delete()
            raise ServiceHandleException(
                msg="add component to app failure", msg_show=msg_show, status_code=code, error_code=code)
        bean = new_service.to_dict()
        if endpoints_type == "api":
            # 生成秘钥
            deploy = deploy_repo.get_deploy_relation_by_service_id(service_id=new_service.service_id)
            api_secret_key = pickle.loads(base64.b64decode(deploy)).get("secret_key")
            # 从环境变量中获取域名，没有在从请求中获取
            host = os.environ.get('DEFAULT_DOMAIN', "http://" + request.get_host())
            api_url = host + "/console/" + "third_party/{0}".format(new_service.service_id)
            bean["api_service_key"] = api_secret_key
            bean["url"] = api_url
            service_endpoints_repo.create_api_endpoints(self.tenant, new_service)

        result = general_message(200, "success", "创建成功", bean=bean)
        return Response(result, status=result["code"])


def check_endpoints(endpoints):
    if not endpoints:
        return ["parameter error"], False
    total_errs = []
    is_domain = False
    for endpoint in endpoints:
        # TODO: ipv6
        if "https://" in endpoint:
            endpoint = endpoint.partition("https://")[2]
        if "http://" in endpoint:
            endpoint = endpoint.partition("http://")[2]
        if ":" in endpoint:
            endpoint = endpoint.rpartition(":")[0]
        errs, domain_ip = validate_endpoint_address(endpoint)
        if domain_ip:
            is_domain = True
        total_errs.extend(errs)
    if len(endpoints) > 1 and is_domain:
        logger.error("endpoint: {}; do not support multi domain endpoint".format(endpoint))
        return ["do not support multi domain endpoint"], is_domain
    elif len(endpoints) == 1 and is_domain:
        return [], is_domain
    else:
        return total_errs, False


# 第三方组件中api注册方式回调接口
class ThirdPartyServiceApiView(AlowAnyApiView):
    """
    获取实例endpoint列表
    """

    def get(self, request, service_id, *args, **kwargs):
        secret_key = request.GET.get("secret_key")
        # 加密
        deploy_key = deploy_repo.get_secret_key_by_service_id(service_id=service_id)
        deploy_key_decode = pickle.loads(base64.b64decode(deploy_key)).get("secret_key")

        if secret_key != deploy_key_decode:
            result = general_message(400, "failed", "密钥错误")
            return Response(result, status=400)

        service_obj = TenantServiceInfo.objects.get(service_id=service_id)
        tenant_obj = Tenants.objects.get(tenant_id=service_obj.tenant_id)

        res, body = region_api.get_third_party_service_pods(service_obj.service_region, tenant_obj.tenant_name,
                                                            service_obj.service_alias)

        if res.status != 200:
            return Response(general_message(412, "region error", "数据中心查询失败"), status=412)

        endpoint_list = []
        for item in body["list"]:
            endpoint = item
            endpoint["ip"] = item["address"]
            endpoint_list.append(endpoint)
        bean = {"endpoint_num": len(endpoint_list)}

        result = general_message(200, "success", "查询成功", list=endpoint_list, bean=bean)
        return Response(result, status=result["code"])

    # 修改实例endpoint
    def put(self, request, service_id, *args, **kwargs):
        secret_key = request.data.get("secret_key")
        # 加密
        deploy_key = deploy_repo.get_secret_key_by_service_id(service_id=service_id)
        deploy_key_decode = pickle.loads(base64.b64decode(deploy_key)).get("secret_key")
        if secret_key != deploy_key_decode:
            result = general_message(400, "failed", "密钥错误")
            return Response(result, status=400)
        address = request.data.get("ip", None)
        # is_online true为上线，false为下线
        is_online = request.data.get("is_online", True)
        if type(is_online) != bool:
            return Response(general_message(400, "is_online type error", "参数类型错误"), status=400)
        if not address:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        try:
            service_obj = TenantServiceInfo.objects.get(service_id=service_id)
            tenant_obj = Tenants.objects.get(tenant_id=service_obj.tenant_id)
            endpoint_dict = dict()
            endpoint_dict["address"] = address
            endpoint_dict["is_online"] = is_online
            # 根据ip从数据中心查询， 有就put，没有就post
            res, body = region_api.get_third_party_service_pods(service_obj.service_region, tenant_obj.tenant_name,
                                                                service_obj.service_alias)

            if res.status != 200:
                return Response(general_message(412, "region error", "数据中心查询失败"), status=412)

            endpoint_list = body["list"]
            # 添加
            if not endpoint_list:
                res, body = region_api.post_third_party_service_endpoints(service_obj.service_region, tenant_obj.tenant_name,
                                                                          service_obj.service_alias, endpoint_dict)
                if res.status != 200:
                    return Response(general_message(412, "region error", "数据中心添加失败"), status=412)
                return Response(general_message(200, "success", "修改成功"))
            addresses = []
            for endpoint in endpoint_list:
                addresses.append(endpoint["address"])
            addr_list = [addr for addr in addresses]
            addr_list.append(address)
            errs, _ = check_endpoints(addr_list)
            if len(errs) > 0:
                return Response(general_message(400, "do not allow multi domain endpoints", "不允许添加多个域名组件实例地址"), status=400)
            if address not in addresses:
                # 添加
                res, body = region_api.post_third_party_service_endpoints(service_obj.service_region, tenant_obj.tenant_name,
                                                                          service_obj.service_alias, endpoint_dict)
                if res.status != 200:
                    return Response(general_message(412, "region error", "数据中心添加失败"), status=412)
                return Response(general_message(200, "success", "修改成功"))
            # 修改
            for endpoint in endpoint_list:
                if endpoint["address"] == address:
                    bean = dict()
                    bean["ep_id"] = endpoint["ep_id"]
                    bean["is_online"] = is_online
                    res, body = region_api.put_third_party_service_endpoints(service_obj.service_region, tenant_obj.tenant_name,
                                                                             service_obj.service_alias, bean)
                    if res.status != 200:
                        return Response(general_message(412, "region error", "数据中心修改失败"), status=412)

                    result = general_message(200, "success", "修改成功")
                    return Response(result, status=200)
        except region_api.CallApiFrequentError as e:
            logger.exception(e)
            return 409, "操作过于频繁，请稍后再试"

    # 删除实例endpoint
    def delete(self, request, service_id, *args, **kwargs):
        secret_key = request.data.get("secret_key")
        # 加密
        deploy_key = deploy_repo.get_secret_key_by_service_id(service_id=service_id)
        deploy_key_decode = pickle.loads(base64.b64decode(deploy_key)).get("secret_key")
        if secret_key != deploy_key_decode:
            result = general_message(400, "failed", "密钥错误")
            return Response(result, status=400)
        address = request.data.get("ip", None)
        if not address:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        service_obj = TenantServiceInfo.objects.get(service_id=service_id)
        tenant_obj = Tenants.objects.get(tenant_id=service_obj.tenant_id)
        # 查询
        res, body = region_api.get_third_party_service_pods(service_obj.service_region, tenant_obj.tenant_name,
                                                            service_obj.service_alias)

        if res.status != 200:
            return Response(general_message(412, "region error", "数据中心查询失败"), status=412)

        endpoint_list = body["list"]
        if not endpoint_list:
            return Response(general_message(412, "ip is null", "ip不存在"), status=412)
        addresses = []
        for endpoint in endpoint_list:
            addresses.append(endpoint["address"])
        if address not in addresses:
            return Response(general_message(412, "ip is null", "ip不存在"), status=412)
        for endpoint in endpoint_list:
            if endpoint["address"] == address:
                endpoint_dict = dict()
                endpoint_dict["ep_id"] = endpoint["ep_id"]
                res, body = region_api.delete_third_party_service_endpoints(service_obj.service_region, tenant_obj.tenant_name,
                                                                            service_obj.service_alias, endpoint_dict)
                if res.status != 200:
                    return Response(general_message(412, "region error", "数据中心删除失败"), status=412)

        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])


# 第三方组件中api注册方式重置秘钥
class ThirdPartyUpdateSecretKeyView(AppBaseView):
    @never_cache
    def put(self, request, *args, **kwargs):
        key_repo = deploy_repo.get_service_key_by_service_id(service_id=self.service.service_id)
        if not key_repo:
            return Response(general_message(412, "service_key is null", "秘钥不存在"), status=412)
        key_repo.delete()
        # 生成秘钥
        deploy = deploy_repo.get_deploy_relation_by_service_id(service_id=self.service.service_id)
        api_secret_key = pickle.loads(base64.b64decode(deploy)).get("secret_key")
        result = general_message(200, "success", "重置成功", bean={"api_service_key": api_secret_key})
        return Response(result)


# 第三方组件pod信息
class ThirdPartyAppPodsView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取第三方组件实例信息
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
        res, body = region_api.get_third_party_service_pods(self.service.service_region, self.tenant.tenant_name,
                                                            self.service.service_alias)
        if res.status != 200:
            return Response(general_message(412, "region error", "数据中心查询失败"), status=412)
        endpoint_list = body["list"]
        for endpoint in endpoint_list:
            endpoint["ip"] = endpoint["address"]
        bean = {"endpoint_num": len(endpoint_list)}

        result = general_message(200, "success", "查询成功", list=endpoint_list, bean=bean)
        return Response(result)

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        添加endpoint实例
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        address = request.data.get("ip", None)
        if not address:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        validate_endpoints_info([address])
        endpoint_service.add_endpoint(self.tenant, self.service, address)

        result = general_message(200, "success", "添加成功")
        return Response(result)

    @never_cache
    @atomic
    def delete(self, request, *args, **kwargs):
        """
        删除endpoint实例
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        ep_id = request.data.get("ep_id", None)
        if not ep_id:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        endpoint_dict = dict()
        endpoint_dict["ep_id"] = ep_id
        res, body = region_api.delete_third_party_service_endpoints(self.response_region, self.tenant.tenant_name,
                                                                    self.service.service_alias, endpoint_dict)
        res, new_body = region_api.get_third_party_service_pods(self.service.service_region, self.tenant.tenant_name,
                                                                self.service.service_alias)
        new_endpoint_list = new_body.get("list", [])
        new_endpoints = [endpoint.address for endpoint in new_endpoint_list]
        service_endpoints_repo.update_or_create_endpoints(self.tenant, self.service, new_endpoints)
        logger.debug('-------res------->{0}'.format(res))
        logger.debug('=======body=======>{0}'.format(body))

        if res.status != 200:
            return Response(general_message(412, "region delete error", "数据中心删除失败"), status=412)
        # service_endpoints_repo.delete_service_endpoints_by_service_id(self.service.service_id)
        result = general_message(200, "success", "删除成功")
        return Response(result)

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改实例上下线
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        ep_id = request.data.get("ep_id", None)
        if not ep_id:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        # 上线操作需要端口开启状态
        tenant_service_ports = port_service.get_service_ports(self.service)
        open_list = []
        if tenant_service_ports:
            for port in tenant_service_ports:
                if port.is_outer_service or port.is_inner_service:
                    open_list.append("1")

        if "1" not in open_list:
            return Response(general_message(200, "port is closed", "端口未开启", bean={"port_closed": True}), status=200)

        endpoint_dict = dict()
        endpoint_dict["ep_id"] = ep_id

        res, body = region_api.put_third_party_service_endpoints(self.response_region, self.tenant.tenant_name,
                                                                 self.service.service_alias, endpoint_dict)
        if res.status != 200:
            return Response(general_message(412, "region delete error", "数据中心修改失败"), status=412)

        result = general_message(200, "success", "修改成功")
        return Response(result)


# 第三方组件健康检测
class ThirdPartyHealthzView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取第三方组件健康检测结果
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        res, body = region_api.get_third_party_service_health(self.service.service_region, self.tenant.tenant_name,
                                                              self.service.service_alias)
        if res.status != 200:
            return Response(general_message(412, "region error", "数据中心查询失败"), status=412)
        bean = body["bean"]
        if not bean:
            return Response(general_message(200, "success", "查询成功"))
        result = general_message(200, "success", "查询成功", bean=bean)
        return Response(result)

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        编辑第三方组件的健康检测
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        scheme = request.data.get("scheme", None)
        port = request.data.get("port", 0)
        time_interval = request.data.get("time_interval", 0)
        max_error_num = request.data.get("max_error_num", 0)
        action = request.data.get("action", None)
        path = request.data.get("path", None)
        if not scheme:
            return Response(general_message(400, "model is null", "检测方式未指明"), status=400)
        if not port:
            return Response(general_message(400, "address is null", "端口未指明"), status=400)
        detection_dict = {
            "scheme": scheme,
            "port": port,
            "time_interval": time_interval,
            "max_error_num": max_error_num,
            "action": action if action else '',
            "path": path if path else ''
        }

        res, body = region_api.put_third_party_service_health(self.service.service_region, self.tenant.tenant_name,
                                                              self.service.service_alias, detection_dict)
        if res.status != 200:
            return Response(general_message(412, "region error", "数据中心修改失败"), status=412)

        result = general_message(200, "success", "修改成功")
        return Response(result)
