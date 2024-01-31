# -*- coding: utf-8 -*-
# creater by: barnett
import base64
import json
import logging
import os
import pickle
import re
import time

from django.db import transaction

from console.constants import PluginCategoryConstants
from console.exception.bcode import ErrK8sComponentNameExists, ErrComponentBuildFailed
from console.exception.main import ServiceHandleException, AccountOverdueException, RegionNotFound, AbortRequest
from console.repositories import deploy_repo
from console.repositories.app import service_repo
from console.repositories.app_config import port_repo
from console.repositories.group import group_service_relation_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.region_app import region_app_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.services.app import app_service as console_app_service
from console.services.app_actions import app_manage_service, event_service
from console.services.app_check_service import app_check_service
from console.services.app_config import (dependency_service, port_service, domain_service, volume_service)
from console.services.app_config.env_service import AppEnvVarService
from console.services.app_config_group import app_config_group_service
from console.services.app_import_and_export_service import import_service
from console.services.compose_service import compose_service
from console.services.group_service import group_service
from console.services.k8s_resource import k8s_resource_service
from console.services.market_app_service import market_app_service
from console.services.plugin import app_plugin_service
from console.services.region_services import region_services
from console.services.service_services import base_service
from console.services.helm_app_yaml import helm_app_service
from console.services.upgrade_services import upgrade_service
from console.utils.validation import validate_endpoints_info
from django.forms.models import model_to_dict
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from console.views.app_config.app_volume import ensure_volume_mode
from openapi.serializer.app_serializer import (
    AppBaseInfoSerializer, AppInfoSerializer, AppPostInfoSerializer, AppServiceEventsSerializer,
    AppServiceTelescopicHorizontalSerializer, AppServiceTelescopicVerticalSerializer, ComponentBuildReqSerializers,
    ComponentEnvsSerializers, ComponentEventSerializers, ComponentMonitorSerializers, CreateThirdComponentResponseSerializer,
    CreateThirdComponentSerializer, ListServiceEventsResponse, ServiceBaseInfoSerializer, ServiceGroupOperationsSerializer,
    TeamAppsCloseSerializers, DeployAppSerializer, ServicePortSerializer, ComponentPortReqSerializers,
    ComponentUpdatePortReqSerializers, ChangeDeploySourceSerializer, ServiceVolumeSerializer)
from openapi.serializer.base_serializer import (FailSerializer, SuccessSerializer)
from openapi.services.app_service import app_service
from openapi.services.component_action import component_action_service
from openapi.views.base import (EnterpriseServiceOauthView, TeamAPIView, TeamAppAPIView, TeamAppServiceAPIView)
from openapi.views.exceptions import ErrAppNotFound
from rest_framework import status
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message, error_message

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


