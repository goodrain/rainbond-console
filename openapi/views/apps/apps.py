# -*- coding: utf-8 -*-
# creater by: barnett

import logging
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from django.forms.models import model_to_dict
from openapi.serializer.base_serializer import FailSerializer, SuccessSerializer
from openapi.views.base import TeamAPIView
from openapi.serializer.app_serializer import AppInfoSerializer, AppBaseInfoSerializer, AppPostInfoSerializer
from openapi.serializer.app_serializer import ServiceBaseInfoSerializer
from openapi.serializer.app_serializer import ServiceGroupOperationsSerializer
from openapi.views.exceptions import ErrAppNotFound
from console.services.group_service import group_service
from openapi.services.app_service import app_service
from console.services.app_actions import app_manage_service
logger = logging.getLogger("default")


class ListAppsView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="团队应用列表",
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
        group_info = group_service.add_group(self.team, self.region_name, data["app_name"], data.get("app_note"))
        re = AppBaseInfoSerializer(group_info)
        return Response(re.data, status=status.HTTP_201_CREATED)


class AppInfoView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="应用详情",
        responses={200: AppInfoSerializer()},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, *args, **kwargs):
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        services = app_service.get_app_services_and_status(app)
        used_cpu, used_momory = app_service.get_app_memory_and_cpu_used(services)
        app_info = model_to_dict(app)
        app_info["service_count"] = app_service.get_app_service_count(app_id)
        app_info["enterprise_id"] = self.enterprise.enterprise_id
        running_count = app_service.get_app_running_service_count(self.team, services)
        app_info["running_service_count"] = running_count
        app_status = "closed"
        if running_count > 0 and running_count < len(services):
            app_status = "part_running"
        if running_count > 0 and running_count == len(services):
            app_status = "running"
        app_info["status"] = app_status
        app_info["team_name"] = self.team.tenant_name
        app_info["used_cpu"] = used_cpu
        app_info["used_momory"] = used_momory
        app_info["app_id"] = app_id
        reapp = AppInfoSerializer(data=app_info)
        reapp.is_valid()
        return Response(reapp.data, status=status.HTTP_200_OK)


class APPOperationsView(TeamAPIView):
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
        sos = ServiceGroupOperationsSerializer(data=request.data)
        sos.is_valid(raise_exception=True)
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        service_ids = sos.data.get("service_ids", None)
        if not service_ids or len(service_ids) == 0:
            service_ids = app_service.get_group_services_by_id(app_id)
        # TODO: Check the amount of resources used
        code, msg = app_manage_service.batch_operations(self.team, request.user, sos.data.get("action"), service_ids, None)
        if code != 200:
            result = {"msg": "batch operation error"}
            rst_serializer = FailSerializer(data=result)
            rst_serializer.is_valid()
            return Response(rst_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        else:
            result = {"msg": msg}
            rst_serializer = SuccessSerializer(data=result)
            rst_serializer.is_valid()
            return Response(rst_serializer.data, status=status.HTTP_200_OK)


class ListAppServicesView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="查询应用下组件列表",
        responses={200: ServiceBaseInfoSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, *args, **kwargs):
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        services = app_service.get_app_services_and_status(app)
        sbis = ServiceBaseInfoSerializer(data=services, many=True)
        sbis.is_valid()
        return Response(sbis.data, status=status.HTTP_200_OK)
