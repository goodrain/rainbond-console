# -*- coding: utf-8 -*-
# creater by: barnett

# -*- coding: utf-8 -*-
# creater by: barnett

import logging

from console.constants import DomainType
from console.exception.main import ServiceHandleException
from console.repositories.app import service_repo
from console.services.app_config import domain_service, port_service
from console.services.app_config.domain_service import (ErrNotFoundDomain, tcp_domain)
from console.services.group_service import group_service
from django.forms.models import model_to_dict
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.gateway_serializer import (EnterpriseHTTPGatewayRuleSerializer, GatewayRuleSerializer,
                                                   HTTPGatewayRuleSerializer, PostGatewayRuleSerializer,
                                                   PostHTTPGatewayRuleSerializer, UpdatePostHTTPGatewayRuleSerializer)
from openapi.views.base import BaseOpenAPIView, TeamAppAPIView
from openapi.views.exceptions import ErrAppNotFound
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger("default")


class ListAppGatewayHTTPRuleView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="获取应用http访问策略列表",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
        ],
        responses={200: HTTPGatewayRuleSerializer(many=True)},
        tags=['openapi-gateway'],
    )
    def get(self, req, app_id, *args, **kwargs):
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        rules = domain_service.get_http_rules_by_app_id(app_id)
        re = HTTPGatewayRuleSerializer(rules, many=True)
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="创建HTTP网关策略",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
        ],
        request_body=PostHTTPGatewayRuleSerializer(),
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-gateway'],
    )
    def post(self, request, app_id, *args, **kwargs):
        ads = PostHTTPGatewayRuleSerializer(data=request.data)
        ads.is_valid(raise_exception=True)
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        httpdomain = ads.data
        # Compatible history code
        httpdomain["domain_heander"] = httpdomain.get("domain_header", None)
        httpdomain["domain_type"] = DomainType.WWW
        protocol = "http"
        if httpdomain.get("certificate_id", None):
            protocol = "https"
        httpdomain["protocol"] = protocol
        service = service_repo.get_service_by_tenant_and_id(self.team.tenant_id, httpdomain["service_id"])
        if not service:
            rst = {"msg": "组件不存在"}
            return Response(rst, status=status.HTTP_400_BAD_REQUEST)
        if domain_service.check_domain_exist(httpdomain["service_id"], httpdomain["container_port"], httpdomain["domain_name"],
                                             protocol, httpdomain.get("domain_path"), httpdomain.get("rule_extensions")):
            rst = {"msg": "策略已存在"}
            return Response(rst, status=status.HTTP_400_BAD_REQUEST)

        if service.service_source == "third_party":
            msg, msg_show, code = port_service.check_domain_thirdpart(self.team, service)
            if code != 200:
                logger.exception(msg, msg_show)
                return Response({"msg": msg, "msg_show": msg_show}, status=code)
        if httpdomain.get("whether_open", True):
            tenant_service_port = port_service.get_service_port_by_port(service, httpdomain["container_port"])
            # 仅开启对外端口
            code, msg, data = port_service.manage_port(self.team, service, service.service_region,
                                                       int(tenant_service_port.container_port), "only_open_outer",
                                                       tenant_service_port.protocol, tenant_service_port.port_alias)
            if code != 200:
                return Response({"msg": "change port fail"}, status=code)
        tenant_service_port = port_service.get_service_port_by_port(service, httpdomain["container_port"])
        if not tenant_service_port.is_outer_service:
            return Response({"msg": "没有开启对外端口"}, status=status.HTTP_400_BAD_REQUEST)
        data = domain_service.bind_httpdomain(self.team, self.request.user, service, httpdomain, True)
        configuration = httpdomain.get("configuration", None)
        if configuration:
            domain_service.update_http_rule_config(self.team, self.region_name, data.http_rule_id, configuration)
        serializer = HTTPGatewayRuleSerializer(data=data.to_dict())
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListEnterpriseAppGatewayHTTPRuleView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取企业应用http访问策略列表",
        manual_parameters=[
            openapi.Parameter("auto_ssl", openapi.IN_QUERY, description="查询条件，是否为需要自动匹配证书的策略", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: EnterpriseHTTPGatewayRuleSerializer(many=True)},
        tags=['openapi-gateway'],
    )
    def get(self, req, *args, **kwargs):
        auto_ssl = req.GET.get("auto_ssl", None)
        is_auto_ssl = None
        if auto_ssl is not None:
            if auto_ssl.lower() == "true":
                is_auto_ssl = True
            else:
                is_auto_ssl = False
        rules = domain_service.get_http_rules_by_enterprise_id(self.enterprise.enterprise_id, is_auto_ssl)
        re = EnterpriseHTTPGatewayRuleSerializer(data=rules, many=True)
        re.is_valid()
        return Response(re.data, status=status.HTTP_200_OK)


