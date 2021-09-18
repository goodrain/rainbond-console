# -*- coding: utf-8 -*-
# creater by: barnett
import base64
import logging
import os
import pickle

from console.constants import PluginCategoryConstants
from console.exception.main import ServiceHandleException
from console.repositories import deploy_repo
from console.repositories.app import service_repo
from console.repositories.group import group_service_relation_repo
from console.services.app import app_service as console_app_service
from console.services.app_actions import app_manage_service, event_service
from console.services.app_config import domain_service, port_service
from console.services.app_config.env_service import AppEnvVarService
from console.services.group_service import group_service
from console.services.plugin import app_plugin_service
from console.services.service_services import base_service
from console.utils.validation import validate_endpoints_info
from django.forms.models import model_to_dict
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.app_serializer import (
    AppBaseInfoSerializer, AppInfoSerializer, AppPostInfoSerializer, AppServiceEventsSerializer,
    AppServiceTelescopicHorizontalSerializer, AppServiceTelescopicVerticalSerializer, ComponentBuildReqSerializers,
    ComponentEnvsSerializers, ComponentEventSerializers, ComponentMonitorSerializers, CreateThirdComponentResponseSerializer,
    CreateThirdComponentSerializer, ListServiceEventsResponse, ServiceBaseInfoSerializer, ServiceGroupOperationsSerializer,
    TeamAppsCloseSerializers)
from openapi.serializer.base_serializer import (FailSerializer, SuccessSerializer)
from openapi.services.app_service import app_service
from openapi.services.component_action import component_action_service
from openapi.views.base import (EnterpriseServiceOauthView, TeamAPIView, TeamAppAPIView, TeamAppServiceAPIView)
from openapi.views.exceptions import ErrAppNotFound
from rest_framework import status
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()
logger = logging.getLogger("default")
env_var_service = AppEnvVarService()

monitor_query_items = {
    "request_time": '?query=ceil(avg(app_requesttime{mode="avg",service_id="%s"}))',
    "request": '?query=sum(ceil(increase(app_request{service_id="%s",method="total"}[1m])/12))',
    "request_client": '?query=max(app_requestclient{service_id="%s"})',
}

monitor_query_range_items = {
    "request_time": '?query=ceil(avg(app_requesttime{mode="avg",service_id="%s"}))&start=%s&end=%s&step=%s',
    "request": '?query=sum(ceil(increase(app_request{service_id="%s",method="total"}[1m])/12))&start=%s&end=%s&step=%s',
    "request_client": '?query=max(app_requestclient{service_id="%s"})&start=%s&end=%s&step=%s',
}


