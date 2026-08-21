# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, List, NoReturn, Optional

from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig
from console.repositories.app_config import dep_relation_repo, port_repo
from console.repositories.region_app import region_app_repo
from console.services.share_services import share_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroupRelation, TenantServiceInfo, Tenants

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class _RBDPluginSyncError(ServiceHandleException):
    """Marks errors already normalized by this reconciliation boundary."""


class RBDPluginSyncService(object):
    REQUIRED_FIELDS = ("plugin_id", "plugin_type", "frontend_component", "entry_path")
    INJECT_POSITION_TYPES = (list, tuple)

    def reconcile(self, tenant: Tenants, region: RegionConfig, app_template: dict, app_id: Any) -> Dict[str, Any]:
        platform_plugin = app_template.get("platform_plugin") if isinstance(app_template, dict) else None
        if not isinstance(platform_plugin, dict) or not platform_plugin.get("is_platform_plugin"):
            return {"status": "skipped", "reason": "not_platform_plugin"}

        raw_plugin_id = platform_plugin.get("plugin_id")
        plugin_id = raw_plugin_id.strip() if isinstance(raw_plugin_id, str) else ""
        try:
            return self._reconcile_platform_plugin(tenant, region, app_template, platform_plugin, app_id)
        except _RBDPluginSyncError:
            raise
        except ServiceHandleException as error:
            self._fail(
                "validate_template",
                app_id,
                plugin_id,
                error=error,
                safe_context={"region_name": getattr(region, "region_name", "")},
            )
        except Exception as error:
            self._fail(
                "validate_template",
                app_id,
                plugin_id,
                error=error,
                safe_context={"region_name": getattr(region, "region_name", "")},
            )

    def _reconcile_platform_plugin(self, tenant: Tenants, region: RegionConfig, app_template: dict, platform_plugin: dict,
                                   app_id: Any) -> Dict[str, Any]:
        platform_plugin = self._validate_template(platform_plugin, app_id)
        plugin_id = platform_plugin["plugin_id"]
        namespace = getattr(tenant, "namespace", "")
        if not isinstance(namespace, str) or not namespace.strip():
            self._fail(
                "validate_template",
                app_id,
                plugin_id,
                safe_context={"field": "namespace"},
            )
        namespace = namespace.strip()
        enterprise_id = getattr(tenant, "enterprise_id", "")
        if not isinstance(enterprise_id, str) or not enterprise_id.strip():
            self._fail(
                "validate_template",
                app_id,
                plugin_id,
                safe_context={"field": "enterprise_id"},
            )
        enterprise_id = enterprise_id.strip()

        service_ids = self._resolve_app_service_ids(tenant, region, app_id, plugin_id)
        components = self._resolve_app_components(tenant, region, app_id, plugin_id, service_ids)
        frontend_component = self._resolve_frontend_component(components, platform_plugin["frontend_component"], app_id,
                                                              plugin_id)
        frontend_port = self._select_http_port(
            self._get_service_ports(
                tenant.tenant_id,
                frontend_component.service_id,
                "resolve_frontend_http_port",
                app_id,
                plugin_id,
            ),
            self._template_component(app_template, frontend_component.service_cname),
            "resolve_frontend_http_port",
            app_id,
            plugin_id,
            frontend_component.service_cname,
        )
        backend_component, backend_port = self._resolve_backend(
            tenant,
            app_template,
            frontend_component,
            frontend_port,
            components,
            app_id,
            plugin_id,
        )

        try:
            region_app_id = region_app_repo.get_region_app_id(region.region_name, app_id)
        except Exception as error:
            self._fail(
                "resolve_region_app_id",
                app_id,
                plugin_id,
                error=error,
                safe_context={"region_name": region.region_name},
            )
        if not region_app_id:
            self._fail(
                "resolve_region_app_id",
                app_id,
                plugin_id,
                safe_context={"region_name": region.region_name},
            )

        frontend_service = self._service_address(frontend_port, namespace)
        entry_path = platform_plugin["entry_path"]
        frontend_service = frontend_service.rstrip("/") + "/" + entry_path.lstrip("/")
        backend_service = self._service_address(backend_port, namespace)
        plugin_data = {
            "plugin_id": plugin_id,
            "plugin_name": platform_plugin.get("plugin_name", ""),
            "plugin_type": platform_plugin["plugin_type"],
            "frontend_component": platform_plugin["frontend_component"],
            "entry_path": entry_path,
            "plugin_views": share_service.normalize_platform_plugin_positions(platform_plugin.get("inject_position", [])),
            "menu_title": platform_plugin.get("menu_title", ""),
            "route_path": platform_plugin.get("route_path", ""),
            "namespace": namespace,
            "frontend_service": frontend_service,
            "backend_service": backend_service,
            "app_id": region_app_id,
        }
        try:
            region_api.create_rbdplugin(enterprise_id, region.region_name, plugin_data)
        except Exception as error:
            safe_context = {
                "region_name": region.region_name,
                "target_service": frontend_service,
            }
            region_status = self._safe_region_status(error)
            if region_status is not None:
                safe_context["region_status"] = region_status
            self._fail(
                "apply_region_rbdplugin",
                app_id,
                plugin_id,
                error=error,
                safe_context=safe_context,
            )

        logger.info(
            "rbdplugin reconciled plugin_id=%s app_id=%s region_name=%s frontend_component=%s "
            "backend_component=%s",
            plugin_id,
            app_id,
            region.region_name,
            frontend_component.service_cname,
            backend_component.service_cname,
        )
        return {
            "status": "reconciled",
            "plugin_id": plugin_id,
            "app_id": app_id,
            "region_app_id": region_app_id,
            "frontend_component": frontend_component.service_cname,
            "frontend_service": frontend_service,
            "backend_service": backend_service,
        }

    def _validate_template(self, platform_plugin: dict, app_id: Any) -> dict:
        raw_plugin_id = platform_plugin.get("plugin_id")
        plugin_id = raw_plugin_id.strip() if isinstance(raw_plugin_id, str) else ""
        normalized = dict(platform_plugin)
        for field in self.REQUIRED_FIELDS:
            value = platform_plugin.get(field)
            if not isinstance(value, str) or not value.strip():
                self._fail(
                    "validate_template",
                    app_id,
                    plugin_id,
                    safe_context={"field": field},
                )
            normalized[field] = value.strip()

        inject_position = platform_plugin.get("inject_position", [])
        if (not isinstance(inject_position, self.INJECT_POSITION_TYPES)
                or any(not isinstance(position, str) for position in inject_position)):
            self._fail(
                "validate_template",
                app_id,
                plugin_id,
                safe_context={"field": "inject_position"},
            )
        normalized["inject_position"] = list(inject_position)
        return normalized

    def _resolve_app_service_ids(self, tenant: Tenants, region: RegionConfig, app_id: Any, plugin_id: str) -> List[str]:
        try:
            service_ids = list(
                ServiceGroupRelation.objects.filter(
                    tenant_id=tenant.tenant_id,
                    region_name=region.region_name,
                    group_id=app_id,
                ).values_list("service_id", flat=True))
        except Exception as error:
            self._fail(
                "resolve_app_components",
                app_id,
                plugin_id,
                error=error,
                safe_context={"region_name": region.region_name},
            )
        if not service_ids:
            self._fail(
                "resolve_app_components",
                app_id,
                plugin_id,
                safe_context={"region_name": region.region_name},
            )
        return service_ids

    def _resolve_app_components(self, tenant: Tenants, region: RegionConfig, app_id: Any, plugin_id: str,
                                service_ids: List[str]) -> List[TenantServiceInfo]:
        try:
            components = list(
                TenantServiceInfo.objects.filter(
                    tenant_id=tenant.tenant_id,
                    service_region=region.region_name,
                    service_id__in=service_ids,
                ))
        except Exception as error:
            self._fail(
                "resolve_app_components",
                app_id,
                plugin_id,
                error=error,
                safe_context={"region_name": region.region_name},
            )
        if not components:
            self._fail(
                "resolve_app_components",
                app_id,
                plugin_id,
                safe_context={"region_name": region.region_name},
            )
        return components

    def _resolve_frontend_component(self, components: List[TenantServiceInfo], frontend_name: str, app_id: Any,
                                    plugin_id: str) -> TenantServiceInfo:
        matches = [component for component in components if component.service_cname == frontend_name]
        if len(matches) != 1:
            self._fail(
                "resolve_frontend_component",
                app_id,
                plugin_id,
                safe_context={
                    "expected_frontend": frontend_name,
                    "candidate_components": [component.service_cname for component in components],
                },
            )
        return matches[0]

    def _resolve_backend(self, tenant: Tenants, app_template: dict, frontend_component: TenantServiceInfo, frontend_port: Any,
                         components: List[TenantServiceInfo], app_id: Any, plugin_id: str) -> Any:
        try:
            dependencies = list(dep_relation_repo.get_service_dependencies(tenant.tenant_id, frontend_component.service_id))
        except Exception as error:
            self._fail(
                "resolve_backend_component",
                app_id,
                plugin_id,
                error=error,
                safe_context={"target_component": frontend_component.service_cname},
            )
        if not dependencies:
            if len(components) == 1:
                return frontend_component, frontend_port
            self._fail(
                "resolve_backend_component",
                app_id,
                plugin_id,
                safe_context={
                    "target_component": frontend_component.service_cname,
                    "component_count": len(components),
                },
            )

        components_by_id = {component.service_id: component for component in components}
        candidates = []
        for dependency in dependencies:
            component = components_by_id.get(dependency.dep_service_id)
            if not component:
                continue
            ports = self._get_service_ports(
                tenant.tenant_id,
                component.service_id,
                "resolve_backend_http_port",
                app_id,
                plugin_id,
            )
            http_ports = self._http_ports(ports)
            if not http_ports:
                continue
            port = self._select_http_port(
                http_ports,
                self._template_component(app_template, component.service_cname),
                "resolve_backend_http_port",
                app_id,
                plugin_id,
                component.service_cname,
            )
            candidates.append((component, port))

        if not candidates:
            self._fail(
                "resolve_backend_http_port",
                app_id,
                plugin_id,
                safe_context={"target_component": frontend_component.service_cname},
            )
        if len(candidates) != 1:
            self._fail(
                "resolve_backend_component",
                app_id,
                plugin_id,
                safe_context={
                    "candidate_components": [component.service_cname for component, _ in candidates],
                },
            )
        return candidates[0]

    def _select_http_port(self, ports: Any, template_component: Optional[dict], phase: str, app_id: Any, plugin_id: str,
                          component_name: str) -> Any:
        http_ports = self._http_ports(ports)
        if len(http_ports) == 1:
            return http_ports[0]
        if not http_ports:
            self._fail(
                phase,
                app_id,
                plugin_id,
                safe_context={
                    "target_component": component_name,
                    "http_port_count": 0
                },
            )

        declared_ports = set()
        if template_component:
            for port in self._template_port_mappings(template_component):
                value = port.get("container_port", port.get("port")) if isinstance(port, dict) else None
                if isinstance(value, bool) or not isinstance(value, (str, int)):
                    continue
                try:
                    declared_ports.add(int(value))
                except (TypeError, ValueError):
                    continue
        matches = []
        for port in http_ports:
            try:
                container_port = int(port.container_port)
            except (TypeError, ValueError):
                continue
            if container_port in declared_ports:
                matches.append(port)
        if len(matches) == 1:
            return matches[0]
        self._fail(
            phase,
            app_id,
            plugin_id,
            safe_context={
                "target_component": component_name,
                "http_port_count": len(http_ports)
            },
        )

    @staticmethod
    def _template_port_mappings(template_component: dict) -> List[dict]:
        if "port_map_list" in template_component:
            port_mappings = template_component.get("port_map_list")
        else:
            port_mappings = template_component.get("ports", [])
        if not isinstance(port_mappings, (list, tuple)):
            return []
        return [port for port in port_mappings if isinstance(port, dict)]

    @staticmethod
    def _http_ports(ports: Any) -> List[Any]:
        return [
            port for port in list(ports) if str(getattr(port, "protocol", "")).lower() == "http"
            and bool(getattr(port, "k8s_service_name", "")) and bool(getattr(port, "container_port", None))
        ]

    def _get_service_ports(self, tenant_id: str, service_id: str, phase: str, app_id: Any, plugin_id: str) -> List[Any]:
        try:
            return list(port_repo.get_service_ports(tenant_id, service_id))
        except Exception as error:
            self._fail(
                phase,
                app_id,
                plugin_id,
                error=error,
                safe_context={"target_service": service_id},
            )

    @staticmethod
    def _template_component(app_template: dict, service_cname: str) -> Optional[dict]:
        matches = [
            component for component in app_template.get("apps", []) or []
            if isinstance(component, dict) and component.get("service_cname") == service_cname
        ]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _service_address(port: Any, namespace: str) -> str:
        return "{}.{}.svc.cluster.local:{}".format(
            port.k8s_service_name,
            namespace,
            port.container_port,
        )

    @staticmethod
    def _safe_region_status(error: Exception) -> Optional[Any]:
        status = getattr(error, "status_code", None)
        if status is None:
            status = getattr(getattr(error, "response", None), "status_code", None)
        if isinstance(status, int):
            return status
        if isinstance(status, str) and status.isdigit():
            return status
        return None

    @staticmethod
    def _safe_log_value(value: Any) -> str:
        if isinstance(value, (list, tuple, set)):
            value = ",".join(str(item) for item in value)
        elif not isinstance(value, (str, int, float, bool)):
            return "unknown"
        return "_".join(str(value).split())[:256]

    @classmethod
    def _fail(cls,
              phase: str,
              app_id: Any,
              plugin_id: str,
              error: Optional[Exception] = None,
              safe_context: Optional[Dict[str, Any]] = None) -> NoReturn:
        error_type = error.__class__.__name__ if error is not None else "ValidationError"
        context_parts = []
        for key, value in sorted((safe_context or {}).items()):
            context_parts.append("{}={}".format(key, cls._safe_log_value(value)))
        logger.warning(
            "rbdplugin reconciliation failed phase=%s plugin_id=%s app_id=%s error_type=%s %s",
            phase,
            cls._safe_log_value(plugin_id),
            cls._safe_log_value(app_id),
            error_type,
            " ".join(context_parts),
        )
        raise _RBDPluginSyncError(
            msg="rbd_plugin_sync_failed",
            msg_show="应用变更已提交，但插件注册同步失败，请重试升级或联系管理员",
            status_code=502,
            bean={
                "operation_committed": True,
                "phase": phase,
                "plugin_id": plugin_id,
                "app_id": app_id,
            },
        )


rbd_plugin_sync_service = RBDPluginSyncService()
