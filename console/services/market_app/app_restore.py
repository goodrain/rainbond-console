# -*- coding: utf8 -*-
import json
import logging
import copy
from datetime import datetime

from .app import MarketApp
from .original_app import OriginalApp
from .new_app import NewApp
from .component import Component
# service
from console.services.app_actions import app_manage_service
# repository
from console.repositories.app_snapshot import app_snapshot_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.repositories.upgrade_repo import component_upgrade_record_repo
# model
from www.models.main import ServiceGroup
from www.models.main import TenantServiceGroup
from www.models.main import TenantServiceInfo
from www.models.main import TenantServiceEnvVar
from www.models.main import TenantServicesPort
from www.models.main import TenantServiceVolume
from www.models.main import TenantServiceConfigurationFile
from www.models.main import TenantServiceRelation
from www.models.main import TenantServiceMountRelation
from www.models.main import ServiceProbe
from www.models.service_publish import ServiceExtendMethod
from console.models.main import UpgradeStatus
from console.models.main import AppUpgradeRecordType
from console.models.main import AppUpgradeRecord
from console.models.main import ServiceUpgradeRecord
from console.models.main import ServiceSourceInfo
from console.models.main import ServiceMonitor
from console.models.main import ComponentGraph
# exception
from console.exception.main import ServiceHandleException
from console.exception.bcode import ErrAppUpgradeDeployFailed

logger = logging.getLogger('django.contrib.gis')


