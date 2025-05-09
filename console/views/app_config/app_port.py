# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from console.exception.main import AbortRequest
from console.repositories.app_config import port_repo
from console.services.app_config import domain_service, port_service
from console.services.operation_log import operation_log_service, Operation
from console.utils.reqparse import parse_item
from console.views.app_config.base import AppBaseView
from django.forms.models import model_to_dict
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppPortView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件的端口信息
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
        tenant_service_ports = port_service.get_service_ports(self.service)
        port_list = []
        for port in tenant_service_ports:
            port_info = port.to_dict()
            port_info["service_alias"] = self.service.service_alias
            variables = port_service.get_port_variables(self.tenant, self.service, port)
            port_info["environment"] = variables["environment"]
            outer_url = ""
            inner_url = ""

            if port_info["environment"] and port.is_inner_service:
                try:
                    inner_host, inner_port = "127.0.0.1", None
                    for pf in port_info["environment"]:
                        if not pf.get("name"):
                            continue
                        if pf.get("name").endswith("PORT"):
                            inner_port = pf.get("value")
                        if pf.get("name").endswith("HOST"):
                            inner_host = pf.get("value")
                    inner_url = "{0}:{1}".format(inner_host, inner_port)
                except Exception as se:
                    logger.exception(se)
            port_info["inner_url"] = inner_url
            outer_service = variables.get("outer_service", None)
            if outer_service:
                outer_url = "{0}:{1}".format(variables["outer_service"]["domain"], variables["outer_service"]["port"])
            port_info["outer_url"] = outer_url
            port_info["bind_domains"] = []
            if port.protocol == "http":
                path = ("/api-gateway/v1/" + self.tenant_name + "/routes/http/domains?service_alias=" +
                        self.service.service_alias + "&port=" + str(port.container_port))
                body = region_api.api_gateway_get_proxy(self.region, self.tenant.tenant_id, path, None)
                if body.get("list", []):
                    port_info["bind_domains"] = [{
                        "protocol": "http",
                        "domain_type": "www",
                        "ID": -1,
                        "domain_name": host,
                        "container_port": port.container_port
                    } for host in body.get("list", [])]
                    port_info["is_outer_service"] = len(port_info["bind_domains"]) > 0
                    port_info["is_outer_service"] = True
                    port.is_outer_service = True
                else:
                    port.is_outer_service = False
                    port_info["is_outer_service"] = False
            else:
                bind_tcp_domains = domain_service.get_tcp_port_bind_domains(self.service, port.container_port)
                if bind_tcp_domains:
                    outer = False
                    tcp_domain_list = []
                    for tcp_domain in bind_tcp_domains:
                        if tcp_domain.is_outer_service:
                            outer = True
                        tcp_domain_list.append(tcp_domain.to_dict())
                    port_info["bind_tcp_domains"] = tcp_domain_list
                    port_info["is_outer_service"] = outer
                    port.is_outer_service = outer
                else:
                    port_info["bind_tcp_domains"] = []
                    port_info["is_outer_service"] = False
                    port.is_outer_service = False
            port.save()
            port_list.append(port_info)
        result = general_message(200, "success", "查询成功", list=port_list)
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        为组件添加端口
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
              description: 是否打开对内组件
              required: true
              type: boolean
              paramType: form
            - name: is_outer_service
              description: 是否打开对外组件
              required: true
              type: boolean
              paramType: form

        """
        port = request.data.get("port", None)
        protocol = request.data.get("protocol", None)
        port_alias = request.data.get("port_alias", None)
        is_inner_service = request.data.get('is_inner_service', False)
        is_outer_service = request.data.get('is_outer_service', False)
        if not port:
            return Response(general_message(400, "params error", "缺少端口参数"), status=400)
        if not protocol:
            return Response(general_message(400, "params error", "缺少协议参数"), status=400)
        if not port_alias:
            port_alias = self.service.service_alias.upper().replace("-", "_") + str(port)
        code, msg, port_info = port_service.add_service_port(self.tenant, self.service, port, protocol, port_alias,
                                                             is_inner_service, is_outer_service, None, self.user.nick_name)
        tenant_service_port = port_service.get_service_port_by_port(self.service, port)
        new_information = port_service.json_service_port(tenant_service_port)
        if code != 200:
            return Response(general_message(code, "add port error", msg), status=code)

        result = general_message(200, "success", "端口添加成功", bean=model_to_dict(port_info))
        comment = operation_log_service.generate_component_comment(
            operation=Operation.ADD,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=" 端口 {}".format(port))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information,
        )
        return Response(result, status=result["code"])


class AppPortManageView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        查看组件的某个端口的详情
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
            - name: port
              description: 端口号
              required: true
              type: string
              paramType: path

        """
        container_port = kwargs.get("port", None)
        if not container_port:
            return Response(general_message(400, "container_port not specify", "端口变量名未指定"), status=400)

        port_info = port_service.get_service_port_by_port(self.service, int(container_port))

        variables = port_service.get_port_variables(self.tenant, self.service, port_info)
        bean = {"port": model_to_dict(port_info)}
        bean.update(variables)
        result = general_message(200, "success", "查询成功", bean=bean)
        return Response(result, status=result["code"])

    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        删除组件的某个端口
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
            - name: port
              description: 端口号
              required: true
              type: string
              paramType: path

        """
        container_port = kwargs.get("port", None)
        if not container_port:
            raise AbortRequest("container_port not specify", "端口变量名未指定")
        tenant_service_port = port_service.get_service_port_by_port(self.service, container_port)
        old_information = port_service.json_service_port(tenant_service_port)
        data = port_service.delete_port_by_container_port(self.tenant, self.service, int(container_port), self.user.nick_name)
        result = general_message(200, "success", "删除成功", bean=model_to_dict(data))
        comment = operation_log_service.generate_component_comment(
            operation=Operation.DELETE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=" 端口 {}".format(container_port))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information)
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改组件的某个端口（打开|关闭|修改协议|修改环境变量）
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
        k8s_service_name = parse_item(request, "k8s_service_name", default="")
        if not container_port:
            raise AbortRequest("container_port not specify", "端口变量名未指定")
        if self.service.service_source == "third_party" and ("outer" in action):
            msg, msg_show, code = port_service.check_domain_thirdpart(self.tenant, self.service)
            if code != 200:
                logger.exception(msg, msg_show)
                return Response(general_message(code, msg, msg_show), status=code)
        tenant_service_port = port_service.get_service_port_by_port(self.service, container_port)
        old_information = port_service.json_service_port(tenant_service_port)
        code, msg, data = port_service.manage_port(self.tenant, self.service, self.response_region, int(container_port), action,
                                                   protocol, port_alias, k8s_service_name, self.user.nick_name, self.app)
        new_information = port_service.json_service_port(tenant_service_port)
        if code != 200:
            return Response(general_message(code, "change port fail", msg), status=code)
        result = general_message(200, "success", "操作成功", bean=model_to_dict(data))
        op = Operation.CHANGE
        if action in "open_outer|open_inner":
            op = Operation.OPEN
        if action in "close_outer|close_inner":
            op = Operation.CLOSE
        comment = operation_log_service.generate_component_comment(
            operation=op,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=" 端口 {} 的{}".format(container_port, operation_log_service.port_action_to_zh(action)))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information,
            new_information=new_information)
        return Response(result, status=result["code"])


class AppTcpOuterManageView(AppBaseView):
    @never_cache
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
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: port
              description: 端口号
              required: true
              type: string
              paramType: path
        """
        tcp_outer_ports = port_service.get_team_region_usable_tcp_ports(self.tenant, self.service)

        port_list = []
        for p in tcp_outer_ports:
            port_list.append({"service_id": p.service_id, "lb_mpping_port": p.lb_mapping_port})
        result = general_message(200, "success", "查询成功", list=port_list)
        return Response(result, status=result["code"])


