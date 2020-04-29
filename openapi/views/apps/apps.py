# -*- coding: utf-8 -*-
# creater by: barnett

import logging
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.views.base import BaseOpenAPIView
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from django.forms.models import model_to_dict
from console.constants import DomainType

from openapi.serializer.base_serializer import FailSerializer, SuccessSerializer
from openapi.views.base import TeamListAPIView, TeamAPIView
from openapi.serializer.app_serializer import AppInfoSerializer, AppBaseInfoSerializer, AppPostInfoSerializer
from openapi.serializer.app_serializer import ServiceBaseInfoSerializer
from openapi.serializer.app_serializer import ServiceGroupOperationsSerializer
from openapi.serializer.app_serializer import APPHttpDomainSerializer
from openapi.serializer.app_serializer import APPHttpDomainRspSerializer

from console.services.group_service import group_service
from console.services.team_services import team_services
from openapi.services.app_service import app_service
from console.services.app_config import port_service
from console.services.app_config import domain_service

logger = logging.getLogger("default")


class ListAppsView(TeamListAPIView):
    @swagger_auto_schema(
        operation_description="应用列表",
        manual_parameters=[
           openapi.Parameter("query", openapi.IN_QUERY, description="搜索查询应用名称，团队名称", type=openapi.TYPE_STRING),
        ],
        responses={200: AppBaseInfoSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, req, *args, **kwargs):
        query = req.GET.get("query", None)
        apps = group_service.get_apps_list(team_id=self.team.tenant_id, region_name=self.region_name, query=query)
        re = AppBaseInfoSerializer(apps, many=True)
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="创建应用",
        request_body=AppPostInfoSerializer(),
        responses={200: AppBaseInfoSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer = AppPostInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        logger.info(data["team_alias"])
        group_info = group_service.add_group(self.team, data["region_name"], data["app_name"], data.get("group_note"))
        re = AppBaseInfoSerializer(group_info)
        return Response(re.data, status=status.HTTP_201_CREATED)


class AppInfoView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="应用详情",
        responses={200: AppInfoSerializer()},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, *args, **kwargs):
        app = group_service.get_group_by_id(self.team.tenant_name, self.region_name, self.app_id)
        if not app:
            return Response(None, status.HTTP_404_NOT_FOUND)
        tenant = team_services.get_team_by_team_id(app.tenant_id)
        if not tenant:
            return Response({"msg": "该应用所属团队已被删除"}, status=status.HTTP_404_NOT_FOUND)
        appstatus, services = app_service.get_app_status(app)
        used_cpu, used_momory = app_service.get_app_memory_and_cpu_used(services)
        app_info = model_to_dict(app)
        app_info["service_count"] = app_service.get_app_service_count(app_id)
        app_info["enterprise_id"] = tenant.enterprise_id
        app_info["running_service_count"] = app_service.get_app_running_service_count(tenant, services)
        app_info["service_list"] = ServiceBaseInfoSerializer(services, many=True).data
        app_info["status"] = appstatus
        app_info["team_name"] = tenant.tenant_name
        app_info["used_cpu"] = used_cpu
        app_info["used_momory"] = used_momory
        app_info["app_id"] = app_id
        reapp = AppInfoSerializer(data=app_info)
        reapp.is_valid()
        return Response(reapp.data, status=status.HTTP_200_OK)


class APPOperationsView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="操作应用",
        request_body=ServiceGroupOperationsSerializer(),
        responses={
            status.HTTP_200_OK: SuccessSerializer,
            status.HTTP_400_BAD_REQUEST: FailSerializer,
            status.HTTP_404_NOT_FOUND: FailSerializer
        },
        tags=['openapi-apps'],
    )
    def post(self, request, app_id, *args, **kwargs):
        try:
            sos = ServiceGroupOperationsSerializer(data=request.data)
            sos.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.debug(e)
            result = {"msg": "请求参数错误"}
            rst_serializer = FailSerializer(data=result)
            rst_serializer.is_valid()
            return Response(rst_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        tenant, service_ids = app_service.get_group_services_by_id(app_id)
        if tenant:
            code, msg = app_service.group_services_operation(tenant,
                                                             sos.data.get("action"), service_ids)
            if code != 200:
                result = {"msg": "batch manage error"}
                rst_serializer = FailSerializer(data=result)
                rst_serializer.is_valid()
                return Response(rst_serializer.data, status=status.HTTP_400_BAD_REQUEST)
            else:
                result = {"msg": "操作成功"}
                rst_serializer = SuccessSerializer(data=result)
                rst_serializer.is_valid()
                return Response(rst_serializer.data, status=status.HTTP_200_OK)
        else:
            result = {"msg": "该应用所属团队已被删除"}
            rst_serializer = FailSerializer(data=result)
            rst_serializer.is_valid()
        return Response(rst_serializer.data, status=status.HTTP_404_NOT_FOUND)


class APPHttpDomainView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="应用绑定域名",
        request_body=APPHttpDomainSerializer(),
        responses={
            status.HTTP_200_OK: APPHttpDomainRspSerializer(),
            status.HTTP_400_BAD_REQUEST: FailSerializer,
            status.HTTP_404_NOT_FOUND: FailSerializer
        },
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        try:
            ads = APPHttpDomainSerializer(data=request.data)
            ads.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.debug(e)
            rst = {"msg": u"参数错误"}
            return Response(rst, status.HTTP_400_BAD_REQUEST)

        group_id = ads.data.get("app_id", None)
        container_port = ads.data.get("container_port", None)
        domain_name = ads.data.get("domain_name", None)
        certificate_id = ads.data.get("certificate_id", None)
        service_key = ads.data.get("service_key", None)
        domain_path = ads.data.get("domain_path", None)
        domain_cookie = ads.data.get("domain_cookie", None)
        domain_heander = ads.data.get("domain_header", None)
        rule_extensions = ads.data.get("rule_extensions", None)
        whether_open = ads.data.get("whether_open", False)
        the_weight = ads.data.get("the_weight", 100)

        service = app_service.get_service_by_service_key_and_group_id(service_key, group_id)
        tenant = app_service.get_tenant_by_group_id(group_id)
        if not service:
            rst = {"msg": u"应用组件不存在"}
            return Response(rst, status=status.HTTP_404_NOT_FOUND)
        if not tenant:
            rst = {"msg": u"未找到应用所属团队"}
            return Response(rst, status=status.HTTP_404_NOT_FOUND)

        protocol = "http"
        if certificate_id:
            protocol = "https"

        strategy_status = app_service.check_strategy_exist(
            service, container_port, domain_name, protocol, domain_path, rule_extensions)
        if strategy_status:
            rst = {"msg": "策略已存在"}
            return Response(rst, status=status.HTTP_400_BAD_REQUEST)

        if service.service_source == "third_party":
            msg, msg_show, code = port_service.check_domain_thirdpart(tenant, service)
            if code != 200:
                logger.exception(msg, msg_show)
                return Response({"msg": msg_show}, status=code)

        if whether_open:
            try:
                tenant_service_port = port_service.get_service_port_by_port(
                    service, container_port)
                # 仅开启对外端口
                code, msg, data = port_service.manage_port(
                    tenant, service, service.service_region, int(tenant_service_port.container_port),
                    "only_open_outer", tenant_service_port.protocol, tenant_service_port.port_alias)
                if code != 200:
                    return Response({"msg": "change port fail"}, status=code)
            except Exception as e:
                logger.debug(e)
                return Response({"msg": e}, status=status.HTTP_400_BAD_REQUEST)
        tenant_service_port = port_service.get_service_port_by_port(
            service, container_port)
        if not tenant_service_port.is_outer_service:
            return Response({"msg": "没有开启对外端口"}, status=status.HTTP_400_BAD_REQUEST)

        # 绑定端口(添加策略)
        code, msg, data = domain_service.bind_httpdomain(
            tenant, self.request.user, service, domain_name, container_port, protocol, certificate_id, DomainType.WWW,
            domain_path, domain_cookie, domain_heander, the_weight, rule_extensions)
        if code != 200:
            return Response({"msg": "bind domain error"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rst_serializer = APPHttpDomainRspSerializer(data=data)
            rst_serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.debug(e)
            return Response({"msg": "返回数据验证错误"}, status=status.HTTP_200_OK)
        return Response(rst_serializer.data, status=status.HTTP_200_OK)
