# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from console.services.app_config import port_service, domain_service
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from django.forms.models import model_to_dict
import logging

logger = logging.getLogger("default")


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
                variables = port_service.get_port_variables(self.tenant, self.service, port)
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
                    outer_url = "{0}:{1}".format(variables["outer_service"]["domain"], variables["outer_service"]["port"])
                port_info["outer_url"] = outer_url
                port_info["bind_domains"] = []
                if port.protocol == "http":
                    bind_domains = domain_service.get_port_bind_domains(self.service, port.container_port)
                    port_info["bind_domains"] = [domain.to_dict() for domain in bind_domains]
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
                port_alias = self.service.service_alias.upper().replace("-", "_")+str(port)
            code, msg, port_info = port_service.add_service_port(self.tenant, self.service, port, protocol, port_alias,
                                                                 is_inner_service,
                                                                 is_outer_service)
            if code != 200:
                return Response(general_message(code, "add port error", msg), status=code)

            result = general_message(200, "success", "端口添加成功", bean=model_to_dict(port_info))
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
            port_info = port_service.get_service_port_by_port(self.service, int(container_port))

            variables = port_service.get_port_variables(self.tenant, self.service, port_info)
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
        try:
            code, msg, data = port_service.delete_port_by_container_port(self.tenant, self.service, int(container_port))
            if code != 200:
                return Response(general_message(code, "delete port fail", msg), status=code)
            result = general_message(200, "success", "删除成功", bean=model_to_dict(data))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
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
        try:
            code, msg, data = port_service.manage_port(self.tenant, self.service, int(container_port), action,
                                                       protocol, port_alias)
            if code != 200:
                return Response(general_message(code, "change port fail", msg), status=code)
            result = general_message(200, "success", "操作成功,重启生效", bean=model_to_dict(data))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
