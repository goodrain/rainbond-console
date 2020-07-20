# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from django.db import connection
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.models.main import EnterpriseUserPerm
from console.repositories.user_repo import user_repo
from console.services.config_service import EnterpriseConfigService
from console.services.enterprise_services import enterprise_services
from console.services.region_services import region_services
from console.utils.timeutil import time_to_str
from openapi.serializer.config_serializers import EnterpriseConfigSeralizer
from openapi.serializer.ent_serializers import (EnterpriseInfoSerializer, EnterpriseSourceSerializer, ListEntsRespSerializer,
                                                UpdEntReqSerializer)
from openapi.views.base import BaseOpenAPIView, ListAPIView
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class ListEnterpriseInfoView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取企业列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="按企业名称, 企业别名搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={status.HTTP_200_OK: ListEntsRespSerializer()},
        tags=['openapi-entreprise'],
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

        ents, total = enterprise_services.list_all(query, page, page_size)
        serializer = ListEntsRespSerializer({"ents": ents, "total": total})
        return Response(serializer.data, status.HTTP_200_OK)


class EnterpriseInfoView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="更新企业信息",
        query_serializer=UpdEntReqSerializer,
        responses={},
        tags=['openapi-entreprise'],
    )
    def put(self, req, eid):
        enterprise_services.update(eid, req.data)
        return Response(None, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="获取企业信息",
        responses={200: EnterpriseInfoSerializer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, eid):
        ent = enterprise_services.get_enterprise_by_id(eid)
        if ent is None:
            return Response({"msg": "企业不存在"}, status=status.HTTP_404_NOT_FOUND)
        serializer = EnterpriseInfoSerializer(data=ent.to_dict())
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EnterpriseSourceView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取企业使用资源信息",
        responses={200: EnterpriseSourceSerializer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, eid):
        data = {"enterprise_id": eid, "used_cpu": 0, "used_memory": 0, "used_disk": 0}
        if not req.user.is_administrator:
            raise ServiceHandleException(status_code=401, error_code=401, msg="Permission denied")
        ent = enterprise_services.get_enterprise_by_id(eid)
        if ent is None:
            return Response({"msg": "企业不存在"}, status=status.HTTP_404_NOT_FOUND)
        regions = region_services.get_regions_by_enterprise_id(eid)
        for region in regions:
            try:
                # Exclude development clusters
                if "development" in region.region_type:
                    logger.debug("{0} region type is development in enterprise {1}".format(region.region_name, eid))
                    continue
                res, body = region_api.get_region_resources(eid, region=region.region_name)
                rst = body.get("bean")
                if res.get("status") == 200 and rst:
                    data["used_cpu"] += rst.get("req_cpu", 0)
                    data["used_memory"] += rst.get("req_mem", 0)
                    data["used_disk"] += rst.get("req_disk", 0)
            except ServiceHandleException:
                continue

        serializer = EnterpriseSourceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EntUserInfoView(BaseOpenAPIView):
    def get(self, request, *args, **kwargs):
        page = int(request.GET.get("page_num", 1))
        page_size = int(request.GET.get("page_size", 10))
        enterprise_id = request.GET.get("eid", None)

        admins_num = EnterpriseUserPerm.objects.filter(enterprise_id=enterprise_id).count()
        admin_list = []
        start = (page - 1) * 10
        remaining_num = admins_num - (page - 1) * 10
        end = 10
        if remaining_num < page_size:
            end = remaining_num

        cursor = connection.cursor()
        cursor.execute(
            "select user_id from enterprise_user_perm where enterprise_id='{0}' order by user_id desc LIMIT {1},{2};".format(
                enterprise_id, start, end))
        admin_tuples = cursor.fetchall()
        for admin in admin_tuples:
            user = user_repo.get_by_user_id(user_id=admin[0])
            bean = dict()
            if user:
                bean["nick_name"] = user.nick_name
                bean["phone"] = user.phone
                bean["email"] = user.email
                bean["create_time"] = time_to_str(user.create_time, "%Y-%m-%d %H:%M:%S")
                bean["user_id"] = user.user_id
            admin_list.append(bean)

        result = {"list": admin_list, "total": admins_num}
        return Response(result, status.HTTP_200_OK)


class EnterpriseConfigView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取企业配置信息",
        responses={200: EnterpriseConfigSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        key = req.GET.get("key", None)
        ent = enterprise_services.get_enterprise_by_id(self.enterprise.enterprise_id)
        if ent is None:
            return Response({"msg": "企业不存在"}, status=status.HTTP_404_NOT_FOUND)
        ent_config = EnterpriseConfigService(self.enterprise.enterprise_id).initialization_or_get_config
        if key is None:
            serializer = EnterpriseConfigSeralizer(data=ent_config)
        elif key in ent_config.keys():
            serializer = EnterpriseConfigSeralizer(data={key: ent_config[key]})
        else:
            raise ServiceHandleException(
                status_code=404, msg="no found config key {}".format(key), msg_show=u"企业没有 {} 配置".format(key))
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
