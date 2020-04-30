# -*- coding: utf-8 -*-
# creater by: barnett

# -*- coding: utf-8 -*-
# creater by: barnett

import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from openapi.views.base import TeamAPIView
from django.forms.models import model_to_dict
from openapi.serializer.gateway_serializer import HTTPGatewayRuleSerializer, PostHTTPGatewayRuleSerializer
from console.services.app_config import domain_service
from console.services.group_service import group_service
from openapi.views.exceptions import ErrAppNotFound
from console.constants import DomainType
from console.services.app_config import port_service
from console.repositories.app import service_repo
logger = logging.getLogger("default")


class ListAppGatewayHTTPRuleView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="获取应用http访问策略列表",
        manual_parameters=[],
        responses={200: HTTPGatewayRuleSerializer(many=True)},
        tags=['openapi-gateway'],
    )
    def get(self, req, app_id,  *args, **kwargs):
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        rules = domain_service.get_http_rules_by_app_id(app_id)
        re = HTTPGatewayRuleSerializer(rules, many=True)
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="创建HTTP网关策略",
        request_body=PostHTTPGatewayRuleSerializer(),
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-apps'],
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
        if domain_service.check_domain_exist(httpdomain["service_id"],
                                             httpdomain["container_port"],
                                             httpdomain["domain_name"],
                                             protocol,
                                             httpdomain.get("domain_path"),
                                             httpdomain.get("rule_extensions")):
            rst = {"msg": "策略已存在"}
            return Response(rst, status=status.HTTP_400_BAD_REQUEST)

        if service.service_source == "third_party":
            msg, msg_show, code = port_service.check_domain_thirdpart(self.team, service)
            if code != 200:
                logger.exception(msg, msg_show)
                return Response({"msg": msg, "msg_show": msg_show}, status=code)
        if httpdomain.get("whether_open", True):
            tenant_service_port = port_service.get_service_port_by_port(
                service, httpdomain["container_port"])
            # 仅开启对外端口
            code, msg, data = port_service.manage_port(
                self.team, service, service.service_region, int(tenant_service_port.container_port),
                "only_open_outer", tenant_service_port.protocol, tenant_service_port.port_alias)
            if code != 200:
                return Response({"msg": "change port fail"}, status=code)
        tenant_service_port = port_service.get_service_port_by_port(
            service, httpdomain["container_port"])
        if not tenant_service_port.is_outer_service:
            return Response({"msg": "没有开启对外端口"}, status=status.HTTP_400_BAD_REQUEST)
        data = domain_service.bind_httpdomain(self.team, self.request.user, service, httpdomain, True)
        return Response(model_to_dict(data), status=status.HTTP_201_CREATED)
