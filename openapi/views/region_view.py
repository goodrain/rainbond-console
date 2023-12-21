# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.exception.exceptions import RegionUnreachableError
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig
from console.services.region_services import region_services
from console.services.region_services import RegionExistException
from openapi.serializer.base_serializer import FailSerializer
from openapi.serializer.region_serializer import RegionInfoRespSerializer
from openapi.serializer.region_serializer import RegionInfoRSerializer
from openapi.serializer.region_serializer import RegionInfoSerializer
from openapi.serializer.region_serializer import UpdateRegionStatusReqSerializer
from openapi.views.base import BaseOpenAPIView
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class ListRegionInfo(BaseOpenAPIView):
    view_perms = ["regions"]

    @swagger_auto_schema(responses={200: RegionInfoRespSerializer(many=True)},
                         tags=['openapi-region'],
                         operation_description="获取全部数据中心列表")
    def get(self, req):
        regions = region_services.get_enterprise_regions(self.enterprise.enterprise_id, level="")
        serializer = RegionInfoRespSerializer(data=regions, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="添加数据中心",
        request_body=openapi.Schema(
            title="AddRegionRequest",
            type=openapi.TYPE_OBJECT,
            required=['region_name', 'region_alias', 'url', 'wsurl', 'httpdomain', 'tcpdomain'],
            properties={
                'region_name': openapi.Schema(type=openapi.TYPE_STRING, description="集群ID"),
                'region_alias': openapi.Schema(type=openapi.TYPE_STRING, description="集群别名"),
                'url': openapi.Schema(type=openapi.TYPE_STRING),
                'wsurl': openapi.Schema(type=openapi.TYPE_STRING),
                'httpdomain': openapi.Schema(type=openapi.TYPE_STRING),
                'tcpdomain': openapi.Schema(type=openapi.TYPE_STRING),
                'scope': openapi.Schema(type=openapi.TYPE_STRING),
                'ssl_ca_cert': openapi.Schema(type=openapi.TYPE_STRING),
                'cert_file': openapi.Schema(type=openapi.TYPE_STRING),
                'key_file': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                'desc': openapi.Schema(type=openapi.TYPE_STRING, description="备注"),
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
            region = region_services.add_region(region_data, request.user)
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
        manual_parameters=[
            openapi.Parameter("region_id", openapi.IN_QUERY, description="数据中心名称、id", type=openapi.TYPE_STRING),
            openapi.Parameter("extend_info",
                              openapi.IN_QUERY,
                              description="是否需要额外数据",
                              type=openapi.TYPE_STRING,
                              enum=["true", "false"]),
        ],
        responses={
            status.HTTP_200_OK: RegionInfoRSerializer(),
        },
        tags=['openapi-region'],
    )
    def get(self, request, region_id, *args, **kwargs):
        extend_info = request.GET.get("extend_info", False)
        if extend_info == "true":
            extend_info = True
        else:
            extend_info = False
        if extend_info:
            extend_info = "yes"
        if not self.region:
            raise ServiceHandleException(msg="no found region", msg_show="数据中心不存在", status_code=404)

        data = region_services.get_enterprise_region(self.enterprise.enterprise_id,
                                                     self.region.region_id,
                                                     check_status=extend_info)
        serializers = RegionInfoRSerializer(data=data)
        serializers.is_valid(raise_exception=True)
        return Response(serializers.data, status=200)

    # @swagger_auto_schema(
    #     operation_description="更新指定数据中心元数据",
    #     request_body=UpdateRegionReqSerializer(),
    #     responses={
    #         200: RegionInfoSerializer(),
    #         400: FailSerializer(),
    #         404: FailSerializer(),
    #     },
    #     tags=['openapi-region'],
    # )
    # def put(self, request, region_id):
    #     serializer = UpdateRegionReqSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     region_data = serializer.data
    #     if not region_id:
    #         return Response({"msg": "RegionID不能为空"}, status=status.HTTP_400_BAD_REQUEST)
    #     try:
    #         region_services.get_region_by_region_id(region_id)
    #     except RegionConfig.DoesNotExist:
    #         # TODO: raise exception or return Response
    #         return Response({"msg": "修改的数据中心不存在"}, status=status.HTTP_404_NOT_FOUND)
    #     region_data["region_id"] = region_id
    #     new_region = region_services.update_region(region_data)
    #     serializer = RegionInfoSerializer(new_region)
    #     return Response(serializer.data, status.HTTP_200_OK)
    #
    # @swagger_auto_schema(
    #     operation_description="删除指定数据中心元数据",
    #     responses={
    #         200: RegionInfoSerializer(),
    #         404: FailSerializer(),
    #     },
    #     tags=['openapi-region'],
    # )
    # def delete(self, request, region_id):
    #     try:
    #         region = region_services.del_by_region_id(region_id)
    #         serializer = RegionInfoSerializer(data=region)
    #         serializer.is_valid(raise_exception=True)
    #         return Response(serializer.data, status.HTTP_200_OK)
    #     except RegionConfig.DoesNotExist:
    #         # TODO: raise exception or return Response
    #         return Response({"msg": "修改的数据中心不存在"}, status=status.HTTP_404_NOT_FOUND)


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


class ReplaceRegionIP(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="通过grctl修改region ip",
        tags=['openapi-region'],
    )
    def post(self, request):
        region_name = request.data.get("region_name", "")
        region_info = region_services.get_by_region_name(region_name)
        region_id = region_info.region_id
        try:
            region_data = {
                "region_name": region_name,
                "ssl_ca_cert": request.data.get("ssl_ca_cert", ""),
                "key_file": request.data.get("key_file", ""),
                "cert_file": request.data.get("cert_file", ""),
                "url": request.data.get("url", ""),
                "wsurl": request.data.get("ws_url", ""),
                "httpdomain": request.data.get("http_domain", ""),
                "tcpdomain": request.data.get("tcp_domain", ""),
                "region_id": region_id,
            }
            region_services.update_region(region_data)
            result = general_message(200, "success", "更新成功")
            return Response(result, status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "failed", "更新失败")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
