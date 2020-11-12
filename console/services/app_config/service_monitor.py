# -*- coding: utf8 -*-

import logging

from django.db.models import Q

from console.exception.main import ServiceHandleException
from console.models.main import ServiceMonitor
from console.services.app_config.port_service import AppPortService
from www.apiclient.regionapi import RegionInvokeApi

port_service = AppPortService()
region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ComponentServiceMonitor(object):
    def get_component_service_monitors(self, tenant_id, service_id):
        return ServiceMonitor.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_component_service_monitor(self, tenant_id, service_id, name):
        sms = ServiceMonitor.objects.filter(tenant_id=tenant_id, service_id=service_id, name=name)
        if sms:
            return sms[0]
        return None

    def create_component_service_monitor(self, tenant, service, user, name, path, port, service_show_name, interval):
        if ServiceMonitor.objects.filter(tenant_id=tenant.tenant_id, name=name).count() > 0:
            raise ServiceHandleException(msg="name is exist", msg_show="配置名称已存在", status_code=400, error_code=400)
        if ServiceMonitor.objects.filter(service_id=service.service_id, port=port, path=path).count() > 0:
            raise ServiceHandleException(msg="service monitor is exist", msg_show="重复的监控目标", status_code=400, error_code=400)
        if not port_service.get_service_port_by_port(service, port):
            raise ServiceHandleException(msg="port not found", msg_show="配置的组件端口不存在", status_code=400, error_code=400)
        req = {"name": name, "path": path, "port": port, "service_show_name": service_show_name, "interval": interval}
        req["operator"] = user.get_name()
        region_api.create_service_monitor(tenant.enterprise_id, service.service_region, tenant.tenant_name,
                                          service.service_alias, req)
        req.pop("operator")
        req["service_id"] = service.service_id
        req["tenant_id"] = tenant.tenant_id
        try:
            sm = ServiceMonitor.objects.create(**req)
            return sm
        except Exception as e:
            region_api.delete_service_monitor(tenant.enterprise_id, service.service_region, tenant.tenant_name, name)
            raise e

    def update_component_service_monitor(self, tenant, service, user, name, path, port, service_show_name, interval):
        sm = self.get_component_service_monitor(tenant.tenant_id, service.service_id, name)
        if not sm:
            raise ServiceHandleException(msg="service monitor is not found", msg_show="配置不存在", status_code=404)
        if ServiceMonitor.objects.filter(service_id=service.service_id, port=port, path=path).filter(~Q(name=name)).count() > 0:
            raise ServiceHandleException(msg="service monitor is exist", msg_show="重复的监控目标", status_code=400, error_code=400)
        if not port_service.get_service_port_by_port(service, port):
            raise ServiceHandleException(msg="port not found", msg_show="配置的组件端口不存在", status_code=400, error_code=400)
        req = {"path": path, "port": port, "service_show_name": service_show_name, "interval": interval}
        req["operator"] = user.get_name()
        region_api.update_service_monitor(tenant.enterprise_id, service.service_region, tenant.tenant_name,
                                          service.service_alias, name, req)
        req.pop("operator")
        ServiceMonitor.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id, name=name).update(**req)
        return self.get_component_service_monitor(tenant.tenant_id, service.service_id, name)

    def delete_component_service_monitor(self, tenant, service, user, name):
        sm = self.get_component_service_monitor(tenant.tenant_id, service.service_id, name)
        if not sm:
            raise ServiceHandleException(msg="service monitor is not found", msg_show="配置不存在", status_code=404)
        body = {
            "operator": user.get_name(),
        }
        try:
            region_api.delete_service_monitor(tenant.enterprise_id, service.service_region, tenant.tenant_name,
                                              service.service_alias, name, body)
        except ServiceHandleException as e:
            if e.error_code != 10101:
                raise e
        ServiceMonitor.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id, name=name).delete()
        return sm

    def bulk_create_component_service_monitors(self, service_monitors):
        ServiceMonitor.objects.bulk_create(service_monitors)


service_monitor_repo = ComponentServiceMonitor()