class AppsPortView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="团队端口列表",
        tags=['openapi-apps'],
    )
    def get(self, req, *args, **kwargs):
        ports = port_repo.get_tenant_services(self.team.tenant_id)
        component_list = service_repo.get_tenant_region_services(self.region_name, self.team.tenant_id)
        component_dict = {component.service_id: component.service_cname for component in component_list}
        port_list = list()
        if ports:
            for port in ports:
                port_dict = dict()
                if not port.is_inner_service:
                    continue
                port_dict["port"] = port.container_port
                port_dict["service_name"] = port.k8s_service_name
                port_dict["namespace"] = self.team.namespace
                port_dict["component_name"] = component_dict.get(port.service_id)
                port_list.append(port_dict)
        ret_data = {"namespace": self.team.namespace, "ports": port_list}
        result = general_message(200, "success", "查询成功", bean=ret_data)
        return Response(result, status=result["code"])


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
        k8s_app = request.data.get("k8s_app", "")
        group_info = group_service.create_app(
            self.team,
            self.region_name,
            data["app_name"],
            data.get("app_note"),
            self.user.get_username(),
            k8s_app=k8s_app if k8s_app else "app-" + make_uuid()[:6],
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
            status_list = base_service.status_multi_service(
                region=self.app.region_name,
                tenant_name=self.team.tenant_name,
                service_ids=service_ids,
                enterprise_id=self.team.enterprise_id)
            status_list = [x for x in [x["status"] for x in status_list] if x not in ["closed", "undeploy"]]
            if len(status_list) > 0:
                raise ServiceHandleException(
                    msg="There are running components under the current application", msg_show="当前应用下有运行态的组件，不可删除")
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

    @swagger_auto_schema(
        operation_description="基于镜像创建组件",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
        ],
        tags=['openapi-apps'],
    )
    def post(self, request, region_name, app_id, *args, **kwargs):
        group_id = request.data.get("group_id", -1)
        service_cname = request.data.get("service_cname", None)
        image = request.data.get("image", "")
        docker_password = request.data.get("password", None)
        docker_user_name = request.data.get("user_name", None)
        k8s_component_name = request.data.get("k8s_component_name", "")
        image_type = "docker_image"
        if k8s_component_name and console_app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            raise ErrK8sComponentNameExists
        try:
            if not image_type:
                return Response(general_message(400, "image_type cannot be null", "参数错误"), status=400)

            # 根据group_id 获取团队
            tenant = app_service.get_tenant_by_group_id(group_id)

            code, msg_show, new_service = console_app_service.create_docker_run_app(
                region_name, tenant, self.user, service_cname, "", image_type, k8s_component_name, image)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)

            # 添加username,password信息
            if docker_password or docker_user_name:
                console_app_service.create_service_source_info(tenant, new_service, docker_user_name, docker_password)

            code, msg_show = group_service.add_service_to_group(tenant, region_name, group_id, new_service.service_id)
            if code != 200:
                logger.debug("service.create", msg_show)

        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)

        # 创建成功后是否构建
        is_deploy = request.data.get("is_deploy", True)
        try:
            # 数据中心创建组件
            region_new_service = console_app_service.create_region_service(tenant, new_service, self.user.nick_name)

            if is_deploy:
                try:
                    app_manage_service.deploy(tenant, region_new_service, self.user)
                except Exception as e:
                    logger.exception(e)
                    err = ErrComponentBuildFailed()
                    result = general_message(err.error_code, e, err.msg_show)
                    return Response(result, status=400)
            bean = {"service_id": region_new_service.service_id}
            result = general_message(200, "success", "组件创建成功", bean=bean)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
            result = general_message(400, "call cloud api failure", e)
            return Response(result, status=400)


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
            raise ServiceHandleException(
                msg="add component to app failure", msg_show=msg_show, status_code=code, error_code=code)
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
        status_list = base_service.status_multi_service(
            region=self.app.region_name,
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
        code, msg = app_manage_service.vertical_upgrade(
            self.team,
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
        app_manage_service.horizontal_upgrade(
            self.team, self.service, self.user, int(new_node), oauth_instance=self.oauth_instance)
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
            openapi.Parameter(
                "is_outer", openapi.IN_QUERY, description="是否只获取对外组件监控", type=openapi.TYPE_STRING, enum=["false", "true"]),
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
            openapi.Parameter(
                "is_outer", openapi.IN_QUERY, description="是否只获取对外组件监控", type=openapi.TYPE_STRING, enum=["false", "true"]),
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
        operation_description="更新组件环境变量",
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


class ComponentPortsChangeView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="删除组件端口",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_STRING),
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队id", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="集群名称", type=openapi.TYPE_STRING),
        ],
        responses={200: ServicePortSerializer()},
        tags=['openapi-apps'],
    )
    def delete(self, request, *args, **kwargs):
        container_port = kwargs.get("port")
        if not container_port:
            raise AbortRequest("container_port not specify", "端口变量名未指定")
        data = port_service.delete_port_by_container_port(self.team, self.service, int(container_port), self.user.nick_name)
        re = ServicePortSerializer(data)
        result = general_message(200, "success", "删除成功", bean=re.data)
        return Response(result, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="更新组件端口",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_STRING),
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队id", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="集群名称", type=openapi.TYPE_STRING),
        ],
        request_body=ComponentUpdatePortReqSerializers,
        responses={200: ServicePortSerializer()},
        tags=['openapi-apps'],
    )
    def put(self, request, *args, **kwargs):
        port_update = ComponentUpdatePortReqSerializers(data=request.data)
        port_update.is_valid(raise_exception=True)
        container_port = kwargs.get("port")
        action = port_update.data.get("action", None)
        port_alias = port_update.data.get("port_alias", None)
        protocol = port_update.data.get("protocol", None)
        k8s_service_name = port_update.data.get("k8s_service_name", "")
        if not container_port:
            raise AbortRequest("container_port not specify", "端口变量名未指定")

        if self.service.service_source == "third_party" and ("outer" in action):
            msg, msg_show, code = port_service.check_domain_thirdpart(self.team, self.service)
            if code != 200:
                logger.exception(msg, msg_show)
                return Response(general_message(code, msg, msg_show), status=code)

        code, msg, data = port_service.manage_port(self.team, self.service, self.region_name, int(container_port), action,
                                                   protocol, port_alias, k8s_service_name, self.user.nick_name)
        if code != 200:
            return Response(general_message(code, "change port fail", msg), status=code)

        re = ServicePortSerializer(data)
        result = general_message(200, "success", "操作成功", bean=re.data)
        return Response(result, status=status.HTTP_200_OK)


