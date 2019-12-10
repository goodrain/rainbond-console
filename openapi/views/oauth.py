# -*- coding: utf8 -*-
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework.response import Response
from rest_framework import status
from rest_framework_jwt.settings import api_settings

from console.utils.oauthutil import OAuthType
from openapi.views.base import ListAPIView

from openapi.serializer.oauth_serializer import OAuthTypeSerializer


logger = logging.getLogger("default")

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class OauthTypeView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取oauth类型",
        responses={200: OAuthTypeSerializer()},
        tags=['openapi-oauth'],
    )
    def get(self, request):
        data = list(OAuthType.OAuthType)
        serializer = OAuthTypeSerializer(data={"type": data})
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)
