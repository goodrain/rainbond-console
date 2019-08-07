# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.models.main import ConsoleSysConfig
from console.services.config_service import config_service
from console.services.enterprise_services import enterprise_services
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
    def get(self, req):
        ent = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=req.user.enterprise_id)
        if ent is None:
            raise Response({"msg": "企业不存在"}, status.HTTP_404_NOT_FOUND)
        data = config_service.list_by_keys(config_service.base_cfg_keys)
        data["ENTERPRISE_ALIAS"] = ent.enterprise_alias
        serializer = BaseConfigRespSerializer(data)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="更新基础配置",
        request_body=UpdateBaseConfigReqSerializer(),
        responses={200: None},
        tags=['openapi-config'],
    )
    @transaction.atomic
    def put(self, req):
        serializer = UpdateBaseConfigReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)
        config_service.update_or_create(req.user.enterprise_id, req.data)
        return Response(None, status=status.HTTP_200_OK)


class ListFeatureConfigView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取全部功能配置",
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


class FeatureConfigView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取指定的功能配置",
        responses={200: FeatureConfigRespSerializer()},
        tags=['openapi-config'],
    )
    def get(self, req, key):
        queryset = config_service.list_by_keys([key])
        serializer = FeatureConfigRespSerializer(queryset)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="删除指定的功能配置",
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_404_NOT_FOUND: None
        },
        tags=['openapi-config'],
    )
    def delete(self, req, key):
        try:
            config_service.delete_by_key(key)
        except ConsoleSysConfig.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)
        return Response(None, status.HTTP_200_OK)
