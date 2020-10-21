# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.services.app_config_group import app_config_group_service
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_data
from console.services.group_service import group_service
from console.serializer import AppConfigGroupCreateSerilizer
from console.serializer import AppConfigGroupUpdateSerilizer
from console.exception.main import AbortRequest


class ListAppConfigGroupView(RegionTenantHeaderView):
    def post(self, request, team_name, app_id, *args, **kwargs):
        serializer = AppConfigGroupCreateSerilizer(data=request.data)
        serializer.is_valid()
        params = serializer.data

        checkParam(app_id, params["service_ids"])
        if len(params["config_items"]) == 0:
            raise AbortRequest(msg="The request must contain a config item")
        acg = app_config_group_service.create_config_group(app_id, params["config_group_name"], params["config_items"],
                                                           params["deploy_type"], params["enable"], params["service_ids"],
                                                           params["region_name"], team_name)
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

        acg = app_config_group_service.list_config_groups(self.region_name, app_id, page, page_size)
        return Response(status=200, data=general_data(bean=acg))


class AppConfigGroupView(RegionTenantHeaderView):
    def put(self, request, team_name, app_id, name, *args, **kwargs):
        serializer = AppConfigGroupUpdateSerilizer(data=request.data)
        serializer.is_valid()
        params = serializer.data

        checkParam(app_id, params["service_ids"])
        if len(params["config_items"]) == 0:
            raise AbortRequest(msg="The request must contain a config item")
        acg = app_config_group_service.update_config_group(self.region_name, app_id, name, params["config_items"],
                                                           params["enable"], params["service_ids"], team_name)
        return Response(status=200, data=general_data(bean=acg))

    def get(self, request, app_id, name, *args, **kwargs):
        acg = app_config_group_service.get_config_group(self.region_name, app_id, name)
        return Response(status=200, data=general_data(bean=acg))

    def delete(self, request, team_name, app_id, name, *args, **kwargs):
        acg = app_config_group_service.delete_config_group(self.region_name, team_name, app_id, name)
        return Response(status=200, data=general_data(bean=acg))


def checkParam(app_id, req_service_ids):
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
