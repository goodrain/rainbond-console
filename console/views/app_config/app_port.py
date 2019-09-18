# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.forms.models import model_to_dict
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.repositories.app_config import port_repo
from console.services.app_config import domain_service
from console.services.app_config import port_service
from console.views.app_config.base import AppBaseView
from www.decorator import perm_required
from www.utils.return_message import error_message
from www.utils.return_message import general_message
from console.utils.validation import validate_endpoint_address
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppPortView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务的端口信息
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
            tenant_service_ports = port_service.get_service_ports(self.service)
            port_list = []
            for port in tenant_service_ports:
                port_info = port.to_dict()
                variables = port_service.get_port_variables(
                    self.tenant, self.service, port)
                port_info["environment"] = variables["environment"]
                outer_url = ""
                inner_url = ""

                if port_info["environment"]:
                    if port.is_inner_service:
                        try:
                            inner_url = "{0}:{1}".format(port_info["environment"][0].get("value"),
                                                         port_info["environment"][1].get("value"))
                        except Exception as se:
                            logger.exception(se)
                port_info["inner_url"] = inner_url
                outer_service = variables.get("outer_service", None)
                if outer_service:
                    outer_url = "{0}:{1}".format(
                        variables["outer_service"]["domain"], variables["outer_service"]["port"])
                port_info["outer_url"] = outer_url
                port_info["bind_domains"] = []
                bind_domains = domain_service.get_port_bind_domains(
                    self.service, port.container_port)
                if bind_domains:
                    for bind_domain in bind_domains:
                        if not bind_domain.domain_path:
                            bind_domain.domain_path = '/'
                            bind_domain.save()
                port_info["bind_domains"] = [domain.to_dict()
                                             for domain in bind_domains]
                bind_tcp_domains = domain_service.get_tcp_port_bind_domains(
                    self.service, port.container_port)

                if bind_tcp_domains:
                    port_info["bind_tcp_domains"] = [domain.to_dict()
                                                     for domain in bind_tcp_domains]
                else:
                    port_info["bind_tcp_domains"] = []
                port_list.append(port_info)
            result = general_message(200, "success", "查询成功", list=port_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def post(self, request, *args, **kwargs):
        """
        为应用添加端口
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
            - name: port
              description: 端口
              required: true
              type: integer
              paramType: form
            - name: protocol
              description: 端口协议
              required: true
              type: string
              paramType: form
            - name: port_alias
              description: 端口别名
              required: true
              type: string
              paramType: form
            - name: is_inner_service
              description: 是否打开对内服务
              required: true
              type: boolean
              paramType: form
            - name: is_outer_service
              description: 是否打开对外服务
              required: true
              type: boolean
              paramType: form

        """
        port = request.data.get("port", None)
        protocol = request.data.get("protocol", None)
        port_alias = request.data.get("port_alias", None)
        is_inner_service = request.data.get('is_inner_service', False)
        is_outer_service = request.data.get('is_outer_service', False)
        try:
            if not port:
                return Response(general_message(400, "params error", u"缺少端口参数"), status=400)
            if not protocol:
                return Response(general_message(400, "params error", u"缺少协议参数"), status=400)
            if not port_alias:
                port_alias = self.service.service_alias.upper().replace("-", "_") + str(port)
            code, msg, port_info = port_service.add_service_port(self.tenant, self.service, port, protocol, port_alias,
                                                                 is_inner_service, is_outer_service)
            if code != 200:
                return Response(general_message(code, "add port error", msg), status=code)

            result = general_message(
                200, "success", "端口添加成功", bean=model_to_dict(port_info))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppPortManageView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        查看应用的某个端口的详情
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
            - name: port
              description: 端口号
              required: true
              type: string
              paramType: path

        """
        container_port = kwargs.get("port", None)
        if not container_port:
            return Response(general_message(400, "container_port not specify", u"端口变量名未指定"), status=400)
        try:
            port_info = port_service.get_service_port_by_port(
                self.service, int(container_port))

            variables = port_service.get_port_variables(
                self.tenant, self.service, port_info)
            bean = {"port": model_to_dict(port_info)}
            bean.update(variables)
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def delete(self, request, *args, **kwargs):
        """
        删除应用的某个端口
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
            - name: port
              description: 端口号
              required: true
              type: string
              paramType: path

        """
        container_port = kwargs.get("port", None)
        if not container_port:
            return Response(general_message(400, "container_port not specify", u"端口变量名未指定"), status=400)
        code, msg, data = port_service.delete_port_by_container_port(
            self.tenant, self.service, int(container_port))
        if code != 200:
            return Response(general_message(code, "delete port fail", msg), status=code)
        result = general_message(
            200, "success", "删除成功", bean=model_to_dict(data))
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        修改应用的某个端口（打开|关闭|修改协议|修改环境变量）
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
            - name: port
              description: 端口号
              required: true
              type: string
              paramType: path
            - name: action
              description: 操作类型（open_outer|close_outer|open_inner|close_inner|change_protocol|change_port_alias）
              required: true
              type: string
              paramType: form
            - name: port_alias
              description: 端口别名(修改端口别名时必须)
              required: false
              type: string
              paramType:
            - name: protocol
              description: 端口协议(修改端口协议时必须)
              required: false
              type: string
              paramType: path

        """
        container_port = kwargs.get("port", None)
        action = request.data.get("action", None)
        port_alias = request.data.get("port_alias", None)
        protocol = request.data.get("protocol", None)
        if not container_port:
            return Response(general_message(400, "container_port not specify", u"端口变量名未指定"), status=400)
        if self.service.service_source == "third_party" and ("outer" in action):
            try:
                res, body = region_api.get_third_party_service_pods(self.service.service_region, self.tenant.tenant_name,
                                                                    self.service.service_alias)
                if res.status != 200:
                    return Response(general_message(412, "region error", "数据中心查询失败"), status=412)
                endpoint_list = body["list"]
                for endpoint in endpoint_list:
                    if "https://" in endpoint:
                        endpoint = endpoint.partition("https://")[2]
                    if "http://" in endpoint:
                        endpoint = endpoint.partition("http://")[2]
                    if ":" in endpoint:
                        endpoint = endpoint.rpartition(":")[0]
                    errs = validate_endpoint_address(endpoint.address)
                    if len(errs) > 0:
                        return Response(general_message(
                            400, "do not allow operate outer port for domain endpoints", "不允许开启域名服务实例对外端口"), status=400)
            except Exception as e:
                logger.exception(e)
                result = error_message(e.message)
                return Response(result, status=result["code"])
        try:
            code, msg, data = port_service.manage_port(self.tenant, self.service, self.response_region, int(container_port),
                                                       action, protocol, port_alias)
            if code != 200:
                return Response(general_message(code, "change port fail", msg), status=code)
            result = general_message(
                200, "success", "操作成功", bean=model_to_dict(data))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppTcpOuterManageView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取当前可修改的tcp端口信息
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
            - name: port
              description: 端口号
              required: true
              type: string
              paramType: path
        """
        try:
            tcp_outer_ports = port_service.get_team_region_usable_tcp_ports(
                self.tenant, self.service)

            port_list = []
            for p in tcp_outer_ports:
                port_list.append({"service_id": p.service_id,
                                  "lb_mpping_port": p.lb_mapping_port})
            result = general_message(200, "success", "查询成功", list=port_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        修改负载均衡端口
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
            - name: lb_mapping_port
              description: 需要修改的负载均衡端口
              required: true
              type: integer
              paramType: form
            - name: service_id
              description: 需要修改的负载均衡端口对应的服务ID
              required: true
              type: integer
              paramType: form

        """
        container_port = kwargs.get("port", None)
        lb_mapping_port = request.data.get("lb_mapping_port", None)
        mapping_service_id = request.data.get("service_id", None)
        try:
            container_port = int(container_port)
            lb_mapping_port = int(lb_mapping_port)
            if not container_port:
                return Response(general_message(400, "params error", u"缺少端口参数"), status=400)
            if not lb_mapping_port:
                return Response(general_message(400, "params error", u"缺少需要修改的负载均衡端口参数"), status=400)
            if not mapping_service_id:
                return Response(general_message(400, "params error", u"缺少端口对应的服务ID"), status=400)
            code, msg = port_service.change_lb_mapping_port(self.tenant, self.service, container_port, lb_mapping_port,
                                                            mapping_service_id)
            if code != 200:
                return Response(general_message(code, "error", msg), status=code)

            result = general_message(200, "success", "端口修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TopologicalPortView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def put(self, request, *args, **kwargs):
        """
        应用拓扑图打开(关闭)对外端口
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            open_outer = request.data.get("open_outer", False)
            close_outer = request.data.get("close_outer", False)
            container_port = request.data.get("container_port", None)
            # 开启对外端口
            if open_outer:
                tenant_service_port = port_service.get_service_port_by_port(
                    self.service, int(container_port))
                code, msg, data = port_service.manage_port(self.tenant, self.service, self.response_region, int(container_port),
                                                           "open_outer", tenant_service_port.protocol,
                                                           tenant_service_port.port_alias)
                if code != 200:
                    return Response(general_message(412, "open outer fail", u"打开对外端口失败"), status=412)
                return Response(general_message(200, "open outer success", u"开启成功"), status=200)
            # 关闭改服务所有对外端口
            if close_outer:
                tenant_service_ports = port_service.get_service_ports(
                    self.service)
                for tenant_service_port in tenant_service_ports:
                    code, msg, data = port_service.manage_port(self.tenant, self.service, self.response_region,
                                                               tenant_service_port.container_port, "close_outer",
                                                               tenant_service_port.protocol, tenant_service_port.port_alias)
                    if code != 200:
                        return Response(general_message(412, "open outer fail", u"关闭对外端口失败"), status=412)
                return Response(general_message(200, "close outer success", u"关闭对外端口成功"), status=200)

            # 校验要依赖的服务是否开启了对外端口
            open_outer_services = port_repo.get_service_ports(self.tenant.tenant_id,
                                                              self.service.service_id).filter(is_outer_service=True)
            if not open_outer_services:
                service_ports = port_repo.get_service_ports(
                    self.tenant.tenant_id, self.service.service_id)
                port_list = [
                    service_port.container_port for service_port in service_ports]
                if len(port_list) == 1:
                    # 一个端口直接开启
                    tenant_service_port = port_service.get_service_port_by_port(
                        self.service, int(port_list[0]))
                    code, msg, data = port_service.manage_port(self.tenant, self.service, self.response_region, int(
                        port_list[0]), "open_outer", tenant_service_port.protocol, tenant_service_port.port_alias)
                    if code != 200:
                        return Response(general_message(412, "open outer fail", u"打开对外端口失败"), status=412)
                    return Response(general_message(200, "open outer success", u"开启成功"), status=200)
                else:
                    # 多个端口需要用户选择后开启
                    return Response(
                        general_message(
                            201, "the service does not open an external port", u"该服务未开启对外端口", list=port_list),
                        status=201)
            else:
                return Response(general_message(202, "the service has an external port open", u"该服务已开启对外端口"), status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])
