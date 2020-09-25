# -*- coding: utf8 -*-
"""
  Created on 18/5/23.
"""
import logging

from django.views.decorators.cache import never_cache
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.services.groupcopy_service import groupapp_copy_service
from openapi.serializer.app_serializer import ServiceBaseInfoSerializer
from openapi.serializer.groupapp_serializer import (AppCopyCResSerializer, AppCopyCSerializer, AppCopyLSerializer)
from openapi.views.base import TeamAPIView

logger = logging.getLogger('default')


class GroupAppsCopyView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="获取需要复制的应用组件信息",
        responses={200: AppCopyLSerializer(many=True)},
        tags=['openapi-apps'],
    )
    @never_cache
    def get(self, request, team_id, app_id, **kwargs):
        group_services = groupapp_copy_service.get_group_services_with_build_source(self.team,
                                                                                    self.region_name,
                                                                                    group_id=app_id)
        serializer = AppCopyLSerializer(data=group_services, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_description="复制应用",
        request_body=AppCopyCSerializer(),
        responses={
            status.HTTP_200_OK: AppCopyCResSerializer(),
            status.HTTP_400_BAD_REQUEST: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
        },
        tags=['openapi-apps'],
    )
    @never_cache
    def post(self, request, team_id, app_id, *args, **kwargs):
        """
        应用复制
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: app_id
              description: 应用id
              required: true
              type: int
              paramType: path
        """
        serializers = AppCopyCSerializer(data=request.data)
        serializers.is_valid(raise_exception=True)
        services = serializers.data.get("services")
        tar_team_name = request.data.get("target_team_name")
        tar_region_name = request.data.get("target_region_name")
        tar_app_id = request.data.get("target_app_id")
        tar_team, tar_group = groupapp_copy_service.check_and_get_team_group(request.user, tar_team_name, tar_region_name,
                                                                             tar_app_id)
        services = groupapp_copy_service.copy_group_services(request.user, self.team, self.region_name, tar_team,
                                                             tar_region_name, tar_group, app_id, services)
        services = ServiceBaseInfoSerializer(data=services, many=True)
        services.is_valid()
        serializers = AppCopyCResSerializer(data={"services": services.data})
        serializers.is_valid()
        return Response(serializers.data, status=200)
