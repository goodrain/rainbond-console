# -*- coding: utf8 -*-
import logging
from typing import Any, Dict, Iterable, List, Optional

from console.repositories.app import service_repo
from console.repositories.app_config import dep_relation_repo, port_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants

logger = logging.getLogger("default")
region_api = RegionInvokeApi()

NETWORK_POLICY_AUTO_ORIGIN = "依赖自动生成"


class NetworkPolicyDependencySyncService(object):
    def sync_after_dependency_change(self, tenant: Tenants, service: TenantServiceInfo, dep_service_id: str) -> None:
        self._sync_component_safely(tenant, service)
        dep_service = self._get_service(tenant.tenant_id, dep_service_id)
        if dep_service:
            self._sync_component_safely(tenant, dep_service)

    def sync_reverse_dependency_change(self, tenant: Tenants, service: TenantServiceInfo,
                                       be_dep_service_ids: str) -> None:
        self._sync_component_safely(tenant, service)
        for service_id in self._split_service_ids(be_dep_service_ids):
            source_service = self._get_service(tenant.tenant_id, service_id)
            if source_service:
                self._sync_component_safely(tenant, source_service)

    def sync_component(self, tenant: Tenants, service: TenantServiceInfo) -> None:
        if not self._can_sync(service):
            return
        query = {
            "team_name": tenant.tenant_name,
            "region_name": service.service_region,
            "service_alias": service.service_alias,
            "service_id": service.service_id,
        }
        payload = self.build_component_dependency_payload(tenant, service)
        region_api.sync_security_center_network_policy_dependencies(
            tenant.tenant_name,
            service.service_region,
            query,
            payload,
        )

    def build_component_dependency_payload(self, tenant: Tenants, service: TenantServiceInfo) -> Dict[str, Any]:
        dependencies = list(dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id))
        reverse_dependencies = list(dep_relation_repo.get_service_reverse_dependencies(tenant.tenant_id, service.service_id))
        dep_service_ids = self._unique_ids([relation.dep_service_id for relation in dependencies])
        source_service_ids = self._unique_ids([relation.service_id for relation in reverse_dependencies])
        known_services = self._service_map(dep_service_ids + source_service_ids)
        current_ports = self._inner_ports(tenant.tenant_id, service.service_id)

        outbound_rules = []
        for dep_service_id in dep_service_ids:
            if dep_service_id not in known_services:
                continue
            for port in self._inner_ports(tenant.tenant_id, dep_service_id):
                outbound_rules.append(self._auto_rule(dep_service_id, port))

        inbound_rules = []
        for source_service_id in source_service_ids:
            if source_service_id not in known_services:
                continue
            for port in current_ports:
                inbound_rules.append(self._auto_rule(source_service_id, port))

        return {
            "inbound_rules": inbound_rules,
            "outbound_rules": outbound_rules,
        }

    def _sync_component_safely(self, tenant: Tenants, service: TenantServiceInfo) -> None:
        try:
            self.sync_component(tenant, service)
        except Exception as exc:
            logger.warning(
                "sync security center network policy dependencies failed: service_id=%s, error=%s",
                getattr(service, "service_id", ""),
                exc,
            )

    @staticmethod
    def _can_sync(service: TenantServiceInfo) -> bool:
        if not service:
            return False
        if not getattr(service, "service_id", "") or not getattr(service, "service_region", ""):
            return False
        if hasattr(service, "create_status") and service.create_status != "complete":
            return False
        return True

    @staticmethod
    def _split_service_ids(service_ids: str) -> List[str]:
        return [service_id.strip() for service_id in (service_ids or "").split(",") if service_id.strip()]

    @staticmethod
    def _unique_ids(service_ids: Iterable[str]) -> List[str]:
        seen = set()
        result = []  # type: List[str]
        for service_id in service_ids:
            if not service_id or service_id in seen:
                continue
            seen.add(service_id)
            result.append(service_id)
        return result

    @staticmethod
    def _auto_rule(peer: str, port: int) -> Dict[str, Any]:
        return {
            "peer": peer,
            "port": port,
            "origin": NETWORK_POLICY_AUTO_ORIGIN,
            "removable": False,
        }

    @staticmethod
    def _inner_ports(tenant_id: str, service_id: str) -> List[int]:
        ports = []
        for port in port_repo.list_inner_ports(tenant_id, service_id):
            try:
                container_port = int(port.container_port)
            except (TypeError, ValueError):
                continue
            if container_port <= 0 or container_port > 65535:
                continue
            ports.append(container_port)
        return sorted(set(ports))

    @staticmethod
    def _service_map(service_ids: List[str]) -> Dict[str, TenantServiceInfo]:
        if not service_ids:
            return {}
        services = service_repo.get_services_by_service_ids(service_ids)
        return {service.service_id: service for service in services}

    @staticmethod
    def _get_service(tenant_id: str, service_id: str) -> Optional[TenantServiceInfo]:
        if not service_id:
            return None
        try:
            return service_repo.get_service_by_tenant_and_id(tenant_id, service_id)
        except Exception as exc:
            logger.warning("get service for network policy dependency sync failed: service_id=%s, error=%s", service_id, exc)
            return None


network_policy_dependency_sync_service = NetworkPolicyDependencySyncService()