class ComponentPortsShowView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="获取组件端口列表",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_STRING),
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队id", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="集群名称", type=openapi.TYPE_STRING),
        ],
        responses={200: ServicePortSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, request, *args, **kwargs):
        ports = port_repo.get_service_ports(self.team.tenant_id, self.service.service_id)
        re = ServicePortSerializer(ports, many=True)
        result = general_message(200, "success", "查询成功", list=re.data)
        return Response(result, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="新增组件端口",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="应用id", type=openapi.TYPE_STRING),
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队id", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="集群名称", type=openapi.TYPE_STRING),
        ],
        request_body=ComponentPortReqSerializers,
        responses={200: ServicePortSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        port_info = ComponentPortReqSerializers(data=request.data)
        port_info.is_valid(raise_exception=True)
        port = port_info.data.get("port")
        protocol = port_info.data.get("protocol")
        port_alias = port_info.data.get("port_alias", "")
        is_inner_service = port_info.data.get("is_inner_service", False)
        if not port:
            return Response(general_message(400, "params error", "缺少端口参数"), status=400)
        if not protocol:
            return Response(general_message(400, "params error", "缺少协议参数"), status=400)
        if not port_alias:
            port_alias = self.service.service_alias.upper().replace("-", "_") + str(port)
        code, msg, port_info = port_service.add_service_port(self.team, self.service, port, protocol, port_alias,
                                                             is_inner_service, False, None, self.user.nick_name)
        if code != 200:
            return Response(general_message(code, "add port error", msg), status=code)
        re = ServicePortSerializer(port_info)
        result = general_message(200, "success", "添加成功", bean=re.data)
        return Response(result, status=status.HTTP_200_OK)


class ServiceVolumeView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="挂载组件的储存",
        manual_parameters=[
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队ID、名称", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="数据中心名称", type=openapi.TYPE_STRING),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用组id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="组件ID", type=openapi.TYPE_STRING)
        ],
        request_body=ServiceVolumeSerializer,
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):

        ServiceVolumeSerializerRequest = ServiceVolumeSerializer(data=request.data)
        ServiceVolumeSerializerRequest.is_valid(raise_exception=True)

        req = ServiceVolumeSerializerRequest.data
        r = re.compile('(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])$')
        if not r.match(req.get("volume_name")):
            raise AbortRequest(msg="volume name illegal", msg_show="持久化名称只支持数字字母下划线")

        file_content = request.data.get("file_content", None)
        provider_name = request.data.get("volume_provider_name", '')
        access_mode = request.data.get("access_mode", '')
        share_policy = request.data.get('share_policy', '')
        backup_policy = request.data.get('back_policy', '')
        reclaim_policy = request.data.get('reclaim_policy', '')
        allow_expansion = request.data.get('allow_expansion', False)
        mode = request.data.get("mode")
        if mode is not None:
            mode = ensure_volume_mode(mode)

        settings = {}
        settings['volume_capacity'] = req.get("volume_capacity")
        settings['provider_name'] = provider_name
        settings['access_mode'] = access_mode
        settings['share_policy'] = share_policy
        settings['backup_policy'] = backup_policy
        settings['reclaim_policy'] = reclaim_policy
        settings['allow_expansion'] = allow_expansion

        data = volume_service.add_service_volume(
            self.team,
            self.service,
            req.get("volume_path"),
            req.get("volume_type"),
            req.get("volume_name"),
            file_content,
            settings,
            self.user.nick_name,
            mode=mode)
        result = general_message(200, "success", "持久化路径添加成功", bean=data.to_dict())

        return Response(result, status=result["code"])


