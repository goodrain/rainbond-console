# -*- coding: utf-8 -*-
# creater by: barnett
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.exceptions import UserNotExistError
from openapi.serializer.base_serializer import FailSerializer
from openapi.serializer.base_serializer import TokenSerializer
from openapi.services.api_user_service import apiUserService


class TokenInfoView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(responses={
        200: TokenSerializer(),
        status.HTTP_400_BAD_REQUEST: FailSerializer(),
        status.HTTP_404_NOT_FOUND: FailSerializer(),
    },
                         request_body=openapi.Schema(
                             title="AuthRequest",
                             type=openapi.TYPE_OBJECT,
                             required=['username', 'password'],
                             properties={
                                 'username': openapi.Schema(type=openapi.TYPE_STRING, description="管理员用户名"),
                                 'password': openapi.Schema(type=openapi.TYPE_STRING, description="管理员密码"),
                             },
                         ),
                         tags=['openapi-auth'],
                         operation_description="企业管理员账号密码获取API-Token")
    def post(self, request):
        username = request.data.get("username", None)
        password = request.data.get("password", None)
        if not username or not password:
            return Response({"msg": "用户名或密码不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = apiUserService.login_api_user(username, password)
            if token:
                return Response({"token": token}, status=status.HTTP_200_OK)
            return Response({"msg": "用户名或密码错误或用户不是管理员用户"}, status=status.HTTP_400_BAD_REQUEST)
        except UserNotExistError as e:
            return Response({"msg": e.message}, status=status.HTTP_404_NOT_FOUND)
