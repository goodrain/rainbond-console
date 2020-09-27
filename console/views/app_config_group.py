# -*- coding: utf-8 -*-
from rest_framework.response import Response
from console.services.app_config_group import app_config_group
from console.repositories.group import group_service_relation_repo
from console.views.base import (CloudEnterpriseCenterView, RegionTenantHeaderView)
from www.utils.return_message import general_data, general_message
from console.repositories.app_config_group import app_config_group_repo
from console.models.main import ApplicationConfigGroup


class AppConfigGroupCommonOperationView(RegionTenantHeaderView, CloudEnterpriseCenterView):
    def post(self, request, app_id, *args, **kwargs):
        services = group_service_relation_repo.get_services_obj_by_group(app_id)
        if not services:
            result = general_message(400, "not service", "当前组内无组件，无法操作")
            return Response(result)

        service_ids = [service.service_id for service in services]
        req_service_ids = request.data.get("service_ids", None)
        config_group_name = request.data.get("config_group_name", None)
        config_items = request.data.get("config_items", None)
        deploy_type = request.data.get("deploy_type", None)
        deploy_status = request.data.get("deploy_status", None)
        region_name = request.data.get("region_name", None)

        # Judge whether the requested service ID is correct
        if not req_service_ids:
            for sid in req_service_ids:
                if sid not in service_ids:
                    result = general_message(404, "The serviceID is not in the serviceID of the current application binding",
                                             "请求的组件ID不在当前应用绑定的组件ID中")
                    return Response(result)

        # If the application config group exists, it is not created
        try:
            app_config_group_repo.get_config_group_by_id(app_id, config_group_name)
        except ApplicationConfigGroup.DoesNotExist:
            acg = app_config_group.create_config_group(app_id, config_group_name, config_items, deploy_type, deploy_status,
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
