# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

from console.exception.exceptions import EmailExistError
from console.exception.exceptions import PhoneExistError
from console.exception.exceptions import UserExistError
from console.exception.exceptions import UserNotExistError
from console.services.team_services import team_services
from console.services.user_services import user_services
from openapi.serializer.team_serializer import ListTeamRespSerializer
from openapi.serializer.user_serializer import CreateUserSerializer
from openapi.serializer.user_serializer import ListUsersRespView
from openapi.serializer.user_serializer import UpdateUserSerializer
from openapi.serializer.user_serializer import UserInfoSerializer
from openapi.serializer.user_serializer import ChangePassWdUserSerializer
from openapi.serializer.user_serializer import ChangePassWdSerializer
from openapi.views.base import BaseOpenAPIView
from openapi.views.base import ListAPIView
from www.models.main import Users

logger = logging.getLogger("default")


class ListUsersView(BaseOpenAPIView):
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
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10
        query = req.GET.get("query", "")
        users, total = user_services.list_users(page, page_size, query)
        serializer = UserInfoSerializer(users, many=True)
        result = {
            "users": serializer.data,
            "total": total,
        }
        return Response(result, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="添加普通用户",
        request_body=CreateUserSerializer,
        responses={},
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
            return Response(e.message, status.HTTP_400_BAD_REQUEST)


class UserInfoView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="根据用户ID获取用户信息",
        responses={200: UserInfoSerializer()},
        tags=['openapi-user'],
    )
    def get(self, req, user_id, *args, **kwargs):
        try:
            uid = int(user_id)
            user = user_services.get_user_by_user_id(uid)
        except (ValueError, UserNotExistError):
            try:
                user = user_services.get_user_by_user_name(req.user.enterprise_id, user_id)
            except UserNotExistError:
                return Response(None, status.HTTP_404_NOT_FOUND)
        serializer = UserInfoSerializer(user)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="删除用户",
        responses={},
        tags=['openapi-user'],
    )
    def delete(self, req, user_id, *args, **kwargs):
        try:
            user_services.delete_user(user_id)
            return Response()
        except Users.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="更新用户信息",
        request_body=UpdateUserSerializer,
        responses={},
        tags=['openapi-user'],
    )
    def put(self, req, user_id, *args, **kwargs):
        serializer = UpdateUserSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_services.update(user_id, req.data)
            return Response(None, status.HTTP_200_OK)
        except Users.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)


class UserTeamInfoView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取用户的团队列表",
        manual_parameters=[
            openapi.Parameter("eid", openapi.IN_QUERY, description="企业ID", type=openapi.TYPE_STRING),
            openapi.Parameter("query", openapi.IN_QUERY, description="团队名称搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListTeamRespSerializer()},
        tags=['openapi-user'],
    )
    def get(self, req, user_id, *args, **kwargs):
        eid = req.GET.get("eid", "")
        if not eid:
            raise serializers.ValidationError("缺少'eid'字段")
        query = req.GET.get("query", "")
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10
        # TODO 修改权限控制
        tenants, total = team_services.list_teams_by_user_id(
            eid=eid, user_id=user_id, query=query, page=page, page_size=page_size)
        result = {"tenants": tenants, "total": total}

        serializer = ListTeamRespSerializer(data=result)
        serializer.is_valid(raise_exception=True)

        return Response(result, status.HTTP_200_OK)


class ChangePassword(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="修改自己账号密码",
        request_body=ChangePassWdSerializer,
        responses={},
        tags=['openapi-user'],
    )
    def put(self, request, *args, **kwargs):
        """
        修改密码
        ---
        parameters:
            - name: password
              description: 新密码
              required: true
              type: string
              paramType: form
            - name: password1
              description: 确认密码
              required: true
              type: string
              paramType: form
        """
        serializer = ChangePassWdSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.data.get("password", None)
        new_password1 = serializer.data.get("password1", None)
        info = u"缺少参数"
        if new_password and new_password == new_password1:
            status, info = user_services.update_password(user_id=request.user.user_id, new_password=new_password)
            if status:
                return Response(None, status=200)
        logger.debug(info)
        return Response(None, status=400)


class ChangeUserPassword(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="修改用户密码",
        request_body=ChangePassWdUserSerializer,
        responses={},
        tags=['openapi-user'],
    )
    def put(self, request, *args, **kwargs):
        """
        修改密码
        ---
        parameters:
            - name: user_id
              description: 用户id
              required: true
              type: string
              paramType: form
            - name: password
              description: 新密码
              required: true
              type: string
              paramType: form
            - name: password1
              description: 确认密码
              required: true
              type: string
              paramType: form
        """
        serializer = ChangePassWdUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.data.get("user_id", None)
        new_password = serializer.data.get("password", None)
        new_password1 = serializer.data.get("password1", None)
        info = u"缺少参数"
        if new_password and new_password == new_password1:
            status, info = user_services.update_password(user_id=user_id, new_password=new_password)
            if status:
                return Response(None, status=200)
        logger.debug(info)
        return Response(None, status=400)
