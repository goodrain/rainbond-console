# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions
from rest_framework import status
from rest_framework.response import Response

from console.services.enterprise_services import enterprise_services
from openapi.serializer.appstore_serializer import AppStoreInfoSerializer
from openapi.serializer.appstore_serializer import ListAppStoreInfosRespSerializer
from openapi.serializer.appstore_serializer import UpdAppStoreInfoReqSerializer
from openapi.serializer.base_serializer import FailSerializer
from openapi.views.base import BaseOpenAPIView
from openapi.views.base import ListAPIView
from www.models.main import TenantEnterpriseToken

logger = logging.getLogger("default")


class ListAppStoresView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取应用市场信息列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="按企业名称, 企业别名搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={status.HTTP_200_OK: ListAppStoreInfosRespSerializer()},
        tags=['openapi-appstore'],
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
        query = req.GET.get("query", "")

        appstores, total = enterprise_services.list_appstore_infos(query, page, page_size)
        serializer = ListAppStoreInfosRespSerializer({"appstores": appstores, "total": total})
        return Response(serializer.data, status.HTTP_200_OK)


class AppStoreInfoView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="修改应用市场信息",
        request_body=UpdAppStoreInfoReqSerializer(),
        responses={
            status.HTTP_200_OK: AppStoreInfoSerializer(),
            status.HTTP_404_NOT_FOUND: FailSerializer(),
        },
        tags=['openapi-appstore'],
    )
    def put(self, req, eid):
        serializer = UpdAppStoreInfoReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        if enterprise_services.get_enterprise_by_id(eid) is None:
            raise exceptions.NotFound({"msg": "企业'{}'不存在".format(eid)})

        try:
            res = enterprise_services.update_appstore_info(eid, req.data)
        except TenantEnterpriseToken:
            raise exceptions.NotFound({"msg": "应用市场信息不存在 {}".format(eid)})

        serializer = AppStoreInfoSerializer(res)
        return Response(serializer.data, status=status.HTTP_200_OK)