class AppRestore(MarketApp):
    """
    AppRestore is responsible for restore an upgrade.
    1. AppRestore will use the snapshot to overwrite the components.
    2. AppRestore will not delete new components in the upgrade.
    3. AppRestore will not restore components that were deleted after the upgrade.
    """

    def __init__(self, tenant, region_name, user, app: ServiceGroup, component_group: TenantServiceGroup,
                 app_upgrade_record: AppUpgradeRecord):
        self.tenant = tenant
        self.region_name = region_name
        self.user = user
        self.app = app
        self.upgrade_group_id = component_group.ID
        self.upgrade_record = app_upgrade_record
        self.rollback_record = None
        self.component_group = component_group

        self.original_app = OriginalApp(tenant.tenant_id, region_name, app, component_group.ID)
        self.snapshot = self._get_snapshot()
        self.new_app = self._create_new_app()
        super(AppRestore, self).__init__(self.original_app, self.new_app)

    def restore(self):
        # Sync the new application to the data center first
        # TODO(huangrh): rollback on api timeout
        self.sync_new_app()
        try:
            # Save the application to the console
            self._save_new_app()
        except Exception as e:
            logger.exception(e)
            self._update_rollback_record(UpgradeStatus.ROLLBACK_FAILED.value)
            self.rollback()
            raise ServiceHandleException("unexpected error", "升级遇到了故障, 暂无法执行, 请稍后重试")

        self._deploy()

        return self.rollback_record

    def _save_new_app(self):
        # save new app
        self.save_new_app()
        # update record
        self.create_rollback_record()

    def create_rollback_record(self):
        rollback_record = self.upgrade_record.to_dict()
        rollback_record.pop("ID")
        rollback_record.pop("can_rollback")
        rollback_record.pop("is_finished")
        rollback_record["status"] = UpgradeStatus.ROLLING.value
        rollback_record["record_type"] = AppUpgradeRecordType.ROLLBACK.value
        rollback_record["parent_id"] = self.upgrade_record.ID
        self.rollback_record = upgrade_repo.create_app_upgrade_record(**rollback_record)

    def _update_upgrade_record(self, status):
        self.upgrade_record.status = status
        self.upgrade_record.save()

    def _update_rollback_record(self, status):
        self.rollback_record.status = status
        self.rollback_record.save()

    def _deploy(self):
        # Optimization: not all components need deploy
        component_ids = [cpt.component.component_id for cpt in self.new_app.components()]

        try:
            events = app_manage_service.batch_operations(self.tenant, self.region_name, self.user, "deploy", component_ids)
        except ServiceHandleException as e:
            self._update_rollback_record(UpgradeStatus.DEPLOY_FAILED.value)
            raise ErrAppUpgradeDeployFailed(e.msg)
        except Exception as e:
            self._update_rollback_record(UpgradeStatus.DEPLOY_FAILED.value)
            raise e
        self._create_component_record(events)

    def _create_component_record(self, events=list):
        event_ids = {event["service_id"]: event["event_id"] for event in events}
        records = []
        for cpt in self.new_app.components():
            event_id = event_ids.get(cpt.component.component_id)
            if not event_id:
                continue
            record = ServiceUpgradeRecord(
                create_time=datetime.now(),
                app_upgrade_record=self.rollback_record,
                service_id=cpt.component.component_id,
                service_cname=cpt.component.service_cname,
                upgrade_type=ServiceUpgradeRecord.UpgradeType.UPGRADE.value,
                event_id=event_id,
                status=UpgradeStatus.ROLLING.value,
            )
            records.append(record)
        component_upgrade_record_repo.bulk_create(records)

    def _get_snapshot(self):
        snap = app_snapshot_repo.get_by_snapshot_id(self.upgrade_record.snapshot_id)
        snap = json.loads(snap.snapshot)
        # filter out components that are in the snapshot but not in the application
        component_ids = [cpt.component.component_id for cpt in self.original_app.components()]
        snap["components"] = [snap for snap in snap["components"] if snap["component_id"] in component_ids]
        return snap

    def _create_new_app(self):
        """
        create new app from the snapshot
        """
        components = []
        for snap in self.snapshot["components"]:
            components.append(self._create_component(snap))
        component_ids = [cpt.component.component_id for cpt in components]

        # component dependencies
        new_deps = self._create_component_deps(component_ids)
        component_deps = self.ensure_component_deps(self.original_app, new_deps)

        # volume dependencies
        new_volume_deps = self._create_volume_deps(component_ids)
        volume_deps = self.ensure_component_deps(self.original_app, new_volume_deps)

        return NewApp(
            tenant=self.tenant,
            region_name=self.region_name,
            app=self.app,
            component_group=self._create_component_group(),
            new_components=[],
            update_components=components,
            component_deps=component_deps,
            volume_deps=volume_deps,
        )

    @staticmethod
    def _create_component(snap):
        # component
        component = TenantServiceInfo(**snap["service_base"])
        # component source
        component_source = ServiceSourceInfo(**snap["service_source"])
        # environment
        envs = [TenantServiceEnvVar(**env) for env in snap["service_env_vars"]]
        # ports
        ports = [TenantServicesPort(**port) for port in snap["service_ports"]]
        # service_extend_method
        extend_info = ServiceExtendMethod(**snap["service_extend_method"])
        # volumes
        volumes = [TenantServiceVolume(**volume) for volume in snap["service_volumes"]]
        # configuration files
        config_files = [TenantServiceConfigurationFile(**config_file) for config_file in snap["service_config_file"]]
        # probe
        probes = [ServiceProbe(**probe) for probe in snap["service_probes"]]
        # monitors
        monitors = [ServiceMonitor(**monitor) for monitor in snap["service_monitors"]]
        # graphs
        graphs = [ComponentGraph(**graph) for graph in snap["component_graphs"]]
        return Component(
            component=component,
            component_source=component_source,
            envs=envs,
            ports=ports,
            volumes=volumes,
            config_files=config_files,
            probe=probes[0] if probes else None,
            extend_info=extend_info,
            monitors=monitors,
            graphs=graphs,
        )

    def _create_component_deps(self, component_ids):
        component_deps = []
        for snap in self.snapshot["components"]:
            component_deps.extend([TenantServiceRelation(**dep) for dep in snap["service_relation"]])
        # filter out the component dependencies which dep_service_id does not belong to the components
        return [dep for dep in component_deps if dep.dep_service_id in component_ids]

    def _create_volume_deps(self, component_ids):
        volume_deps = []
        for snap in self.snapshot["components"]:
            volume_deps.extend([TenantServiceMountRelation(**dep) for dep in snap["service_mnts"]])
        # filter out the component dependencies which dep_service_id does not belong to the components
        return [dep for dep in volume_deps if dep.dep_service_id in component_ids]

    def _create_component_group(self):
        component_group = self.snapshot["component_group"]
        version = component_group["group_version"]
        component_group = copy.deepcopy(self.component_group)
        component_group.group_version = version
        return component_group