class ChangeDeploySourceView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="更改docker构建方式的镜像地址",
        manual_parameters=[
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队ID、名称", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="数据中心名称", type=openapi.TYPE_STRING),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用组id", type=openapi.TYPE_INTEGER),
            openapi.Parameter("service_id", openapi.IN_PATH, description="组件ID", type=openapi.TYPE_STRING)
        ],
        request_body=ChangeDeploySourceSerializer,
        tags=['openapi-apps'],
    )
    def put(self, request, *args, **kwargs):
        image = request.data.get("image", None)
        if image:
            version = image.split(':')[-1]
            if not version:
                version = "latest"
                image = image + ":" + version
            self.service.image = image
            self.service.version = version
        self.service.save()
        return Response(general_message(200, "success", "更改镜像地址成功"), status=200)


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


class AppModelImportEvent(TeamAPIView):
    @swagger_auto_schema(
        operation_description="创建应用导入记录",
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        # 查询导入记录，如果有未完成的记录返回未完成的记录，如果没有，创建新的导入记录
        unfinished_records = import_service.get_user_not_finish_import_record_in_enterprise(
            self.enterprise.enterprise_id, self.user)
        new = False
        r = None
        if unfinished_records:
            r = unfinished_records[len(unfinished_records) - 1]
            region = region_services.get_region_by_region_name(r.region)
            if not region:
                logger.warning("not found region for old import recoder")
                new = True
        else:
            new = True
        if new:
            try:
                r = import_service.create_app_import_record_2_enterprise(self.enterprise.enterprise_id, self.user.nick_name)
            except RegionNotFound:
                return Response(general_message(200, "success", "查询成功", bean={"region_name": ''}), status=200)
        upload_url = import_service.get_upload_url(r.region, r.event_id)
        region = region_services.get_region_by_region_name(r.region)
        data = {
            "status": r.status,
            "source_dir": r.source_dir,
            "event_id": r.event_id,
            "upload_url": upload_url,
            "region_name": region.region_alias if region else '',
        }
        return Response(general_message(200, "success", "查询成功", bean=data), status=200)


class AppTarballDirView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="应用包目录查询",
        tags=['openapi-apps'],
    )
    def get(self, request, *args, **kwargs):
        """
        查询应用包目录
        """
        event_id = kwargs.get("event_id", None)
        if not event_id:
            return Response(general_message(400, "event id is null", "请指明需要查询的event id"), status=400)

        apps = import_service.get_import_app_dir(event_id)
        result = general_message(200, "success", "查询成功", list=apps)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        """
        批量导入时创建一个目录
        """
        import_record = import_service.create_import_app_dir(self.team, self.user, self.region_name)

        result = general_message(200, "success", "查询成功", bean=import_record.to_dict())
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        """
        删除导入
        """
        event_id = request.GET.get("event_id", None)
        if not event_id:
            return Response(general_message(400, "event id is null", "请指明需要查询的event id"), status=400)

        import_record = import_service.delete_import_app_dir(self, self.region_name)

        result = general_message(200, "success", "查询成功", bean=import_record.to_dict())
        return Response(result, status=result["code"])


