# -*- coding: utf8 -*-
from rest_framework.response import Response

from console.services.app_config import component_service_monitor
from console.services.monitor_service import monitor_service
from console.services.operation_log import operation_log_service, Operation
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
        sm = component_service_monitor.create_component_service_monitor(self.tenant, self.service, name, path, port,
                                                                        service_show_name, interval, self.user)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.FOR,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="创建了监控点{}".format(name))
        new_information = component_service_monitor.json_component_service_monitor(
            name=name, s_name=service_show_name, interval=interval, path=path, port=port)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information)
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
        old = component_service_monitor.get_component_service_monitor(self.tenant.tenant_id, self.service.service_id, name)
        sm = component_service_monitor.update_component_service_monitor(self.tenant, self.service, self.user, name, path, port,
                                                                        service_show_name, interval)
        new_information = component_service_monitor.json_component_service_monitor(
            name=name, s_name=service_show_name, interval=interval, path=path, port=port)
        old_information = component_service_monitor.json_component_service_monitor(
            name=old.name, s_name=old.service_show_name, interval=old.interval, path=old.path, port=old.port)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.UPDATE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="的监控点{}".format(name))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information,
            old_information=old_information)
        return Response(status=200, data=general_data(bean=sm.to_dict()))

    def delete(self, request, name, *args, **kwargs):
        sm = component_service_monitor.delete_component_service_monitor(self.tenant, self.service, self.user, name)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.DELETE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="的监控点{}".format(name))
        old_information = component_service_monitor.json_component_service_monitor(
            name=sm.name, s_name=sm.service_show_name, interval=sm.interval, path=sm.path, port=sm.port)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information)
        return Response(status=200, data=general_data(bean=sm.to_dict()))

    def get(self, request, name, *args, **kwargs):
        sm = component_service_monitor.get_component_service_monitor(self.tenant.tenant_id, self.service.service_id, name)
        return Response(status=200, data=general_data(bean=sm.to_dict()))


class ComponentMetricsView(AppBaseView):
    def get(self, request, *args, **kwargs):
        metrics = monitor_service.get_monitor_metrics(
            self.region_name, self.tenant, "component", component_id=self.service.service_id)
        return Response(general_message(200, "OK", "获取成功", list=metrics), status=200)
