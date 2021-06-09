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
# exception
from console.exception.main import AbortRequest


class OriginalApp(object):
    def __init__(self, tenant_id, app_id, upgrade_group_id, app_model_key, governance_mode):
        self.app_id = app_id
        self.upgrade_group_id = upgrade_group_id
        self.app_model_key = app_model_key
        self.governance_mode = governance_mode
        self._components = self._create_components(app_id, upgrade_group_id, app_model_key)

        self.component_deps = dep_relation_repo.list_by_component_ids(tenant_id,
                                                                      [cpt.component.component_id for cpt in self._components])
        # TODO(huangrh): volume dependency
        self.volume_deps = []
        # TODO(huangrh): config groups
        # TODO(huangrh): config files

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

    def components(self):
        return self._components
