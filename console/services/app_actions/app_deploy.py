# -*- coding: utf-8 -*-
import json
import logging
from copy import deepcopy
from datetime import datetime
from enum import IntEnum

from addict import Dict
from console.exception.main import (EnvAlreadyExist, ErrDepVolumeNotFound,
                                    ErrInvalidVolume, InnerPortNotFound,
                                    InvalidEnvName, ServiceHandleException,
                                    ServiceRelationAlreadyExist)
from console.repositories.app import service_repo, service_source_repo
from console.repositories.app_config import port_repo, volume_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.service_backup_repo import service_backup_repo
from console.services.app_actions import app_manage_service
from console.services.app_actions.app_restore import AppRestore
from console.services.app_actions.exception import ErrBackupNotFound
from console.services.app_actions.properties_changes import (
    PropertiesChanges, get_upgrade_app_version_template_app)
from console.services.app_config import (AppPortService, env_var_service,
                                         mnt_service)
from console.services.app_config.app_relation_service import \
    AppServiceRelationService
from console.services.backup_service import \
    groupapp_backup_service as backup_service
from console.services.exception import ErrDepServiceNotFound
from console.services.market_app_service import market_app_service
from console.services.plugin import app_plugin_service
from console.services.rbd_center_app_service import rbd_center_app_service
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()
app_port_service = AppPortService()
app_relation_service = AppServiceRelationService()
baseService = BaseTenantService()


class AsyncAction(IntEnum):
    BUILD = 0
    UPDATE = 1
    NOTHING = 2


# priority: build > update > nothing
priority = {AsyncAction.BUILD.value: 0, AsyncAction.UPDATE.value: 1, AsyncAction.NOTHING.value: 2}


class PropertyType(IntEnum):
    """type of property
    ALL: do not distinguish, use all properties
    ORDINARY: ordinary properties
    DEPENDENT: properties that need to handle dependencies
    """
    ALL = 0
    ORDINARY = 1
    DEPENDENT = 2


class AppDeployService(object):
    def __init__(self):
        self.impl = OtherService()

    def set_impl(self, impl):
        self.impl = impl

    def pre_deploy_action(self, tenant, service, version=None):
        """perform pre-deployment actions"""
        if service.service_source == "market":
            self.impl = MarketService(tenant, service, version)

        self.impl.pre_action()

    def get_async_action(self):
        return self.impl.get_async_action()

    def execute(self, tenant, service, user, is_upgrade, version, committer_name=None, oauth_instance=None):
        async_action = self.get_async_action()
        logger.info("service id: {}; async action is '{}'".format(service.service_id, async_action))
        if async_action == AsyncAction.BUILD.value:
            code, msg, event_id = app_manage_service.deploy(
                tenant, service, user, group_version=version, oauth_instance=oauth_instance, committer_name=committer_name)
        elif async_action == AsyncAction.UPDATE.value:
            code, msg, event_id = app_manage_service.upgrade(
                tenant, service, user, committer_name, oauth_instance=oauth_instance)
        else:
            return 200, "", ""
        return code, msg, event_id

    def deploy(self, tenant, service, user, version, committer_name=None, oauth_instance=None):
        """
        After the preparation is completed, emit a deployment task to the data center.
        """
        self.pre_deploy_action(tenant, service, version)

        return self.execute(tenant, service, user, version, committer_name, oauth_instance=oauth_instance)


class OtherService(object):
    """
    Services outside the market service
    """

    def pre_action(self):
        logger.info("type: other; pre-deployment action.")

    def get_async_action(self):
        return AsyncAction.BUILD.value


