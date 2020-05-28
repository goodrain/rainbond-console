# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.services.announcement_service import announcement_service
from openapi.serializer.announcement_serializer import CreateAncmReqSerilizer
from openapi.serializer.announcement_serializer import ListAnnouncementRespSerializer
from openapi.serializer.announcement_serializer import UpdateAncmReqSerilizer
from openapi.views.base import BaseOpenAPIView

logger = logging.getLogger("default")


class ListAnnouncementView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取站内信列表",
        manual_parameters=[
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListAnnouncementRespSerializer()},
        tags=['openapi-announcement'],
    )
    def get(self, req):
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10
        ancm, total = announcement_service.list(page, page_size)
        serializer = ListAnnouncementRespSerializer({"total": total, "announcements": ancm})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="添加站内信",
        request_body=CreateAncmReqSerilizer(),
        responses={status.HTTP_201_CREATED: None},
        tags=['openapi-announcement'],
    )
    def post(self, request, **kwargs):
        announcement_service.create(request.data)
        return Response(None, status.HTTP_201_CREATED)


class AnnouncementView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="更新站内信",
        request_body=UpdateAncmReqSerilizer(),
        responses={200: None},
        tags=['openapi-announcement'],
    )
    def put(self, req, aid, *args, **kwargs):
        serializer = UpdateAncmReqSerilizer(data=req.data)
        serializer.is_valid(raise_exception=True)
        announcement_service.update(aid, req.data)
        return Response(None, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除站内信",
        responses={200: None},
        tags=['openapi-announcement'],
    )
    def delete(self, request, aid, *args, **kwargs):
        announcement_service.delete(aid)
        return Response(None, status.HTTP_200_OK)
