# -*- coding: utf8 -*-
"""
  Created on 18/5/23.
"""
import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from openapi.views.base import TeamAPIView
from console.services.groupcopy_service import groupapp_copy_service
from openapi.serializer.groupapp_serializer import GroupAppCopyLSerializer
from openapi.serializer.groupapp_serializer import GroupAppCopyCSerializer
from openapi.serializer.groupapp_serializer import GroupAppCopyCResSerializer

logger = logging.getLogger('default')


class GroupAppsCopyView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="获取需要复制的应用组件信息",
        responses={200: GroupAppCopyLSerializer()},
        tags=['openapi-apps'],
    )
    @never_cache
    def get(self, request, team_id, group_id, **kwargs):
        group_services = groupapp_copy_service.get_group_services_with_build_source(self.team, self.region_name, group_id)
        serializer = GroupAppCopyLSerializer(data=group_services, many=True)
        serializer.is_valid(raise_exception=True)
        result = {
            "result": serializer.validated_data,
            "total": len(serializer.validated_data)
        }
        return Response(result, status=200)

    @swagger_auto_schema(
        operation_description="复制应用",
        request_body=GroupAppCopyCSerializer(),
        responses={
            status.HTTP_200_OK: GroupAppCopyCResSerializer(),
            status.HTTP_400_BAD_REQUEST: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
        },
        tags=['openapi-apps'],
    )
    @never_cache
    def post(self, request, team_id, group_id, *args, **kwargs):
        """
        应用复制
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: int
              paramType: path
        """
        serializers = GroupAppCopyCSerializer(data=request.data)
        serializers.is_valid(raise_exception=True)
        services = serializers.data.get("services")
        tar_team_name = request.data.get("tar_team_name")
        tar_region_name = request.data.get("tar_region_name")
        tar_group_id = request.data.get("tar_group_id")
        if not self.team:
            return Response({"msg": "应用所在团队不存在"}, status=404)
        tar_team, tar_group = groupapp_copy_service.check_and_get_team_group(
            request.user, tar_team_name, tar_region_name, tar_group_id)
        groupapp_copy_service.copy_group_services(
            request.user, self.team, tar_team, tar_region_name, tar_group, group_id, services)
        domain = request.META.get("wsgi.url_scheme") + "://" + request.META.get("HTTP_HOST")
        group_app_url = "/".join([domain, "#/team", tar_team_name, "region", tar_region_name, "apps", str(tar_group_id)])
        serializers = GroupAppCopyCResSerializer(data={"group_app_url": group_app_url})
        serializers.is_valid(raise_exception=True)
        return Response(serializers.data, status=200)
