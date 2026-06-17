# -*- coding: utf8 -*-
import json
import logging
from typing import Any, List, Optional

from django.db.models import Q
from django.db.models.query import QuerySet

from console.exception.main import ServiceHandleException
from console.exception.bcode import ErrServiceMonitorExists, ErrRepeatMonitoringTarget
from console.models.main import ServiceMonitor
from console.services.app_config.port_service import AppPortService
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants
from www.utils.crypt import make_uuid

port_service = AppPortService()
region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ComponentServiceMonitor(object):
    def list_by_service_ids(self, tenant_id: str, service_ids: Any) -> "QuerySet[ServiceMonitor]":
        return ServiceMonitor.objects.filter(tenant_id=tenant_id, service_id__in=service_ids)

    def get_component_service_monitors(self, tenant_id: str, service_id: str) -> "QuerySet[ServiceMonitor]":
        return ServiceMonitor.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_tenant_service_monitor(self, tenant_id: str, name: str) -> "QuerySet[ServiceMonitor]":
        return ServiceMonitor.objects.filter(tenant_id=tenant_id, name=name)

    def get_component_service_monitor(self, tenant_id: str, service_id: str, name: str) -> Optional[ServiceMonitor]:
        sms = ServiceMonitor.objects.filter(tenant_id=tenant_id, service_id=service_id, name=name)
        if sms:
            return sms[0]
        return None

    def json_component_service_monitor(self, name: str, s_name: str, interval: str, path: str, port: int) -> str:
        return json.dumps({"配置名": name, "收集任务名称": s_name, "收集间隔时间": interval, "指标路径": path, "端口号": port}, ensure_ascii=False)

    def create_component_service_monitor(self, tenant: Tenants, service: TenantServiceInfo, name: str, path: str, port: int,
                                         service_show_name: str, interval: str, user: Any = None) -> ServiceMonitor:
        if ServiceMonitor.objects.filter(tenant_id=tenant.tenant_id, name=name).count() > 0:
            raise ErrServiceMonitorExists
        if ServiceMonitor.objects.filter(service_id=service.service_id, port=port, path=path).count() > 0:
            raise ErrRepeatMonitoringTarget
        if not port_service.get_service_port_by_port(service, port):
            raise ServiceHandleException(msg="port not found", msg_show="配置的组件端口不存在", status_code=400, error_code=400)
        req = {"name": name, "path": path, "port": port, "service_show_name": service_show_name, "interval": interval}
        req["operator"] = user.get_name() if user else None
        if service.create_status == "complete":
            # NOTE: tenant.enterprise_id is Optional[str] on the model; region_api expects str.
            region_api.create_service_monitor(tenant.enterprise_id, service.service_region,  # type: ignore[arg-type]
                                              tenant.tenant_name, service.service_alias, req)
        req.pop("operator")
        req["service_id"] = service.service_id
        req["tenant_id"] = tenant.tenant_id
        try:
            sm = ServiceMonitor.objects.create(**req)
            return sm
        except Exception as e:
            if service.create_status == "complete":
                # NOTE: enterprise_id Optional[str] -> str; body None passed on rollback path.
                region_api.delete_service_monitor(tenant.enterprise_id, service.service_region,  # type: ignore[arg-type]
                                                  tenant.tenant_name, service.service_alias, name,
                                                  None)  # type: ignore[arg-type]
            raise e

    def update_component_service_monitor(self, tenant: Tenants, service: TenantServiceInfo, user: Any, name: str, path: str,
                                         port: int, service_show_name: str, interval: str) -> Optional[ServiceMonitor]:
        sm = self.get_component_service_monitor(tenant.tenant_id, service.service_id, name)
        if not sm:
            raise ServiceHandleException(msg="service monitor is not found", msg_show="配置不存在", status_code=404)
        if ServiceMonitor.objects.filter(service_id=service.service_id, port=port, path=path).filter(~Q(name=name)).count() > 0:
            raise ServiceHandleException(msg="service monitor is exist", msg_show="重复的监控目标", status_code=400, error_code=400)
        if not port_service.get_service_port_by_port(service, port):
            raise ServiceHandleException(msg="port not found", msg_show="配置的组件端口不存在", status_code=400, error_code=400)
        req = {"path": path, "port": port, "service_show_name": service_show_name, "interval": interval}
        req["operator"] = user.get_name()
        # NOTE: tenant.enterprise_id is Optional[str] on the model; region_api expects str.
        region_api.update_service_monitor(tenant.enterprise_id, service.service_region,  # type: ignore[arg-type]
                                          tenant.tenant_name, service.service_alias, name, req)
        req.pop("operator")
        ServiceMonitor.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id, name=name).update(**req)
        return self.get_component_service_monitor(tenant.tenant_id, service.service_id, name)

    def delete_component_service_monitor(self, tenant: Tenants, service: TenantServiceInfo, user: Any,
                                         name: str) -> ServiceMonitor:
        sm = self.get_component_service_monitor(tenant.tenant_id, service.service_id, name)
        if not sm:
            raise ServiceHandleException(msg="service monitor is not found", msg_show="配置不存在", status_code=404)
        body = {
            "operator": user.get_name(),
        }
        try:
            # NOTE: tenant.enterprise_id is Optional[str] on the model; region_api expects str.
            region_api.delete_service_monitor(tenant.enterprise_id, service.service_region,  # type: ignore[arg-type]
                                              tenant.tenant_name, service.service_alias, name, body)
        except ServiceHandleException as e:
            if e.error_code != 10101:
                raise e
        ServiceMonitor.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id, name=name).delete()
        return sm

    def bulk_create_component_service_monitors(self, tenant: Tenants, service: TenantServiceInfo,
                                               service_monitors: Any) -> None:
        monitor_list = []
        for monitor in service_monitors:
            if ServiceMonitor.objects.filter(tenant_id=tenant.tenant_id, name=monitor["name"]).count() > 0:
                monitor["name"] = "-".join([monitor["name"], make_uuid()[-4:]])
            data = ServiceMonitor(
                name=monitor["name"],
                tenant_id=tenant.tenant_id,
                service_id=service.service_id,
                path=monitor["path"],
                port=monitor["port"],
                service_show_name=monitor["service_show_name"],
                interval=monitor["interval"])
            monitor_list.append(data)
        ServiceMonitor.objects.bulk_create(monitor_list)

    def delete_by_service_id(self, service_id: str) -> Any:
        return ServiceMonitor.objects.filter(service_id=service_id).delete()

    @staticmethod
    def bulk_create(monitors: List[ServiceMonitor]) -> None:
        ServiceMonitor.objects.bulk_create(monitors)

    def overwrite_by_component_ids(self, component_ids: Any, monitors: List[ServiceMonitor]) -> None:
        ServiceMonitor.objects.filter(service_id__in=component_ids).delete()
        self.bulk_create(monitors)


service_monitor_repo = ComponentServiceMonitor()
