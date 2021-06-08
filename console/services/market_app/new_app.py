# -*- coding: utf8 -*-

from console.repositories.service_repo import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import extend_repo
from console.repositories.probe_repo import probe_repo
from console.services.app_config.service_monitor import service_monitor_repo
from console.repositories.component_graph import component_graph_repo


class NewApp(object):
    """
    A new application formed by template application in existing application
    """

    def __init__(self, upgrade_group_id, new_components, update_components):
        self.upgrade_group_id = upgrade_group_id
        self.new_components = new_components
        self.update_components = update_components

    def save(self):
        self._save_components()
        self._update_components()

    def components(self):
        return self.new_components + self.update_components

    def _save_components(self):
        """
        create new components
        """
        component_sources = []
        envs = []
        ports = []
        volumes = []
        probes = []
        extend_infos = []
        monitors = []
        graphs = []
        for cpt in self.new_components:
            envs.extend(cpt.envs)
            ports.extend(cpt.ports)
            volumes.extend(cpt.volumes)
            probes.extend(cpt.probes)
            extend_infos.append(cpt.extend_info)
            monitors.extend(cpt.monitors)
            graphs.extend(cpt.graphs)
        components = [cpt.component for cpt in self.new_components]

        service_repo.bulk_create(components)
        service_source_repo.bulk_create(component_sources)
        env_var_repo.bulk_create(envs)
        port_repo.bulk_create(ports)
        probe_repo.bulk_create(probes)
        extend_repo.bulk_create(extend_infos)
        service_monitor_repo.bulk_create(monitors)
        component_graph_repo.bulk_create(graphs)

    def _update_components(self):
        """
        update existing components
        """
        envs = []
        ports = []
        volumes = []
        probes = []
        extend_infos = []
        monitors = []
        graphs = []
        for cpt in self.update_components:
            envs.extend(cpt.envs)
            ports.extend(cpt.ports)
            volumes.extend(cpt.volumes)
            if cpt.probe:
                probes.append(cpt.probe)
            extend_infos.append(cpt.extend_info)
            monitors.extend(cpt.monitors)
            graphs.extend(cpt.graphs)

        components = [cpt.component for cpt in self.update_components]
        service_repo.bulk_update(components)
        # TODO(huangrh): component sources
        env_var_repo.bulk_create_or_update(envs)
        # TODO(huangrh): ports, probe, etc.