class ListAppsView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="团队应用列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="搜索查询应用名称，团队名称", type=openapi.TYPE_STRING),
        ],
        responses={200: AppBaseInfoSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, req, *args, **kwargs):
        query = req.GET.get("query", None)
        apps = group_service.get_apps_list(team_id=self.team.tenant_id, region_name=self.region_name, query=query)
        re = AppBaseInfoSerializer(apps, many=True)
        return Response(re.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="创建应用",
        request_body=AppPostInfoSerializer(),
        responses={200: AppBaseInfoSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer = AppPostInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        group_info = group_service.create_app(
            self.team,
            self.region_name,
            data["app_name"],
            data.get("app_note"),
            self.user.get_username(),
        )
        re = AppBaseInfoSerializer(group_info)
        return Response(re.data, status=status.HTTP_201_CREATED)


class AppInfoView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="应用详情",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        responses={200: AppInfoSerializer()},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, *args, **kwargs):
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        services = app_service.get_app_services_and_status(app)
        used_cpu, used_momory = app_service.get_app_memory_and_cpu_used(services)
        app_info = model_to_dict(app)
        app_info["service_count"] = app_service.get_app_service_count(app_id)
        app_info["enterprise_id"] = self.enterprise.enterprise_id
        running_count = app_service.get_app_running_service_count(self.team, services)
        app_info["running_service_count"] = running_count
        app_status = "closed"
        if running_count > 0 and running_count < len(services):
            app_status = "part_running"
        if running_count > 0 and running_count == len(services):
            app_status = "running"
        app_info["status"] = app_status
        app_info["team_name"] = self.team.tenant_name
        app_info["used_cpu"] = used_cpu
        app_info["used_momory"] = used_momory
        app_info["app_id"] = app_id
        reapp = AppInfoSerializer(data=app_info)
        reapp.is_valid()
        return Response(reapp.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除应用",
        manual_parameters=[
            openapi.Parameter("force", openapi.IN_QUERY, description="强制删除", type=openapi.TYPE_INTEGER, enum=[0, 1]),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        responses={},
        tags=['openapi-apps'],
    )
    def delete(self, req, app_id, *args, **kwargs):
        msg_list = []
        try:
            force = int(req.GET.get("force", 0))
        except ValueError:
            raise ServiceHandleException(msg='force value error', msg_show="参数错误")
        service_ids = app_service.get_group_services_by_id(self.app.ID)
        services = service_repo.get_services_by_service_ids(service_ids)
        if services:
            status_list = base_service.status_multi_service(region=self.app.region_name,
                                                            tenant_name=self.team.tenant_name,
                                                            service_ids=service_ids,
                                                            enterprise_id=self.team.enterprise_id)
            status_list = [x for x in [x["status"] for x in status_list] if x not in ["closed", "undeploy"]]
            if len(status_list) > 0:
                raise ServiceHandleException(msg="There are running components under the current application",
                                             msg_show="当前应用下有运行态的组件，不可删除")
            else:
                code_status = 200
                for service in services:
                    code, msg = app_manage_service.batch_delete(self.user, self.team, service, is_force=True)
                    msg_dict = dict()
                    msg_dict['status'] = code
                    msg_dict['msg'] = msg
                    msg_dict['service_id'] = service.service_id
                    msg_dict['service_cname'] = service.service_cname
                    msg_list.append(msg_dict)
                    if code != 200:
                        code_status = code
                        if force:
                            code_status = 200
                            app_manage_service.delete_again(self.user, self.team, service, is_force=True)
                if code_status != 200:
                    raise ServiceHandleException(msg=msg_list, msg_show="请求错误")
        group_service.delete_app(self.team, self.region_name, self.app)
        return Response(None, status=200)


class APPOperationsView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="操作应用",
        request_body=ServiceGroupOperationsSerializer(),
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        responses={
            status.HTTP_200_OK: SuccessSerializer,
            status.HTTP_400_BAD_REQUEST: FailSerializer,
            status.HTTP_404_NOT_FOUND: FailSerializer
        },
        tags=['openapi-apps'],
    )
    def post(self, request, app_id, *args, **kwargs):
        sos = ServiceGroupOperationsSerializer(data=request.data)
        sos.is_valid(raise_exception=True)
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not app:
            raise ErrAppNotFound
        service_ids = sos.data.get("service_ids", None)
        if not service_ids or len(service_ids) == 0:
            service_ids = app_service.get_group_services_by_id(app_id)
        # TODO: Check the amount of resources used
        action = sos.data.get("action")
        if action == "stop":
            self.has_perms([300006, 400008])
        if action == "start":
            self.has_perms([300005, 400006])
        if action == "upgrade":
            self.has_perms([300007, 400009])
        if action == "deploy":
            self.has_perms([300008, 400010])
        app_manage_service.batch_operations(self.team, self.region_name, request.user, action, service_ids, None)
        result = {"msg": "操作成功"}
        rst_serializer = SuccessSerializer(data=result)
        rst_serializer.is_valid()
        return Response(rst_serializer.data, status=status.HTTP_200_OK)


class ListAppServicesView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="查询应用下组件列表",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ServiceBaseInfoSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, *args, **kwargs):
        services = app_service.get_app_services_and_status(self.app)
        serializer = ServiceBaseInfoSerializer(data=services, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateThirdComponentView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="创建第三方组件",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        request_body=CreateThirdComponentSerializer(),
        responses={200: CreateThirdComponentResponseSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, app_id, *args, **kwargs):
        ctcs = CreateThirdComponentSerializer(data=request.data)
        ctcs.is_valid(raise_exception=True)
        req_date = ctcs.data
        validate_endpoints_info(req_date["endpoints"])
        new_component = console_app_service.create_third_party_app(self.region_name, self.team, self.user,
                                                                   req_date["component_name"], req_date["endpoints"],
                                                                   req_date["endpoints_type"])
        # add component to app
        code, msg_show = group_service.add_service_to_group(self.team, self.region_name, app_id, new_component.service_id)
        if code != 200:
            raise ServiceHandleException(msg="add component to app failure",
                                         msg_show=msg_show,
                                         status_code=code,
                                         error_code=code)
        endpoints_type = req_date["endpoints_type"]
        bean = new_component.to_dict()
        if endpoints_type == "api":
            # 生成秘钥
            deploy = deploy_repo.get_deploy_relation_by_service_id(service_id=new_component.service_id)
            api_secret_key = pickle.loads(base64.b64decode(deploy)).get("secret_key")
            # 从环境变量中获取域名，没有在从请求中获取
            host = os.environ.get('DEFAULT_DOMAIN', "http://" + request.get_host())
            api_url = host + "/console/" + "third_party/{0}".format(new_component.service_id)
            bean["api_service_key"] = api_secret_key
            bean["url"] = api_url
        console_app_service.create_third_party_service(self.team, new_component, self.user.nick_name)
        return Response(bean, status=status.HTTP_200_OK)


class AppServicesView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="查询组件信息",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ServiceBaseInfoSerializer()},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, service_id, *args, **kwargs):
        status_list = base_service.status_multi_service(region=self.app.region_name,
                                                        tenant_name=self.team.tenant_name,
                                                        service_ids=[self.service.service_id],
                                                        enterprise_id=self.team.enterprise_id)
        data = self.service.to_dict()
        data["status"] = status_list[0]["status"]
        data["access_infos"] = domain_service.get_component_access_infos(self.region_name, self.service.service_id)
        serializer = ServiceBaseInfoSerializer(data=data)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除组件",
        manual_parameters=[
            openapi.Parameter("force", openapi.IN_QUERY, description="强制删除", type=openapi.TYPE_INTEGER, enum=[0, 1]),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        responses={},
        tags=['openapi-apps'],
    )
    def delete(self, req, app_id, service_id, *args, **kwargs):
        try:
            force = int(req.GET.get("force", 0))
        except ValueError:
            raise ServiceHandleException(msg='force value error', msg_show="参数错误")
        code, msg = app_manage_service.delete(self.user, self.team, self.service, True)
        if code != 200 and force:
            app_manage_service.delete_again(self.user, self.team, self.service, is_force=True)
        msg_dict = dict()
        msg_dict['status'] = code
        msg_dict['msg'] = msg
        msg_dict['service_id'] = self.service.service_id
        msg_dict['service_cname'] = self.service.service_cname
        if code != 200:
            raise ServiceHandleException(msg="delete error", msg_show=msg, status_code=code)
        return Response(None, status=status.HTTP_200_OK)


