# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.services.app_config_group import app_config_group_service
from console.services.operation_log import operation_log_service
from console.views.base import RegionTenantHeaderView, ApplicationView
from www.utils.return_message import general_data
from console.services.group_service import group_service
from console.serializer import AppConfigGroupCreateSerilizer
from console.serializer import AppConfigGroupUpdateSerilizer
from console.exception.main import AbortRequest


class ListAppConfigGroupView(ApplicationView):
    def post(self, request, team_name, app_id, *args, **kwargs):
        serializer = AppConfigGroupCreateSerilizer(data=request.data)
        serializer.is_valid()
        params = serializer.data

        check_services(app_id, params["service_ids"])
        acg = app_config_group_service.create_config_group(app_id, params["config_group_name"], params["config_items"],
                                                           params["deploy_type"], params["enable"], params["service_ids"],
                                                           params["region_name"], team_name)
        service_names = [service["service_cname"] for service in acg["services"]]
        config_items = [{"变量名": item["item_key"], "变量值": item["item_value"]} for item in acg["config_items"]]
        app_name = operation_log_service.process_app_name(self.app.app_name, self.region_name, self.tenant_name,
                                                          self.app.app_id)
        new_information = app_config_group_service.json_config_groups(
            config_group_name=acg["config_group_name"],
            config_items=config_items,
            enable=acg["enable"],
            services_names=service_names)
        comment = "为应用 {} 创建了配置组 {}".format(app_name, params["config_group_name"])
        operation_log_service.create_app_log(self, comment, format_app=False, new_information=new_information)
        return Response(status=200, data=general_data(bean=acg))

    def get(self, request, app_id, *args, **kwargs):
        try:
            page = int(request.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(request.GET.get("page_size", 10))
        except ValueError:
            page_size = 10
        query = request.GET.get("query", None)
        acg, total = app_config_group_service.list_config_groups(self.region_name, app_id, page, page_size, query)
        return Response(status=200, data=general_data(list=acg, total=total))


class AppConfigGroupView(ApplicationView):
    def put(self, request, team_name, app_id, name, *args, **kwargs):
        serializer = AppConfigGroupUpdateSerilizer(data=request.data)
        serializer.is_valid()
        params = serializer.data

        check_services(app_id, params["service_ids"])
        acg = app_config_group_service.get_config_group(self.region_name, app_id, name)
        service_names = [service["service_cname"] for service in acg["services"]]
        config_items = [{"变量名": item["item_key"], "变量值": item["item_value"]} for item in acg["config_items"]]
        old_information = app_config_group_service.json_config_groups(
            config_group_name=acg["config_group_name"],
            config_items=config_items,
            enable=acg["enable"],
            services_names=service_names)
        acg = app_config_group_service.update_config_group(self.region_name, app_id, name, params["config_items"],
                                                           params["enable"], params["service_ids"], team_name)
        service_names = [service["service_cname"] for service in acg["services"]]
        config_items = [{"变量名": item["item_key"], "变量值": item["item_value"]} for item in acg["config_items"]]

        app_name = operation_log_service.process_app_name(self.app.app_name, self.region_name, self.tenant_name,
                                                          self.app.app_id)
        new_information = app_config_group_service.json_config_groups(
            config_group_name=acg["config_group_name"],
            config_items=config_items,
            enable=acg["enable"],
            services_names=service_names)
        comment = "修改了应用 {} 的配置组 {}".format(app_name, name)
        operation_log_service.create_app_log(
            self, comment, format_app=False, new_information=new_information, old_information=old_information)
        return Response(status=200, data=general_data(bean=acg))

    def get(self, request, app_id, name, *args, **kwargs):
        acg = app_config_group_service.get_config_group(self.region_name, app_id, name)
        return Response(status=200, data=general_data(bean=acg))

    def delete(self, request, team_name, app_id, name, *args, **kwargs):
        acg = app_config_group_service.delete_config_group(self.region_name, team_name, app_id, name)
        service_names = [service["service_cname"] for service in acg["services"]]
        config_items = [{"变量名": item["item_key"], "变量值": item["item_value"]} for item in acg["config_items"]]
        old_information = app_config_group_service.json_config_groups(
            config_group_name=acg["config_group_name"],
            config_items=config_items,
            enable=acg["enable"],
            services_names=service_names)
        app_config_group_service.delete_config_group(self.region_name, team_name, app_id, name)
        app_name = operation_log_service.process_app_name(self.app.app_name, self.region_name, self.tenant_name,
                                                          self.app.app_id)
        comment = "删除了应用 {} 的配置组 {}".format(app_name, name)
        operation_log_service.create_app_log(self, comment, format_app=False, old_information=old_information)
        return Response(status=200, data=general_data(bean=acg))


def check_services(app_id, req_service_ids):
    services = group_service.get_group_services(app_id)
    service_ids = [service.service_id for service in services]

    # Judge whether the requested service ID is correct
    if req_service_ids is not None:
        for sid in req_service_ids:
            if sid not in service_ids:
                raise AbortRequest(
                    msg="The serviceID is not in the serviceID of the current application binding",
                    msg_show="请求的组件ID不在当前应用绑定的组件ID中",
                    status_code=404)
