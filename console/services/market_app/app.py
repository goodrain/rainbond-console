# -*- coding: utf8 -*-
import json

from .new_app import NewApp
from .original_app import OriginalApp
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

    def install_plugins(self):
        pass

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
        new_components = []
        for cpt in app.components():
            component_base = cpt.component.to_dict()
            component_base["component_id"] = component_base["service_id"]
            component_base["component_name"] = component_base["service_name"]
            component_base["component_alias"] = component_base["service_alias"]
            component = {
                "component_base": component_base,
                "envs": [env.to_dict() for env in cpt.envs],
                "ports": [port.to_dict() for port in cpt.ports],
                "config_files": [cf.to_dict() for cf in cpt.config_files],
                "probe": cpt.probe,
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
            new_components.append(component)

        body = {
            "components": new_components,
        }
        print(json.dumps(body))
        region_api.sync_components(self.tenant_name, self.region_name, self.new_app.region_app_id, body)

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
        print(json.dumps(body))
        region_api.sync_config_groups(self.tenant_name, self.region_name, self.new_app.region_app_id, body)
