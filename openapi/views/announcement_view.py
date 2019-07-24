# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from backends.models.main import Announcement
from console.services.announcement_service import AnnouncementService
from openapi.serializer.announcement_serializer import AnnouncementRespSerilizer
from openapi.views.base import BaseOpenAPIView
from openapi.views.base import ListAPIView

logger = logging.getLogger("default")


class ListAnnouncementView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取站内信列表",
        responses={200: AnnouncementRespSerilizer(many=True)},
        tags=['openapi-announcement'],
    )
    def get(self, request):
        queryset = Announcement.objects.all().order_by('-create_time')
        serializer = AnnouncementRespSerilizer(queryset, many=True)
        return Response(serializer.data)


class AnnouncementView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="添加站内信",
        request_body=openapi.Schema(
            title="new announcement",
            type=openapi.TYPE_OBJECT,
            required=['content', 'type', 'active', 'title', 'level'],
            properties={
                'content': openapi.Schema(type=openapi.TYPE_STRING,  description="通知内容"),
                'type': openapi.Schema(type=openapi.TYPE_STRING,  description="通知类型"),
                'active': openapi.Schema(type=openapi.TYPE_STRING,  description="是否开启"),
                'title': openapi.Schema(type=openapi.TYPE_STRING,  description="标题"),
                'level': openapi.Schema(type=openapi.TYPE_STRING,  description="等级"),
                'a_tag': openapi.Schema(type=openapi.TYPE_STRING, description="A标签文字"),
                'a_tag_url': openapi.Schema(type=openapi.TYPE_STRING, description="A标签跳转地址"),
            },
        ),
        responses={200: AnnouncementRespSerilizer(many=True)},
        tags=['openapi-announcement'],
    )
    def post(self, request, **kwargs):
        svc = AnnouncementService()
        svc.create(request.data)
        return Response(None, status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="更新站内信",
        request_body=openapi.Schema(
            title="update announcement",
            type=openapi.TYPE_OBJECT,
            required=['aid'],
            properties={
                'aid': openapi.Schema(type=openapi.TYPE_STRING, description="唯一标识"),
                'content': openapi.Schema(type=openapi.TYPE_STRING, description="通知内容"),
                'a_tag': openapi.Schema(type=openapi.TYPE_STRING, description="A标签文字"),
                'a_tag_url': openapi.Schema(type=openapi.TYPE_STRING, description="A标签跳转地址"),
                'type': openapi.Schema(type=openapi.TYPE_STRING, description="通知类型"),
                'active': openapi.Schema(type=openapi.TYPE_STRING, description="是否开启"),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description="标题"),
                'level': openapi.Schema(type=openapi.TYPE_STRING, description="等级"),
            },
        ),
        responses={200: AnnouncementRespSerilizer(many=True)},
        tags=['openapi-announcement'],
    )
    def put(self, request, *args, **kwargs):
        svc = AnnouncementService()
        svc.update(request.data)
        return Response(None, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除站内信",
        request_body=openapi.Schema(
            title="delete announcement",
            type=openapi.TYPE_OBJECT,
            required=['aid'],
            properties={
                'aid': openapi.Schema(type=openapi.TYPE_STRING, description="唯一标识"),
            },
        ),
        responses={200: None},
        tags=['openapi-announcement'],
    )
    def delete(self, request, *args, **kwargs):
        svc = AnnouncementService()
        svc.delete(request.data["aid"])
        return Response(None, status.HTTP_200_OK)
