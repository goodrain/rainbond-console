# -*- coding: utf-8 -*-
import logging

from .utils import get_component_template
# service
from console.services.market_app.component import Component
from console.services.app_config.promql_service import promql_service
# repository
from console.services.app_config.service_monitor import service_monitor_repo
# model
from www.models.plugin import TenantPlugin
from www.models.plugin import TenantServicePluginRelation
# exception
from console.exception.main import AbortRequest
# utils
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class PropertyChanges(object):
    def __init__(self, components, plugins: [TenantPlugin], app_template):
        self.components = components
        self.plugins = plugins
        self.app_template = app_template
        self.changes = self._get_component_changes(components, app_template)

    def need_change(self):
        return self.changes

    def _get_component_changes(self, components, app_template):
        cpt_changes = []
        for cpt in components:
            # get component template
            tmpl = get_component_template(cpt.component_source, app_template)
            if not tmpl:
                continue
            cpt_changes.append(self._get_component_change(cpt, tmpl))

        return cpt_changes

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
        volumes = self._volumes(component.volumes, component_tmpl.get("service_volume_map_list", []), component.config_files)
        if volumes:
            result["volumes"] = volumes
        probe = self._probe(component.probe, component_tmpl["probes"])
        if probe:
            result["probe"] = probe
        # plugin dependency
        plugin_deps = self._plugin_deps(component.plugin_deps, component_tmpl.get("service_related_plugin_config"))
        if plugin_deps:
            result["plugin_deps"] = plugin_deps

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
        is_change = old != new
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
        """
        Support for adding and updating.
        Allow to update is_inner_service, is_inner_service, protocol and port alias.
        The port can be opened, but the port cannot be closed.
        """
        if not new_ports:
            return
        old_container_ports = {port.container_port: port for port in old_ports}
        create_ports = [port for port in new_ports if port["container_port"] not in old_container_ports]

        update_ports = []
        for new_port in new_ports:
            if new_port["container_port"] not in old_container_ports:
                continue
            old_port = old_container_ports[new_port["container_port"]]
            outer_change = new_port["is_outer_service"] and not old_port.is_outer_service
            inner_change = new_port["is_inner_service"] and not old_port.is_inner_service
            protocol_change = new_port["protocol"] != old_port.protocol
            port_alias_change = new_port["port_alias"] != old_port.port_alias
            if outer_change or inner_change or protocol_change or port_alias_change:
                update_ports.append(new_port)
        if not create_ports and not update_ports:
            return None

        result = {}
        if create_ports:
            result["add"] = create_ports
        if update_ports:
            result["upd"] = update_ports
        return result

    @staticmethod
    def _volumes(old_volumes, new_volumes, config_files):
        """
        Support for adding volume and updating config file.
        """
        if not new_volumes:
            return
        old_volume_paths = {volume.volume_path: volume for volume in old_volumes}
        old_volume_names = {volume.volume_name: volume for volume in old_volumes}
        config_files = {config_file.volume_name: config_file for config_file in config_files}

        add = []
        update = []
        for new_volume in new_volumes:
            old_volume = old_volume_paths.get(new_volume["volume_path"])
            old_volume_name = old_volume_names.get(new_volume["volume_name"])
            if not old_volume and not old_volume_name:
                add.append(new_volume)
                continue
            if not old_volume and old_volume_name:
                new_volume["volume_name"] = new_volume["volume_name"] + "-" + make_uuid()[:6]
                add.append(new_volume)
                continue
            file_content = new_volume.get("file_content")
            if not file_content:
                continue
            # configuration file
            config_file = config_files.get(new_volume["volume_name"])
            if config_file and config_file.file_content != new_volume["file_content"]:
                update.append(new_volume)
        if not add and not update:
            return None
        return {
            "add": add,
            "upd": update,
        }

    @staticmethod
    def _probe(old_probe, new_probes):
        """
        Support adding and updating all attributes
        """
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
            if k in list(old_probe.keys()) and old_probe[k] != v:
                return {"add": [], "upd": new_probe}
        return None

    @staticmethod
    def _graphs(component_id, old_graphs, graphs):
        """
        Support adding and updating promql
        """
        if not graphs:
            return None

        old_graphs = {graph.title: graph for graph in old_graphs if old_graphs}
        add = []
        update = []
        for graph in graphs:
            old_graph = old_graphs.get(graph.get("title"))
            if not old_graph:
                add.append(graph)
                continue

            try:
                old_promql = promql_service.add_or_update_label(component_id, old_graph.promql)
                new_promql = promql_service.add_or_update_label(component_id, graph.get("promql"))
            except AbortRequest as e:
                logger.warning("promql: {}, {}".format(graph.get("promql"), e))
                continue
            if new_promql != old_promql:
                update.append(graph)
        return {
            "add": add,
            "upd": update,
        }

    @staticmethod
    def _monitors(tenant_id, old_monitors, monitors):
        """
        Support adding and updating
        """
        if not monitors:
            return None
        add = []
        old_monitor_names = [monitor.name for monitor in old_monitors if old_monitors]
        old_show_names = [monitor.service_show_name for monitor in old_monitors if old_monitors]
        for monitor in monitors:
            if monitor["name"] in old_monitor_names:
                continue
            else:
                if monitor["service_show_name"] in old_show_names:
                    continue
            # Optimization: do not check monitor name iteratively
            tenant_monitor = service_monitor_repo.get_tenant_service_monitor(tenant_id, monitor["name"])
            if tenant_monitor:
                monitor["name"] += "-" + make_uuid()[:4]
            add.append(monitor)
        if not add:
            return None
        return {"add": add}

    def _plugin_deps(self, old_plugin_deps: [TenantServicePluginRelation], plugin_deps):
        if not plugin_deps:
            return None
        add = []
        exist_plugin_ids = [plugin_dep.plugin_id for plugin_dep in old_plugin_deps]
        exist_plugin_keys = [plugin.origin_share_id for plugin in self.plugins if plugin.plugin_id in exist_plugin_ids]
        plugins = {plugin.origin_share_id: plugin for plugin in self.plugins}
        for plugin_dep in plugin_deps:
            if plugin_dep["plugin_key"] in exist_plugin_keys:
                continue
            plugin = plugins.get(plugin_dep["plugin_key"])
            if not plugin:
                logger.warning("plugin {} not found".format(plugin_dep["plugin_key"]))
                continue
            plugin_dep["plugin"] = plugin.to_dict()
            add.append(plugin_dep)
        return {"add": add}
