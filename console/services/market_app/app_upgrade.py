# -*- coding: utf8 -*-
import json
import logging
import copy
from datetime import datetime

from django.db import transaction

from .enum import ActionType
from console.services.market_app.plugin import Plugin
from console.services.market_app.market_app import MarketApp
from console.services.market_app.new_app import NewApp
from console.services.market_app.original_app import OriginalApp
from console.services.market_app.new_components import NewComponents
from console.services.market_app.update_components import UpdateComponents
from console.services.market_app.property_changes import PropertyChanges
from console.services.market_app.component_group import ComponentGroup
from console.services.market_app.component import Component
# service
from console.services.backup_service import groupapp_backup_service
from console.services.app_config import label_service
# repo
from console.repositories.upgrade_repo import component_upgrade_record_repo
from console.repositories.app_snapshot import app_snapshot_repo
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.k8s_resources import k8s_resources_repo
# exception
from console.exception.main import ServiceHandleException, ErrTenantLackOfMemory
from console.exception.bcode import ErrAppUpgradeDeployFailed
# model
from console.models.main import AppUpgradeRecord, K8sResource
from console.models.main import UpgradeStatus
from console.models.main import ServiceUpgradeRecord
from console.models.main import AppUpgradeSnapshot
from console.models.main import ApplicationConfigGroup
from console.models.main import ConfigGroupItem
from console.models.main import ConfigGroupService
from console.models.main import RegionConfig
from www.models.main import TenantServiceRelation
from www.models.main import TenantServiceMountRelation
from www.models.main import ServiceGroup
from www.models.plugin import TenantServicePluginRelation
from www.models.plugin import ServicePluginConfigVar
from www.models.plugin import TenantPlugin
from www.models.plugin import PluginBuildVersion
from www.models.plugin import PluginConfigItems
from www.models.plugin import PluginConfigGroup
# www
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppUpgrade(MarketApp):
    def __init__(self,
                 enterprise_id,
                 tenant,
                 region: RegionConfig,
                 user,
                 app: ServiceGroup,
                 version,
                 component_group,
                 app_template,
                 install_from_cloud,
                 market_name,
                 record: AppUpgradeRecord = None,
                 component_keys=None,
                 is_deploy=False,
                 is_upgrade_one=False):
        """
        components_keys: component keys that the user select.
        """
        self.enterprise_id = enterprise_id
        self.tenant = tenant
        self.tenant_id = tenant.tenant_id
        self.region = region
        self.region_name = region.region_name
        self.user = user

        self.component_group = ComponentGroup(enterprise_id, component_group, version)
        self.record = record
        self.app = app
        self.app_id = app.app_id
        self.upgrade_group_id = self.component_group.upgrade_group_id
        self.app_model_key = self.component_group.app_model_key
        self.old_version = self.component_group.version
        self.version = version
        self.component_keys = component_keys if component_keys else None
        self.is_deploy = is_deploy
        self.is_upgrade_one = is_upgrade_one

        # app template
        self.app_template = app_template
        self.install_from_cloud = install_from_cloud
        self.market_name = market_name

        self.support_labels = label_service.list_available_labels(tenant, region.region_name)

        # original app
        self.original_app = OriginalApp(self.tenant, self.region, self.app, self.upgrade_group_id, self.support_labels)

        # plugins
        self.original_plugins = self.list_original_plugins()
        self.delete_plugin_ids = self.list_delete_plugin_ids()
        self.new_plugins = self._create_new_plugins()
        plugins = [plugin.plugin for plugin in self._plugins()]

        self.property_changes = PropertyChanges(self.original_app.components(), plugins, self.app_template, self.support_labels)

        self.new_app = self._create_new_app()
        self.property_changes.ensure_dep_changes(self.new_app, self.original_app)
        self.app_property_changes = self._get_app_property_changes()

        super(AppUpgrade, self).__init__(self.original_app, self.new_app, self.user)

    def preinstall(self):
        self.pre_install_plugins()
        self.pre_sync_new_app()
        self._install_predeploy()

    def install(self):
        # install plugins
        self.install_plugins()

        # Sync the new application to the data center first
        # TODO(huangrh): rollback on api timeout
        self.sync_new_app()

        try:
            # Save the application to the console
            self.save_new_app()
            self.create_service_tcp_domains(self.region)
        except Exception as e:
            logger.exception(e)
            # rollback on failure
            self.rollback()
            raise ServiceHandleException("unexpected error", "安装遇到了故障, 暂无法执行, 请稍后重试")

        if self.is_deploy:
            self._install_deploy()

    def upgrade(self):
        # install plugins
        try:
            self.install_plugins()
        except Exception as e:
            self._update_upgrade_record(UpgradeStatus.UPGRADE_FAILED.value)
            raise e

        # Sync the new application to the data center first
        try:
            self.sync_new_app()
        except Exception as e:
            # TODO(huangrh): rollback on api timeout
            self._update_upgrade_record(UpgradeStatus.UPGRADE_FAILED.value)
            raise e

        try:
            # Save the application to the console
            self._save_app()
        except Exception as e:
            logger.exception(e)
            self._update_upgrade_record(UpgradeStatus.UPGRADE_FAILED.value)
            # rollback on failure
            self.rollback()
            raise ServiceHandleException("unexpected error", "升级遇到了故障, 暂无法执行, 请稍后重试")

        self._deploy(self.record)

        return self.record

    def changes(self):
        templates = list()
        if self.app_template.get("apps"):
            templates = self.app_template.get("apps")
        templates = {tmpl["service_key"]: tmpl for tmpl in templates}

        result = []
        original_components = {cpt.component.component_id: cpt for cpt in self.original_app.components()}
        cpt_changes = {change["component_id"]: change for change in self.property_changes.changes}
        # upgrade components
        for cpt in self.new_app.update_components:
            component_id = cpt.component.component_id
            change = cpt_changes.get(component_id, {})
            if "component_id" in change.keys():
                change.pop("component_id")

            original_cpt = original_components.get(component_id)

            upgrade_info = cpt_changes.get(component_id, None)
            current_version = original_cpt.component_source.version
            result.append({
                "service": {
                    "service_id": cpt.component.component_id,
                    "service_cname": cpt.component.service_cname,
                    "service_key": cpt.component.service_key,
                    "type": "upgrade",
                    'current_version': current_version,
                    'can_upgrade': original_cpt is not None,
                    'have_change': True if upgrade_info and current_version != self.version else False
                },
                "upgrade_info": upgrade_info,
            })

        # new components
        for cpt in self.new_app.new_components:
            tmpl = templates.get(cpt.component.service_key)
            if not tmpl:
                continue
            result.append({
                "service": {
                    "service_id": "",
                    "service_cname": cpt.component.service_cname,
                    "service_key": cpt.component.service_key,
                    "type": "add",
                    "can_upgrade": True,
                },
                "upgrade_info": tmpl,
            })

        return result

    @transaction.atomic
    def pre_install_plugins(self):
        # sync plugins
        self._sync_plugins(self.new_app.new_plugins)
        # deploy plugins
        self._deploy_plugins(self.new_app.new_plugins)

    @transaction.atomic
    def install_plugins(self):
        # delete old plugins
        self.delete_original_plugins(self.list_delete_plugin_ids())
        # save plugins
        self.save_new_plugins()
        # sync plugins
        self._sync_plugins(self.new_app.new_plugins)
        # deploy plugins
        self._deploy_plugins(self.new_app.new_plugins)

    @transaction.atomic
    def _save_new_app(self):
        self.save_new_app()

    def _sync_plugins(self, plugins: [Plugin]):
        new_plugins = []
        for plugin in plugins:
            new_plugins.append({
                "build_model": plugin.plugin.build_source,
                "git_url": plugin.plugin.code_repo,
                "image_url": "{0}:{1}".format(plugin.plugin.image, plugin.build_version.image_tag),
                "plugin_id": plugin.plugin.plugin_id,
                "plugin_info": plugin.plugin.desc,
                "plugin_model": plugin.plugin.category,
                "plugin_name": plugin.plugin.plugin_name
            })
        body = {
            "plugins": new_plugins,
        }
        region_api.sync_plugins(self.tenant_name, self.region_name, body)

    def _install_predeploy(self):

        try:
            helm_chart_parameter = dict()
            helm_chart_parameter["app_name"] = self.app_template["group_name"]
            helm_chart_parameter["app_version"] = self.app_template["group_version"]
            _ = self.predeploy(helm_chart_parameter)
        except ErrTenantLackOfMemory as e:
            logger.exception(e)
            raise ErrTenantLackOfMemory()
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(msg="install app failure", msg_show="安装应用发生异常{}".format(e))

    def _install_deploy(self):
        try:
            _ = self.deploy()
        except ErrTenantLackOfMemory as e:
            logger.exception(e)
            raise ErrTenantLackOfMemory()
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(msg="install app failure", msg_show="安装应用发生异常{}".format(e))

    def _deploy_plugins(self, plugins: [Plugin]):
        new_plugins = []
        for plugin in plugins:
            origin = plugin.plugin.origin
            if origin == "local_market":
                plugin_from = "yb"
            elif origin == "market":
                plugin_from = "ys"
            else:
                plugin_from = None

            new_plugins.append({
                "plugin_id": plugin.plugin.plugin_id,
                "build_version": plugin.build_version.build_version,
                "event_id": plugin.build_version.event_id,
                "info": plugin.build_version.update_info,
                "operator": self.user.nick_name,
                "plugin_cmd": plugin.build_version.build_cmd,
                "plugin_memory": int(plugin.build_version.min_memory),
                "plugin_cpu": int(plugin.build_version.min_cpu),
                "repo_url": plugin.build_version.code_version,
                "username": plugin.plugin.username,  # git username
                "password": plugin.plugin.password,  # git password
                "tenant_id": self.tenant_id,
                "ImageInfo": plugin.plugin_image,
                "build_image": "{0}:{1}".format(plugin.plugin.image, plugin.build_version.image_tag),
                "plugin_from": plugin_from,
            })
        body = {
            "plugins": new_plugins,
        }
        region_api.build_plugins(self.tenant_name, self.region_name, body)

    def _deploy(self, record):
        # Optimization: not all components need deploy
        try:
            events = self.deploy()
        except ServiceHandleException as e:
            self._update_upgrade_record(UpgradeStatus.DEPLOY_FAILED.value)
            raise ErrAppUpgradeDeployFailed(e.msg)
        except Exception as e:
            self._update_upgrade_record(UpgradeStatus.DEPLOY_FAILED.value)
            raise e
        self._create_component_record(record, events)

    def _create_component_record(self, app_record: AppUpgradeRecord, events):
        if self.is_upgrade_one:
            return
        event_ids = {event["service_id"]: event["event_id"] for event in events}
        records = []
        for cpt in self.new_app.components():
            event_id = event_ids.get(cpt.component.component_id)
            record = ServiceUpgradeRecord(
                create_time=datetime.now(),
                app_upgrade_record=app_record,
                service_id=cpt.component.component_id,
                service_cname=cpt.component.service_cname,
                upgrade_type=ServiceUpgradeRecord.UpgradeType.UPGRADE.value,
                event_id=event_id,
                status=UpgradeStatus.UPGRADING.value,
            )
            if cpt.action_type == ActionType.NOTHING.value:
                record.status = UpgradeStatus.UPGRADED.value
                records.append(record)
                continue
            if not event_id:
                continue
            records.append(record)
        component_upgrade_record_repo.bulk_create(records)

    @transaction.atomic
    def _save_app(self):
        snapshot = self._take_snapshot()
        self.save_new_app()
        self._update_upgrade_record(UpgradeStatus.UPGRADING.value, snapshot)

    def _create_new_app(self):
        # new components
        new_components = NewComponents(
            self.tenant,
            self.region,
            self.user,
            self.original_app,
            self.app_model_key,
            self.app_template,
            self.version,
            self.install_from_cloud,
            self.component_keys,
            self.market_name,
            self.is_deploy,
            support_labels=self.support_labels).components
        # components that need to be updated
        update_components = UpdateComponents(self.original_app, self.app_model_key, self.app_template, self.version,
                                             self.component_keys, self.property_changes).components

        components = new_components + update_components

        # component existing in the template.
        tmpl_components = self._tmpl_components(components)
        tmpl_component_ids = [cpt.component.component_id for cpt in tmpl_components]

        # create new component dependency from app_template
        new_component_deps = self._create_component_deps(components)
        component_deps = self.ensure_component_deps(new_component_deps, tmpl_component_ids, self.is_upgrade_one)

        # volume dependencies
        new_volume_deps = self._create_volume_deps(components)
        volume_deps = self.ensure_volume_deps(new_volume_deps, tmpl_component_ids, self.is_upgrade_one)

        # config groups
        config_groups = self._config_groups()
        config_group_items = self._config_group_items(config_groups)
        config_group_components = self._config_group_components(components, config_groups)

        # k8s resources
        k8s_resources = list(self._k8s_resources())

        # plugins
        new_plugin_deps, new_plugin_configs = self._new_component_plugins(components)
        plugin_deps = self.original_app.plugin_deps + new_plugin_deps
        plugin_configs = self.original_app.plugin_configs + new_plugin_configs

        new_component_group = copy.deepcopy(self.component_group.component_group)
        new_component_group.group_version = self.version

        return NewApp(
            self.tenant,
            self.region_name,
            self.app,
            ComponentGroup(self.enterprise_id, new_component_group, need_save=not self.is_upgrade_one),
            new_components,
            update_components,
            component_deps,
            volume_deps,
            plugins=self._plugins(),
            plugin_deps=plugin_deps,
            plugin_configs=plugin_configs,
            new_plugins=self.new_plugins,
            config_groups=config_groups,
            config_group_items=config_group_items,
            config_group_components=config_group_components,
            k8s_resources=k8s_resources)

    def _create_original_plugins(self):
        return self.list_original_plugins()

    def _plugins(self):
        return self.original_plugins + self.new_plugins

    def _create_component_deps(self, components):
        """
        组件唯一标识: cpt.component_source.service_share_uuid
        组件模板唯一标识: tmpl.get("service_share_uuid")
        被依赖组件唯一标识: dep["dep_service_key"]
        """
        components = {cpt.component_source.service_share_uuid: cpt.component for cpt in components}
        original_components = {cpt.component_source.service_share_uuid: cpt.component for cpt in self.original_app.components()}

        deps = []
        apps = list()
        if self.app_template.get("apps", []):
            apps = self.app_template.get("apps", [])
        for tmpl in apps:
            for dep in tmpl.get("dep_service_map_list", []):
                component_key = tmpl.get("service_share_uuid")
                component = components.get(component_key)
                if not component:
                    continue

                dep_component_key = dep["dep_service_key"]
                dep_component = components.get(dep_component_key) if components.get(
                    dep_component_key) else original_components.get(dep_component_key)
                if not dep_component:
                    logger.info("The component({}) cannot find the dependent component({})".format(
                        component_key, dep_component_key))
                    continue

                dep = TenantServiceRelation(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    dep_service_id=dep_component.service_id,
                    dep_service_type="application",
                    dep_order=0,
                )
                deps.append(dep)
        return deps

    def _create_volume_deps(self, raw_components):
        """
        Create new volume dependencies with application template
        """
        volumes = []
        for cpt in raw_components:
            volumes.extend(cpt.volumes)
        components = {cpt.component_source.service_share_uuid: cpt.component for cpt in raw_components}
        original_components = {cpt.component_source.service_share_uuid: cpt.component for cpt in self.original_app.components()}

        deps = []
        apps = list()
        if self.app_template.get("apps", []):
            apps = self.app_template.get("apps", [])
        for tmpl in apps:
            component_key = tmpl.get("service_share_uuid")
            component = components.get(component_key)
            if not component:
                continue

            volume_deps = tmpl.get("mnt_relation_list")
            if not volume_deps:
                continue
            for dep in volume_deps:
                # check if the dependent component exists
                dep_component_key = dep["service_share_uuid"]
                dep_component = components.get(dep_component_key) if components.get(
                    dep_component_key) else original_components.get(dep_component_key)
                if not dep_component:
                    logger.info("dependent component({}) not found".format(dep_component_key))
                    continue

                # check if the dependent volume exists
                if not self._volume_exists(volumes, dep_component.service_id, dep["mnt_name"]):
                    logger.info("dependent volume({}/{}) not found".format(dep_component.service_id, dep["mnt_name"]))
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

    @staticmethod
    def _volume_exists(volumes, component_id, volume_name):
        volumes = {vol.service_id + vol.volume_name: vol for vol in volumes}
        return True if volumes.get(component_id + volume_name) else False

    def _config_groups(self):
        """
        only add
        """
        config_groups = list(app_config_group_repo.list(self.region_name, self.app_id))
        config_group_names = [cg.config_group_name for cg in config_groups]
        tmpl = self.app_template.get("app_config_groups") if self.app_template.get("app_config_groups") else []
        for cg in tmpl:
            if cg["name"] in config_group_names:
                continue
            config_group = ApplicationConfigGroup(
                app_id=self.app_id,
                config_group_name=cg["name"],
                deploy_type=cg["injection_type"],
                enable=True,  # always true
                region_name=self.region_name,
                config_group_id=make_uuid(),
            )
            config_groups.append(config_group)
        return config_groups

    def _update_upgrade_record(self, status, snapshot=None):
        if self.is_upgrade_one:
            return
        self.record.status = status
        self.record.snapshot_id = snapshot.snapshot_id if snapshot else None
        self.record.version = self.version
        self.record.save()

    def _take_snapshot(self):
        if self.is_upgrade_one:
            return

        new_components = {cpt.component.component_id: cpt for cpt in self.new_app.components()}

        components = []
        for cpt in self.original_app.components():
            # component snapshot
            csnap, _ = groupapp_backup_service.get_service_details(self.tenant, cpt.component)
            new_component = new_components.get(cpt.component.component_id)
            if new_component:
                csnap["action_type"] = new_component.action_type
            else:
                # no action for original component without changes
                csnap["action_type"] = ActionType.NOTHING.value
            components.append(csnap)
        if not components:
            return None
        snapshot = app_snapshot_repo.create(
            AppUpgradeSnapshot(
                tenant_id=self.tenant_id,
                upgrade_group_id=self.upgrade_group_id,
                snapshot_id=make_uuid(),
                snapshot=json.dumps({
                    "components": components,
                    "component_group": self.component_group.component_group.to_dict(),
                }),
            ))
        return snapshot

    def _config_group_items(self, config_groups):
        """
        only add
        """
        config_groups = {cg.config_group_name: cg for cg in config_groups}
        config_group_items = list(app_config_group_item_repo.list_by_app_id(self.app_id))

        item_keys = [item.config_group_name + item.item_key for item in config_group_items]
        tmpl = self.app_template.get("app_config_groups") if self.app_template.get("app_config_groups") else []
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

    def _config_group_components(self, components, config_groups):
        """
        only add
        """
        components = {cpt.component.service_key: cpt for cpt in components}

        config_groups = {cg.config_group_name: cg for cg in config_groups}

        config_group_components = list(app_config_group_service_repo.list_by_app_id(self.app_id))
        config_group_component_keys = [cgc.config_group_name + cgc.service_id for cgc in config_group_components]

        tmpl = self.app_template.get("app_config_groups") if self.app_template.get("app_config_groups") else []
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

    def _new_component_plugins(self, components: [Component]):
        plugins = {plugin.plugin.origin_share_id: plugin for plugin in self._plugins()}
        old_plugin_deps = [dep.service_id + dep.plugin_id for dep in self.original_app.plugin_deps]

        components = {cpt.component.service_key: cpt for cpt in components}
        apps = list()
        if self.app_template.get("apps", []):
            apps = self.app_template.get("apps", [])
        component_keys = {tmpl["service_id"]: tmpl["service_key"] for tmpl in apps}

        plugin_deps = []
        for component in apps:
            plugin_deps.extend(component.get("service_related_plugin_config", []))

        new_plugin_deps = []
        new_plugin_configs = []
        for plugin_dep in plugin_deps:
            # get component
            component_key = component_keys.get(plugin_dep["service_id"])
            if not component_key:
                logger.warning("component key {} not found".format(plugin_dep["service_id"]))
                continue
            component = components.get(component_key)
            if not component:
                logger.info("component {} not found".format(component_key))
                continue

            # get plugin
            plugin = plugins.get(plugin_dep["plugin_key"])
            if not plugin:
                logger.info("plugin {} not found".format(plugin_dep["plugin_key"]))
                continue

            if component.component.component_id + plugin.plugin.plugin_id in old_plugin_deps:
                continue

            # plugin configs
            plugin_configs, ignore_plugin = self._create_plugin_configs(component, plugin, plugin_dep["attr"], component_keys,
                                                                        components)
            if ignore_plugin:
                continue
            new_plugin_configs.extend(plugin_configs)

            new_plugin_deps.append(
                TenantServicePluginRelation(
                    service_id=component.component.component_id,
                    plugin_id=plugin.plugin.plugin_id,
                    build_version=plugin.build_version.build_version,
                    service_meta_type=plugin_dep.get("service_meta_type"),
                    plugin_status=plugin_dep.get("plugin_status"),
                    min_memory=max(plugin_dep.get("min_memory", 0) or 512, 512),
                    min_cpu=max(plugin_dep.get("min_cpu", 0) or 250, 250),
                ))
        return new_plugin_deps, new_plugin_configs

    @staticmethod
    def _create_plugin_configs(component: Component, plugin: Plugin, plugin_configs, component_keys: [str], components):
        """
        return new_plugin_configs, ignore_plugin
        new_plugin_configs: new plugin configs created from app template
        ignore_plugin: ignore the plugin if the dependent component not found
        """
        new_plugin_configs = []
        for plugin_config in plugin_configs:
            new_plugin_config = ServicePluginConfigVar(
                service_id=component.component.component_id,
                plugin_id=plugin.plugin.plugin_id,
                build_version=plugin.build_version.build_version,
                service_meta_type=plugin_config["service_meta_type"],
                injection=plugin_config["injection"],
                container_port=plugin_config["container_port"],
                attrs=plugin_config["attrs"],
                protocol=plugin_config["protocol"],
            )

            # dest_service_id, dest_service_alias
            dest_service_id = plugin_config.get("dest_service_id")
            if dest_service_id:
                dep_component_key = component_keys.get(dest_service_id)
                if not dep_component_key:
                    logger.info("dependent component key {} not found".format(dest_service_id))
                    return [], True
                dep_component = components.get(dep_component_key)
                if not dep_component:
                    logger.info("dependent component {} not found".format(dep_component_key))
                    return [], True
                new_plugin_config.dest_service_id = dep_component.component.component_id
                new_plugin_config.dest_service_alias = dep_component.component.service_alias
            new_plugin_configs.append(new_plugin_config)

        return new_plugin_configs, False

    def list_delete_plugin_ids(self):
        plugin_templates = self.app_template.get("plugins")
        if not plugin_templates:
            return []

        original_plugins = {plugin.plugin.origin_share_id: plugin.plugin for plugin in self.original_plugins}
        original_plugins_version = {plugin.plugin.origin_share_id: plugin.build_version for plugin in self.original_plugins}
        plugin_ids = []
        for plugin_tmpl in plugin_templates:
            original_plugin = original_plugins.get(plugin_tmpl.get("plugin_key"))
            original_plugin_version = original_plugins_version.get(plugin_tmpl.get("plugin_key"))

            if plugin_tmpl["share_image"]:
                image_and_tag = plugin_tmpl["share_image"].rsplit(":", 1)
                if len(image_and_tag) > 1:
                    tags = image_and_tag[1].rsplit("_")
                    new_version = tags[len(tags) - 2] if len(tags) > 2 else ""
            if original_plugin and new_version > original_plugin_version.build_version:
                plugin_ids.append(original_plugin.plugin_id)
        return plugin_ids

    def _create_new_plugins(self):
        plugin_templates = self.app_template.get("plugins")
        if not plugin_templates:
            return []

        original_plugins = {plugin.plugin.origin_share_id: plugin.plugin for plugin in self.original_plugins}
        original_plugins_version = {plugin.plugin.origin_share_id: plugin.build_version for plugin in self.original_plugins}
        plugins = []
        for plugin_tmpl in plugin_templates:
            original_plugin = original_plugins.get(plugin_tmpl.get("plugin_key"))
            original_plugin_version = original_plugins_version.get(plugin_tmpl.get("plugin_key"))

            image = None
            if plugin_tmpl["share_image"]:
                image_and_tag = plugin_tmpl["share_image"].rsplit(":", 1)
                image = image_and_tag[0]
                if len(image_and_tag) > 1:
                    tags = image_and_tag[1].rsplit("_")
                    new_version = tags[len(tags) - 2] if len(tags) > 2 else ""

            plugin_id = make_uuid()
            if original_plugin:
                if new_version > original_plugin_version.build_version:
                    plugin_id = original_plugin.plugin_id
                else:
                    continue

            plugin = TenantPlugin(
                tenant_id=self.tenant.tenant_id,
                region=self.region_name,
                plugin_id=plugin_id,
                create_user=self.user.user_id,
                desc=plugin_tmpl["desc"],
                plugin_alias=plugin_tmpl["plugin_alias"],
                category=plugin_tmpl["category"],
                build_source="image",
                image=image,
                code_repo=plugin_tmpl["code_repo"],
                username=plugin_tmpl["plugin_image"]["hub_user"],
                password=plugin_tmpl["plugin_image"]["hub_password"],
                origin="local_market",
                origin_share_id=plugin_tmpl["plugin_key"])

            build_version = self._create_build_version(plugin.plugin_id, plugin_tmpl)
            config_groups, config_items = self._create_config_groups(plugin.plugin_id, build_version,
                                                                     plugin_tmpl.get("config_groups", []))
            plugins.append(Plugin(plugin, build_version, config_groups, config_items, plugin_tmpl["plugin_image"]))

        return plugins

    def _create_build_version(self, plugin_id, plugin_tmpl):
        image_tag = None
        if plugin_tmpl["share_image"]:
            image_and_tag = plugin_tmpl["share_image"].rsplit(":", 1)
            if len(image_and_tag) > 1:
                image_tag = image_and_tag[1]
            else:
                image_tag = "latest"
        min_memory = max(plugin_tmpl.get('min_memory', 0) or 512, 512)
        min_cpu = max(int(min_memory) / 128 * 20, 250)

        return PluginBuildVersion(
            plugin_id=plugin_id,
            tenant_id=self.tenant.tenant_id,
            region=self.region_name,
            user_id=self.user.user_id,
            event_id=make_uuid(),
            build_version=plugin_tmpl.get('build_version'),
            build_status="building",
            min_memory=min_memory,
            min_cpu=min_cpu,
            image_tag=image_tag,
            plugin_version_status="fixed",
        )

    @staticmethod
    def _create_config_groups(plugin_id, build_version, config_groups_tmpl):
        config_groups = []
        config_items = []
        for config in config_groups_tmpl:
            options = config["options"]
            plugin_config_meta = PluginConfigGroup(
                plugin_id=plugin_id,
                build_version=build_version.build_version,
                config_name=config["config_name"],
                service_meta_type=config["service_meta_type"],
                injection=config["injection"])
            config_groups.append(plugin_config_meta)

            for option in options:
                config_item = PluginConfigItems(
                    plugin_id=plugin_id,
                    build_version=build_version.build_version,
                    service_meta_type=config["service_meta_type"],
                    attr_name=option.get("attr_name", ""),
                    attr_alt_value=option.get("attr_alt_value", ""),
                    attr_type=option.get("attr_type", "string"),
                    attr_default_value=option.get("attr_default_value", None),
                    is_change=option.get("is_change", False),
                    attr_info=option.get("attr_info", ""),
                    protocol=option.get("protocol", ""))
                config_items.append(config_item)
        return config_groups, config_items

    def _tmpl_components(self, components: [Component]):
        apps = list()
        if self.app_template.get("apps", []):
            apps = self.app_template.get("apps", [])
        component_keys = [tmpl.get("service_key") for tmpl in apps]
        return [cpt for cpt in components if cpt.component.service_key in component_keys]

    def _k8s_resources(self):
        # only add
        k8s_resources = list(k8s_resources_repo.list_by_app_id(self.app_id))
        k8s_resource_names = [r.name + r.kind for r in k8s_resources]
        finall_k8s_resources = list()
        tmpl = self.app_template.get("k8s_resources") if self.app_template.get("k8s_resources") else []
        for rs in tmpl:
            if rs["name"] + rs["kind"] in k8s_resource_names:
                continue
            resource = K8sResource(
                app_id=self.app_id,
                name=rs["name"],
                kind=rs["kind"],
                content=rs["content"],
                state=1  # 添加默认状态值
            )
            finall_k8s_resources.append(resource)
        return finall_k8s_resources

    def _get_app_property_changes(self):
        changes = {"upgrade_info": dict()}
        k8s_resources = self._k8s_resource_changes()
        if k8s_resources:
            changes["upgrade_info"]["k8s_resources"] = k8s_resources
        return changes

    def _k8s_resource_changes(self):
        if not self.new_app.k8s_resources:
            return None
        add = []
        old_k8s_resources = {rs.name + rs.kind: rs for rs in self.original_app.k8s_resources}
        for new_k8s_resource in self.new_app.k8s_resources:
            new_resource_key = new_k8s_resource.name + new_k8s_resource.kind
            if not old_k8s_resources.get(new_resource_key):
                add.append(new_k8s_resource.to_dict())
        result = {}
        if add:
            result["add"] = add
        return result
