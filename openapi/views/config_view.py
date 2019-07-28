# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.services.config_service import config_service
from openapi.serializer.config_serializers import BaseConfigRespSerializer
from openapi.serializer.config_serializers import FeatureConfigRespSerializer
from openapi.serializer.config_serializers import UpdateBaseConfigReqSerializer
from openapi.serializer.config_serializers import UpdateFeatureCfgReqSerializer
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

    @swagger_auto_schema(
        operation_description="更新基础配置",
        request_body=UpdateBaseConfigReqSerializer(),
        responses={200: None},
        tags=['openapi-config'],
    )
    @transaction.atomic
    def put(self, request):
        serializer = UpdateBaseConfigReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config_service.update(request.data)
        return Response(None, status=status.HTTP_200_OK)


class FeatureConfigView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取功能配置",
        responses={200: FeatureConfigRespSerializer()},
        tags=['openapi-config'],
    )
    def get(self, request):
        queryset = config_service.list_by_keys(config_service.feature_cfg_keys)
        serializer = FeatureConfigRespSerializer(queryset)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="新增或更新功能配置",
        request_body=UpdateFeatureCfgReqSerializer(),
        responses={200: None},
        tags=['openapi-config'],
    )
    def put(self, request):
        serializer = UpdateFeatureCfgReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config_service.update_or_create(request.data)
        return Response(None, status=status.HTTP_200_OK)
