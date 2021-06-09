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
from console.repositories.app_config import config_file_repo
from console.repositories.app_config import mnt_repo as volume_dep_repo
from console.repositories.component_graph import component_graph_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app_config_group import app_config_group_service_repo
# model
from www.models.main import TenantServiceRelation
from www.models.main import TenantServiceMountRelation
from console.models.main import ApplicationConfigGroup
from console.models.main import ConfigGroupItem
from console.models.main import ConfigGroupService
# utils
from www.utils.crypt import make_uuid
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class NewApp(object):
    """
    A new application formed by template application in existing application
    """

    def __init__(self, tenant_id, region_name, app_id, upgrade_group_id, app_template, new_components, update_components):
        self.tenant_id = tenant_id
        self.region_name = region_name
        self.app_id = app_id
        self.upgrade_group_id = upgrade_group_id
        self.app_template = app_template
        self.new_components = new_components
        self.update_components = update_components

        # component dependencies
        self.component_deps = self._component_deps()
        self.volume_deps = self._volume_deps()
        # config groups
        self.config_groups = self._config_groups()
        self.config_group_items = self._config_group_items()
        self.config_group_components = self._config_group_components()

    def save(self):
        # component
        self._save_components()
        self._update_components()
        # dependency
        self._save_component_deps()
        self._save_volume_deps()
        # config group
        self._save_config_groups()

    def components(self):
        components = self._components()
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
        for cpt in components:
            cpt.component_deps = component_deps.get(cpt.component.component_id)
            cpt.volume_deps = volume_deps.get(cpt.component.component_id)
            cpt.app_config_groups = config_group_components.get(cpt.component.component_id)
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
        service_source_repo.bulk_create_or_update(sources)
        service_repo.bulk_update(components)
        env_var_repo.bulk_create_or_update(envs)
        port_repo.bulk_create_or_update(ports)
        volume_repo.bulk_create_or_update(volumes)
        config_file_repo.bulk_create_or_update(config_files)
        extend_repo.bulk_create_or_update(extend_infos)
        service_monitor_repo.bulk_create_or_update(monitors)
        component_graph_repo.bulk_create_or_update(graphs)

    def _save_component_deps(self):
        dep_relation_repo.bulk_create_or_update(self.tenant_id, self.component_deps)

    def _save_volume_deps(self):
        volume_dep_repo.bulk_create_or_update(self.tenant_id, self.volume_deps)

    def _save_config_groups(self):
        app_config_group_repo.bulk_create_or_update(self.config_groups)
        app_config_group_item_repo.bulk_create_or_update(self.config_group_items)
        app_config_group_service_repo.bulk_create_or_update(self.config_group_components)

    def _exiting_deps(self):
        components = self._components()
        return dep_relation_repo.list_by_component_ids(self.tenant_id, [cpt.component.component_id for cpt in components])

    def _existing_volume_deps(self):
        components = self._components()
        volume_deps = volume_dep_repo.list_mnt_relations_by_service_ids(self.tenant_id,
                                                                        [cpt.component.component_id for cpt in components])
        return {dep.key(): dep for dep in volume_deps}

    def _component_deps(self):
        components = {cpt.component_source.service_share_uuid: cpt.component for cpt in self._components()}
        existing_deps = {dep.service_id + dep.dep_service_id: dep for dep in self._exiting_deps()}

        deps = []
        for tmpl in self.app_template.get("apps", []):
            for dep in tmpl.get("dep_service_map_list", []):
                component_key = tmpl.get("service_share_uuid")
                component = components.get(component_key)
                if not component:
                    continue

                dep_component_key = dep["dep_service_key"]
                dep_component = components.get(dep_component_key)
                if not dep_component:
                    logger.info("The component({}) cannot find the dependent component({})".format(
                        component_key, dep_component_key))
                    continue

                if existing_deps.get(component.component_id + dep_component.component_id):
                    continue

                dep = TenantServiceRelation(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    dep_service_id=dep_component.service_id,
                    dep_service_type="application",
                    dep_order=0,
                )
                deps.append(dep)
        deps.extend(self._exiting_deps())
        return deps

    def _volume_deps(self):
        components = {cpt.component_source.service_share_uuid: cpt.component for cpt in self._components()}
        existing_volume_deps = self._existing_volume_deps()
        deps = []
        for tmpl in self.app_template.get("apps", []):
            component_key = tmpl.get("service_share_uuid")
            component = components.get(component_key)
            if not component:
                continue

            for dep in tmpl.get("mnt_relation_list", []):
                # check if the dependent component exists
                dep_component_key = dep["service_share_uuid"]
                dep_component = components.get(dep_component_key)
                if not dep_component:
                    logger.info("dependent component({}) not found".format(dep_component.service_id))
                    continue

                # check if the dependent volume exists
                if not self._volume_exists(dep_component.service_id, dep["mnt_name"]):
                    logger.info("dependent volume({}/{}) not found".format(dep_component.service_id, dep["mnt_name"]))
                    continue

                # check if the volume dependency exists
                if existing_volume_deps.get(component.component_id + dep_component.component_id + dep["mnt_name"]):
                    continue

                dep = TenantServiceMountRelation(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    dep_service_id=dep_component.service_id,
                    mnt_name=dep["mnt_name"],
                    mnt_dir=dep["mnt_dir"],
                )
                deps.append(dep)
        return deps

    def _volume_exists(self, component_id, volume_name):
        volumes = []
        for cpt in self._components():
            volumes.extend(cpt.volumes)
        volumes = {vol.service_id + vol.volume_name: vol for vol in volumes}
        return True if volumes.get(component_id + volume_name) else False

    def _config_groups(self):
        config_groups = list(app_config_group_repo.list(self.region_name, self.app_id))
        config_group_names = [cg.config_group_name for cg in config_groups]
        tmpl = self.app_template.get("app_config_groups")
        for cg in tmpl:
            if cg["name"] in config_group_names:
                continue
            config_group = ApplicationConfigGroup(
                app_id=self.app_id,
                config_group_name=cg["name"],
                deploy_type=cg["injection_type"],
                enable=True,  # tmpl does not have the 'enable' property
                region_name=self.region_name,
                config_group_id=make_uuid(),
            )
            config_groups.append(config_group)
        return config_groups

    def _config_group_items(self):
        config_group_ids = [cg.config_group_id for cg in self.config_groups]
        config_groups = {cg.config_group_name: cg for cg in self.config_groups}

        config_group_items = list(app_config_group_item_repo.list_by_config_group_ids(config_group_ids))
        item_keys = [item.config_group_name + item.item_key for item in config_group_items]
        tmpl = self.app_template.get("app_config_groups")
        for cg in tmpl:
            config_group = config_groups.get(cg["name"])
            if not config_group:
                logger.warning("config group {} not found".format(cg["name"]))
                continue
            items = cg.get("config_items")
            if not items:
                continue
            for item_key in items:
                key = cg["name"] + item_key
                if key in item_keys:
                    # do not change existing items
                    continue
                item = ConfigGroupItem(
                    app_id=self.app_id,
                    config_group_name=cg["name"],
                    item_key=item_key,
                    item_value=items[item_key],
                    config_group_id=config_group.config_group_id,
                )
                config_group_items.append(item)
        return config_group_items

    def _config_group_components(self):
        components = {cpt.component.service_key: cpt for cpt in self._components()}

        config_groups = {cg.config_group_name: cg for cg in self.config_groups}

        config_group_components = list(app_config_group_service_repo.list_by_app_id(self.app_id))
        config_group_component_keys = [cgc.config_group_name + cgc.service_id for cgc in config_group_components]

        tmpl = self.app_template.get("app_config_groups")
        for cg in tmpl:
            config_group = config_groups.get(cg["name"])
            if not config_group:
                continue

            component_keys = cg.get("component_keys", [])
            for component_key in component_keys:
                cpt = components.get(component_key)
                if not cpt:
                    continue
                key = config_group.config_group_name + cpt.component.component_id
                if key in config_group_component_keys:
                    continue
                cgc = ConfigGroupService(
                    app_id=self.app_id,
                    config_group_name=config_group.config_group_name,
                    service_id=cpt.component.component_id,
                    config_group_id=config_group.config_group_id,
                )
                config_group_components.append(cgc)
        return config_group_components
