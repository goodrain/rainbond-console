# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.services.config_service import config_service
from openapi.serializer.config_serializers import BaseConfigRespSerializer
from openapi.serializer.config_serializers import FeatureConfigRespSerializer
from openapi.views.base import BaseOpenAPIView

logger = logging.getLogger("default")


class BaseConfigView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取基础配置",
        responses={200: BaseConfigRespSerializer()},
        tags=['openapi-config'],
    )
    def get(self, request):
        queryset = config_service.list_by_keys(config_service.base_cfg_keys)
        serializer = BaseConfigRespSerializer(queryset)
        return Response(serializer.data)

    def put(self, request):
        config_service.update(request.data)
        return Response(None, status=status.HTTP_200_OK)


class FeatureConfigView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取特性配置",
        responses={200: FeatureConfigRespSerializer()},
        tags=['openapi-config'],
    )
    def get(self, request):
        queryset = config_service.list_by_keys(config_service.feature_cfg_keys)
        serializer = FeatureConfigRespSerializer(queryset)
        return Response(serializer.data)

    def put(self, request):
        config_service.update(request.data)
        return Response(None, status=status.HTTP_200_OK)
