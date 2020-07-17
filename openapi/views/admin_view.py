# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

from console.exception.exceptions import UserNotExistError
from console.services.enterprise_services import enterprise_services
from console.services.exception import ErrAdminUserDoesNotExist
from console.services.exception import ErrCannotDelLastAdminUser
from console.services.user_services import user_services
from openapi.serializer.base_serializer import FailSerializer
from openapi.serializer.user_serializer import CreateAdminUserReqSerializer
from openapi.serializer.user_serializer import ListUsersRespView
from openapi.serializer.user_serializer import UserInfoSerializer
from openapi.views.base import BaseOpenAPIView

logger = logging.getLogger("default")


class ListAdminsView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取企业管理员列表",
        manual_parameters=[
            openapi.Parameter("eid", openapi.IN_QUERY, description="企业ID", type=openapi.TYPE_STRING),
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
        eid = req.GET.get("eid", None)

        users, total = user_services.list_admin_users(page, page_size, eid)
        serializer = UserInfoSerializer(users, many=True)
        result = {
            "users": serializer.data,
            "total": total,
        }
        return Response(result, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="添加企业用户",
        request_body=CreateAdminUserReqSerializer,
        responses={},
        tags=['openapi-user'],
    )
    def post(self, req, *args, **kwargs):
        serializer = CreateAdminUserReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = user_services.get_user_by_user_id(req.data["user_id"])
        except UserNotExistError:
            raise exceptions.NotFound("用户'{}'不存在".format(req.data["user_id"]))
        ent = enterprise_services.get_enterprise_by_enterprise_id(req.data["eid"])
        if ent is None:
            raise serializers.ValidationError("企业'{}'不存在".format(req.data["eid"]), status.HTTP_404_NOT_FOUND)

        user_services.create_admin_user(user, ent)

        return Response(None, status.HTTP_201_CREATED)


class AdminInfoView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="删除企业管理员",
        responses={
            status.HTTP_400_BAD_REQUEST: FailSerializer(),
            status.HTTP_404_NOT_FOUND: FailSerializer(),
        },
        tags=['openapi-user'],
    )
    def delete(self, req, user_id, *args, **kwargs):
        if str(req.user.user_id) == user_id:
            raise serializers.ValidationError({"msg": "不能删除自己"}, status.HTTP_400_BAD_REQUEST)
        try:
            user_services.delete_admin_user(user_id)
            return Response(None, status.HTTP_200_OK)
        except ErrAdminUserDoesNotExist as e:
            raise exceptions.NotFound(detail="用户'{}'不是企业管理员".format(user_id))
        except ErrCannotDelLastAdminUser as e:
            raise serializers.ValidationError({"msg": e.message}, status.HTTP_400_BAD_REQUEST)
