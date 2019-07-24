# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

from backends.services.exceptions import EmailExistError
from backends.services.exceptions import PhoneExistError
from backends.services.exceptions import UserExistError
from console.services.user_services import user_services
from openapi.serializer.user_serializer import CreateUserSerializer
from openapi.serializer.user_serializer import ListUsersRespView
from openapi.serializer.user_serializer import UserInfoSerializer
from openapi.views.base import BaseOpenAPIView
from openapi.views.base import ListAPIView
from www.models.main import Users

logger = logging.getLogger("default")


class ListUsersView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取用户列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="用户名、邮箱、手机号搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListUsersRespView()},
        tags=['openapi-user'],
    )
    def get(self, req, *args, **kwargs):
        # TODO validation
        page = int(req.GET.get("page", 1))
        page_size = int(req.GET.get("page_size", 10))
        item = req.GET.get("query", "")
        users, total = user_services.list_users(page, page_size, item)
        serializer = UserInfoSerializer(users, many=True)
        result = {
            "users": serializer.data,
            "total": total,
        }
        return Response(result, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="添加普通用户",
        query_serializer=CreateUserSerializer,
        responses={
            status.HTTP_201_CREATED: None,
            status.HTTP_404_NOT_FOUND: None,
        },
        security=[],
        tags=['openapi-user'],
    )
    def post(self, req, *args, **kwargs):
        serializer = CreateUserSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        if not req.data.get("email", "") and not req.data.get("phone", ""):
            raise serializers.ValidationError('缺少参数 email 或 phone')

        try:
            user_services.create(req.data)
            return Response(None, status.HTTP_201_CREATED)
        except (UserExistError, EmailExistError, PhoneExistError) as e:
            return Response({"msg": e.message}, status.HTTP_400_BAD_REQUEST)


class UserInfoView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="根据用户ID获取用户信息",
        responses={200: UserInfoSerializer()},
        tags=['openapi-user'],
    )
    def get(self, req, user_id, *args, **kwargs):
        try:
            user = user_services.get_user_by_user_id(user_id)
            serializer = UserInfoSerializer(user)
            return Response(serializer.data)
        except Users.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="删除用户",
        manual_parameters=[
            openapi.Parameter("user_id", openapi.IN_QUERY, description="用户ID", type=openapi.TYPE_STRING),
        ],
        responses={
            status.HTTP_201_CREATED: None,
            status.HTTP_404_NOT_FOUND: None
        },
        tags=['openapi-user'],
    )
    def delete(self, req, *args, **kwargs):
        if not req.data.get("user_id", ""):
            raise serializers.ValidationError("缺少参数'user_id'")
        try:
            user_services.delete_user(req.GET.get("user_id"))
            return Response()
        except Users.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="更新用户信息",
        request_body=openapi.Schema(
            title="update user",
            type=openapi.TYPE_OBJECT,
            required=['nick_name'],
            properties={
                # user_id
                'nick_name': openapi.Schema(type=openapi.TYPE_STRING,  description="用户名"),
                'password': openapi.Schema(type=openapi.TYPE_STRING,  description="密码"),
                'email': openapi.Schema(type=openapi.TYPE_STRING,  description="邮箱"),
                'phone': openapi.Schema(type=openapi.TYPE_STRING,  description="手机号码"),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN,  description="是否激活"),
            },
        ),
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_404_NOT_FOUND: None,
        },
        security=[],
        tags=['openapi-user'],
    )
    def put(self, req, *args, **kwargs):
        if not req.data.get("nick_name", ""):
            raise serializers.ValidationError("缺少参数'nick_name'")
        try:
            user_services.update(req)
            return Response(None, status.HTTP_201_CREATED)
        except Users.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)
