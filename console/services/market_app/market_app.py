# -*- coding: utf8 -*-
import json
import logging
from datetime import datetime
from json.decoder import JSONDecodeError

from django.db import transaction

from console.services.market_app.new_app import NewApp
from console.services.market_app.original_app import OriginalApp
from console.services.market_app.new_components import NewComponents
from console.services.market_app.update_components import UpdateComponents
# service
from console.services.group_service import group_service
from console.services.app import app_market_service
from console.services.app_actions import app_manage_service
# repo
from console.repositories.app import service_source_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.region_app import region_app_repo
from console.repositories.upgrade_repo import component_upgrade_record_repo
from console.repositories.group import group_repo
# exception
from console.exception.main import AbortRequest, ServiceHandleException
# model
from www.models.main import TenantServiceGroup
from console.models.main import AppUpgradeRecord
from console.models.main import UpgradeStatus
from console.models.main import ServiceUpgradeRecord
# www
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class MarketApp(object):
    def __init__(self, enterprise_id, tenant, region_name, user, version, service_group: TenantServiceGroup, component_keys):
        """
        components_keys: component keys that the user select.
        """
        self.enterprise_id = enterprise_id
        self.tenant = tenant
        self.tenant_id = tenant.tenant_id
        self.region_name = region_name
        self.user = user

        self.service_group = service_group
        self.app_id = service_group.service_group_id
        self.app = group_repo.get_group_by_pk(tenant.tenant_id, region_name, self.app_id)
        self.upgrade_group_id = service_group.ID
        self.app_model_key = service_group.group_key
        self.old_version = service_group.group_version
        self.version = version
        self.component_keys = component_keys

        # app template
        self.app_template_source = self._app_template_source()
        self.app_template = self._app_template()
        # original app
        self.original_app = OriginalApp(self.tenant_id, self.app_id, self.upgrade_group_id, self.app_model_key, self.app.governance_mode)
        self.new_app = self._new_app()

    def upgrade(self):
        try:
            self._upgrade()
            record = self._create_upgrade_record(UpgradeStatus.UPGRADING.value)
        except Exception as e:
            logger.exception(e)
            # rollback on failure
            self._sync_components(self.original_app)
            self._create_upgrade_record(UpgradeStatus.UPGRADE_FAILED.value)
            raise ServiceHandleException("unexpected error", "未知错误, 请联系管理员")
        # TODO(huangrh): show deploy error
        self._deploy(record)

    @transaction.atomic
    def _upgrade(self):
        # TODO(huangrh): install plugins
        self._save()
        self._update_service_group()

    def _deploy(self, record):
        # Optimization: not all components need deploy
        component_ids = [cpt.component.component_id for cpt in self.new_app.components()]
        events = app_manage_service.batch_operations(self.tenant, self.region_name, self.user, "deploy", component_ids)
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

    def _save(self):
        self.new_app.save()
        self._sync_components(self.new_app)
        self._sync_app_config_groups(self.new_app)

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
            # volume dependency
            if cpt.volume_deps:
                component["volume_relations"] = [dep.to_dict() for dep in cpt.volume_deps]
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

    def _update_service_group(self):
        self.service_group.group_version = self.version
        self.service_group.group_key = self.app_model_key
        self.service_group.save()

    def _rollback_original_app(self):
        """
        rollback the original app on failure
        """
        # TODO(huangrh): retry
        self._sync_components(self.original_app)

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

    def _app_template_source(self):
        components = group_service.get_rainbond_services(self.app_id, self.app_model_key, self.upgrade_group_id)
        if not components:
            raise AbortRequest("components not found", "找不到组件", status_code=404, error_code=404)
        component = components[0]
        component_source = service_source_repo.get_service_source(component.tenant_id, component.service_id)
        return component_source

    def _new_app(self):
        # new components
        new_components = NewComponents(self.tenant, self.region_name, self.user, self.original_app,
                                       self.app_model_key, self.app_template, self.version,
                                       self.app_template_source.is_install_from_cloud(), self.component_keys,
                                       self.app_template_source.get_market_name()).components
        # components that need to be updated
        update_components = UpdateComponents(self.original_app, self.app_model_key, self.app_template, self.version,
                                             self.component_keys).components
        return NewApp(self.tenant_id, self.region_name, self.app_id, self.upgrade_group_id, self.app_template, self.app.governance_mode, new_components,
                      update_components)

    def _create_upgrade_record(self, status):
        record = AppUpgradeRecord(
            tenant_id=self.tenant_id,
            group_id=self.app_id,
            group_key=self.app_model_key,
            version=self.version,
            old_version=self.old_version,
            status=status,
        )
        record.save()
        return record