class AppImportView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="应用导入",
        tags=['openapi-apps'],
    )
    def post(self, request, event_id, *args, **kwargs):
        """
        导入应用包
        """
        file_name = request.data.get("file_name", None)
        team_name = request.data.get("tenant_name", None)
        if not file_name:
            raise AbortRequest(msg="file name is null", msg_show="请选择要导入的文件")
        if not event_id:
            raise AbortRequest(msg="event is not found", msg_show="参数错误，未提供事件ID")
        files = file_name.split(",")
        import_service.start_import_apps("enterprise", event_id, files, team_name, self.enterprise.enterprise_id)
        result = general_message(200, 'success', "操作成功，正在导入")
        return Response(result, status=result["code"])

    def get(self, request, event_id, *args, **kwargs):
        """
        查询应用包导入状态
        """
        sid = None
        try:
            sid = transaction.savepoint()
            record, metadata = import_service.openapi_deploy_app_get_import_by_event_id(event_id)
            transaction.savepoint_commit(sid)
            result = general_message(200, 'success', "查询成功", bean=record.to_dict(), list=metadata)
        except Exception as e:
            if sid:
                transaction.savepoint_rollback(sid)
            raise e
        return Response(result, status=result["code"])

    def delete(self, request, event_id, *args, **kwargs):
        """
        放弃导入
        """
        try:
            import_service.delete_import_app_dir_by_event_id(event_id)
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e)
        return Response(result, status=result["code"])


