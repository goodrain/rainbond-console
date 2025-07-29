# -*- coding: utf-8 -*-
# creater by: barnett
import logging
import os
from drf_yasg import openapi

from console.exception.main import ServiceHandleException
from console.models.main import EnterpriseUserPerm
from console.repositories.user_repo import user_repo
from console.services.config_service import EnterpriseConfigService
from console.services.enterprise_services import enterprise_services
from console.services.performance_overview import performance_overview
from console.services.region_services import region_services
from console.services.global_resource_processing import Global_resource_processing
from console.services.region_services import region_services
from console.utils.timeutil import time_to_str
from django.db import connection
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.config_serializers import (
    EnterpriseConfigSeralizer, EnterpriseOverviewSeralizer, VisualMonitorSeralizer, AppRankOverviewSeralizer,
    MonitorMessageOverviewSeralizer, MonitorQueryOverviewSeralizer, RegionMonitorOverviewSeralizer,
    InstancesMonitorOverviewSeralizer, ResourceOverviewSeralizer, ServieOveriewSeralizer, PerformanceOverviewSeralizer, ComponentMemoryOverviewSeralizer)
from openapi.serializer.ent_serializers import (EnterpriseInfoSerializer, EnterpriseSourceSerializer,
                                                UpdEntReqSerializer)
from openapi.views.base import BaseOpenAPIView
from rest_framework import status
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from console.services.team_services import team_services
from console.services.group_service import group_repo
from console.repositories.app import service_repo

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


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
        elif key in list(ent_config.keys()):
            serializer = EnterpriseConfigSeralizer(data={key: ent_config[key]})
        else:
            raise ServiceHandleException(
                status_code=404, msg="no found config key {}".format(key), msg_show="企业没有 {} 配置".format(key))
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResourceOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="资源信息总览",
        responses={200: ResourceOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        handle = Global_resource_processing()
        handle.region_obtain_handle(self.enterprise.enterprise_id)
        handle.tenant_obtain_handle(self.enterprise.enterprise_id)
        handle.app_obtain_handle()
        handle.host_obtain_handle()
        nodes, links = handle.template_handle()
        result = [{"nodes": nodes, "links": links}]
        serializer = ResourceOverviewSeralizer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)

class EnterpriseOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取企业总览信息",
        responses={200: EnterpriseOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        regions = region_services.get_enterprise_regions(self.user.enterprise_id, level="")
        nodes = 0
        instances = 0
        for region in regions:
            nodes += region.get("all_nodes", 0)
            instances += region.get("pods", 0)
        teams = team_services.count_teams(self.user.enterprise_id)
        apps = group_repo.count_apps()
        components = service_repo.count_components()
        visual_monitor = {
            "value": {
                "home_url": os.getenv("home_url", "https://visualmonitor.goodrain.com"),
                "cluster_monitor_suffix": os.getenv("cluster_monitor_suffix", "/d/cluster/ji-qun-jian-kong-ke-shi-hua"),
                "node_monitor_suffix": os.getenv("node_monitor_suffix", "/d/node/jie-dian-jian-kong-ke-shi-hua"),
                "component_monitor_suffix": os.getenv("component_monitor_suffix", "/d/component/zu-jian-jian-kong-ke-shi-hua"),
                "slo_monitor_suffix": os.getenv("slo_monitor_suffix", "/d/service/fu-wu-jian-kong-ke-shi-hua"),
            },
            "enable": True
        }
        visual_monitor_serializer = VisualMonitorSeralizer(data=visual_monitor)
        visual_monitor_serializer.is_valid()
        data = {
            "teams": teams,
            "apps": apps,
            "components": components,
            "instances": instances,
            "nodes": nodes,
            "visual_monitor": visual_monitor_serializer.data,
        }
        serializer = EnterpriseOverviewSeralizer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AppRankOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取应用排名总览信息",
        responses={200: AppRankOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        team_name = req.GET.get("team_name", "")
        regions = region_services.get_enterprise_regions(self.user.enterprise_id, level="", check_status="no")
        tenants, _ = team_services.get_enterprise_teams(self.user.enterprise_id)
        result = enterprise_services.get_app_ranking(regions, tenants, team_name)
        serializer = AppRankOverviewSeralizer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class MonitorMessageOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取组件异常事件信息",
        responses={200: MonitorMessageOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        team_name = req.GET.get("team_name", "")
        interval = req.GET.get("interval", 60)
        regions = region_services.get_enterprise_regions(self.user.enterprise_id, level="", check_status="no")
        tenants, _ = team_services.get_enterprise_teams(self.user.enterprise_id)
        result = enterprise_services.get_monitor_message(regions, tenants, team_name, interval)
        serializer = MonitorMessageOverviewSeralizer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class Performance_overview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="性能总览",
        responses={200: PerformanceOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        result = performance_overview.get_performance_overview(self.enterprise.enterprise_id)
        serializer = PerformanceOverviewSeralizer(data=result)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ServiceOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="组件信息总览",
        responses={200: ServieOveriewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        region_name = req.GET.get("region_name")
        run_count, abnormal_count, closed_count = service_overview.get_service_overview(
            enterprise_id=self.enterprise.enterprise_id,
            region_name=region_name)
        result = {"abnormal_service_num": abnormal_count, "closed_service_num": closed_count,
                  "started_service_num": run_count}
        serializer = ServieOveriewSeralizer(data=result)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResourceOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="资源信息总览",
        responses={200: ResourceOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        handle = Global_resource_processing()
        handle.region_obtain_handle(self.enterprise.enterprise_id)
        handle.tenant_obtain_handle(self.enterprise.enterprise_id)
        handle.app_obtain_handle()
        handle.host_obtain_handle()
        nodes, links = handle.template_handle()
        result = [{"nodes": nodes, "links": links}]
        serializer = ResourceOverviewSeralizer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class MonitorQueryOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="prometheus query接口",
        manual_parameters=[
            openapi.Parameter("region_name", openapi.IN_QUERY, description="集群名称", type=openapi.TYPE_STRING),
            openapi.Parameter("query", openapi.IN_QUERY, description="PromQL表达式", type=openapi.TYPE_STRING),
        ],
        responses={200: MonitorQueryOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        region_name = req.GET.get("region_name", "")
        query = req.GET.get("query", "")
        _, body = region_api.get_query_data(region_name, "", "?query={}".format(query))
        serializer = MonitorQueryOverviewSeralizer(data=body)
        serializer.is_valid()
        return Response(body, status=status.HTTP_200_OK)


class MonitorQueryRangeOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="prometheus query_range接口",
        manual_parameters=[
            openapi.Parameter("region_name", openapi.IN_QUERY, description="集群名称", type=openapi.TYPE_STRING),
            openapi.Parameter("query", openapi.IN_QUERY, description="PromQL表达式", type=openapi.TYPE_STRING),
            openapi.Parameter("start", openapi.IN_QUERY, description="起始时间", type=openapi.TYPE_NUMBER),
            openapi.Parameter("end", openapi.IN_QUERY, description="结束时间", type=openapi.TYPE_NUMBER),
            openapi.Parameter("step", openapi.IN_QUERY, description="查询步长", type=openapi.TYPE_NUMBER),
        ],
        responses={200: MonitorQueryOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        region_name = req.GET.get("region_name", "")
        query = req.GET.get("query", "")
        start = req.GET.get("start")
        end = req.GET.get("end")
        step = req.GET.get("step")
        _, body = region_api.get_query_range_data(region_name, "", "?query={}&start={}&end={}&step={}".format(
            query, start, end, step))
        serializer = MonitorQueryOverviewSeralizer(data=body)
        serializer.is_valid()
        return Response(body, status=status.HTTP_200_OK)


class MonitorSeriesOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="prometheus series接口",
        manual_parameters=[
            openapi.Parameter("match[]", openapi.IN_QUERY, description="选择器", type=openapi.TYPE_STRING),
            openapi.Parameter("start", openapi.IN_QUERY, description="起始时间", type=openapi.TYPE_NUMBER),
            openapi.Parameter("end", openapi.IN_QUERY, description="结束时间", type=openapi.TYPE_NUMBER),
            openapi.Parameter("region_name", openapi.IN_QUERY, description="集群名称", type=openapi.TYPE_STRING),
        ],
        responses={200: MonitorQueryOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        region_name = req.GET.get("region_name", "")
        match = req.GET.get("match[]")
        start = req.GET.get("start")
        end = req.GET.get("end")
        query = "?match[]={}".format(match)
        if start:
            query = "{}&start={}".format(query, start)
        if end:
            query = "{}&end={}".format(query, end)
        _, body = region_api.get_query_series(region_name, "", query)
        serializer = MonitorQueryOverviewSeralizer(data=body)
        serializer.is_valid()
        return Response(body, status=status.HTTP_200_OK)


class RegionsMonitorOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取所有集群异常节点信息",
        responses={200: RegionMonitorOverviewSeralizer(many=True)},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        regions = region_services.get_enterprise_regions(self.user.enterprise_id, level="", check_status="no")
        data = enterprise_services.get_exception_nodes_info(regions)
        serializer = RegionMonitorOverviewSeralizer(data=data, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class InstancesMonitorOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取实例监控信息",
        manual_parameters=[
            openapi.Parameter("region_name", openapi.IN_QUERY, description="集群名称", type=openapi.TYPE_STRING),
            openapi.Parameter("node_name", openapi.IN_QUERY, description="节点名", type=openapi.TYPE_STRING),
            openapi.Parameter("query", openapi.IN_QUERY, description="区分查询全部或不健康的实例, unhealthy",
                              type=openapi.TYPE_STRING),
        ],
        responses={200: InstancesMonitorOverviewSeralizer(many=True)},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        region_name = req.GET.get("region_name", "")
        node_name = req.GET.get("node_name", "")
        query = req.GET.get("query", "")
        regions = region_services.get_enterprise_regions(self.user.enterprise_id, level="", check_status="no")
        tenants, _ = team_services.get_enterprise_teams(self.user.enterprise_id)
        result = enterprise_services.get_instances_monitor(regions, tenants, region_name, node_name, query)
        serializer = InstancesMonitorOverviewSeralizer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ComponentMemoryOverview(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="组件内存桑吉图信息总览",
        responses={200: ComponentMemoryOverviewSeralizer},
        tags=['openapi-entreprise'],
    )
    def get(self, req, *args, **kwargs):
        from console.services.component_memory_processing import Component_memory_processing
        handle = Component_memory_processing()
        handle.region_obtain_handle(self.enterprise.enterprise_id)
        handle.tenant_obtain_handle(self.enterprise.enterprise_id)
        handle.component_memory_obtain_handle(self.enterprise.enterprise_id)
        nodes, links = handle.template_handle()
        result = [{"nodes": nodes, "links": links}]
        serializer = ComponentMemoryOverviewSeralizer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)