class AppServiceEventsView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="查询组件事件信息",
        manual_parameters=[
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_INTEGER),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ListServiceEventsResponse()},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, service_id, *args, **kwargs):
        page = int(req.GET.get("page", 1))
        page_size = int(req.GET.get("page_size", 10))
        events, total, has_next = event_service.get_target_events("service", self.service.service_id, self.team,
                                                                  self.service.service_region, page, page_size)
        serializer = AppServiceEventsSerializer(data=events, many=True)
        serializer.is_valid()
        result = {"events": serializer.data, "total": total, "page": page, "page_size": page_size}
        re = ListServiceEventsResponse(data=result)
        re.is_valid()
        return Response(re.data, status=status.HTTP_200_OK)


class AppServiceTelescopicVerticalView(TeamAppServiceAPIView, EnterpriseServiceOauthView):
    @swagger_auto_schema(
        operation_description="组件垂直伸缩",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        request_body=AppServiceTelescopicVerticalSerializer,
        responses={},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer = AppServiceTelescopicVerticalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_memory = serializer.data.get("new_memory")
        new_gpu = serializer.data.get("new_gpu", None)
        new_cpu = serializer.data.get("new_cpu", None)
        code, msg = app_manage_service.vertical_upgrade(self.team,
                                                        self.service,
                                                        self.user,
                                                        int(new_memory),
                                                        oauth_instance=self.oauth_instance,
                                                        new_gpu=new_gpu,
                                                        new_cpu=new_cpu)
        if code != 200:
            raise ServiceHandleException(status_code=code, msg="vertical upgrade error", msg_show=msg)
        return Response(None, status=code)


class AppServiceTelescopicHorizontalView(TeamAppServiceAPIView, EnterpriseServiceOauthView):
    @swagger_auto_schema(
        operation_description="组件水平伸缩",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        request_body=AppServiceTelescopicHorizontalSerializer,
        responses={},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer = AppServiceTelescopicHorizontalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_node = serializer.data.get("new_node")
        app_manage_service.horizontal_upgrade(self.team,
                                              self.service,
                                              self.user,
                                              int(new_node),
                                              oauth_instance=self.oauth_instance)
        return Response(None, status=200)


class TeamAppsCloseView(TeamAPIView, EnterpriseServiceOauthView):
    @swagger_auto_schema(
        operation_description="批量关闭应用",
        request_body=TeamAppsCloseSerializers,
        responses={},
        tags=['openapi-apps'],
    )
    def post(self, request, team_id, region_name, *args, **kwargs):
        serializers = TeamAppsCloseSerializers(data=request.data)
        serializers.is_valid(raise_exception=True)
        service_id_list = serializers.data.get("service_ids", None)
        services = service_repo.get_tenant_region_services(self.region_name, self.team.tenant_id)
        if not services:
            return Response(None, status=200)
        service_ids = services.values_list("service_id", flat=True)
        if service_id_list:
            service_ids = list(set(service_ids) & set(service_id_list))
        code, msg = app_manage_service.batch_action(self.region_name, self.team, self.user, "stop", service_ids, None,
                                                    self.oauth_instance)
        if code != 200:
            raise ServiceHandleException(status_code=code, msg="batch manage error", msg_show=msg)
        return Response(None, status=200)


class TeamAppsMonitorQueryView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="应用下组件实时监控",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("is_outer",
                              openapi.IN_QUERY,
                              description="是否只获取对外组件监控",
                              type=openapi.TYPE_STRING,
                              enum=["false", "true"]),
        ],
        responses={200: ComponentMonitorSerializers(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, request, team_id, region_name, app_id, *args, **kwargs):
        is_outer = request.GET.get("is_outer", False)
        if is_outer == "true":
            is_outer = True
        data = []
        services_relation = group_service_relation_repo.get_services_by_group(self.app.ID)
        service_ids = services_relation.values_list('service_id', flat=True)
        if service_ids:
            services = service_repo.get_services_by_service_ids(service_ids).exclude(service_source="third_party")
            for service in services:
                is_outer_service = True
                has_plugin = False
                service_abled_plugins = app_plugin_service.get_service_abled_plugin(service)
                for plugin in service_abled_plugins:
                    if plugin.category == PluginCategoryConstants.PERFORMANCE_ANALYSIS:
                        has_plugin = True
                if is_outer:
                    is_outer_service = False
                    tenant_service_ports = port_service.get_service_ports(service)
                    for service_port in tenant_service_ports:
                        if service_port.is_outer_service:
                            is_outer_service = True
                            break
                if has_plugin and is_outer_service:
                    dt = {
                        "service_id": service.service_id,
                        "service_cname": service.service_cname,
                        "service_alias": service.service_alias,
                        "monitors": []
                    }
                    for k, v in list(monitor_query_items.items()):
                        monitor = {"monitor_item": k}
                        res, body = region_api.get_query_data(self.region_name, self.team.tenant_name, v % service.service_id)
                        if body.get("data"):
                            if body["data"]["result"]:
                                result_list = []
                                for result in body["data"]["result"]:
                                    result["value"] = [str(value) for value in result["value"]]
                                    result_list.append(result)
                                body["data"]["result"] = result_list
                                monitor.update(body)
                                dt["monitors"].append(monitor)
                    data.append(dt)
        serializers = ComponentMonitorSerializers(data=data, many=True)
        serializers.is_valid(raise_exception=True)
        return Response(serializers.data, status=200)


class TeamAppsMonitorQueryRangeView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="应用下组件历史监控",
        manual_parameters=[
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队ID、名称", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="数据中心名称", type=openapi.TYPE_STRING),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("start", openapi.IN_PATH, description="起始时间戳", type=openapi.TYPE_NUMBER),
            openapi.Parameter("end", openapi.IN_PATH, description="结束时间戳", type=openapi.TYPE_NUMBER),
            openapi.Parameter("step", openapi.IN_PATH, description="步长（默认60）", type=openapi.TYPE_NUMBER),
            openapi.Parameter("is_outer",
                              openapi.IN_QUERY,
                              description="是否只获取对外组件监控",
                              type=openapi.TYPE_STRING,
                              enum=["false", "true"]),
        ],
        responses={200: ComponentMonitorSerializers(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, request, team_id, region_name, app_id, *args, **kwargs):
        is_outer = request.GET.get("is_outer", False)
        if is_outer == "true":
            is_outer = True
        data = []
        start = request.GET.get("start")
        end = request.GET.get("end")
        step = request.GET.get("step", 60)
        if not start or not end:
            raise ServiceHandleException(msg="params error", msg_show="缺少query参数")
        services_relation = group_service_relation_repo.get_services_by_group(self.app.ID)
        service_ids = services_relation.values_list('service_id', flat=True)
        if service_ids:
            services = service_repo.get_services_by_service_ids(service_ids).exclude(service_source="third_party")
            for service in services:
                is_outer_service = True
                has_plugin = False
                service_abled_plugins = app_plugin_service.get_service_abled_plugin(service)
                for plugin in service_abled_plugins:
                    if plugin.category == PluginCategoryConstants.PERFORMANCE_ANALYSIS:
                        has_plugin = True
                if is_outer:
                    is_outer_service = False
                    tenant_service_ports = port_service.get_service_ports(service)
                    for service_port in tenant_service_ports:
                        if service_port.is_outer_service:
                            is_outer_service = True
                            break
                if has_plugin and is_outer_service:
                    dt = {
                        "service_id": service.service_id,
                        "service_cname": service.service_cname,
                        "service_alias": service.service_alias,
                        "monitors": []
                    }
                    for k, v in list(monitor_query_range_items.items()):
                        monitor = {"monitor_item": k}
                        body = {}
                        try:
                            res, body = region_api.get_query_range_data(self.region_name, self.team.tenant_name,
                                                                        v % (service.service_id, start, end, step))
                        except Exception as e:
                            logger.debug(e)
                        if body.get("data"):
                            if body["data"]["result"]:
                                result_list = []
                                for result in body["data"]["result"]:
                                    result["value"] = [str(value) for value in result["value"]]
                                    result_list.append(result)
                                body["data"]["result"] = result_list
                                monitor.update(body)
                                dt["monitors"].append(monitor)
                    data.append(dt)
        serializers = ComponentMonitorSerializers(data=data, many=True)
        serializers.is_valid(raise_exception=True)
        return Response(serializers.data, status=200)


class ComponentEnvsUView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="批量关闭应用",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_STRING),
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队id", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="集群名称", type=openapi.TYPE_STRING),
        ],
        request_body=ComponentEnvsSerializers,
        responses={
            status.HTTP_200_OK: ComponentEnvsSerializers,
        },
        tags=['openapi-apps'],
    )
    def put(self, request, *args, **kwargs):
        serializers = ComponentEnvsSerializers(data=request.data)
        serializers.is_valid(raise_exception=True)
        envs = serializers.data.get("envs")
        rst = env_var_service.update_or_create_envs(self.team, self.service, envs)
        serializers = ComponentEnvsSerializers(data=rst)
        serializers.is_valid(raise_exception=True)
        return Response(serializers.data, status=200)


class ComponentBuildView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="构建组件，用于CI/CD工作流调用",
        manual_parameters=[
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队ID、名称", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="数据中心名称", type=openapi.TYPE_STRING),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用组id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="组件ID", type=openapi.TYPE_STRING)
        ],
        request_body=ComponentBuildReqSerializers,
        responses={200: ComponentEventSerializers()},
        tags=['openapi-apps'],
    )
    def post(self, request, team_id, region_name, app_id, service_id, *args, **kwargs):
        build_info = ComponentBuildReqSerializers(data=request.data)
        build_info.is_valid(raise_exception=True)
        event_id = component_action_service.component_build(self.team, self.service, self.user, build_info.data)
        serializers = ComponentEventSerializers(data={"event_id": event_id})
        serializers.is_valid(raise_exception=True)
        return Response(serializers.data, status=200)
