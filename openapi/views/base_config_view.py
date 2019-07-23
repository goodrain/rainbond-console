# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from backends.services.configservice import config_service
from openapi.serializer.base_cfg_serializers import BaseCfgSerializer
from openapi.views.base import BaseOpenAPIView

logger = logging.getLogger("default")


class BaseConfigView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取基础配置",
        responses={200: BaseCfgSerializer()},
        tags=['openapi-title'],
    )
    def get(self, request):
        key = request.GET.get("key")
        queryset = config_service.get_by_key(key)
        serializer = BaseCfgSerializer(queryset)
        return Response(serializer.data)

    def put(self, request):
        config_service.update(request.data)
        return Response(None, status=status.HTTP_200_OK)
