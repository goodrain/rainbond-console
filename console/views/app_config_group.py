from rest_framework.response import Response
from console.services.app_config_group import app_config_group
from console.repositories.group import group_service_relation_repo
from console.views.base import (CloudEnterpriseCenterView, RegionTenantHeaderView)
from www.utils.return_message import general_data, general_message


class AppConfigGroupCommonOperationView(RegionTenantHeaderView, CloudEnterpriseCenterView):
    def post(self, request, *args, **kwargs):
        group_id = int(kwargs.get("group_id", None))
        services = group_service_relation_repo.get_services_obj_by_group(group_id)
        if not services:
            result = general_message(400, "not service", "当前组内无组件，无法操作")
            return Response(result)
        service_ids = [service.service_id for service in services]

        # Judge whether the requested service ID is correct
        req_service_ids = request.data.get("service_ids", None)
        for sid in req_service_ids:
            if sid not in service_ids:
                result = general_message(404, "The serviceID is not in the serviceID of the current application binding",
                                         "请求的组件ID不在当前应用绑定的组件ID中")
                return Response(result)

        config_group_name = request.data.get("config_group_name", None)
        config_items = request.data.get("config_items", None)
        deploy_type = request.data.get("deploy_type", None)
        deploy_status = request.data.get("deploy_status", None)
        region_name = request.data.get("region_name", None)
        acg = app_config_group.create_config_group(group_id, config_group_name, config_items, deploy_type, deploy_status,
                                                   req_service_ids, region_name)

        return Response(status=200, data=general_data(bean=acg.to_dict()))

    def get(self, request, *args, **kwargs):
        group_id = int(kwargs.get("group_id", None))
        try:
            page = int(request.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(request.GET.get("page_size", 10))
        except ValueError:
            page_size = 10

        acg = app_config_group.list_config_groups(group_id, page, page_size)
        return Response(status=200, data=general_data(bean=acg.to_dict()))


class AppConfigGroupEditOperationView(RegionTenantHeaderView, CloudEnterpriseCenterView):
    def delete(self, request, *args, **kwargs):
        group_id = int(kwargs.get("group_id", None))
        config_group_name = request.GET.get("name", None)
        acg = app_config_group.delete_config_group(group_id, config_group_name)
        return Response(status=200, data=general_data(bean=acg.to_dict()))

    def get(self, request, *args, **kwargs):
        group_id = int(kwargs.get("group_id", None))
        config_group_name = request.GET.get("name", None)
        acg = app_config_group.get_config_group(group_id, config_group_name)
        return Response(status=200, data=general_data(bean=acg.to_dict()))
