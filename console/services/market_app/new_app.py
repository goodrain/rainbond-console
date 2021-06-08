# -*- coding: utf8 -*-
import logging

# repository
from console.services.app_config.service_monitor import service_monitor_repo
from console.repositories.service_repo import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import extend_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.app_config import volume_repo
from console.repositories.component_graph import component_graph_repo
# model
from www.models.main import TenantServiceRelation

logger = logging.getLogger('default')


class NewApp(object):
    """
    A new application formed by template application in existing application
    """

    def __init__(self, upgrade_group_id, app_template, new_components, update_components):
        self.upgrade_group_id = upgrade_group_id
        self.app_template = app_template
        self.new_components = new_components
        self.update_components = update_components

        # component dependencies
        self.component_deps = self._component_deps()

    def save(self):
        self._save_components()
        self._update_components()
        self._update_component_deps()

    def components(self):
        components = self.new_components + self.update_components
        component_deps = {}
        for dep in self.component_deps:
            deps = component_deps.get(dep.service_id, [])
            deps.append(dep)
            component_deps[dep.service_id] = deps
        for cpt in components:
            cpt.component_deps = component_deps.get(cpt.component_id)
        return components

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
            if cpt.extend_info:
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
        sources = []
        envs = []
        ports = []
        volumes = []
        probes = []
        extend_infos = []
        monitors = []
        graphs = []
        for cpt in self.update_components:
            sources.append(cpt.component_source)
            envs.extend(cpt.envs)
            ports.extend(cpt.ports)
            volumes.extend(cpt.volumes)
            if cpt.probe:
                probes.append(cpt.probe)
            if cpt.extend_info:
                extend_infos.append(cpt.extend_info)
            monitors.extend(cpt.monitors)
            graphs.extend(cpt.graphs)

        components = [cpt.component for cpt in self.update_components]
        service_source_repo.bulk_create_or_update(sources)
        service_repo.bulk_update(components)
        env_var_repo.bulk_create_or_update(envs)
        port_repo.bulk_create_or_update(ports)
        volume_repo.bulk_create_or_update(volumes)
        extend_repo.bulk_create_or_update(extend_infos)
        service_monitor_repo.bulk_create_or_update(monitors)
        component_graph_repo.bulk_create_or_update(graphs)

    def _update_component_deps(self):
        dep_relation_repo.bulk_create_or_update(self.component_deps)

    def _exiting_deps(self):
        components = self.components()
        return dep_relation_repo.list_by_component_ids([cpt.component.component_id for cpt in components])

    def _component_deps(self):
        components = {cpt.component.service_key: cpt.component for cpt in self.components()}
        existing_deps = {dep.service_id + dep.dep_service_id: dep for dep in self._exiting_deps()}
        deps = []
        for tmpl in self.app_template.get("apps", []):
            for dep in tmpl.get("dep_service_map_list", []):
                component_key = tmpl.get("service_key")
                component = components.get(component_key)
                if not component:
                    continue

                dep_component_key = dep["dep_service_key"]
                dep_component = components.get(dep_component_key)
                if not dep_component:
                    logger.info("The component({}) cannot find the dependent component({})".format(component_key,
                                                                                                   dep_component_key))
                    continue

                if existing_deps.get(component_key + dep_component_key):
                    continue

                dep = TenantServiceRelation(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    dep_service_id=dep_component.service_id,
                )
                deps.append(dep)
        deps.extend(self._exiting_deps())
        return deps
