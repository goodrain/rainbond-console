# -*- coding: utf-8 -*-
import logging

# service
from console.services.market_app.new_components import Component
from console.services.app_config.promql_service import promql_service
# repository
from console.services.app_config.service_monitor import service_monitor_repo
# exception
from console.exception.main import AbortRequest
# utils
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class PropertyChanges(object):
    def __init__(self, components, app_template):
        self.components = components
        self.app_template = app_template
        self.changes = self._get_component_changes(components, app_template)

    def need_change(self):
        return self.changes

    def _get_component_changes(self, components, app_template):
        cpt_changes = []
        for cpt in components:
            # get component template
            tmpl = self._get_component_template(cpt.component_source, app_template)
            if not tmpl:
                continue
            cpt_changes.append(self._get_component_change(cpt, tmpl))

        return cpt_changes

    @staticmethod
    def _get_component_template(component_source, app_template):
        component_tmpls = app_template.get("apps")

        def func(x):
            result = x.get("service_share_uuid", None) == component_source.service_share_uuid \
                     or x.get("service_key", None) == component_source.service_share_uuid

            return result

        return next(iter([x for x in component_tmpls if func(x)]), None)

    def _get_component_change(self, component: Component, component_tmpl: map):
        result = {"component_id": component.component.service_id}
        deploy_version = self._deploy_version(component.component.deploy_version, component_tmpl.get("deploy_version"))
        if deploy_version:
            result["deploy_version"] = deploy_version
        envs = self._envs(component.envs, component_tmpl.get("service_env_map_list", []))
        if envs:
            result["envs"] = envs
        connect_infos = self._envs(component.envs, component_tmpl.get("service_connect_info_map_list", []))
        if connect_infos:
            result["connect_infos"] = connect_infos
        ports = self._ports(component.ports, component_tmpl.get("port_map_list", []))
        if ports:
            result["ports"] = ports
        volumes = self._volumes(component.volumes, component_tmpl.get("service_volume_map_list", []))
        if volumes:
            result["volumes"] = volumes
        probe = self._probe(component.probe, component_tmpl["probes"])
        if probe:
            result["probe"] = probe
        # TODO(huangrh)
        # dep_uuids = []
        # if component.get("dep_service_map_list", []):
        #     dep_uuids = [item["dep_service_key"] for item in component.get("dep_service_map_list")]
        # dep_services = self.dep_services_changes(component, dep_uuids, component_names, level)
        # if dep_services:
        #     result["dep_services"] = dep_services
        # dep_volumes = self.dep_volumes_changes(component.get("mnt_relation_list", []))
        # if dep_volumes:
        #     result["dep_volumes"] = dep_volumes
        # plugin_component_configs = self.plugin_changes(component.get("service_related_plugin_config", []))
        # if plugin_component_configs:
        #     result["plugins"] = plugin_component_configs
        # app_config_groups = self.app_config_group_changes(template)
        # if app_config_groups:
        #     logger.debug("app_config_groups changes: {}".format(json.dumps(app_config_groups)))
        #     result["app_config_groups"] = app_config_groups

        component_graphs = self._graphs(component.component.component_id, component.graphs,
                                        component_tmpl.get("component_graphs", []))
        if component_graphs:
            result["component_graphs"] = component_graphs

        monitors = self._monitors(component.component.tenant_id, component.monitors, component_tmpl.get(
            "component_monitors", []))
        if monitors:
            result["component_monitors"] = monitors

        return result

    @staticmethod
    def _deploy_version(old, new):
        """
        compare the old and new deploy versions to determine if there is any change
        """
        # deploy_version is Build the app version of the source
        if not new:
            return None
        is_change = old < new
        if not is_change:
            return None
        return {"old": old, "new": new, "is_change": is_change}

    @staticmethod
    def _envs(exist_envs, new_envs):
        """
        Environment variables are only allowed to increase, not allowed to
        update and delete. Compare existing environment variables and input
        environment variables to find out which ones need to be added.
        """
        exist_envs = {env.attr_name: env for env in exist_envs}
        add_env = [env for env in new_envs if not exist_envs.get(env["attr_name"])]
        if not add_env:
            return None
        return {"add": add_env}

    @staticmethod
    def _ports(old_ports, new_ports):
        """port can only be created, cannot be updated and deleted"""
        if not new_ports:
            return
        old_container_ports = {port.container_port: port for port in old_ports}
        create_ports = [port for port in new_ports if port["container_port"] not in old_container_ports]
        update_ports = []
        for new_port in new_ports:
            if new_port["container_port"] not in old_container_ports:
                continue
            old_port = old_container_ports[new_port["container_port"]]
            if new_port["is_outer_service"] and not old_port.is_outer_service:
                update_ports.append(new_port)
                continue
            if new_port["is_inner_service"] and not old_port.is_inner_service:
                update_ports.append(new_port)
                continue
        if not create_ports and not update_ports:
            return None
        result = {}
        if create_ports:
            result["add"] = create_ports
        if update_ports:
            result["upd"] = update_ports
        return result

    @staticmethod
    def _volumes(old_volumes, new_volumes):
        if not new_volumes:
            return
        old_volume_paths = {volume.volume_path: volume for volume in old_volumes}
        old_volume_names = {volume.volume_name: volume for volume in old_volumes}
        add = []
        update = []
        for new_volume in new_volumes:
            old_volume = old_volume_paths.get(new_volume["volume_path"], None)
            old_volume_name = old_volume_names.get(new_volume["volume_name"], None)
            if not old_volume and not old_volume_name:
                add.append(new_volume)
                continue
            if not old_volume and old_volume_name:
                new_volume["volume_name"] = new_volume["volume_name"] + "-" + make_uuid()[:6]
                add.append(new_volume)
                continue
            if not new_volume.get("file_content"):
                continue
            # TODO(huangrh)
            # old_file_content = volume_repo.get_service_config_file(old_volume.ID)
            # if old_file_content and old_file_content.file_content != new_volume["file_content"]:
            #     update.append(new_volume)
        if not add and not update:
            return None
        return {
            "add": add,
            "upd": update,
        }

    @staticmethod
    def _probe(old_probe, new_probes):
        if not new_probes:
            return None
        new_probe = new_probes[0]
        # remove redundant keys
        for key in ["ID", "probe_id", "service_id"]:
            if key in list(new_probe.keys()):
                new_probe.pop(key)
        if not old_probe:
            return {"add": new_probe, "upd": []}
        old_probe = old_probe.to_dict()
        for k, v in list(new_probe.items()):
            if key in list(new_probe.keys()) and old_probe[k] != v:
                return {"add": [], "upd": new_probe}
        return None

    @staticmethod
    def _graphs(component_id, old_graphs, graphs):
        if not graphs:
            return None

        old_promqls = [graph.promql for graph in old_graphs if old_graphs]
        add = []
        for graph in graphs:
            try:
                new_promql = promql_service.add_or_update_label(component_id, graph.get("promql"))
            except AbortRequest as e:
                logger.warning("promql: {}, {}".format(graph.get("promql"), e))
                continue
            if new_promql not in old_promqls:
                add.append(graph)
        if not add:
            return None
        return {"add": add}

    @staticmethod
    def _monitors(tenant_id, old_monitors, monitors):
        if not monitors:
            return None
        add = []
        old_monitor_names = [monitor.name for monitor in old_monitors if old_monitors]
        for monitor in monitors:
            # Optimization: do not check monitor name iteratively
            tenant_monitor = service_monitor_repo.get_tenant_service_monitor(tenant_id, monitor["name"])
            if not tenant_monitor and monitor["name"] not in old_monitor_names:
                add.append(monitor)
        if not add:
            return None
        return {"add": add}
