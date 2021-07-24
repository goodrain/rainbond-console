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
from console.repositories.app_config import domain_repo
from console.repositories.probe_repo import probe_repo
from console.services.app_config.service_monitor import service_monitor_repo
from console.repositories.component_graph import component_graph_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import mnt_repo as volume_dep_repo
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.plugin import service_plugin_config_repo
# model
from www.models.main import ServiceGroup
from console.models.main import RegionConfig


class OriginalApp(object):
    def __init__(self, tenant_id, region: RegionConfig, app: ServiceGroup, upgrade_group_id):
        self.tenant_id = tenant_id
        self.region = region
        self.region_name = region.region_name
        self.app_id = app.app_id
        self.upgrade_group_id = upgrade_group_id
        self.app = group_repo.get_group_by_pk(tenant_id, region.region_name, app.app_id)
        self.governance_mode = app.governance_mode

        self._component_ids = self._component_ids()
        self._components = self._create_components(app.app_id, upgrade_group_id)

        # dependency
        component_deps = dep_relation_repo.list_by_component_ids(self.tenant_id,
                                                                 [cpt.component.component_id for cpt in self._components])
        self.component_deps = list(component_deps)
        self.volume_deps = self._volume_deps()

        # plugins
        self.plugin_deps = self._plugin_deps()
        self.plugin_configs = self._plugin_configs()

        # config groups
        self.config_groups = self._config_groups()
        self.config_group_items = self._config_group_items()
        self.config_group_components = self._config_group_components()

    def components(self):
        return self._components

    def _component_ids(self):
        components = group_service.list_components_by_upgrade_group_id(self.app_id, self.upgrade_group_id)
        return [cpt.component_id for cpt in components]

    def _create_components(self, app_id, upgrade_group_id):
        components = group_service.list_components_by_upgrade_group_id(app_id, upgrade_group_id)
        component_ids = [cpt.component_id for cpt in components]

        http_rules = self._list_http_rules(component_ids)

        result = []
        # TODO(huangrh): get the attributes at once, don't get it iteratively
        for cpt in components:
            component_source = service_source_repo.get_service_source(cpt.tenant_id, cpt.service_id)
            envs = env_var_repo.get_service_env(cpt.tenant_id, cpt.service_id)
            ports = port_repo.get_service_ports(cpt.tenant_id, cpt.service_id)
            volumes = volume_repo.get_service_volumes_with_config_file(cpt.service_id)
            config_files = volume_repo.get_service_config_files(cpt.service_id)
            probes = probe_repo.list_probes(cpt.service_id)
            monitors = service_monitor_repo.list_by_service_ids(cpt.tenant_id, [cpt.service_id])
            graphs = component_graph_repo.list(cpt.service_id)
            rules = http_rules.get(cpt.component_id)
            component = Component(
                cpt, component_source, envs, ports, volumes, config_files, probes, None, monitors, graphs, [], http_rules=rules)
            result.append(component)
        return result

    @staticmethod
    def _list_http_rules(component_ids):
        http_rules = domain_repo.list_by_component_ids(component_ids)
        result = {}
        for rule in http_rules:
            rules = result.get(rule.service_id, [])
            rules.append(rule)
            result[rule.service_id] = rules
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

    def _plugin_configs(self):
        return service_plugin_config_repo.list_by_component_ids(self._component_ids)
