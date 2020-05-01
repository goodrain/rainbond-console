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
from openapi.views.base import ListAPIView
from openapi.serializer.app_serializer import AppInfoSerializer, AppBaseInfoSerializer, AppPostInfoSerializer
from openapi.serializer.app_serializer import ServiceBaseInfoSerializer
from openapi.serializer.app_serializer import ServiceGroupOperationsSerializer
from openapi.serializer.app_serializer import APPHttpDomainSerializer
from openapi.serializer.app_serializer import APPHttpDomainRspSerializer

from console.services.group_service import group_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from openapi.services.app_service import app_service
from console.services.app_config import port_service
from console.services.app_config import domain_service

logger = logging.getLogger("default")


class ListAppsView(ListAPIView):
    @swagger_auto_schema(
        operation_description="应用列表",
        manual_parameters=[
            openapi.Parameter("team_alias", openapi.IN_QUERY, description="团名唯一别名", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_QUERY, description="数据中心唯一名称", type=openapi.TYPE_STRING),
            openapi.Parameter("query", openapi.IN_QUERY, description="搜索查询应用名称，团队名称", type=openapi.TYPE_STRING),
        ],
        responses={200: AppBaseInfoSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, req, *args, **kwargs):
        team_alias = req.GET.get("team_alias", None)
        team = None
        if team_alias:
            team = team_services.get_team_by_team_alias(team_alias)
        region_name = req.GET.get("region_name", None)
        query = req.GET.get("query", None)
        apps = group_service.get_apps_list(team_id=team.tenant_id if team else None, region_name=region_name, query=query)
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
        tenant = team_services.get_tenant_by_tenant_name(data["team_alias"])
        if not tenant:
            raise serializers.ValidationError("指定租户不存在")
        if not region_services.verify_team_region(team_name=data["team_alias"], region_name=data["region_name"]):
            raise serializers.ValidationError("指定数据中心租户未开通")
        group_info = group_service.add_group(tenant, data["region_name"], data["app_name"], data.get("group_note"))
        re = AppBaseInfoSerializer(group_info)
        return Response(re.data, status=status.HTTP_201_CREATED)


class AppInfoView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="应用详情",
        responses={200: AppInfoSerializer()},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, *args, **kwargs):
        app = group_service.get_app_by_id(app_id)
        if not app:
            return Response(None, status.HTTP_404_NOT_FOUND)
        tenant = team_services.get_team_by_team_id(app.tenant_id)
        if not tenant:
            return Response({"msg": "该应用所属团队已被删除"}, status=status.HTTP_404_NOT_FOUND)
        appstatus, services = app_service.get_app_status(app)
        used_cpu, used_momory = app_service.get_app_memory_and_cpu_used(services)
        appInfo = model_to_dict(app)
        appInfo["service_count"] = app_service.get_app_service_count(app_id)
        appInfo["enterprise_id"] = tenant.enterprise_id
        appInfo["running_service_count"] = app_service.get_app_running_service_count(tenant, services)
        appInfo["service_list"] = ServiceBaseInfoSerializer(services, many=True).data
        appInfo["status"] = appstatus
        appInfo["team_name"] = tenant.tenant_name
        appInfo["used_cpu"] = used_cpu
        appInfo["used_momory"] = used_momory
        appInfo["app_id"] = app_id
        reapp = AppInfoSerializer(data=appInfo)
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
            serializers = ServiceGroupOperationsSerializer(data=request.data)
            serializers.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.debug(e)
            result = {"msg": "请求参数错误"}
            rst_serializer = FailSerializer(data=result)
            rst_serializer.is_valid()
            return Response(rst_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        tenant, service_ids = app_service.get_group_services_by_id(app_id)
        if tenant:
            code, msg = app_service.group_services_operation(tenant, serializers.data.get("action"), service_ids)
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
            serializers = APPHttpDomainSerializer(data=request.data)
            serializers.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.debug(e)
            rst = {"msg": u"参数错误"}
            return Response(rst, status.HTTP_400_BAD_REQUEST)

        group_id = serializers.data.get("app_id", None)
        container_port = serializers.data.get("container_port", None)
        domain_name = serializers.data.get("domain_name", None)
        certificate_id = serializers.data.get("certificate_id", None)
        service_key = serializers.data.get("service_key", None)
        domain_path = serializers.data.get("domain_path", None)
        domain_cookie = serializers.data.get("domain_cookie", None)
        domain_heander = serializers.data.get("domain_header", None)
        rule_extensions = serializers.data.get("rule_extensions", None)
        whether_open = serializers.data.get("whether_open", False)
        the_weight = serializers.data.get("the_weight", 100)

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

        strategy_status = app_service.check_strategy_exist(service, container_port, domain_name, protocol, domain_path,
                                                           rule_extensions)
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
                tenant_service_port = port_service.get_service_port_by_port(service, container_port)
                # 仅开启对外端口
                code, msg, data = port_service.manage_port(tenant, service, service.service_region,
                                                           int(tenant_service_port.container_port), "only_open_outer",
                                                           tenant_service_port.protocol, tenant_service_port.port_alias)
                if code != 200:
                    return Response({"msg": "change port fail"}, status=code)
            except Exception as e:
                logger.debug(e)
                return Response({"msg": e}, status=status.HTTP_400_BAD_REQUEST)
        tenant_service_port = port_service.get_service_port_by_port(service, container_port)
        if not tenant_service_port.is_outer_service:
            return Response({"msg": "没有开启对外端口"}, status=status.HTTP_400_BAD_REQUEST)

        # 绑定端口(添加策略)
        code, msg, data = domain_service.bind_httpdomain(tenant, self.request.user, service, domain_name, container_port,
                                                         protocol, certificate_id, DomainType.WWW, domain_path, domain_cookie,
                                                         domain_heander, the_weight, rule_extensions)
        if code != 200:
            return Response({"msg": "bind domain error"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rst_serializer = APPHttpDomainRspSerializer(data=data)
            rst_serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.debug(e)
            return Response({"msg": "返回数据验证错误"}, status=status.HTTP_200_OK)
        return Response(rst_serializer.data, status=status.HTTP_200_OK)
