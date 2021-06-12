# -*- coding: utf8 -*-
import json
import logging
import copy
from datetime import datetime
from json.decoder import JSONDecodeError

from django.db import transaction

from console.services.market_app.app import MarketApp
from console.services.market_app.new_app import NewApp
from console.services.market_app.original_app import OriginalApp
from console.services.market_app.new_components import NewComponents
from console.services.market_app.update_components import UpdateComponents
from console.services.market_app.property_changes import PropertyChanges
from console.services.market_app.component_group import ComponentGroup
# service
from console.services.group_service import group_service
from console.services.app import app_market_service
from console.services.app_actions import app_manage_service
from console.services.backup_service import groupapp_backup_service
# repo
from console.repositories.app import service_source_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.region_app import region_app_repo
from console.repositories.upgrade_repo import component_upgrade_record_repo
from console.repositories.group import group_repo
from console.repositories.app_snapshot import app_snapshot_repo
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app_config_group import app_config_group_service_repo
# exception
from console.exception.main import AbortRequest, ServiceHandleException
from console.exception.bcode import ErrAppUpgradeDeploy
# model
from www.models.main import TenantServiceRelation
from www.models.main import TenantServiceMountRelation
from console.models.main import AppUpgradeRecord
from console.models.main import UpgradeStatus
from console.models.main import ServiceUpgradeRecord
from console.models.main import AppSnapshot
from console.models.main import ApplicationConfigGroup
from console.models.main import ConfigGroupItem
from console.models.main import ConfigGroupService
# www
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppUpgrade(MarketApp):
    def __init__(self,
                 enterprise_id,
                 tenant,
                 region_name,
                 user,
                 version,
                 component_group,
                 record: AppUpgradeRecord = None,
                 component_keys=None):
        """
        components_keys: component keys that the user select.
        """
        self.enterprise_id = enterprise_id
        self.tenant = tenant
        self.tenant_id = tenant.tenant_id
        self.region_name = region_name
        self.user = user

        self.component_group = ComponentGroup(enterprise_id, component_group, version)
        self.record = record
        self.app_id = component_group.app_id
        self.app = group_repo.get_group_by_pk(tenant.tenant_id, region_name, self.app_id)
        self.upgrade_group_id = component_group.upgrade_group_id
        self.app_model_key = component_group.app_model_key
        self.old_version = component_group.version
        self.version = version
        self.component_keys = component_keys if component_keys else None

        # app template
        self.app_template_source = self.app_template_source()
        self.app_template = self._app_template()
        # original app
        self.original_app = OriginalApp(self.tenant_id, self.region_name, self.app, self.upgrade_group_id)
        self.property_changes = PropertyChanges(self.original_app.components(), self.app_template)
        self.new_app = self._create_new_app()

        super(AppUpgrade, self).__init__(self.original_app, self.new_app)

    def upgrade(self):
        # TODO(huangrh): install plugins
        # Sync the new application to the data center first
        # TODO(huangrh): rollback on api timeout
        self.sync_new_app()

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

    def changes(self):
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
                },
                "upgrade_info": tmpl,
            })

        return result

    def _deploy(self, record):
        # Optimization: not all components need deploy
        component_ids = [cpt.component.component_id for cpt in self.new_app.components()]
        try:
            events = app_manage_service.batch_operations(self.tenant, self.region_name, self.user, "deploy", component_ids)
        except ServiceHandleException as e:
            raise ErrAppUpgradeDeploy(e.msg)
        self._create_component_record(record, events)

    def _create_component_record(self, app_record: AppUpgradeRecord, events=list):
        event_ids = {event["service_id"]: event["event_id"] for event in events}
        records = []
        for cpt in self.new_app.components():
            event_id = event_ids.get(cpt.component.component_id)
            if not event_id:
                continue
            record = ServiceUpgradeRecord(
                create_time=datetime.now(),
                app_upgrade_record=app_record,
                service_id=cpt.component.component_id,
                service_cname=cpt.component.service_cname,
                upgrade_type=ServiceUpgradeRecord.UpgradeType.UPGRADE.value,
                event_id=event_id,
                status=UpgradeStatus.UPGRADING.value,
            )
            records.append(record)
        component_upgrade_record_repo.bulk_create(records)

    @transaction.atomic
    def _save_app(self):
        snapshot = self._take_snapshot()
        self.save_new_app()
        self._update_upgrade_record(UpgradeStatus.UPGRADING.value, snapshot.snapshot_id)

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
        region_app_id = region_app_repo.get_region_app_id(self.region_name, self.app_id)
        region_api.sync_components(self.tenant.tenant_name, self.region_name, region_app_id, body)

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

        region_app_id = region_app_repo.get_region_app_id(self.region_name, self.app_id)
        region_api.sync_config_groups(self.tenant.tenant_name, self.region_name, region_app_id, body)

    def _app_template(self):
        if not self.app_template_source.is_install_from_cloud():
            _, app_version = rainbond_app_repo.get_rainbond_app_and_version(self.enterprise_id, self.app_model_key,
                                                                            self.version)
        else:
            _, app_version = app_market_service.cloud_app_model_to_db_model(self.app_template_source.get_market_name(),
                                                                            self.app_model_key, self.version)
        try:
            return json.loads(app_version.app_template)
        except JSONDecodeError:
            raise AbortRequest("invalid app template", "该版本应用模板已损坏, 无法升级")

    def _create_new_app(self):
        # new components
        new_components = NewComponents(self.tenant, self.region_name, self.user, self.original_app,
                                       self.app_model_key, self.app_template, self.version,
                                       self.app_template_source.is_install_from_cloud(), self.component_keys,
                                       self.app_template_source.get_market_name()).components
        # components that need to be updated
        update_components = UpdateComponents(self.original_app, self.app_model_key, self.app_template, self.version,
                                             self.component_keys, self.property_changes).components

        components = new_components + update_components

        # create new component dependency from app_template
        new_component_deps = self._create_component_deps(components)
        component_deps = self.ensure_component_deps(self.original_app, new_component_deps)

        # volume dependencies
        new_volume_deps = self._create_volume_deps(components)
        volume_deps = self.ensure_component_deps(self.original_app, new_volume_deps)

        # config groups
        config_groups = self._config_groups()
        config_group_items = self._config_group_items(config_groups)
        config_group_components = self._config_group_components(components, config_groups)

        component_group = copy.deepcopy(self.component_group.component_group)
        component_group.group_version = self.version

        return NewApp(
            self.tenant,
            self.region_name,
            self.app,
            component_group,
            new_components,
            update_components,
            component_deps,
            volume_deps,
            config_groups=config_groups,
            config_group_items=config_group_items,
            config_group_components=config_group_components)

    def _create_component_deps(self, components):
        """
        组件唯一标识: cpt.component_source.service_share_uuid
        组件模板唯一标识: tmpl.get("service_share_uuid")
        被依赖组件唯一标识: dep["dep_service_key"]
        """
        components = {cpt.component_source.service_share_uuid: cpt.component for cpt in components}

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

    def _update_upgrade_record(self, status, snapshot_id=None):
        self.record.status = status
        self.record.snapshot_id = snapshot_id
        self.record.save()

    def _take_snapshot(self):
        components = []
        for cpt in self.original_app.components():
            # component snapshot
            csnap, _ = groupapp_backup_service.get_service_details(self.tenant, cpt.component)
            components.append(csnap)
        if not components:
            return None
        snapshot = app_snapshot_repo.create(
            AppSnapshot(
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

    def _config_group_components(self, components, config_groups):
        """
        only add
        """
        components = {cpt.component.service_key: cpt for cpt in components}

        config_groups = {cg.config_group_name: cg for cg in config_groups}

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
