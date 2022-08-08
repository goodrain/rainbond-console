# -*- coding: utf8 -*-
import json

from django.db import transaction

from .enum import ActionType
from .new_app import NewApp
from .original_app import OriginalApp
from .plugin import Plugin
# repository
from console.repositories.label_repo import label_repo
from console.repositories.plugin import config_group_repo
from console.repositories.plugin import config_item_repo
from console.repositories.plugin.plugin import plugin_version_repo
from console.repositories.plugin.plugin import plugin_repo
from console.repositories.plugin.plugin_version import build_version_repo
from console.repositories.app_config import domain_repo
# constant
from console.constants import PluginMetaType
from console.constants import PluginInjection
# model
from www.models.main import ServiceDomain
# www
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_app import region_app_repo

region_api = RegionInvokeApi()


class MarketApp(object):
    def __init__(self, original_app: OriginalApp, new_app: NewApp):
        self.original_app = original_app
        self.new_app = new_app

        self.tenant_name = self.new_app.tenant.tenant_name
        self.region_name = self.new_app.region_name

        self.labels = {label.label_id: label for label in label_repo.get_all_labels()}

    @transaction.atomic
    def save_new_app(self):
        self.new_app.save()

    def sync_new_app(self):
        self._sync_new_components()
        self._sync_app_config_groups(self.new_app)
        self._sync_app_k8s_resources(self.new_app)

    def rollback(self):
        self._rollback_components()
        self._sync_app_config_groups(self.original_app)
        # Since the application of k8s resources can create PV and other resources,
        # this kind of resources will not be rolled back for the time being
        # self._sync_app_k8s_resources(self.original_app)

    def deploy(self):
        builds = self._generate_builds()
        upgrades = self._generate_upgrades()

        # Region do not support different operation in one API.
        # We have to call build, then upgrade.
        res = []
        if builds:
            body = {
                "operation": "build",
                "build_infos": builds,
            }
            _, body = region_api.batch_operation_service(self.new_app.region_name, self.new_app.tenant.tenant_name, body)
            res += body["bean"]["batch_result"]

        if upgrades:
            body = {
                "operation": "upgrade",
                "upgrade_infos": upgrades,
            }
            _, body = region_api.batch_operation_service(self.new_app.region_name, self.new_app.tenant.tenant_name, body)
            res += body["bean"]["batch_result"]

        return res

    def ensure_component_deps(self, new_deps, tmpl_component_ids=[], is_upgrade_one=False):
        """
        确保组件依赖关系的正确性.
        根据已有的依赖关系, 新的依赖关系计算出最终的依赖关系, 计算规则如下:
        只处理同一应用下, 同一 upgrade_group_id 的组件的依赖关系, 即
        情况 1: 覆盖 app_id 和 upgrade_group_id 依赖关系
        情况 2: 保留 app_id 和 upgrade_group_id 都不同的依赖关系
        """
        # 保留 app_id 和 upgrade_group_id 都不同的依赖关系
        # component_ids 是相同 app_id 和 upgrade_group_id 下的组件, 所以 dep_service_id 不属于 component_ids 的依赖关系属于'情况2'
        if is_upgrade_one:
            # If the dependency of the component has changed with other components (existing in the template
            # and installed), then update it.
            new_deps.extend(self.original_app.component_deps)
            return self._dedup_deps(new_deps)
        component_ids = [cpt.component.component_id for cpt in self.original_app.components()]
        if tmpl_component_ids:
            component_ids = [component_id for component_id in component_ids if component_id in tmpl_component_ids]
        deps = []
        for dep in self.original_app.component_deps:
            if dep.dep_service_id not in component_ids:
                deps.append(dep)
                continue
            if tmpl_component_ids and dep.service_id not in tmpl_component_ids:
                deps.append(dep)
        deps.extend(new_deps)
        return self._dedup_deps(deps)

    def ensure_volume_deps(self, new_deps, tmpl_component_ids=[], is_upgrade_one=False):
        """
        确保存储依赖关系的正确性.
        根据已有的依赖关系, 新的依赖关系计算出最终的依赖关系, 计算规则如下:
        只处理同一应用下, 同一 upgrade_group_id 的存储的依赖关系, 即
        情况 1: 覆盖 app_id 和 upgrade_group_id 存储依赖关系
        情况 2: 保留 app_id 和 upgrade_group_id 都不同的存储依赖关系
        """
        # 保留 app_id 和 upgrade_group_id 都不同的依赖关系
        # component_ids 是相同 app_id 和 upgrade_group_id 下的组件, 所以 dep_service_id 不属于 component_ids 的依赖关系属于'情况2'
        if is_upgrade_one:
            # If the dependency of the component has changed with other components (existing in the template
            # and installed), then update it.
            new_deps.extend(self.original_app.volume_deps)
            return self._dedup_deps(new_deps)
        component_ids = [cpt.component.component_id for cpt in self.original_app.components()]
        if tmpl_component_ids:
            component_ids = [component_id for component_id in component_ids if component_id in tmpl_component_ids]
        deps = []
        for dep in self.original_app.volume_deps:
            if dep.dep_service_id not in component_ids:
                deps.append(dep)
                continue
            if tmpl_component_ids and dep.service_id not in tmpl_component_ids:
                deps.append(dep)
        deps.extend(new_deps)
        return self._dedup_deps(deps)

    def _sync_new_components(self):
        """
        synchronous components to the application in region
        """
        body = {
            "components": self._create_component_body(self.new_app),
        }
        region_api.sync_components(self.tenant_name, self.region_name, self.new_app.region_app_id, body)

    def _rollback_components(self):
        body = {
            "components": self._create_component_body(self.original_app),
            "delete_component_ids": [cpt.component.component_id for cpt in self.new_app.new_components]
        }
        region_api.sync_components(self.tenant_name, self.region_name, self.new_app.region_app_id, body)

    def _create_component_body(self, app):
        components = app.components()
        plugin_bodies = self._create_plugin_body(components)
        new_components = []
        certs = domain_repo.list_all_certificate()
        cert_id_rels = dict()
        if certs:
            cert_id_rels = {cert.ID: cert.certificate_id for cert in certs}
        for cpt in components:
            component_base = cpt.component.to_dict()
            component_base["component_id"] = component_base["service_id"]
            component_base["component_name"] = component_base["service_name"]
            component_base["component_alias"] = component_base["service_alias"]
            component_base["container_cpu"] = cpt.component.min_cpu
            component_base["container_memory"] = cpt.component.min_memory
            component_base["replicas"] = cpt.component.min_node
            probes = [probe.to_dict() for probe in cpt.probes]
            for probe in probes:
                probe["is_used"] = 1 if probe["is_used"] else 0
            component = {
                "component_base": component_base,
                "envs": [env.to_dict() for env in cpt.envs],
                "ports": [port.to_dict() for port in cpt.ports],
                "config_files": [cf.to_dict() for cf in cpt.config_files],
                "probes": probes,
                "monitors": [monitor.to_dict() for monitor in cpt.monitors],
                "http_rules": self._create_http_rules(cpt.http_rules, cert_id_rels),
                "http_rule_configs": [json.loads(config.value) for config in cpt.http_rule_configs],
                "component_k8s_attributes": [attr.to_dict() for attr in cpt.k8s_attributes],
            }
            volumes = [volume.to_dict() for volume in cpt.volumes]
            for volume in volumes:
                volume["allow_expansion"] = True if volume["allow_expansion"] == 1 else False
            component["volumes"] = volumes
            # labels
            labels = []
            for cl in cpt.labels:
                label = self.labels.get(cl.label_id)
                if not label:
                    continue
                labels.append({"label_key": "node-selector", "label_value": label.label_name})
            component["labels"] = labels
            # volume dependency
            deps = []
            if cpt.volume_deps:
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
        return new_components

    def _create_plugin_body(self, components):
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
                "switch": plugin_dep.plugin_status == 1,
                "config_envs": {
                    "normal_envs": normal_envs,
                    "complex_envs": {
                        "base_ports": base_ports,
                        "base_services": base_services,
                        "base_normal": base_normal,
                    }
                },
            }
            pds = new_plugin_deps.get(plugin_dep.service_id, [])
            pds.append(new_plugin_dep)
            new_plugin_deps[plugin_dep.service_id] = pds
        return new_plugin_deps

    @staticmethod
    def _create_http_rules(gateway_rules: [ServiceDomain], cert_id_rels: dict):
        rules = []
        for gateway_rule in gateway_rules:
            rule = gateway_rule.to_dict()
            rule["domain"] = gateway_rule.domain_name
            rule["certificate_id"] = cert_id_rels.get(rule["certificate_id"], "")

            rule_extensions = []
            for ext in gateway_rule.rule_extensions.split(";"):
                kvs = ext.split(":")
                if len(kvs) != 2 or kvs[0] == "" or kvs[1] == "":
                    continue
                rule_extensions.append({
                    "key": kvs[0],
                    "value": kvs[1],
                })
            rule["rule_extensions"] = rule_extensions
            rule["path"] = gateway_rule.domain_path
            rule["header"] = gateway_rule.domain_heander
            rule["cookie"] = gateway_rule.domain_cookie
            rule["weight"] = gateway_rule.the_weight
            rule["path_rewrite"] = gateway_rule.path_rewrite
            rewrites = gateway_rule.rewrites if gateway_rule.rewrites else []
            if isinstance(rewrites, str):
                rewrites = eval(rewrites)
            rule["rewrites"] = rewrites
            rules.append(rule)
        return rules

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

    def _sync_app_k8s_resources(self, app):
        # only add k8s resources
        k8s_resources = list()
        region_app_id = region_app_repo.get_region_app_id(self.region_name, self.app_id)
        for k8s_resource in app.k8s_resources:
            resource = {
                "name": k8s_resource.name,
                "app_id": region_app_id,
                "namespace": app.tenant.namespace,
                "kind": k8s_resource.kind,
                "resource_yaml": k8s_resource.content,
            }
            k8s_resources.append(resource)
        data = {
            "k8s_resources": k8s_resources,
        }
        res, body = region_api.sync_k8s_resources(self.tenant_name, self.region_name, data)
        if not body.get("list"):
            return
        resource_statuses = {resource["name"] + resource["kind"]: resource for resource in body["list"]}
        for k8s_resource in app.k8s_resources:
            resource_key = k8s_resource.name + k8s_resource.kind
            if resource_statuses.get(resource_key):
                k8s_resource.state = resource_statuses[resource_key]["state"]
                k8s_resource.error_overview = resource_statuses[resource_key]["error_overview"]
        if isinstance(app, NewApp):
            self.new_app.k8s_resources = app.k8s_resources

    def list_original_plugins(self):
        plugins = plugin_repo.list_by_tenant_id(self.original_app.tenant_id, self.region_name)
        plugin_ids = [plugin.plugin_id for plugin in plugins]
        plugin_versions = self._list_plugin_versions(plugin_ids)

        new_plugins = []
        for plugin in plugins:
            plugin_version = plugin_versions.get(plugin.plugin_id)
            new_plugins.append(Plugin(plugin, plugin_version))
        return new_plugins

    @staticmethod
    def _list_plugin_versions(plugin_ids):
        plugin_versions = plugin_version_repo.list_by_plugin_ids(plugin_ids)
        return {plugin_version.plugin_id: plugin_version for plugin_version in plugin_versions}

    @staticmethod
    def delete_original_plugins(plugin_ids):
        plugin_repo.delete_by_plugin_ids(plugin_ids)
        build_version_repo.delete_build_version_by_plugin_ids(plugin_ids)
        config_group_repo.delete_config_group_by_plugin_ids(plugin_ids)
        config_item_repo.delete_config_items_by_plugin_ids(plugin_ids)

    def save_new_plugins(self):
        plugins = []
        build_versions = []
        config_groups = []
        config_items = []
        for plugin in self.new_app.new_plugins:
            plugins.append(plugin.plugin)
            build_versions.append(plugin.build_version)
            config_groups.extend(plugin.config_groups)
            config_items.extend(plugin.config_items)

        plugin_repo.bulk_create(plugins)
        build_version_repo.bulk_create(build_versions)
        config_group_repo.bulk_create_plugin_config_group(config_groups)
        config_item_repo.bulk_create_items(config_items)

    def _generate_builds(self):
        builds = []
        for cpt in self.new_app.components():
            if cpt.action_type != ActionType.BUILD.value:
                continue
            build = dict()
            build["service_id"] = cpt.component.component_id
            build["action"] = 'deploy'
            if cpt.component.build_upgrade:
                build["action"] = 'upgrade'
            build["kind"] = "build_from_market_image"
            extend_info = json.loads(cpt.component_source.extend_info)
            build["image_info"] = {
                "image_url": cpt.component.image,
                "user": extend_info.get("hub_user"),
                "password": extend_info.get("hub_password"),
                "cmd": cpt.component.cmd,
            }
            builds.append(build)
        return builds

    def _generate_upgrades(self):
        upgrades = []
        for cpt in self.new_app.components():
            if cpt.action_type != ActionType.UPDATE.value:
                continue
            upgrade = dict()
            upgrade["service_id"] = cpt.component.component_id
            upgrades.append(upgrade)
        return upgrades

    def _dedup_deps(self, deps):
        result = []
        if not deps:
            return []

        exists = []
        for dep in deps:
            if dep.service_id + dep.dep_service_id in exists:
                continue
            result.append(dep)
            exists.append(dep.service_id + dep.dep_service_id)
        return result
