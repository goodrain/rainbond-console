# -*- coding: utf8 -*-

from console.services.market_app.component import Component
# service
from console.services.group_service import group_service
# repository
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
# exception
from console.exception.main import AbortRequest


class OriginalApp(object):
    def __init__(self, tenant, region_name, app_id, upgrade_group_id, app_model_key, governance_mode):
        self.tenant_id = tenant.tenant_id
        self.region_name = region_name
        self.app_id = app_id
        self.upgrade_group_id = upgrade_group_id
        self.app_model_key = app_model_key
        self.governance_mode = governance_mode
        self._components = self._create_components(app_id, upgrade_group_id, app_model_key)

        self.component_deps = dep_relation_repo.list_by_component_ids(self.tenant_id,
                                                                      [cpt.component.component_id for cpt in self._components])
        self.volume_deps = self._volume_deps()

        # config groups
        self.config_groups = self._config_groups()
        self.config_group_items = self._config_group_items()
        self.config_group_components = self._config_group_components()

    def components(self):
        return self._components

    @staticmethod
    def _create_components(app_id, upgrade_group_id, app_model_key):
        components = group_service.get_rainbond_services(app_id, app_model_key, upgrade_group_id)
        if not components:
            raise AbortRequest("components not found", "找不到组件", status_code=404, error_code=404)

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
            result.append(Component(cpt, component_source, envs, ports, volumes, config_files, probe, None, monitors, graphs))
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