class UpdateAppGatewayHTTPRuleView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="获取应用http访问策略详情",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter("rule_id", openapi.IN_PATH, description="网关策略id", type=openapi.TYPE_STRING),
        ],
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-gateway'],
    )
    def get(self, req, app_id, rule_id, *args, **kwargs):
        rule = domain_service.get_http_rules_by_app_id(self.app.ID).filter(http_rule_id=rule_id).first()
        re = HTTPGatewayRuleSerializer(rule)
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="更新HTTP访问策略",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter("rule_id", openapi.IN_PATH, description="网关策略id", type=openapi.TYPE_STRING),
        ],
        request_body=UpdatePostHTTPGatewayRuleSerializer(),
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-gateway'],
    )
    def put(self, request, app_id, rule_id, *args, **kwargs):
        ads = UpdatePostHTTPGatewayRuleSerializer(data=request.data)
        ads.is_valid(raise_exception=True)
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        httpdomain = ads.data
        service = service_repo.get_service_by_tenant_and_id(self.team.tenant_id, httpdomain["service_id"])
        if not service:
            rst = {"msg": "组件不存在"}
            return Response(rst, status=status.HTTP_400_BAD_REQUEST)
        data = domain_service.update_httpdomain(self.team, service, rule_id, ads.data, True)

        re = HTTPGatewayRuleSerializer(data=model_to_dict(data))
        re.is_valid()
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除HTTP访问策略",
        manual_parameters=[],
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-gateway'],
    )
    def delete(self, request, app_id, rule_id, *args, **kwargs):
        rule = domain_service.get_http_rule_by_id(self.team.tenant_id, rule_id)
        if not rule:
            raise ErrNotFoundDomain
        domain_service.unbind_httpdomain(self.team, self.region_name, rule_id)
        re = HTTPGatewayRuleSerializer(data=model_to_dict(rule))
        re.is_valid()
        return Response(re.data, status=status.HTTP_200_OK)