class MarketService(object):
    """
    Define some methods for upgrading market services.
    """

    def __init__(self, tenant, service, version):
        self.tenant = tenant
        self.service = service
        self.market_name = None
        self.service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        if self.service_source.extend_info:
            extend_info = json.loads(self.service_source.extend_info)
            self.install_from_cloud = extend_info.get("install_from_cloud", False)
            self.market_name = extend_info.get("market_name", None)
            if self.install_from_cloud:
                logger.info("service {0} imstall from cloud".format(service.service_alias))
        else:
            self.install_from_cloud = False
        # If no version is specified, the default version is used.
        self.async_action = None
        if not version:
            version = self.service_source.version
            self.async_action = AsyncAction.BUILD.value
        self.version = version
        self.group_key = self.service_source.group_key
        self.changes = {}
        # data that has been successfully changed
        self.changed = {}
        self.backup = None

        self.update_funcs = self._create_update_funcs()
        self.sync_funcs = self._create_sync_funcs()
        self.restore_func = self._create_restore_funcs()
        self.async_build, self.async_update = self._create_async_action_tbl()

        self.app_restore = AppRestore(tenant, service)
        self.auto_restore = True

    def dummy_func(self, changes):
        pass

    def set_properties(self, typ3=PropertyType.ALL.value):
        """
        Types of service properties are ordinary and dependent. when updating an application,
        you need to process the ordinary properties first and then the dependent ones.
        In addition, you don't need to distinguish properties when you roll back.
        """
        all_update_funcs = self._create_update_funcs()
        all_sync_funcs = self._create_sync_funcs()
        m = {
            PropertyType.ORDINARY.value:
            ["deploy_version", "app_version", "image", "slug_path", "envs", "connect_infos", "ports", "volumes", "probe"],
            PropertyType.DEPENDENT.value: ["dep_services", "dep_volumes", "plugins"]
        }
        keys = m.get(typ3, None)
        if keys is None:
            self.update_funcs = all_update_funcs
            self.sync_funcs = all_sync_funcs
            return
        self.update_funcs = {key: all_update_funcs[key] for key in keys if key in all_update_funcs}
        self.sync_funcs = {key: all_sync_funcs[key] for key in keys if key in all_sync_funcs}

    def _create_update_funcs(self):
        return {
            "deploy_version": self._update_deploy_version,
            "app_version": self._update_version,
            "image": self.dummy_func,
            "slug_path": self.dummy_func,
            "envs": self._update_inner_envs,
            "connect_infos": self._update_outer_envs,
            "ports": self._update_ports,
            "volumes": self._update_volumes,
            "probe": self._update_probe,
            "dep_services": self._update_dep_services,
            "dep_volumes": self._update_dep_volumes,
            "plugins": self._update_plugins,
        }

    def _create_sync_funcs(self):
        return {
            "deploy_version": self.dummy_func,
            "app_version": self.dummy_func,
            "image": self.dummy_func,
            "slug_path": self.dummy_func,
            "envs": self._sync_inner_envs,
            "connect_infos": self._sync_outer_envs,
            "ports": self._sync_ports,
            "volumes": self._sync_volumes,
            "probe": self._sync_probe,
            "dep_services": self._sync_dep_services,
            "dep_volumes": self._sync_dep_volumes,
            "plugins": self._sync_plugins,
        }

    def _create_restore_funcs(self):
        return {
            "deploy_version": self.dummy_func,
            "app_version": self.dummy_func,
            "image": self.dummy_func,
            "slug_path": self.dummy_func,
            "envs": self._restore_inner_envs,
            "connect_infos": self._restore_outer_envs,
            "ports": self._restore_ports,
            "volumes": self._restore_volumes,
            "probe": self._restore_probe,
            "dep_services": self._restore_dep_services,
            "dep_volumes": self._restore_dep_volumes,
            "plugins": self._restore_plugins,
            "service": self._restore_service,
            "service_source": self._restore_service_source,
        }

    @staticmethod
    def _create_async_action_tbl():
        """
        create an asynchronous action corresponding to the modification of each property
        asynchronous action: build, update or nothing
        """
        async_build = ["deploy_version", "image", "slug_path"]
        async_update = ["envs", "connect_infos", "ports", "volumes", "probe", "dep_services", "dep_volumes", "plugins"]
        return async_build, async_update

    def pre_action(self):
        """
        raise RbdAppNotFound
        raise RecordNotFound
        raise ErrServiceSourceNotFound
        """
        logger.info("type: market; service id: {}; pre-deployment action.".format(self.service.service_id))
        backup = self.create_backup()
        logger.info("service id: {}; backup id: {}; backup successfully.".format(self.service.service_id, backup.backup_id))
        self.set_changes()

        try:
            with transaction.atomic():
                self.modify_property()
                self.sync_region_property()
        except RegionApiBaseHttpClient.CallApiError as e:
            logger.exception(e)
            logger.error("service id: {}; failed to change properties for market service: {}".format(
                self.service.service_id, e))
            self.restore_backup(backup)
            # when a single service is upgraded, if a restore occurs,
            # there is no need to emit an asynchronous action.
            self.async_action = AsyncAction.NOTHING.value

    def set_changes(self):
        pc = PropertiesChanges(self.service, self.tenant, self.install_from_cloud)
        app = get_upgrade_app_version_template_app(self.tenant, self.version, pc)
        changes = pc.get_property_changes(app)
        logger.debug("service id: {}; dest version: {}; changes: {}".format(self.service.service_id, self.version, changes))
        self.changes = changes
        logger.info("upgrade from cloud do not support.")

    def create_backup(self):
        """create_backup
        Create a pre-service backup to prepare for deployment failure
        """
        backup_data = backup_service.get_service_details(self.tenant, self.service)
        backup = {
            "region_name": self.service.service_region,
            "tenant_id": self.tenant.tenant_id,
            "service_id": self.service.service_id,
            "backup_id": make_uuid(),
            "backup_data": json.dumps(backup_data),
            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        return service_backup_repo.create(**backup)

    def modify_property(self):
        """
        Perform modifications to the given properties. must be called after `set_changes`.
        """
        service_source = service_source_repo.get_service_source(self.tenant.tenant_id, self.service.service_id)
        if self.install_from_cloud:
            app = market_app_service.get_service_app_from_cloud(self.tenant, self.group_key, self.version, service_source)
        else:
            app = rbd_center_app_service.get_version_app(self.tenant.enterprise_id, self.version, service_source)
        self._update_service(app)
        self._update_service_source(app, self.version)
        changes = deepcopy(self.changes)
        if changes:
            for k, v in changes.items():
                func = self.update_funcs.get(k, None)
                if func is None:
                    continue
                func(v)

    @staticmethod
    def _compare_async_action(a, b):
        """
        compare a, b, two asynchronous actions, returning the ones with higher priority
        """
        if priority[a] < priority[b]:
            return a
        return b

    def get_async_action(self):
        """ get asynchronous action
        must be called after `set_changes`.
        """
        if self.install_from_cloud:
            return AsyncAction.BUILD.value
        if self.async_action is not None:
            return self.async_action
        changes = deepcopy(self.changes)
        async_action = AsyncAction.NOTHING.value
        if changes:
            for key in changes:
                async_action = self._compare_async_action(async_action, self._key_action(key))
        return async_action

    def _key_action(self, key):
        if key in self.async_build:
            return AsyncAction.BUILD.value
        if key in self.async_update:
            return AsyncAction.UPDATE.value
        return AsyncAction.NOTHING.value

    def sync_region_property(self):
        """
        After modifying the properties on the console side, you need to
        synchronize with the region side. must be called after `set_changes`.
        raise: RegionApiBaseHttpClient.CallApiError
        """
        changes = deepcopy(self.changes)
        if changes:
            for k, v in changes.items():
                func = self.sync_funcs.get(k, None)
                if func is None:
                    continue
                func(v)
                self.changed[k] = v

    def restore_backup(self, backup=None):
        """
        Restore data in the region based on backup information
        when an error occurs during deployment.
        """
        logger.info("service id: {}; changed properties: {}; restore service from backup".format(
            self.service.service_id, json.dumps(self.changed)))
        if backup is None:
            # use the latest backup
            backup = service_backup_repo.get_newest_by_sid(self.tenant.tenant_id, self.service.service_id)
        if backup is None:
            raise ErrBackupNotFound(self.service.service_id)

        self._update_changed()

        async_action = AsyncAction.NOTHING.value
        for k, v in self.changed.items():
            func = self.restore_func.get(k, None)
            if func is None:
                continue
            try:
                func(backup)
            except RegionApiBaseHttpClient.CallApiError as e:
                # ignore restore error
                logger.error("service id: {}; failed to restore {}; {}".format(self.service.service_id, k, e))
            async_action = self._compare_async_action(async_action, self._key_action(k))
        self.async_action = async_action

    def _update_changed(self):
        if not self.changed:
            logger.info("service id: {}; no specified changed, will restore \
                all properties".format(self.service.service_id))
            self.changed = self._create_restore_funcs()
        logger.debug("changed to be restored: {}".format(self.changed))

    def _update_service(self, app):
        share_image = app.get("share_image", None)
        if share_image:
            self.service.image = share_image
        self.service.cmd = app.get("cmd", "")
        self.service.version = app["version"]
        self.service.min_node = app["extend_method_map"]["min_node"]
        self.service.min_memory = app["extend_method_map"]["min_memory"]
        self.service.min_cpu = baseService.calculate_service_cpu(self.service.service_region, self.service.min_memory)
        self.service.total_memory = self.service.min_node * self.service.min_memory
        self.service.save()

    def _update_service_source(self, app, version):
        new_extend_info = {}
        share_image = app.get("share_image", None)
        share_slug_path = app.get("share_slug_path", None)
        if share_image and app.get("service_image", None):
            new_extend_info = app["service_image"]
        if share_slug_path:
            slug_info = app.get("service_slug")
            slug_info["slug_path"] = share_slug_path
            new_extend_info = slug_info
        new_extend_info["source_deploy_version"] = app.get("deploy_version")

        if app.get("service_share_uuid", None):
            service_share_uuid = app.get("service_share_uuid")
        else:
            service_share_uuid = app.get("service_key", "")
        new_extend_info["source_service_share_uuid"] = service_share_uuid
        if self.install_from_cloud:
            new_extend_info["install_from_cloud"] = True
            new_extend_info["market"] = "default"
            new_extend_info["market_name"] = self.market_name
        data = {
            "extend_info": json.dumps(new_extend_info),
            "version": version,
        }
        logger.debug("service id: {}; data: {}; update service source.".format(self.service.service_id, data))
        service_source_repo.update_service_source(self.tenant.tenant_id, self.service.service_id, **data)

    def _update_deploy_version(self, dv):
        if not dv["is_change"]:
            return
        self.service.deploy_version = dv["new"]
        self.service.save()

    def _update_version(self, v):
        if not v["is_change"]:
            return
        self.service.version = v["new"]
        self.service.save()

    def _update_inner_envs(self, envs):
        self._update_envs(envs, "inner")

    def _update_outer_envs(self, envs):
        self._update_envs(envs, "outer")

    def _update_envs(self, envs, scope):
        if envs is None:
            return
        logger.debug("service id: {}; update envs; data: {}".format(self.service.service_id, envs))
        # create envs
        add = envs.get("add", [])
        for env in add:
            container_port = env.get("container_port", 0)
            if container_port == 0 and env["attr_value"] == "**None**":
                env["attr_value"] = self.service.service_id[:8]
            try:
                env_var_service.create_env_var(self.service, container_port, env["name"], env["attr_name"], env["attr_value"],
                                               env["is_change"], scope)
            except (EnvAlreadyExist, InvalidEnvName) as e:
                logger.warning("failed to create env: {}; will ignore this env".format(e))

    def _sync_inner_envs(self, envs):
        self._sync_envs(envs, "inner")

    def _sync_outer_envs(self, envs):
        self._sync_envs(envs, "outer")

    def _sync_envs(self, envs, scope):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        if envs is None:
            return
        logger.debug("service id: {}; sync envs; data: {}".format(self.service.service_id, envs))
        add = envs.get("add", [])
        for env in add:
            body = self._create_env_body(env, scope)
            try:
                region_api.add_service_env(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                           body)
            except region_api.CallApiError as e:
                if e.status == 400:
                    logger.warning("env name: {}; failed to create env: {}".format(env["attr_name"], e))
                    continue
                res = Dict({"status": e.status})
                raise region_api.CallApiError(e.apitype, e.url, e.method, res, e.body)

    def _restore_inner_envs(self, backup):
        self._restore_envs(backup, "inner")

    def _restore_outer_envs(self, backup):
        self._restore_envs(backup, "outer")

    def _restore_envs(self, backup, scope):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            service_env_vars = backup_data[0].get("service_env_vars", [])
        else:
            service_env_vars = backup_data.get("service_env_vars", [])

        if not self.auto_restore:
            self.app_restore.envs(service_env_vars)

        body = {"scope": scope, "envs": []}
        for env in service_env_vars:
            if scope != env["scope"]:
                continue
            body["envs"].append(self._create_env_body(env, scope))
        try:
            region_api.restore_properties(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                          "/app-restore/envs", body)
        except RegionApiBaseHttpClient.CallApiError as e:
            # ignore restore envs error:
            logger.error("backup id: {}; failed to restore envs: {}".format(backup.backup_id, e))

    def _create_env_body(self, env, scope):
        """
        convert env to the body needed to add environment variables to the region
        """
        container_port = env.get("container_port", 0)
        if container_port == 0 and env["attr_value"] == "**None**":
            env["attr_value"] = self.service.service_id[:8]
        result = {
            "container_port": container_port,
            "tenant_id": self.service.tenant_id,
            "service_id": self.service.service_id,
            "name": env["name"],
            "attr_name": env["attr_name"],
            "attr_value": str(env["attr_value"]),
            "is_change": True,
            "scope": scope,
            "env_name": env["attr_name"],
            "env_value": str(env["attr_value"]),
            "enterprise_id": self.tenant.enterprise_id
        }
        return result

    def _create_envs_4_ports(self, port):
        container_port = int(port["container_port"])
        port_alias = self.service.service_alias.upper()
        host_env = {
            "name": u"连接地址",
            "attr_name": port_alias + str(port["container_port"]) + "_HOST",
            "attr_value": "127.0.0.1",
            "is_change": False,
        }
        port_env = {
            "name": u"端口",
            "attr_name": port_alias + str(port["container_port"]) + "_PORT",
            "attr_value": container_port,
            "is_change": False,
        }
        return [host_env, port_env]

    def update_port_data(self, port):
        container_port = int(port["container_port"])
        port_alias = self.service.service_alias.upper()
        port["tenant_id"] = self.tenant.tenant_id
        port["service_id"] = self.service.service_id
        port["mapping_port"] = container_port
        port["port_alias"] = port_alias

    def _update_ports(self, ports):
        if ports is None:
            return

        add = ports.get("add", [])
        envs = {"add": []}
        for port in add:
            self.update_port_data(port)
            port_repo.add_service_port(**port)
            if not port["is_inner_service"]:
                continue
            envs["add"].extend(self._create_envs_4_ports(port))
        upd = ports.get("upd", [])
        for port in upd:
            self.update_port_data(port)
            port_repo.update(**port)
        if not envs["add"]:
            return
        self._update_envs(envs, "outer")

    def _sync_ports(self, ports):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        if ports is None:
            return
        add = ports.get("add", [])
        envs = {"add": []}
        for port in add:
            self.update_port_data(port)
            if not port["is_inner_service"]:
                continue
            envs["add"].extend(self._create_envs_4_ports(port))
        upd = ports.get("upd", [])
        for port in upd:
            self.update_port_data(port)
        add_body = {"port": add, "enterprise_id": self.tenant.enterprise_id}
        region_api.add_service_port(self.service.service_region, self.tenant.tenant_name, self.service.service_alias, add_body)
        upd_body = {"port": upd, "enterprise_id": self.tenant.enterprise_id}
        region_api.update_service_port(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                       upd_body)

        if envs:
            self._sync_outer_envs(envs)

    def _restore_ports(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            service_ports = backup_data[0].get("service_ports", [])
        else:
            service_ports = backup_data.get("service_ports", [])

        if not self.auto_restore:
            self.app_restore.ports(service_ports)

        try:
            body = {"ports": service_ports}
            region_api.restore_properties(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                          "/app-restore/ports", body)
        except RegionApiBaseHttpClient.CallApiError as e:
            # ignore restore ports error:
            logger.error("backup id: {}; failed to restore ports: {}".format(backup.backup_id, e))

    def _update_volumes(self, volumes):
        for volume in volumes.get("add"):
            volume["service_id"] = self.service.service_id
            host_path = "/grdata/tenant/{0}/service/{1}{2}".format(self.tenant.tenant_id, self.service.service_id,
                                                                   volume["volume_path"])
            volume["host_path"] = host_path
            file_content = volume.get("file_content", None)
            if file_content is not None:
                volume.pop("file_content")
            v = volume_repo.add_service_volume(**volume)
            if not file_content and volume["volume_type"] != "config-file":
                continue
            file_data = {"service_id": self.service.service_id, "volume_id": v.ID, "file_content": file_content}
            _ = volume_repo.add_service_config_file(**file_data)
        for volume in volumes.get("upd"):
            # only volume of type config-file can be updated,
            # and only the contents of the configuration file can be updated.
            file_content = volume.get("file_content", None)
            if not file_content and volume["volume_type"] != "config-file":
                continue
            v = volume_repo.get_service_volume_by_name(self.service.service_id, volume["volume_name"])
            if not v:
                logger.warning("service id: {}; volume name: {}; failed to update volume: \
                    volume not found.".format(self.service.service_id, volume["volume_name"]))
            cfg = volume_repo.get_service_config_file(v.ID)
            cfg.file_content = file_content
            cfg.save()

    def _sync_volumes(self, volumes):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        for volume in volumes.get("add"):
            volume["enterprise_id"] = self.tenant.enterprise_id
            region_api.add_service_volumes(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                           volume)

    def _restore_volumes(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            service_config_file = backup_data[0].get("service_config_file", [])
            service_volumes = backup_data[0].get("service_volumes", [])
        else:
            service_config_file = backup_data.get("service_config_file", [])
            service_volumes = backup_data.get("service_volumes", [])
        cfgfs = {item["volume_id"]: item["file_content"] for item in service_config_file}

        if not self.auto_restore:
            self.app_restore.volumes(service_volumes, service_config_file)

        body = {"volumes": []}
        for item in service_volumes:
            item_id = item.get("ID")
            if not item_id:
                item["file_content"] = ""
            else:
                item["file_content"] = cfgfs.get(item_id, "")
            body["volumes"].append(item)
        try:
            region_api.restore_properties(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                          "/app-restore/volumes", body)
        except RegionApiBaseHttpClient.CallApiError as e:
            # ignore restore volumes error:
            logger.error("backup id: {}; failed to restore volumes: {}".format(backup.backup_id, e))

    def _update_probe(self, probe):
        logger.debug("probe: {}".format(probe))
        add = probe.get("add")
        if add:
            add["probe_id"] = make_uuid()
            probe_repo.update_or_create(self.service.service_id, add)
        upd = probe.get("upd", None)
        if upd:
            probe_repo.update_or_create(self.service.service_id, upd)

    def _sync_probe(self, probe):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        p = probe_repo.get_probe(self.service.service_id)
        data = p.to_dict()
        data["is_used"] = 1 if data["is_used"] else 0
        add = probe.get("add", None)
        if add:
            region_api.add_service_probe(self.service.service_region, self.tenant.tenant_name, self.service.service_alias, data)
        upd = probe.get("upd", None)
        if upd:
            region_api.update_service_probec(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                             data)

    def _restore_probe(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            pd = backup_data[0].get("service_probes", [])
        else:
            pd = backup_data.get("service_probes", [])
        if pd:
            probe = pd[0]
            probe["is_used"] = 1 if probe["is_used"] else 0
        else:
            probe = ""

        if not self.auto_restore:
            self.app_restore.probe(probe)

        try:
            region_api.restore_properties(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                          "/app-restore/probe", probe)
        except RegionApiBaseHttpClient.CallApiError as e:
            # ignore restore probe error:
            logger.error("backup id: {}; failed to restore probe: {}".format(backup.backup_id, e))

    def _update_dep_services(self, dep_services):
        def create_dep_service(dep_service_id):
            try:
                app_relation_service.create_service_relation(self.tenant, self.service, dep_service_id)
            except (ErrDepServiceNotFound, ServiceRelationAlreadyExist, InnerPortNotFound) as e:
                logger.warning("failed to create service relation: {}".format(e))

        add = dep_services.get("add", [])
        for dep_service in add:
            create_dep_service(dep_service["service_id"])

    def _sync_dep_services(self, dep_services):
        def sync_dep_service(dep_service_id):
            """
            raise RegionApiBaseHttpClient.CallApiError
            """
            dep_service = service_repo.get_service_by_service_id(dep_service_id)
            body = dict()
            body["dep_service_id"] = dep_service.service_id
            body["tenant_id"] = self.tenant.tenant_id
            body["dep_service_type"] = dep_service.service_type
            body["enterprise_id"] = self.tenant.enterprise_id
            region_api.add_service_dependency(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                              body)

        add = dep_services.get("add", [])
        for dep_service in add:
            sync_dep_service(dep_service["service_id"])

    def _restore_dep_services(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            service_relation = backup_data[0].get("service_relation", [])
        else:
            service_relation = backup_data.get("service_relation", [])

        if not self.auto_restore:
            self.app_restore.dep_services(service_relation)

        body = {"deps": []}
        for item in service_relation:
            body["deps"].append({
                "dep_service_id": item["dep_service_id"],
                "dep_service_type": item["dep_service_type"],
            })
        try:
            region_api.restore_properties(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                          "/app-restore/deps", body)
        except RegionApiBaseHttpClient.CallApiError as e:
            # ignore restore service relations error:
            logger.error("backup id: {}; failed to restore service relations: {}".format(backup.backup_id, e))

    def _update_dep_volumes(self, dep_volumes):
        def create_dep_vol(dep_volume):
            data = {
                "service_id": dep_volume["service_id"],
                "volume_name": dep_volume["mnt_name"],
                "path": dep_volume["mnt_dir"]
            }
            try:
                mnt_service.create_service_volume(self.tenant, self.service, data)
            except (ErrInvalidVolume, ErrDepVolumeNotFound) as e:
                logger.warning("failed to create dep volume: {}".format(e))

        add = dep_volumes.get("add", [])
        for dep_volume in add:
            create_dep_vol(dep_volume)

    def _sync_dep_volumes(self, dep_volumes):
        def sync_dep_vol(dep_vol_info):
            """
            raise RegionApiBaseHttpClient.CallApiError
            """
            dep_vol = volume_repo.get_service_volume_by_name(dep_vol_info["service_id"], dep_vol_info["mnt_name"])
            if dep_vol is None:
                logger.warning("dep service id: {}; volume name: {}; fail to \
                    sync dep volume: dep volume not found".format(dep_vol_info["service_id"], dep_vol_info["mnt_name"]))
                return
            data = {
                "depend_service_id": dep_vol.service_id,
                "volume_name": dep_vol.volume_name,
                "volume_path": dep_vol_info['mnt_dir'].strip(),
                "enterprise_id": self.tenant.enterprise_id,
                "volume_type": dep_vol.volume_type
            }
            if dep_vol.volume_type == "config-file":
                config_file = volume_repo.get_service_config_file(dep_vol.ID)
                data["file_content"] = config_file.file_content
            region_api.add_service_dep_volumes(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                               data)

        add = dep_volumes.get("add", [])
        for dep_vol in add:
            sync_dep_vol(dep_vol)

    def _restore_dep_volumes(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            dep_vols = backup_data[0].get("service_mnts", [])
        else:
            dep_vols = backup_data.get("service_mnts", [])

        if not self.auto_restore:
            self.app_restore.dep_volumes(dep_vols)

        body = {"dep_vols": []}
        for dv in dep_vols:
            body["dep_vols"].append({
                "dep_service_id": dv["dep_service_id"],
                "volume_path": dv["mnt_dir"],
                "volume_name": dv["mnt_name"]
            })
        try:
            region_api.restore_properties(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                          "/app-restore/depvols", body)
        except RegionApiBaseHttpClient.CallApiError as e:
            # ignore restore service dependent volumes error:
            logger.error("backup id: {}; failed to restore service dependent volumes: {}".format(backup.backup_id, e))

    def _update_plugins(self, plugins):
        logger.debug("start updating plugins; plugin datas: {}".format(plugins))
        add = plugins.get("add", [])
        try:
            app_plugin_service.create_plugin_4marketsvc(self.service.service_region, self.tenant, self.service, self.version,
                                                        add)
        except ServiceHandleException as e:
            logger.warning("plugin data: {}; failed to create plugin: {}", add, e)

        delete = plugins.get("delete", [])
        for plugin in delete:
            app_plugin_service.delete_service_plugin_relation(self.service, plugin["plugin_id"])
            app_plugin_service.delete_service_plugin_config(self.service, plugin["plugin_id"])

    def _sync_plugins(self, plugins):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        logger.debug("start syncing plugins; plugin datas: {}".format(plugins))
        add = plugins.get("add", [])
        for plugin in add:
            data = app_plugin_service.build_plugin_data_4marketsvc(self.tenant, self.service, plugin)
            region_api.install_service_plugin(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                              data)

        delete = plugins.get("delete", [])
        for plugin in delete:
            region_api.uninstall_service_plugin(self.service.service_region, self.tenant.tenant_name, plugin["plugin_id"],
                                                self.service.service_alias)

    def _restore_plugins(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            relations = backup_data[0].get("service_plugin_relation", [])
        else:
            relations = backup_data.get("service_plugin_relation", [])

        if not self.auto_restore:
            self.app_restore.plugins(relations)

        body = {"plugins": []}
        for r in relations:
            body["plugins"].append({
                "plugin_id": r["plugin_id"],
                "version_id": r["build_version"],
                "switch": r["plugin_status"],
            })
        try:
            region_api.restore_properties(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                          "/app-restore/plugins", body)
        except RegionApiBaseHttpClient.CallApiError as e:
            # ignore restore service plugins error:
            logger.error("backup id: {}; failed to restore service plugins: {}".format(backup.backup_id, e))

    def _restore_service(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            service_base = backup_data[0].get("service_base", None)
        else:
            service_base = backup_data.get("service_base", None)
        if not self.app_restore:
            self.app_restore.svc(service_base)

    def _restore_service_source(self, backup):
        backup_data = json.loads(backup.backup_data)
        if isinstance(backup_data, list):
            service_source = backup_data[0].get("service_source", None)
        else:
            service_source = backup_data.get("service_source", None)
        if not self.auto_restore:
            self.app_restore.svc_source(service_source)
