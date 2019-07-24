# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.services.user_services import user_services
from openapi.serializer.user_serializer import ListUsersSerializer
from openapi.serializer.user_serializer import UserInfoSerializer
from openapi.views.base import ListAPIView
# from openapi.views.base import BaseOpenAPIView

logger = logging.getLogger("default")


class ListUsersView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取用户列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="用户名、邮箱、手机号搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListUsersSerializer()},
        tags=['openapi-user'],
    )
    def get(self, req, *args, **kwargs):
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
