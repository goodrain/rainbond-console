# -*- coding: utf8 -*-
import logging
from typing import Any, Dict, List, Optional

from .plugin import Plugin
from .component_group import ComponentGroup
from .component import Component
# repository
from console.services.app_config.service_monitor import service_monitor_repo
from console.repositories.service_repo import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import domain_repo
from console.repositories.app_config import configuration_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import extend_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.app_config import volume_repo
from console.repositories.app_config import config_file_repo
from console.repositories.app_config import mnt_repo as volume_dep_repo
from console.repositories.component_graph import component_graph_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.region_app import region_app_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.plugin import service_plugin_config_repo
from console.repositories.label_repo import service_label_repo
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.repositories.k8s_resources import k8s_resources_repo
# model
from www.models.main import ServiceGroup
from console.models.main import K8sResource
# utils
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class NewApp(object):
    """
    A new application formed by template application in existing application
    """

    def __init__(self,
                 tenant: Any,
                 region_name: str,
                 app: ServiceGroup,
                 component_group: ComponentGroup,
                 new_components: List[Component],
                 update_components: List[Component],
                 component_deps: Any,
                 volume_deps: Any,
                 plugins: List[Plugin],
                 plugin_deps: Any,
                 plugin_configs: Any,
                 new_plugins: Optional[List[Plugin]] = None,
                 config_groups: Optional[List[Any]] = None,
                 config_group_items: Optional[List[Any]] = None,
                 config_group_components: Optional[List[Any]] = None,
                 k8s_resources: Optional[List[Any]] = None) -> None:
        self.tenant = tenant
        self.tenant_id = tenant.tenant_id
        self.region_name = region_name
        self.app_id = app.app_id
        self.app = app
        self.component_group = component_group
        self.upgrade_group_id = component_group.upgrade_group_id
        self.version = component_group.version
        self.region_app_id = region_app_repo.get_region_app_id(self.region_name, self.app_id)
        self.governance_mode = app.governance_mode
        self.new_components = new_components
        self.update_components = update_components
        self.component_ids = [cpt.component.component_id for cpt in self._components()]

        # plugins
        self.plugins = plugins
        self.new_plugins = new_plugins
        self.plugin_deps = plugin_deps
        self.plugin_configs = plugin_configs

        # component dependencies
        self.component_deps = component_deps if component_deps else []
        # volume dependencies
        self.volume_deps = volume_deps if volume_deps else []
        # config groups
        self.config_groups = config_groups if config_groups else []
        self.config_group_items = config_group_items if config_group_items else []
        self.config_group_components = config_group_components if config_group_components else []
        # k8s resources
        self.k8s_resources = k8s_resources if k8s_resources else []

    def save(self) -> None:
        # component
        self._save_components()
        self._update_components()

        # plugins
        self._save_plugin_deps()
        self._save_plugin_configs()

        # dependency
        self._save_component_deps()
        self._save_volume_deps()
        # config group
        self._save_config_groups()
        # component group
        self.component_group.save()
        # k8s resources
        self._save_k8s_resources()

    def components(self) -> List[Component]:
        return self._ensure_components(self._components())

    def list_update_components(self) -> List[Component]:
        return self._ensure_components(self.update_components)

    def _ensure_components(self, components: List[Component]) -> List[Component]:
        # component dependency
        component_deps: Dict[str, List[Any]] = {}
        for dep in self.component_deps:
            deps = component_deps.get(dep.service_id, [])
            deps.append(dep)
            component_deps[dep.service_id] = deps
        # volume dependency
        volume_deps: Dict[str, List[Any]] = {}
        for dep in self.volume_deps:
            deps = volume_deps.get(dep.service_id, [])
            deps.append(dep)
            volume_deps[dep.service_id] = deps
        # application config groups
        config_group_components: Dict[str, List[Any]] = {}
        for cgc in self.config_group_components:
            cgcs = config_group_components.get(cgc.service_id, [])
            cgcs.append(cgc)
            config_group_components[cgc.service_id] = cgcs
        # plugins
        plugin_deps: Dict[str, List[Any]] = {}
        for plugin_dep in self.plugin_deps:
            pds = plugin_deps.get(plugin_dep.service_id, [])
            pds.append(plugin_dep)
            plugin_deps[plugin_dep.service_id] = pds
        plugin_configs: Dict[str, List[Any]] = {}
        for plugin_config in self.plugin_configs:
            pcs = plugin_configs.get(plugin_config.service_id, [])
            pcs.append(plugin_config)
            plugin_configs[plugin_config.service_id] = pcs
        for cpt in components:
            cpt.component_deps = component_deps.get(cpt.component.component_id)  # type: ignore[assignment]
            cpt.volume_deps = volume_deps.get(cpt.component.component_id)  # type: ignore[assignment]
            cpt.app_config_groups = config_group_components.get(cpt.component.component_id)  # type: ignore[assignment]
            cpt.plugin_deps = plugin_deps.get(cpt.component.component_id)  # type: ignore[assignment]
            cpt.plugin_configs = plugin_configs.get(cpt.component.component_id)  # type: ignore[attr-defined]
            # NOTE: Component class does not define plugin_configs attribute; set dynamically here
        return components

    def _components(self) -> List[Component]:
        return self.new_components + self.update_components

    def _save_components(self) -> None:
        """
        create new components
        """
        component_sources = []
        envs = []
        ports = []
        http_rules = []
        http_rule_configs = []
        volumes = []
        config_files = []
        probes = []
        extend_infos = []
        monitors = []
        graphs = []
        service_group_rels = []
        labels = []
        k8s_attributes = []
        for cpt in self.new_components:
            if cpt.component_source:
                component_sources.append(cpt.component_source)
            envs.extend(cpt.envs)
            ports.extend(cpt.ports)
            http_rules.extend(cpt.http_rules)
            http_rule_configs.extend(cpt.http_rule_configs)
            volumes.extend(cpt.volumes)
            config_files.extend(cpt.config_files)
            if cpt.probes:
                probes.extend(cpt.probes)
            if cpt.extend_info:
                extend_infos.append(cpt.extend_info)
            monitors.extend(cpt.monitors)
            graphs.extend(cpt.graphs)
            service_group_rels.append(cpt.service_group_rel)
            labels.extend(cpt.labels)
            k8s_attributes.extend(cpt.k8s_attributes)
        components = [cpt.component for cpt in self.new_components]

        service_repo.bulk_create(components)
        service_source_repo.bulk_create(component_sources)
        env_var_repo.bulk_create(envs)
        port_repo.bulk_create(ports)
        domain_repo.bulk_create(http_rules)
        configuration_repo.bulk_create(http_rule_configs)
        volume_repo.bulk_create(volumes)
        config_file_repo.bulk_create(config_files)
        probe_repo.bulk_create(probes)
        extend_repo.bulk_create_or_update(extend_infos)
        service_monitor_repo.bulk_create(monitors)
        component_graph_repo.bulk_create(graphs)
        service_group_relation_repo.bulk_create(service_group_rels)  # type: ignore[arg-type]
        # NOTE: service_group_rels can contain None when cpt.service_group_rel is None
        service_label_repo.bulk_create(labels)
        k8s_attribute_repo.overwrite_by_component_ids([cpt.component_id for cpt in components], k8s_attributes)

    def _update_components(self) -> None:
        """
        update existing components
        """
        if not self.update_components:
            return

        sources = []
        envs = []
        ports = []
        volumes = []
        config_files = []
        probes = []
        extend_infos = []
        monitors = []
        graphs = []
        labels = []
        k8s_attributes = []
        # TODO(huangrh): merged with _save_components
        for cpt in self.update_components:
            if cpt.component_source:
                sources.append(cpt.component_source)
            envs.extend(cpt.envs)
            ports.extend(cpt.ports)
            volumes.extend(cpt.volumes)
            config_files.extend(cpt.config_files)
            if cpt.probes:
                probes.extend(cpt.probes)
            if cpt.extend_info:
                extend_infos.append(cpt.extend_info)
            monitors.extend(cpt.monitors)
            graphs.extend(cpt.graphs)
            labels.extend(cpt.labels)
            k8s_attributes.extend(cpt.k8s_attributes)

        components = [cpt.component for cpt in self.update_components]
        component_ids = [cpt.component_id for cpt in components]
        service_repo.bulk_update(components)
        service_source_repo.overwrite_by_component_ids(component_ids, sources)
        extend_repo.bulk_create_or_update(extend_infos)
        env_var_repo.overwrite_by_component_ids(component_ids, envs)
        port_repo.overwrite_by_component_ids(component_ids, ports)
        volume_repo.overwrite_by_component_ids(component_ids, volumes)
        config_file_repo.overwrite_by_component_ids(component_ids, config_files)
        probe_repo.overwrite_by_component_ids(component_ids, probes)
        service_monitor_repo.overwrite_by_component_ids(component_ids, monitors)
        component_graph_repo.overwrite_by_component_ids(component_ids, graphs)
        service_label_repo.overwrite_by_component_ids(component_ids, labels)
        k8s_attribute_repo.overwrite_by_component_ids(component_ids, k8s_attributes)

    def _save_component_deps(self) -> None:
        dep_relation_repo.overwrite_by_component_id(self.component_ids, self.component_deps)

    def _save_volume_deps(self) -> None:
        volume_dep_repo.overwrite_by_component_id(self.component_ids, self.volume_deps)

    def _save_config_groups(self) -> None:
        app_config_group_repo.bulk_create_or_update(self.config_groups)
        app_config_group_item_repo.bulk_create_or_update(self.config_group_items)
        app_config_group_service_repo.bulk_create_or_update(self.config_group_components)

    def _save_k8s_resources(self) -> None:
        resources = []
        old_resources = k8s_resources_repo.list_by_app_id(self.app_id)
        old_resources_map = {r.name + r.kind: r for r in old_resources}
        for rs in self.k8s_resources:
            if old_resources_map.get(rs.name + rs.kind):
                continue
            resources.append(
                K8sResource(
                    app_id=self.app_id,
                    name=rs.name,
                    kind=rs.kind,
                    content=rs.content,
                    state=rs.state,
                    error_overview=rs.error_overview,
                ))
        k8s_resources_repo.bulk_create(resources)

    def _existing_volume_deps(self) -> Dict[str, Any]:
        components = self._components()
        volume_deps = volume_dep_repo.list_mnt_relations_by_service_ids(self.tenant_id,
                                                                        [cpt.component.component_id for cpt in components])
        return {dep.key(): dep for dep in volume_deps}

    def _save_plugin_deps(self) -> None:
        app_plugin_relation_repo.overwrite_by_component_ids(self.component_ids, self.plugin_deps)

    def _save_plugin_configs(self) -> None:
        service_plugin_config_repo.overwrite_by_component_ids(self.component_ids, self.plugin_configs)
