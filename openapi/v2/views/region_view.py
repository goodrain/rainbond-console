# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.exception.exceptions import RegionUnreachableError
from console.models.main import RegionConfig
from console.services.region_services import (RegionExistException, region_services)
from openapi.serializer.base_serializer import FailSerializer
from openapi.v2.serializer.region_serializer import (ListRegionsRespSerializer, RegionInfoSerializer, UpdateRegionReqSerializer,
                                                     UpdateRegionStatusReqSerializer)
from openapi.v2.views.base import BaseOpenAPIView, ListAPIView
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class ListRegionInfo(ListAPIView):
    view_perms = ["regions"]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="根据数据中心名称搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("current", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("pageSize", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListRegionsRespSerializer()},
        tags=['openapi-region'],
        operation_description="获取全部数据中心列表")
    def get(self, req):
        query = req.GET.get("query", "")
        try:
            page = int(req.GET.get("current", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("pageSize", 99))
        except ValueError:
            page_size = 99
        regions, total = region_services.get_regions_with_resource(query, page, page_size)
        serializer = ListRegionsRespSerializer(data={"data": regions, "total": total})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="添加数据中心",
        request_body=openapi.Schema(
            title="AddRegionRequest",
            type=openapi.TYPE_OBJECT,
            required=['region_name', 'region_alias', 'url', 'wsurl', 'httpdomain', 'tcpdomain'],
            properties={
                'region_name': openapi.Schema(type=openapi.TYPE_STRING),
                'region_alias': openapi.Schema(type=openapi.TYPE_STRING),
                'url': openapi.Schema(type=openapi.TYPE_STRING),
                'wsurl': openapi.Schema(type=openapi.TYPE_STRING),
                'httpdomain': openapi.Schema(type=openapi.TYPE_STRING),
                'tcpdomain': openapi.Schema(type=openapi.TYPE_STRING),
                'scope': openapi.Schema(type=openapi.TYPE_STRING),
                'ssl_ca_cert': openapi.Schema(type=openapi.TYPE_STRING),
                'cert_file': openapi.Schema(type=openapi.TYPE_STRING),
                'key_file': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                'desc': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            status.HTTP_201_CREATED: RegionInfoSerializer(),
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
            status.HTTP_400_BAD_REQUEST: FailSerializer(),
        },
        tags=['openapi-region'],
    )
    def post(self, request):
        try:
            serializer = RegionInfoSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            region_data = serializer.data
            region_data["region_id"] = make_uuid()
            region = region_services.add_region(region_data)
            serializer = RegionInfoSerializer(region)
            if region:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(None, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except RegionExistException as e:
            logger.exception(e)
            return Response({"msg": e.message}, status=status.HTTP_400_BAD_REQUEST)


class RegionInfo(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取指定数据中心数据",
        responses={
            status.HTTP_200_OK: RegionInfoSerializer(),
            status.HTTP_404_NOT_FOUND: FailSerializer(),
        },
        tags=['openapi-region'],
    )
    def get(self, request, region_id):
        try:
            queryset = region_services.get_region_by_region_id(region_id)
            serializer = RegionInfoSerializer(queryset)
            return Response(serializer.data)
        except RegionConfig.DoesNotExist:
            return Response({"msg": "数据中心不存在"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="更新指定数据中心元数据",
        request_body=UpdateRegionReqSerializer(),
        responses={
            200: RegionInfoSerializer(),
            400: FailSerializer(),
            404: FailSerializer(),
        },
        tags=['openapi-region'],
    )
    def put(self, request, region_id):
        serializer = UpdateRegionReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        region_data = serializer.data
        if not region_id:
            return Response({"msg": "RegionID不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            region_services.get_region_by_region_id(region_id)
        except RegionConfig.DoesNotExist:
            # TODO: raise exception or return Response
            return Response({"msg": "修改的数据中心不存在"}, status=status.HTTP_404_NOT_FOUND)
        region_data["region_id"] = region_id
        new_region = region_services.update_region(region_data)
        serializer = RegionInfoSerializer(new_region)
        return Response(serializer.data, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除指定数据中心元数据",
        responses={
            200: RegionInfoSerializer(),
            404: FailSerializer(),
        },
        tags=['openapi-region'],
    )
    def delete(self, request, region_id):
        try:
            region = region_services.del_by_region_id(region_id)
            serializer = RegionInfoSerializer(data=region)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status.HTTP_200_OK)
        except RegionConfig.DoesNotExist:
            # TODO: raise exception or return Response
            return Response({"msg": "修改的数据中心不存在"}, status=status.HTTP_404_NOT_FOUND)


class RegionStatusView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="修改数据中心的状态(上线, 下线, 设为维护)",
        request_body=UpdateRegionStatusReqSerializer(),
        responses={
            status.HTTP_200_OK: RegionInfoSerializer(),
            status.HTTP_404_NOT_FOUND: FailSerializer(),
            status.HTTP_400_BAD_REQUEST: FailSerializer(),
        },
        tags=['openapi-region'],
    )
    def put(self, req, region_id):
        serializer = UpdateRegionStatusReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        try:
            region = region_services.update_region_status(region_id, req.data["status"])
            serializer = RegionInfoSerializer(region)
            return Response(serializer.data, status.HTTP_200_OK)
        except RegionConfig.DoesNotExist:
            fs = FailSerializer({"msg": "数据中心不存在"})
            return Response(fs.data, status.HTTP_404_NOT_FOUND)
        except RegionUnreachableError as e:
            fs = FailSerializer({"msg": e.message})
            return Response(fs.data, status.HTTP_400_BAD_REQUEST)
