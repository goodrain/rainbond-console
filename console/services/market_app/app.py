# -*- coding: utf8 -*-
import json

from .new_app import NewApp
from .original_app import OriginalApp
# constant
from console.constants import PluginMetaType
from console.constants import PluginInjection
# www
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class MarketApp(object):
    def __init__(self, original_app: OriginalApp, new_app: NewApp):
        self.original_app = original_app
        self.new_app = new_app

        self.tenant_name = self.new_app.tenant.tenant_name
        self.region_name = self.new_app.region_name

    def save_new_app(self):
        self.new_app.save()

    def sync_new_app(self):
        self._sync_app(self.new_app)

    def rollback(self):
        self._sync_app(self.original_app)

    @staticmethod
    def ensure_component_deps(original_app: OriginalApp, new_deps):
        """
        确保组件依赖关系的正确性.
        根据已有的依赖关系, 新的依赖关系计算出最终的依赖关系, 计算规则如下:
        只处理同一应用下, 同一 upgrade_group_id 的组件的依赖关系, 即
        情况 1: 覆盖 app_id 和 upgrade_group_id 依赖关系
        情况 2: 保留 app_id 和 upgrade_group_id 都不同的依赖关系
        """
        # 保留 app_id 和 upgrade_group_id 都不同的依赖关系
        # component_ids 是相同 app_id 和 upgrade_group_id 下的组件, 所以 dep_service_id 不属于 component_ids 的依赖关系属于'情况2'
        component_ids = [cpt.component.component_id for cpt in original_app.components()]
        deps = [dep for dep in original_app.component_deps if dep.dep_service_id not in component_ids]
        deps.extend(new_deps)
        return deps

    @staticmethod
    def ensure_volume_deps(original_app: OriginalApp, new_deps):
        """
        确保存储依赖关系的正确性.
        根据已有的依赖关系, 新的依赖关系计算出最终的依赖关系, 计算规则如下:
        只处理同一应用下, 同一 upgrade_group_id 的存储的依赖关系, 即
        情况 1: 覆盖 app_id 和 upgrade_group_id 存储依赖关系
        情况 2: 保留 app_id 和 upgrade_group_id 都不同的存储依赖关系
        """
        # 保留 app_id 和 upgrade_group_id 都不同的依赖关系
        # component_ids 是相同 app_id 和 upgrade_group_id 下的组件, 所以 dep_service_id 不属于 component_ids 的依赖关系属于'情况2'
        component_ids = [cpt.component.component_id for cpt in original_app.components()]
        deps = [dep for dep in original_app.volume_deps if dep.dep_service_id not in component_ids]
        deps.extend(new_deps)
        return deps

    def _sync_app(self, app):
        self._sync_components(app)
        self._sync_app_config_groups(app)

    def _sync_components(self, app):
        """
        synchronous components to the application in region
        """
        components = app.components()
        plugin_bodies = self._create_plugin_bodies(components)
        new_components = []
        for cpt in components:
            component_base = cpt.component.to_dict()
            component_base["component_id"] = component_base["service_id"]
            component_base["component_name"] = component_base["service_name"]
            component_base["component_alias"] = component_base["service_alias"]
            probe = cpt.probe.to_dict()
            probe["is_used"] = 1 if probe["is_used"] else 0
            component = {
                "component_base": component_base,
                "envs": [env.to_dict() for env in cpt.envs],
                "ports": [port.to_dict() for port in cpt.ports],
                "config_files": [cf.to_dict() for cf in cpt.config_files],
                "probe": probe,
                "monitors": [monitor.to_dict() for monitor in cpt.monitors],
            }
            volumes = [volume.to_dict() for volume in cpt.volumes]
            for volume in volumes:
                volume["allow_expansion"] = True if volume["allow_expansion"] == 1 else False
            component["volumes"] = volumes
            # volume dependency
            if cpt.volume_deps:
                deps = []
                for dep in cpt.volume_deps:
                    new_dep = dep.to_dict()
                    new_dep["dep_volume_name"] = dep.mnt_name
                    new_dep["mount_path"] = dep.mnt_dir
                    deps.append(new_dep)
                component["volume_relations"] = deps
            # component dependency
            if cpt.component_deps:
                component["relations"] = [dep.to_dict() for dep in cpt.component_deps]
            if cpt.app_config_groups:
                component["app_config_groups"] = [{
                    "config_group_name": config_group.config_group_name
                } for config_group in cpt.app_config_groups]
            # plugin
            plugin_body = plugin_bodies.get(cpt.component.component_id, [])
            component["plugins"] = plugin_body
            new_components.append(component)

        body = {
            "components": new_components,
        }
        print(json.dumps(body))
        region_api.sync_components(self.tenant_name, self.region_name, self.new_app.region_app_id, body)

    def _create_plugin_bodies(self, components):
        components = {cpt.component.component_id: cpt for cpt in components}
        plugins = {plugin.plugin.plugin_id: plugin for plugin in self.new_app.plugins}
        plugin_configs = {}
        for plugin_config in self.new_app.plugin_configs:
            pcs = plugin_configs.get(plugin_config.service_id, [])
            pcs.append(plugin_config)
            plugin_configs[plugin_config.service_id] = pcs

        new_plugin_deps = {}
        for plugin_dep in self.new_app.plugin_deps:
            plugin = plugins.get(plugin_dep.plugin_id)
            if not plugin:
                continue
            component = components.get(plugin_dep.service_id)
            if not component:
                continue

            cpt_plugin_configs = plugin_configs.get(plugin_dep.service_id, [])
            normal_envs = []
            base_normal = {}
            base_ports = []
            base_services = []
            for plugin_config in cpt_plugin_configs:
                if plugin_config.service_meta_type == PluginMetaType.UNDEFINE:
                    if plugin_config.injection == PluginInjection.EVN:
                        attr_map = json.loads(plugin_config.attrs)
                        for k, v in list(attr_map.items()):
                            normal_envs.append({"env_name": k, "env_value": v})
                    else:
                        base_normal["options"] = json.loads(plugin_config.attrs)
                if plugin_config.service_meta_type == PluginMetaType.UPSTREAM_PORT:
                    base_ports.append({
                        "service_id": plugin_config.service_id,
                        "options": json.loads(plugin_config.attrs),
                        "protocol": plugin_config.protocol,
                        "port": plugin_config.container_port,
                        "service_alias": component.component.service_alias
                    })
                if plugin_config.service_meta_type == PluginMetaType.DOWNSTREAM_PORT:
                    base_services.append({
                        "depend_service_alias": plugin_config.dest_service_alias,
                        "protocol": plugin_config.protocol,
                        "service_alias": component.component.service_alias,
                        "options": json.loads(plugin_config.attrs),
                        "service_id": component.component.service_id,
                        "depend_service_id": plugin_config.dest_service_id,
                        "port": plugin_config.container_port,
                    })
            new_plugin_dep = {
                "plugin_id": plugin_dep.plugin_id,
                "version_id": plugin.build_version.build_version,
                "plugin_model": plugin.plugin.category,
                "container_cpu": plugin_dep.min_cpu,
                "container_memory": plugin_dep.min_memory,
                "switch": plugin_dep.min_memory == 1,
                "config_envs": {
                    "normal_envs": normal_envs,
                },
                "complex_envs": {
                    "base_ports": base_ports,
                    "base_services": base_services,
                    "base_normal": base_normal,
                }
            }
            pds = new_plugin_deps.get(plugin_dep.service_id, [])
            pds.append(new_plugin_dep)
            new_plugin_deps[plugin_dep.service_id] = pds
        return new_plugin_deps


    def _sync_app_config_groups(self, app):
        config_group_items = dict()
        for item in app.config_group_items:
            items = config_group_items.get(item.config_group_name, [])
            new_item = item.to_dict()
            items.append(new_item)
            config_group_items[item.config_group_name] = items
        config_group_components = dict()
        for cgc in app.config_group_components:
            cgcs = config_group_components.get(cgc.config_group_name, [])
            new_cgc = cgc.to_dict()
            cgcs.append(new_cgc)
            config_group_components[cgc.config_group_name] = cgcs
        config_groups = list()
        for config_group in app.config_groups:
            cg = config_group.to_dict()
            cg["config_items"] = config_group_items.get(config_group.config_group_name)
            cg["config_group_services"] = config_group_components.get(config_group.config_group_name)
            config_groups.append(cg)

        body = {
            "app_config_groups": config_groups,
        }
        region_api.sync_config_groups(self.tenant_name, self.region_name, self.new_app.region_app_id, body)
