# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from django.urls import get_script_prefix
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response

from console.services.enterprise_services import enterprise_services
from openapi.serializer.ent_serializers import EnterpriseInfoSerializer
from openapi.views.base import ListAPIView

logger = logging.getLogger("default")


class ListEnterpriseInfo(ListAPIView):
    view_perms = ["teams"]
    get_script_prefix()

    @swagger_auto_schema(
        responses={200: EnterpriseInfoSerializer(many=True)},
        tags=['openapi-team'],
    )
    def get(self, request):
        queryset = enterprise_services.list_all()
        serializer = EnterpriseInfoSerializer(queryset, many=True)
        return Response(serializer.data)