class AppDeployView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="部署应用, ram or docker-compose",
        request_body=DeployAppSerializer(),
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer_data = DeployAppSerializer(data=request.data)
        serializer_data.is_valid(raise_exception=True)
        req_date = serializer_data.data
        if req_date["deploy_type"] == "ram":
            if req_date["action"] == "deploy":
                # 走安装模版的逻辑
                app_version = req_date["group_version"]
                app_key = req_date["group_key"]
                market_app_service.install_app(
                    self.team,
                    self.region,
                    self.user,
                    req_date["app_id"],
                    app_key,
                    app_version,
                    "",
                    False,
                    is_deploy=True,
                    dry_run=False)
                return Response(general_message(200, "success", "安装应用成功"), status=200)
            elif req_date["action"] == "upgrade":
                # 走更新的逻辑
                try:
                    group = group_service.get_app_by_id(
                        tenant=self.team, region=self.region.region_name, app_id=req_date["app_id"])
                    apps = market_app_service.get_market_apps_in_app(self.region_name, self.team, group)
                    app_enable_upgrade_map = {app["app_model_id"]: app["can_upgrade"] for app in apps}
                    app_upgrade_group_id_map = {app["app_model_id"]: app["upgrade_group_id"] for app in apps}

                    app_version = req_date["group_version"]
                    app_key = req_date["group_key"]
                    enable_upgrade = app_enable_upgrade_map[app_key]
                    app_upgrade_group_id = app_upgrade_group_id_map[app_key]
                    if enable_upgrade:
                        # 升级
                        rainbond_app = rainbond_app_repo.get_rainbond_app_by_key_version(group_key=app_key, version=app_version)
                        ram_model_info = json.loads(rainbond_app.app_template)
                        component_keys = [cpt["service_key"] for cpt in ram_model_info["apps"]]
                        record = upgrade_service.create_upgrade_record(self.user.enterprise_id, self.team, group,
                                                                       app_upgrade_group_id)
                        app_upgrade_record = upgrade_repo.get_by_record_id(record["ID"])
                        record, _ = upgrade_service.upgrade(
                            self.team,
                            self.region,
                            self.user,
                            group,
                            app_version,
                            app_upgrade_record,
                            component_keys,
                        )
                    else:
                        return Response(general_message(404, "failed", "没有可升级的版本"), status=404)
                except ServiceHandleException as e:
                    if e.status_code != 404:
                        raise e
                return Response(general_message(200, "success", "升级应用成功"), status=200)
            else:
                return Response(general_message(400, "params error", "暂不支持当前操作:{}".format(req_date["action"])), status=400)
        if req_date["deploy_type"] == "docker-compose":
            group_name = request.data.get("group_name", None)
            k8s_app = request.data.get("k8s_app", None)
            hub_user = request.data.get("user_name", "")
            hub_pass = request.data.get("password", "")
            yaml_content = request.data.get("yaml_content", "")
            group_note = request.data.get("group_note", "")
            if group_note and len(group_note) > 2048:
                return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
            if not group_name:
                return Response(general_message(400, 'params error', "请指明需要创建的compose组名"), status=400)
            if not yaml_content:
                return Response(general_message(400, "params error", "未指明yaml内容"), status=400)
            # Parsing yaml determines whether the input is illegal
            code, msg, json_data = compose_service.yaml_to_json(yaml_content)
            if code != 200:
                return Response(general_message(code, "parse yaml error", msg), status=code)
            # 创建组
            group_info = group_service.create_app(
                self.team, self.region_name, group_name, group_note, self.user.get_username(), k8s_app=k8s_app)
            code, msg, group_compose = compose_service.create_group_compose(self.team, self.region_name, group_info["group_id"],
                                                                            yaml_content, hub_user, hub_pass)
            if code != 200:
                return Response(general_message(code, "create group compose error", msg), status=code)
            # 检测
            code, msg, compose_bean = compose_service.check_compose(self.region_name, self.team, group_compose.compose_id)
            # 获取检测结果
            compose_id = group_compose.compose_id
            while True:
                sid = None
                try:
                    group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
                    code, msg, data = app_check_service.get_service_check_info(self.team, self.region_name,
                                                                               compose_bean["check_uuid"])
                    logger.debug("start save compose info ! {0}".format(group_compose.create_status))
                    save_code, save_msg, service_list = compose_service.save_compose_services(
                        self.team, self.user, self.region_name, group_compose, data)
                    if save_code != 200:
                        data["check_status"] = "failure"
                        return Response(general_message(code, "check docker compose error", msg), status=code)
                    else:
                        transaction.savepoint_commit(sid)
                except Exception as e:
                    logger.exception(e)
                    return Response(general_message(10410, "resource is not enough", e), status=412)
                if data["check_status"] != "checking":
                    break
                time.sleep(2)
            # build
            services = None
            try:
                group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
                services = compose_service.get_compose_services(compose_id)
                # 数据中心创建组件
                new_app_list = []
                for service in services:
                    new_service = console_app_service.create_region_service(self.team, service, self.user.nick_name)
                    new_app_list.append(new_service)
                group_compose.create_status = "complete"
                group_compose.save()
                for s in new_app_list:
                    try:
                        app_manage_service.deploy(self.team, s, self.user, oauth_instance=None)
                    except Exception as e:
                        logger.exception(e)
                        continue
            except Exception as e:
                logger.exception(e)
                if services:
                    for service in services:
                        event_service.delete_service_events(service)
                        port_service.delete_region_port(self.team, service)
                        volume_service.delete_region_volumes(self.team, service)
                        env_var_service.delete_region_env(self.team, service)
                        dependency_service.delete_region_dependency(self.team, service)
                        app_manage_service.delete_region_service(self.team, service)
                        service.create_status = "checked"
                        service.save()
                raise e
            return Response(general_message(200, "success", "docker compose 部署成功"), status=200)
        else:
            return Response(general_message(400, "params error", "暂不支持当前操作:{}".format(req_date["deploy_type"])), status=400)


