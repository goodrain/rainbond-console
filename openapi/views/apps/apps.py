# -*- coding: utf-8 -*-
# creater by: barnett

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.views.base import BaseOpenAPIView
from rest_framework import serializers
from rest_framework import status
from django.forms.models import model_to_dict
from openapi.serializer.base_serializer import FailSerializer
from rest_framework.response import Response
from openapi.views.base import ListAPIView
from openapi.serializer.app_serializer import AppInfoSerializer, AppBaseInfoSerializer, AppPostInfoSerializer
from openapi.serializer.app_serializer import ServiceBaseInfoSerializer
from console.services.group_service import group_service
from console.services.region_services import region_services
from console.services.team_services import team_services


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
        tenant = team_services.get_tenant_by_tenant_name(data["team_alias"])
        if not tenant:
            raise serializers.ValidationError("指定租户不存在")
        if not region_services.verify_team_region(team_name=data["team_alias"], region_name=data["region_name"]):
            raise serializers.ValidationError("指定数据中心租户未开通")
        code, msg, group_info = group_service.add_group(tenant, data["region_name"], data["app_name"])
        if not group_info:
            return Response(FailSerializer({"msg": msg}), status=code)
        return Response(AppBaseInfoSerializer({
            "enterprise_id": tenant.enterprise_id,
            "team_alias": tenant.tenant_alias,
            "app_name": group_info.group_name,
            "app_id": group_info.ID,
            "create_time": "",
        }), status=status.HTTP_201_CREATED)


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
            raise serializers.ValidationError("指定租户不存在")
        services = group_service.get_group_services(app_id)
        appInfo = model_to_dict(app)
        appInfo["enterprise_id"] = tenant.enterprise_id
        appInfo["service_list"] = ServiceBaseInfoSerializer(services, many=True).data
        reapp = AppInfoSerializer(data=appInfo)
        reapp.is_valid()
        return Response(reapp.data, status=status.HTTP_200_OK)