class TopologicalPortView(AppBaseView):
    @never_cache
    def put(self, request, *args, **kwargs):
        """
        组件拓扑图打开(关闭)对外端口
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        open_outer = request.data.get("open_outer", False)
        close_outer = request.data.get("close_outer", False)
        container_port = request.data.get("container_port", None)
        # 开启对外端口
        if open_outer:
            tenant_service_port = port_service.get_service_port_by_port(self.service, int(container_port))
            if self.service.service_source == "third_party":
                msg, msg_show, code = port_service.check_domain_thirdpart(self.tenant, self.service)
                if code != 200:
                    logger.exception(msg, msg_show)
                    return Response(general_message(code, msg, msg_show), status=code)
            code, msg, data = port_service.manage_port(self.tenant, self.service, self.response_region, int(container_port),
                                                       "open_outer", tenant_service_port.protocol,
                                                       tenant_service_port.port_alias)
            if code != 200:
                return Response(general_message(412, "open outer fail", "打开对外端口失败"), status=412)
            return Response(general_message(200, "open outer success", "开启成功"), status=200)
        # 关闭该组件所有对外端口
        if close_outer:
            tenant_service_ports = port_service.get_service_ports(self.service)
            for tenant_service_port in tenant_service_ports:
                code, msg, data = port_service.manage_port(
                    self.tenant, self.service, self.response_region, tenant_service_port.container_port, "close_outer",
                    tenant_service_port.protocol, tenant_service_port.port_alias, user_name=self.user.nick_name, app=self.app)
                if code != 200:
                    return Response(general_message(412, "open outer fail", "关闭对外端口失败"), status=412)
            return Response(general_message(200, "close outer success", "关闭对外端口成功"), status=200)

        # 校验要依赖的组件是否开启了对外端口
        open_outer_services = port_repo.get_service_ports(self.tenant.tenant_id,
                                                          self.service.service_id).filter(is_outer_service=True)
        if not open_outer_services:
            if self.service.service_source == "third_party":
                msg, msg_show, code = port_service.check_domain_thirdpart(self.tenant, self.service)
                if code != 200:
                    logger.exception(msg, msg_show)
                    return Response(general_message(code, msg, msg_show), status=code)
            service_ports = port_repo.get_service_ports(self.tenant.tenant_id, self.service.service_id)
            port_list = [service_port.container_port for service_port in service_ports]
            if len(port_list) == 1:
                # 一个端口直接开启
                tenant_service_port = port_service.get_service_port_by_port(self.service, int(port_list[0]))
                code, msg, data = port_service.manage_port(self.tenant, self.service, self.response_region, int(
                    port_list[0]), "open_outer", tenant_service_port.protocol, tenant_service_port.port_alias, user_name=self.user.nick_name, app=self.app)
                if code != 200:
                    return Response(general_message(412, "open outer fail", "打开对外端口失败"), status=412)
                return Response(general_message(200, "open outer success", "开启成功"), status=200)
            else:
                # 多个端口需要用户选择后开启
                return Response(
                    general_message(201, "the service does not open an external port", "该组件未开启对外端口", list=port_list),
                    status=201)
        else:
            return Response(general_message(202, "the service has an external port open", "该组件已开启对外端口"), status=200)
