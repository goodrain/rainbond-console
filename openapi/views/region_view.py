# -*- coding: utf-8 -*-
# creater by: barnett
import logging
from console.services.region_services import region_services
from console.services.region_services import RegionExistException
from openapi.views.base import ListAPIView
from rest_framework import status
from rest_framework.response import Response
from drf_yasg import openapi
from www.utils.crypt import make_uuid
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.region_serializer import RegionInfoSerializer
from django.urls import get_script_prefix

logger = logging.getLogger("default")


class ListRegionInfo(ListAPIView):
    view_perms = ["regions"]
    get_script_prefix()

    @swagger_auto_schema(
        query_serializer=RegionInfoSerializer,
        responses={200: RegionInfoSerializer(many=True)},
        tags=['openapi-region'],
    )
    def get(self, request):
        queryset = region_services.get_all_regions()
        serializer = RegionInfoSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="add region",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['region_name', 'region_alias', 'url', 'wsurl', 'httpdomain', 'tcpdomain'],
            properties={
                'region_name': openapi.Schema(type=openapi.TYPE_STRING),
                'region_alias': openapi.Schema(type=openapi.TYPE_STRING),
                'url': openapi.Schema(type=openapi.TYPE_STRING),
                'token': openapi.Schema(type=openapi.TYPE_STRING),
                'wsurl': openapi.Schema(type=openapi.TYPE_STRING),
                'httpdomain': openapi.Schema(type=openapi.TYPE_STRING),
                'tcpdomain': openapi.Schema(type=openapi.TYPE_STRING),
                'scope': openapi.Schema(type=openapi.TYPE_STRING),
                'ssl_ca_cert': openapi.Schema(type=openapi.TYPE_STRING),
                'cert_file': openapi.Schema(type=openapi.TYPE_STRING),
                'key_file': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            status.HTTP_201_CREATED: RegionInfoSerializer(),
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
            status.HTTP_400_BAD_REQUEST: None,
        },
        security=[],
        tags=['openapi-region'],
    )
    def post(self, request):
        try:
            serializer = RegionInfoSerializer(request.data)
            serializer.is_valid(raise_exception=True)
            region_data = serializer.data
            region_data["region_id"] = make_uuid()
            region = region_services.add_region(region_data)
            if region:
                return Response(region, status=status.HTTP_201_CREATED)
            else:
                return Response(None, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except RegionExistException as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
