# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.services.app_config_group import app_config_group_service
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_data, general_message
from console.services.group_service import group_service
from console.serializer import AppConfigGroupCreateSerilizer
from console.serializer import AppConfigGroupUpdateSerilizer
from console.exception.main import AbortRequest


class ListAppConfigGroupView(RegionTenantHeaderView):
    def post(self, request, app_id, *args, **kwargs):
        serializer = AppConfigGroupCreateSerilizer(data=request.data)
        serializer.is_valid()
        params = dict(serializer.data)
        req_service_ids = request.data.get("service_ids", None)
        config_items = request.data.get("config_items", None)

        result = checkParam(app_id, req_service_ids)
        if result:
            return Response(result)
        if len(config_items) == 0:
            raise AbortRequest(msg="The request must contain a config item")

        acg = app_config_group_service.create_config_group(app_id, params["config_group_name"], config_items,
                                                           params["deploy_type"], params["enable"], req_service_ids,
                                                           params["region_name"])
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

        acg = app_config_group_service.list_config_groups(app_id, page, page_size)
        return Response(status=200, data=general_data(bean=acg))


class AppConfigGroupView(RegionTenantHeaderView):
    def put(self, request, app_id, name, *args, **kwargs):
        serializer = AppConfigGroupUpdateSerilizer(data=request.data)
        serializer.is_valid()
        params = dict(serializer.data)
        config_items = request.data.get("config_items", None)
        req_service_ids = request.data.get("service_ids", None)
        result = checkParam(app_id, req_service_ids)
        if result:
            return Response(result)
        if len(config_items) == 0:
            raise AbortRequest(msg="The request must contain a config item")

        acg = app_config_group_service.update_config_group(app_id, name, config_items, params["enable"], req_service_ids)
        return Response(status=200, data=general_data(bean=acg))

    def get(self, request, app_id, name, *args, **kwargs):
        acg = app_config_group_service.get_config_group(app_id, name)
        return Response(status=200, data=general_data(bean=acg))

    def delete(self, request, app_id, name, *args, **kwargs):
        acg = app_config_group_service.delete_config_group(app_id, name)
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
