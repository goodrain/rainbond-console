# -*- coding: utf-8 -*-
# creater by: barnett
import logging
from console.services.team_services import team_services
from console.services.enterprise_services import enterprise_services
from console.services.region_services import region_services
from openapi.views.base import ListAPIView
from openapi.views.base import BaseOpenAPIView
from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.team_serializer import TeamInfoSerializer
from django.urls import get_script_prefix

logger = logging.getLogger("default")


class ListTeamInfo(ListAPIView):
    view_perms = ["teams"]
    get_script_prefix()

    @swagger_auto_schema(
        query_serializer=TeamInfoSerializer,
        responses={200: TeamInfoSerializer(many=True)},
        tags=['openapi-team'],
    )
    def get(self, request):
        queryset = team_services.get_enterprise_teams(enterprise_id=request.user.enterprise_id)
        serializer = TeamInfoSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="add team",
        request_body=openapi.Schema(
            title="AddTeamRequest",
            type=openapi.TYPE_OBJECT,
            required=['team_name'],
            properties={
                'team_name': openapi.Schema(type=openapi.TYPE_STRING, description="团队名称"),
                'enterprise_id': openapi.Schema(type=openapi.TYPE_STRING, description="团队所属企业ID,未提供时默认使用请求用户企业ID"),
                'creater': openapi.Schema(type=openapi.TYPE_STRING, description="团队所属人，未提供时默认使用登录用户作为所属人"),
                'region_name': openapi.Schema(type=openapi.TYPE_STRING, description="默认开通的数据中心，未指定则不开通"),
            },
        ),
        responses={
            status.HTTP_201_CREATED: TeamInfoSerializer(),
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
            status.HTTP_400_BAD_REQUEST: None,
        },
        security=[],
        tags=['openapi-team'],
    )
    def post(self, request):
        serializer = TeamInfoSerializer(request.data)
        serializer.is_valid(raise_exception=True)
        team_data = serializer.data
        enterprise_id = team_data.get("enterprise_id", None)
        if not enterprise_id:
            enterprise_id = request.user.enterprise_id
        en = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
        if not en:
            raise serializers.ValidationError("指定企业不存在")
        region = None
        if team_data.get("region_name", None):
            region = region_services.get_region_by_region_name(team_data.get("region_name"))
            if not region:
                raise serializers.ValidationError("指定数据中心不存在")
        team = team_services.create_team(request.user, en, team_data["team_name"])
        if team:
            if region:
                code, message, bean = region_services.create_tenant_on_region(team.tenant_name, region.region_name)
                if code != 200:
                    team.delete()
                    return Response({"msg": message}, status=code)
                return Response(team, status=status.HTTP_201_CREATED)
        else:
            return Response(None, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TeamInfo(BaseOpenAPIView):
    @swagger_auto_schema(
        query_serializer=TeamInfoSerializer,
        responses={200: TeamInfoSerializer()},
        tags=['openapi-team'],
    )
    def get(self, request, team_name):
        queryset = team_services.get_tenant_by_tenant_name(team_name)
        serializer = TeamInfoSerializer(queryset)
        return Response(serializer.data)

    @swagger_auto_schema(
        query_serializer=TeamInfoSerializer,
        responses={200: TeamInfoSerializer()},
        tags=['openapi-team'],
    )
    def put(self, request):
        # todo
        pass
