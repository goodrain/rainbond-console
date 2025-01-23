# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from console.exception.exceptions import (EmailExistError, PhoneExistError, UserExistError, UserNotExistError)
from console.exception.main import ServiceHandleException
from console.repositories.group import group_repo
from console.repositories.user_repo import user_repo
from console.services.app_actions import app_manage_service
from console.services.app_config_group import app_config_group_service
from console.services.group_service import group_service
from console.services.k8s_resource import k8s_resource_service
from console.services.user_services import user_services
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.user_serializer import (ChangePassWdSerializer, ChangePassWdUserSerializer, CreateUserSerializer,
                                                ListUsersRespView, UpdateUserSerializer, UserInfoSerializer)
from openapi.views.base import BaseOpenAPIView
from rest_framework import serializers, status
from rest_framework.response import Response
from www.models.main import Users, Tenants
from www.utils.return_message import general_message

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
        info = "缺少参数"
        if new_password and new_password == new_password1:
            status, info = user_services.update_password(user_id=request.user.user_id, new_password=new_password)
            oauth_instance, _ = user_services.check_user_is_enterprise_center_user(request.user.user_id)
            if oauth_instance:
                data = {
                    "password": new_password,
                    "real_name": request.user.real_name,
                }
                oauth_instance.update_user(request.user.enterprise_id, request.user.enterprise_center_user_id, data)
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
        info = "缺少参数"
        user = user_repo.get_enterprise_user_by_id(request.user.enterprise_id, user_id)
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show="用户不存在", status_code=404)
        if new_password and new_password == new_password1:
            status, info = user_services.update_password(user_id=user_id, new_password=new_password)
            oauth_instance, _ = user_services.check_user_is_enterprise_center_user(user_id)
            if oauth_instance:
                data = {
                    "password": new_password,
                    "real_name": user.real_name,
                }
                oauth_instance.update_user(request.user.enterprise_id, user.enterprise_center_user_id, data)
            if status:
                return Response(None, status=200)
        logger.debug(info)
        return Response(None, status=400)


class CurrentUsersView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取当前用户信息",
        manual_parameters=[],
        tags=['openapi-user'],
    )
    def get(self, req, *args, **kwargs):
        if req.user:
            user_info = req.user.to_dict()
            res = {
                "user_id": user_info["user_id"],
                "email": user_info["email"],
                "nick_name": user_info["nick_name"],
                "real_name": user_info["real_name"],
                "phone": user_info["phone"],
                "is_active": user_info["is_active"],
                "origion": user_info["origion"],
                "enterprise_id": user_info["enterprise_id"]
            }
            return Response({"bean": res}, status=200)
        return Response(None, status=400)


class UserTenantClose(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="根据用户ID关闭所有团队",
        tags=['openapi-user'],
    )
    def get(self, req, user_id, *args, **kwargs):
        uid = int(user_id)
        user = user_services.get_user_by_user_id(uid)
        tenants = Tenants.objects.filter(creater=uid)
        user.nick_name = "系统（余额不足）"
        for tenant in tenants:
            app_manage_service.close_all_component_in_team(tenant, user)
        return Response({"bean": "close success"}, status=200)


class UserTenantDelete(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="根据用户ID删除团队下所有应用",
        tags=['openapi-user'],
    )
    def get(self, req, user_id, *args, **kwargs):
        uid = int(user_id)
        tenants = Tenants.objects.filter(creater=uid)
        user = user_services.get_user_by_user_id(uid)
        for tenant in tenants:
            apps = group_repo.get_groups_by_tenant_id(tenant.tenant_id)
            for app in apps:
                app_id = app.app_id
                group_service.batch_delete_app_services(user, tenant.tenant_id, app.region_name, app_id)
                # delete k8s resource
                k8s_resources = k8s_resource_service.list_by_app_id(str(app_id))
                resource_ids = [k8s_resource.ID for k8s_resource in k8s_resources]
                k8s_resource_service.batch_delete_k8s_resource(user.enterprise_id, tenant.tenant_name, str(app_id),
                                                               app.region_name, resource_ids)
                # delete configs
                app_config_group_service.batch_delete_config_group(app.region_name, tenant.tenant_name, app_id)
                # delete records
                group_service.delete_app_share_records(tenant.tenant_name, app_id)
                # delete app
                app = group_service.get_app_by_id(tenant, app.region_name, app_id)
                group_service.delete_app(tenant, app.region_name, app)
        return Response({"bean": "delete success"}, status=200)