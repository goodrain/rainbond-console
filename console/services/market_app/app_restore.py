# -*- coding: utf8 -*-
import json
import logging
import copy

from .app import MarketApp
from .original_app import OriginalApp
from .new_app import NewApp
from .component import Component
# service
from console.services.app_actions import app_manage_service
# repository
from console.repositories.app_snapshot import app_snapshot_repo
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
from console.models.main import AppUpgradeRecord
from console.models.main import ServiceSourceInfo
from console.models.main import ServiceMonitor
from console.models.main import ComponentGraph
# exception
from console.exception.main import ServiceHandleException
from console.exception.bcode import ErrAppUpgradeDeploy

logger = logging.getLogger('django.contrib.gis')


class AppRestore(MarketApp):
    """
    AppRestore is responsible for restore an upgrade.
    1. AppRestore will use the snapshot to overwrite the components.
    2. AppRestore will not delete new components in the upgrade.
    3. AppRestore will not restore components that were deleted after the upgrade.
    """

    def __init__(self, tenant, region_name, user, app: ServiceGroup, component_group: TenantServiceGroup,
                 record: AppUpgradeRecord):
        self.tenant = tenant
        self.region_name = region_name
        self.user = user
        self.app = app
        self.upgrade_group_id = component_group.ID
        self.record = record
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
            self.rollback()
            raise ServiceHandleException("unexpected error", "升级遇到了故障, 暂无法执行, 请稍后重试")

        self._deploy()

    def _save_new_app(self):
        # save new app
        self.save_new_app()
        # update record
        self._update_upgrade_record(UpgradeStatus.ROLLING.value)

    def _update_upgrade_record(self, status, snapshot_id=None):
        self.record.status = status
        self.record.snapshot_id = snapshot_id
        self.record.save()

    def _deploy(self):
        # Optimization: not all components need deploy
        component_ids = [cpt.component.component_id for cpt in self.new_app.components()]

        try:
            events = app_manage_service.batch_operations(self.tenant, self.region_name, self.user, "deploy", component_ids)
        except ServiceHandleException as e:
            raise ErrAppUpgradeDeploy(e.msg)
        self._update_component_record(events)

    def _update_component_record(self, events):
        event_ids = {event["service_id"]: event["event_id"] for event in events}
        records = component_upgrade_record_repo.list_by_app_record_id(self.record.ID)
        for record in records:
            event_id = event_ids.get(record.service_id)
            if not event_id:
                continue
            record.status = UpgradeStatus.ROLLING.value
            record.event_id = event_id
        component_upgrade_record_repo.bulk_update(records)

    def _get_snapshot(self):
        snap = app_snapshot_repo.get_by_snapshot_id(self.record.snapshot_id)
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
