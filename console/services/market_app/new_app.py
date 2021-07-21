# -*- coding: utf8 -*-
import logging

from .plugin import Plugin
from .component_group import ComponentGroup
# repository
from console.services.app_config.service_monitor import service_monitor_repo
from console.repositories.service_repo import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import domain_repo
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
# model
from www.models.main import ServiceGroup
# utils
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class NewApp(object):
    """
    A new application formed by template application in existing application
    """

    def __init__(self,
                 tenant,
                 region_name,
                 app: ServiceGroup,
                 component_group: ComponentGroup,
                 new_components,
                 update_components,
                 component_deps,
                 volume_deps,
                 plugins: [Plugin],
                 plugin_deps,
                 plugin_configs,
                 new_plugins: [Plugin] = None,
                 config_groups=None,
                 config_group_items=None,
                 config_group_components=None):
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

    def save(self):
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

    def components(self):
        return self._ensure_components(self._components())

    def list_update_components(self):
        return self._ensure_components(self.update_components)

    def _ensure_components(self, components):
        # component dependency
        component_deps = {}
        for dep in self.component_deps:
            deps = component_deps.get(dep.service_id, [])
            deps.append(dep)
            component_deps[dep.service_id] = deps
        # volume dependency
        volume_deps = {}
        for dep in self.volume_deps:
            deps = volume_deps.get(dep.service_id, [])
            deps.append(dep)
            volume_deps[dep.service_id] = deps
        # application config groups
        config_group_components = {}
        for cgc in self.config_group_components:
            cgcs = config_group_components.get(cgc.service_id, [])
            cgcs.append(cgc)
            config_group_components[cgc.service_id] = cgcs
        # plugins
        plugin_deps = {}
        for plugin_dep in self.plugin_deps:
            pds = plugin_deps.get(plugin_dep.service_id, [])
            pds.append(plugin_dep)
            plugin_deps[plugin_dep.service_id] = pds
        plugin_configs = {}
        for plugin_config in self.plugin_configs:
            pcs = plugin_configs.get(plugin_config.service_id, [])
            pcs.append(plugin_config)
            plugin_configs[plugin_config.service_id] = pcs
        for cpt in components:
            cpt.component_deps = component_deps.get(cpt.component.component_id)
            cpt.volume_deps = volume_deps.get(cpt.component.component_id)
            cpt.app_config_groups = config_group_components.get(cpt.component.component_id)
            cpt.plugin_deps = plugin_deps.get(cpt.component.component_id)
            cpt.plugin_configs = plugin_configs.get(cpt.component.component_id)
        return components

    def _components(self):
        return self.new_components + self.update_components

    def _save_components(self):
        """
        create new components
        """
        component_sources = []
        envs = []
        ports = []
        http_rules = []
        volumes = []
        config_files = []
        probes = []
        extend_infos = []
        monitors = []
        graphs = []
        service_group_rels = []
        for cpt in self.new_components:
            component_sources.append(cpt.component_source)
            envs.extend(cpt.envs)
            ports.extend(cpt.ports)
            http_rules.extend(cpt.http_rules)
            volumes.extend(cpt.volumes)
            config_files.extend(cpt.config_files)
            if cpt.probe:
                probes.append(cpt.probe)
            if cpt.extend_info:
                extend_infos.append(cpt.extend_info)
            monitors.extend(cpt.monitors)
            graphs.extend(cpt.graphs)
            service_group_rels.append(cpt.service_group_rel)
        components = [cpt.component for cpt in self.new_components]

        service_repo.bulk_create(components)
        service_source_repo.bulk_create(component_sources)
        env_var_repo.bulk_create(envs)
        port_repo.bulk_create(ports)
        domain_repo.bulk_create(http_rules)
        volume_repo.bulk_create(volumes)
        config_file_repo.bulk_create(config_files)
        probe_repo.bulk_create(probes)
        extend_repo.bulk_create(extend_infos)
        service_monitor_repo.bulk_create(monitors)
        component_graph_repo.bulk_create(graphs)
        service_group_relation_repo.bulk_create(service_group_rels)

    def _update_components(self):
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
        # TODO(huangrh): merged with _save_components
        for cpt in self.update_components:
            sources.append(cpt.component_source)
            envs.extend(cpt.envs)
            ports.extend(cpt.ports)
            volumes.extend(cpt.volumes)
            config_files.extend(cpt.config_files)
            if cpt.probe:
                probes.append(cpt.probe)
            if cpt.extend_info:
                extend_infos.append(cpt.extend_info)
            monitors.extend(cpt.monitors)
            graphs.extend(cpt.graphs)

        components = [cpt.component for cpt in self.update_components]
        component_ids = [cpt.component_id for cpt in components]
        service_repo.bulk_update(components)
        service_source_repo.bulk_update(sources)
        extend_repo.bulk_create_or_update(extend_infos)
        env_var_repo.overwrite_by_component_ids(component_ids, envs)
        port_repo.overwrite_by_component_ids(component_ids, ports)
        volume_repo.overwrite_by_component_ids(component_ids, volumes)
        config_file_repo.overwrite_by_component_ids(component_ids, config_files)
        probe_repo.overwrite_by_component_ids(component_ids, probes)
        service_monitor_repo.overwrite_by_component_ids(component_ids, monitors)
        component_graph_repo.overwrite_by_component_ids(component_ids, graphs)

    def _save_component_deps(self):
        dep_relation_repo.overwrite_by_component_id(self.component_ids, self.component_deps)

    def _save_volume_deps(self):
        volume_dep_repo.overwrite_by_component_id(self.component_ids, self.volume_deps)

    def _save_config_groups(self):
        app_config_group_repo.bulk_create_or_update(self.config_groups)
        app_config_group_item_repo.bulk_create_or_update(self.config_group_items)
        app_config_group_service_repo.bulk_create_or_update(self.config_group_components)

    def _existing_volume_deps(self):
        components = self._components()
        volume_deps = volume_dep_repo.list_mnt_relations_by_service_ids(self.tenant_id,
                                                                        [cpt.component.component_id for cpt in
                                                                         components])
        return {dep.key(): dep for dep in volume_deps}

    def _save_plugin_deps(self):
        app_plugin_relation_repo.overwrite_by_component_ids(self.component_ids, self.plugin_deps)

    def _save_plugin_configs(self):
        service_plugin_config_repo.overwrite_by_component_ids(self.component_ids, self.plugin_configs)