class AppChartInfo(TeamAPIView):
    @swagger_auto_schema(
        operation_description="chart包部署应用",
        tags=['openapi-apps'],
    )
    def post(self, request, event_id, *args, **kwargs):
        """
        chart包部署应用
        """
        group_id = request.data.get("app_id", None)
        name = request.data.get("name", None)
        version = request.data.get("version", None)
        file_name = "{}-{}.tgz".format(name, version)
        action = request.data.get("action", None)
        if not group_id:
            return Response(general_message(400, "params error", "缺少应用id"), status=400)
        if not name:
            return Response(general_message(400, 'params error', "缺少chart包名称"), status=400)
        if not version:
            return Response(general_message(400, "params error", "缺少chart包版本"), status=400)
        if not action:
            return Response(general_message(400, "params error", "请指定操作方式，deploy or upgrade"), status=400)

        try:
            region_app_id = region_app_repo.get_region_app_id(self.region_name, group_id)

            cvdata = import_service.get_helm_yaml_info(self.region_name, self.team, event_id, file_name, region_app_id, name,
                                                       version, self.enterprise.enterprise_id, self.region.region_id)
            if not cvdata["convert_resource"]:
                return Response(general_message(400, "failed", "解析失败，没有找到{}".format(file_name)), status=200)

            helm_center_app = helm_app_service.create_center_app_by_chart(self.enterprise.enterprise_id, name)

            helm_app_service.generate_template(cvdata, helm_center_app, version, self.team, name, self.region_name,
                                               self.enterprise.enterprise_id, self.user.user_id, "", group_id)
            helm_app_service.parse_chart_record(event_id)
        except Exception as e:
            logger.error(e)
            raise e

        if action == "deploy":
            # 安装应用
            market_app_service.install_app(
                self.team,
                self.region,
                self.user,
                group_id,
                helm_center_app.app_id,
                version,
                "",
                False,
                is_deploy=True,
                dry_run=False)
            return Response(general_message(200, "success", "安装应用成功"), status=200)
        elif action == "upgrade":
            # 更新应用
            try:
                group = group_service.get_app_by_id(tenant=self.team, region=self.region.region_name, app_id=group_id)
                apps = market_app_service.get_market_apps_in_app(self.region_name, self.team, group)
                app_enable_upgrade_map = {app["app_model_id"]: app["can_upgrade"] for app in apps}
                app_upgrade_group_id_map = {app["app_model_id"]: app["upgrade_group_id"] for app in apps}

                app_version = version
                app_key = helm_center_app.app_id
                enable_upgrade = app_enable_upgrade_map[app_key]
                app_upgrade_group_id = app_upgrade_group_id_map[app_key]
                if enable_upgrade:
                    # 升级
                    rainbond_app = rainbond_app_repo.get_rainbond_app_by_key_version(group_key=app_key, version=app_version)
                    ram_model_info = json.loads(rainbond_app.app_template)
                    component_keys = [cpt["service_key"] for cpt in ram_model_info["apps"]]
                    record = upgrade_service.create_upgrade_record(self.user.enterprise_id, self.team, group,
                                                                   app_upgrade_group_id)
                    app_upgrade_record = upgrade_repo.get_by_record_id(record["ID"])
                    record, _ = upgrade_service.upgrade(
                        self.team,
                        self.region,
                        self.user,
                        group,
                        app_version,
                        app_upgrade_record,
                        component_keys,
                    )
                else:
                    return Response(general_message(404, "failed", "没有可升级的版本"), status=404)
            except ServiceHandleException as e:
                if e.status_code != 404:
                    raise e
            return Response(general_message(200, "success", "更新应用成功"), status=200)
        else:
            return Response(general_message(400, "params error", "暂不支持当前操作:{}".format(action)), status=400)


class DeleteApp(TeamAPIView):
    @swagger_auto_schema(
        operation_description="一键删除应用",
        tags=['openapi-apps'],
    )
    def delete(self, request, app_id, *args, **kwargs):
        """
        删除应用及所有资源
        """
        # delete services
        group_service.batch_delete_app_services(self.user, self.team.tenant_id, self.region_name, app_id)
        # delete k8s resource
        k8s_resources = k8s_resource_service.list_by_app_id(str(app_id))
        resource_ids = [k8s_resource.ID for k8s_resource in k8s_resources]
        k8s_resource_service.batch_delete_k8s_resource(self.user.enterprise_id, self.team.tenant_name, str(app_id),
                                                       self.region_name, resource_ids)
        # delete configs
        app_config_group_service.batch_delete_config_group(self.region_name, self.team.tenant_name, app_id)
        # delete records
        group_service.delete_app_share_records(self.team.tenant_name, app_id)
        # delete app
        app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        group_service.delete_app(self.team, self.region_name, app)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])
