# -*- coding: utf8 -*-

from console.services.market_app.component import Component
# service
from console.services.group_service import group_service
# repository
from console.repositories.group import group_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import volume_repo
from console.repositories.probe_repo import probe_repo
from console.services.app_config.service_monitor import service_monitor_repo
from console.repositories.component_graph import component_graph_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import mnt_repo as volume_dep_repo
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.plugin import app_plugin_relation_repo
# model
from www.models.main import ServiceGroup
# exception
from console.exception.main import AbortRequest


class OriginalApp(object):
    def __init__(self, tenant_id, region_name, app: ServiceGroup, upgrade_group_id):
        self.tenant_id = tenant_id
        self.region_name = region_name
        self.app_id = app.app_id
        self.upgrade_group_id = upgrade_group_id
        self.app = group_repo.get_group_by_pk(tenant_id, region_name, app.app_id)
        self.governance_mode = app.governance_mode

        self._component_ids = self._component_ids()
        self._components = self._create_components(app.app_id, upgrade_group_id)

        # dependency
        self.component_deps = dep_relation_repo.list_by_component_ids(self.tenant_id,
                                                                      [cpt.component.component_id for cpt in self._components])
        self.volume_deps = self._volume_deps()
        # config groups
        self.config_groups = self._config_groups()
        self.config_group_items = self._config_group_items()
        self.config_group_components = self._config_group_components()

    def components(self):
        return self._components

    def _component_ids(self):
        components = group_service.list_components_by_upgrade_group_id(self.app_id, self.upgrade_group_id)
        if not components:
            raise AbortRequest("components not found", "找不到组件", status_code=404, error_code=404)
        return [cpt.component_id for cpt in components]

    def _create_components(self, app_id, upgrade_group_id):
        components = group_service.list_components_by_upgrade_group_id(app_id, upgrade_group_id)
        if not components:
            raise AbortRequest("components not found", "找不到组件", status_code=404, error_code=404)

        plugin_deps = self._plugin_deps()
        # make a map of plugin_deps
        plugin_deps = {plugin_dep.service_id: plugin_dep for plugin_dep in plugin_deps}

        result = []
        # Optimization: get the attributes at once, don't get it iteratively
        for cpt in components:
            component_source = service_source_repo.get_service_source(cpt.tenant_id, cpt.service_id)
            envs = env_var_repo.get_service_env(cpt.tenant_id, cpt.service_id)
            ports = port_repo.get_service_ports(cpt.tenant_id, cpt.service_id)
            volumes = volume_repo.get_service_volumes_with_config_file(cpt.service_id)
            config_files = volume_repo.get_service_config_files(cpt.service_id)
            probe = probe_repo.get_probe(cpt.service_id)
            monitors = service_monitor_repo.list_by_service_ids(cpt.tenant_id, [cpt.service_id])
            graphs = component_graph_repo.list(cpt.service_id)
            cpt_plugin_deps = plugin_deps.get(cpt.component_id)
            result.append(Component(cpt, component_source, envs, ports, volumes, config_files, probe, None, monitors, graphs, cpt_plugin_deps))
        return result

    def _volume_deps(self):
        component_ids = [cpt.component.component_id for cpt in self._components]
        return list(volume_dep_repo.list_mnt_relations_by_service_ids(self.tenant_id, component_ids))

    def _config_groups(self):
        return list(app_config_group_repo.list(self.region_name, self.app_id))

    def _config_group_items(self):
        return list(app_config_group_item_repo.list_by_app_id(self.app_id))

    def _config_group_components(self):
        return list(app_config_group_service_repo.list_by_app_id(self.app_id))

    def _plugin_deps(self):
        return app_plugin_relation_repo.list_by_component_ids(self._component_ids)
