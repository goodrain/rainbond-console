# -*- coding: utf8 -*-
from rest_framework.response import Response

from console.services.app_config import component_service_monitor
from console.views.app_config.base import AppBaseView
from www.utils.return_message import general_data, general_message


class ComponentServiceMonitorView(AppBaseView):
    def post(self, request, *args, **kwargs):
        port = request.data.get("port", None)
        name = request.data.get("name", None)
        service_show_name = request.data.get("service_show_name", None)
        path = request.data.get("path", "/metrics")
        interval = request.data.get("interval", "10s")
        if not port or not name or not service_show_name:
            return Response(status=400, data=general_message(400, "port or name or service_show_name must be set", "参数不全"))
        if not path.startswith("/"):
            return Response(status=400, data=general_message(400, "path must start with /", "参数错误"))
        sm = component_service_monitor.create_component_service_monitor(self.tenant, self.service, self.user, name, path, port,
                                                                        service_show_name, interval)
        return Response(status=200, data=general_data(bean=sm.to_dict()))

    def get(self, request, *args, **kwargs):
        sms = component_service_monitor.get_component_service_monitors(self.tenant.tenant_id, self.service.service_id)
        return Response(status=200, data=general_data(list=[p.to_dict() for p in sms]))


class ComponentServiceMonitorEditView(AppBaseView):
    def put(self, request, name, *args, **kwargs):
        port = request.data.get("port", None)
        service_show_name = request.data.get("service_show_name", None)
        path = request.data.get("path", "/metrics")
        interval = request.data.get("interval", "10s")
        if not port or not name or not service_show_name:
            return Response(status=400, data=general_message(400, "port or name or service_show_name must be set", "参数不全"))
        if not path.startswith("/"):
            return Response(status=400, data=general_message(400, "path must start with /", "参数错误"))
        sm = component_service_monitor.update_component_service_monitor(self.tenant, self.service, self.user, name, path, port,
                                                                        service_show_name, interval)
        return Response(status=200, data=general_data(bean=sm.to_dict()))

    def delete(self, request, name, *args, **kwargs):
        sm = component_service_monitor.delete_component_service_monitor(self.tenant, self.service, self.user, name)
        return Response(status=200, data=general_data(bean=sm.to_dict()))

    def get(self, request, name, *args, **kwargs):
        sm = component_service_monitor.get_component_service_monitor(self.tenant.tenant_id, self.service.service_id, name)
        return Response(status=200, data=general_data(bean=sm.to_dict()))
