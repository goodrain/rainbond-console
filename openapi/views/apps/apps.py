# -*- coding: utf-8 -*-
# creater by: barnett

import logging

from django.forms.models import model_to_dict
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.repositories.app import service_repo
from console.services.app_actions import app_manage_service, event_service
from console.services.group_service import group_service
from console.services.service_services import base_service
from openapi.serializer.app_serializer import (AppBaseInfoSerializer, AppInfoSerializer, AppPostInfoSerializer,
                                               ServiceBaseInfoSerializer, ServiceGroupOperationsSerializer,
                                               AppServiceEventsSerializer)
from openapi.serializer.base_serializer import (FailSerializer, SuccessSerializer)
from openapi.services.app_service import app_service
from openapi.views.base import TeamAPIView, TeamAppAPIView, TeamAppServiceAPIView
from openapi.views.exceptions import ErrAppNotFound

logger = logging.getLogger("default")


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
        group_info = group_service.add_group(self.team, self.region_name, data["app_name"], data.get("app_note"))
        re = AppBaseInfoSerializer(group_info)
        return Response(re.data, status=status.HTTP_201_CREATED)


class AppInfoView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="应用详情",
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
        responses={200: None},
        tags=['openapi-apps'],
    )
    def delete(self, req, app_id, *args, **kwargs):
        msg_list = []
        service_ids = app_service.get_group_services_by_id(self.app.ID)
        services = service_repo.get_services_by_service_ids(service_ids)
        if services:
            status_list = base_service.status_multi_service(
                region=self.app.region_name, tenant_name=self.team.tenant_name,
                service_ids=service_ids, enterprise_id=self.team.enterprise_id)
            status_list = filter(lambda x: x not in ["closed", "undeploy"], map(lambda x: x["status"], status_list))
            if len(status_list) > 0:
                raise ServiceHandleException(msg="There are running components under the current application",
                                             msg_show=u"当前应用下有运行态的组件，不可删除")
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
                if code_status != 200:
                    raise ServiceHandleException(msg=msg_list, msg_show=u"请求错误")
                else:
                    code, msg, data = group_service.delete_group_no_service(self.app.ID)
                    if code != 200:
                        raise ServiceHandleException(msg=msg, msg_show=u"请求错误")
                    return Response(None, status=code)
        code, msg, data = group_service.delete_group_no_service(self.app.ID)
        if code != 200:
            raise ServiceHandleException(msg=msg, msg_show=u"请求错误")
        return Response(None, status=code)


class APPOperationsView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="操作应用",
        request_body=ServiceGroupOperationsSerializer(),
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
        code, msg = app_manage_service.batch_operations(self.team, request.user, action, service_ids, None)
        if code != 200:
            result = {"msg": "batch operation error"}
            rst_serializer = FailSerializer(data=result)
            rst_serializer.is_valid()
            return Response(rst_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        else:
            result = {"msg": msg}
            rst_serializer = SuccessSerializer(data=result)
            rst_serializer.is_valid()
            return Response(rst_serializer.data, status=status.HTTP_200_OK)


class ListAppServicesView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="查询应用下组件列表",
        responses={200: ServiceBaseInfoSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, *args, **kwargs):
        services = app_service.get_app_services_and_status(self.app)
        serializer = ServiceBaseInfoSerializer(data=services, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class AppServicesView(TeamAppServiceAPIView):
    @swagger_auto_schema(
        operation_description="查询组件信息",
        responses={200: ServiceBaseInfoSerializer()},
        tags=['openapi-apps'],
    )
    def get(self, req, app_id, service_id, *args, **kwargs):
        status_list = base_service.status_multi_service(
            region=self.app.region_name, tenant_name=self.team.tenant_name,
            service_ids=[self.service.service_id], enterprise_id=self.team.enterprise_id)
        self.service.status = status_list[0]["status"]
        serializer = ServiceBaseInfoSerializer(data=self.service.to_dict())
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除组件",
        responses={200: None},
        tags=['openapi-apps'],
    )
    def delete(self, req, app_id, service_id, *args, **kwargs):
        code, msg = app_manage_service.delete(self.user, self.team, self.service, True)
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
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: AppServiceEventsSerializer()},
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
        return Response(result, status=status.HTTP_200_OK)
