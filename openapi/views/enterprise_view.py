# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from django.urls import get_script_prefix
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.services.enterprise_services import enterprise_services
from openapi.serializer.ent_serializers import EnterpriseInfoSerializer
from openapi.serializer.ent_serializers import UpdEntReqSerializer
from openapi.views.base import BaseOpenAPIView
from openapi.views.base import ListAPIView

logger = logging.getLogger("default")


class ListEnterpriseInfo(ListAPIView):
    view_perms = ["enterprises"]
    get_script_prefix()

    @swagger_auto_schema(
        responses={200: EnterpriseInfoSerializer(many=True)},
        tags=['openapi-entreprise'],
    )
    def get(self, request):
        queryset = enterprise_services.list_all()
        serializer = EnterpriseInfoSerializer(queryset, many=True)
        return Response(serializer.data)


class EnterpriseInfo(BaseOpenAPIView):
    @swagger_auto_schema(
        query_serializer=UpdEntReqSerializer,
        responses={200: None},
        tags=['openapi-entreprise'],
    )
    def put(self, request):
        enterprise_services.update(request.data)
        return Response(None, status=status.HTTP_200_OK)