class ListAppGatewayRuleView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="获取应用访问策略列表",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
        ],
        responses={200: GatewayRuleSerializer()},
        tags=['openapi-gateway'],
    )
    def get(self, req, app_id, *args, **kwargs):
        query = req.GET.get("query", None)
        data = {}
        if query == "http":
            http_rules = domain_service.get_http_rules_by_app_id(app_id)
            data["http"] = http_rules
        elif query == "tcp":
            tcp_rules = domain_service.get_tcp_rules_by_app_id(app_id)
            data["tcp"] = tcp_rules
        else:
            http_rules = domain_service.get_http_rules_by_app_id(app_id)
            tcp_rules = domain_service.get_tcp_rules_by_app_id(app_id)
            data["http"] = http_rules
            data["tcp"] = tcp_rules

        re = GatewayRuleSerializer(data)
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="创建网关策略",
        request_body=PostGatewayRuleSerializer(),
        responses={200: GatewayRuleSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, app_id, *args, **kwargs):
        ads = PostGatewayRuleSerializer(data=request.data)
        ads.is_valid(raise_exception=True)
        if ads.data.get("protocol") == "tcp":
            tcpdomain = ads.data.get("tcp")
            if not tcpdomain:
                raise ServiceHandleException(msg="Missing parameters: tcp", msg_show="缺少参数: tcp")

            container_port = tcpdomain.get("container_port", None)
            service_id = tcpdomain.get("service_id", None)
            end_point = tcpdomain.get("end_point", None)
            rule_extensions = tcpdomain.get("rule_extensions", None)
            default_port = tcpdomain.get("default_port", None)
            default_ip = tcpdomain.get("default_ip", None)
            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                raise ServiceHandleException(msg="not service", msg_show="组件不存在")

            # Check if the given endpoint exists.
            service_tcpdomain = tcp_domain.get_tcpdomain_by_end_point(self.region.region_id, end_point)
            if service_tcpdomain:
                raise ServiceHandleException(msg="exist", msg_show="策略已存在")

            if service.service_source == "third_party":
                msg, msg_show, code = port_service.check_domain_thirdpart(self.team, service)
                if code != 200:
                    raise ServiceHandleException(msg=msg, msg_show=msg_show)
            try:
                tenant_service_port = port_service.get_service_port_by_port(service, container_port)
                # 仅打开对外端口
                code, msg, data = port_service.manage_port(self.team, service, service.service_region,
                                                           int(tenant_service_port.container_port), "only_open_outer",
                                                           tenant_service_port.protocol, tenant_service_port.port_alias)
                if code != 200:
                    raise ServiceHandleException(status_code=code, msg="change port fail", msg_show=msg)
            except Exception as e:
                logger.exception(e)
                raise ServiceHandleException(status_code=code, msg="change port fail", msg_show="open port failure")
            # 添加tcp策略
            code, msg, data = domain_service.bind_tcpdomain(self.team, self.user, service, end_point, container_port,
                                                            default_port, rule_extensions, default_ip)

            if code != 200:
                raise ServiceHandleException(status_code=code, msg="bind domain error", msg_show=msg)

        elif ads.data.get("protocol") == "http":
            httpdomain = ads.data.get("http")
            if not httpdomain:
                raise ServiceHandleException(msg="Missing parameters: tcp", msg_show="缺少参数: http")
            httpdomain["domain_heander"] = httpdomain.get("domain_header", None)
            httpdomain["domain_type"] = DomainType.WWW
            protocol = "http"
            if httpdomain.get("certificate_id", None):
                protocol = "https"
            httpdomain["protocol"] = protocol
            service = service_repo.get_service_by_tenant_and_id(self.team.tenant_id, httpdomain["service_id"])
            if not service:
                rst = {"msg": "组件不存在"}
                return Response(rst, status=status.HTTP_400_BAD_REQUEST)
            if domain_service.check_domain_exist(httpdomain["service_id"], httpdomain["container_port"],
                                                 httpdomain["domain_name"], protocol, httpdomain.get("domain_path"),
                                                 httpdomain.get("rule_extensions")):
                rst = {"msg": "策略已存在"}
                return Response(rst, status=status.HTTP_400_BAD_REQUEST)

            if service.service_source == "third_party":
                msg, msg_show, code = port_service.check_domain_thirdpart(self.team, service)
                if code != 200:
                    logger.exception(msg, msg_show)
                    return Response({"msg": msg, "msg_show": msg_show}, status=code)
            if httpdomain.get("whether_open", True):
                tenant_service_port = port_service.get_service_port_by_port(service, httpdomain["container_port"])
                # 仅开启对外端口
                code, msg, data = port_service.manage_port(self.team, service, service.service_region,
                                                           int(tenant_service_port.container_port), "only_open_outer",
                                                           tenant_service_port.protocol, tenant_service_port.port_alias)
                if code != 200:
                    return Response({"msg": "change port fail"}, status=code)
            tenant_service_port = port_service.get_service_port_by_port(service, httpdomain["container_port"])
            if not tenant_service_port:
                raise ServiceHandleException("port not found", "端口不存在", 404, 404)
            if not tenant_service_port.is_outer_service:
                return Response({"msg": "没有开启对外端口"}, status=status.HTTP_400_BAD_REQUEST)
            domain_service.bind_httpdomain(self.team, self.request.user, service, httpdomain, True)
        else:
            raise ServiceHandleException(msg="error parameters: protocol", msg_show="错误参数: protocol")
        data = {}
        http_rules = domain_service.get_http_rules_by_app_id(app_id)
        tcp_rules = domain_service.get_tcp_rules_by_app_id(app_id)
        data["http"] = http_rules
        data["tcp"] = tcp_rules
        re = GatewayRuleSerializer(data)
        return Response(re.data, status=status.HTTP_200_OK)


class UpdateAppGatewayRuleView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="更新访问策略",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
        ],
        request_body=UpdatePostHTTPGatewayRuleSerializer(),
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-gateway'],
    )
    def put(self, request, app_id, rule_id, *args, **kwargs):
        ads = UpdatePostHTTPGatewayRuleSerializer(data=request.data)
        ads.is_valid(raise_exception=True)
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        httpdomain = ads.data
        service = service_repo.get_service_by_tenant_and_id(self.team.tenant_id, httpdomain["service_id"])
        if not service:
            rst = {"msg": "组件不存在"}
            return Response(rst, status=status.HTTP_400_BAD_REQUEST)
        data = domain_service.update_httpdomain(self.team, service, rule_id, ads.data, True)

        re = HTTPGatewayRuleSerializer(data=model_to_dict(data))
        re.is_valid()
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除HTTP访问策略",
        manual_parameters=[],
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-gateway'],
    )
    def delete(self, request, app_id, rule_id, *args, **kwargs):
        rule = domain_service.get_http_rule_by_id(self.team.tenant_id, rule_id)
        if not rule:
            raise ErrNotFoundDomain
        domain_service.unbind_httpdomain(self.team, self.region_name, rule_id)
        re = HTTPGatewayRuleSerializer(data=model_to_dict(rule))
        re.is_valid()
        return Response(re.data, status=status.HTTP_200_OK)
