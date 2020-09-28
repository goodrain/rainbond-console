# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.services.app_config_group import app_config_group
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_data, general_message
from console.models.main import ApplicationConfigGroup
from console.services.group_service import group_service


class ListAppConfigGroupView(RegionTenantHeaderView):
    def post(self, request, app_id, *args, **kwargs):
        req_service_ids = request.data.get("service_ids", None)
        config_group_name = request.data.get("config_group_name", None)
        config_items = request.data.get("config_items", None)
        deploy_type = request.data.get("deploy_type", None)
        enable = request.data.get("enable", None)
        region_name = request.data.get("region_name", None)

        result = checkParam(app_id, req_service_ids)
        if result:
            return Response(result)
        # If the application config group exists, it is not created
        try:
            app_config_group.get_config_group(app_id, config_group_name)
        except ApplicationConfigGroup.DoesNotExist:
            acg = app_config_group.create_config_group(app_id, config_group_name, config_items, deploy_type, enable,
                                                       req_service_ids, region_name)
            return Response(status=200, data=general_data(bean=acg))
        else:
            result = general_message(409, "The configuration group already exists", "该配置组已存在")
            return Response(result)

    def get(self, request, app_id, *args, **kwargs):
        try:
            page = int(request.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(request.GET.get("page_size", 10))
        except ValueError:
            page_size = 10

        acg = app_config_group.list_config_groups(app_id, page, page_size)
        return Response(status=200, data=general_data(bean=acg))


class AppConfigGroupView(RegionTenantHeaderView):
    def put(self, request, app_id, name, *args, **kwargs):
        try:
            app_config_group.get_config_group(app_id, name)
        except ApplicationConfigGroup.DoesNotExist:
            result = general_message(404, "not app config group", "没有该应用配置组，无法操作")
            return Response(result)

        config_items = request.data.get("config_items", None)
        enable = request.data.get("enable", None)
        req_service_ids = request.data.get("service_ids", None)

        result = checkParam(app_id, req_service_ids)
        if result:
            return Response(result)
        acg = app_config_group.update_config_group(app_id, name, config_items, enable, req_service_ids)
        return Response(status=200, data=general_data(bean=acg))

    def get(self, request, app_id, name, *args, **kwargs):
        try:
            acg = app_config_group.get_config_group(app_id, name)
        except ApplicationConfigGroup.DoesNotExist:
            result = general_message(404, "The configuration group not found", "该配置组不存在")
            return Response(result)
        return Response(status=200, data=general_data(bean=acg))

    def delete(self, request, app_id, name, *args, **kwargs):
        acg = app_config_group.delete_config_group(app_id, name)
        return Response(status=200, data=general_data(bean=acg))


def checkParam(app_id, req_service_ids):
    services = group_service.get_group_services(app_id)
    service_ids = [service.service_id for service in services]

    # Judge whether the requested service ID is correct
    if req_service_ids is not None:
        for sid in req_service_ids:
            if sid["service_id"] not in service_ids:
                result = general_message(404, "The serviceID is not in the serviceID of the current application binding",
                                         "请求的组件ID不在当前应用绑定的组件ID中")
                return result
