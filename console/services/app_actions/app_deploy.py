# -*- coding: utf-8 -*-
import json
import logging
from copy import deepcopy
from datetime import datetime

from django.db import transaction

from console.exception.main import EnvAlreadyExist
from console.exception.main import ErrDepVolumeNotFound
from console.exception.main import ErrInvalidVolume
from console.exception.main import InnerPortNotFound
from console.exception.main import InvalidEnvName
from console.exception.main import ServiceRelationAlreadyExist
from console.repositories.app import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import volume_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.service_backup_repo import service_backup_repo
from console.services.app_actions import app_manage_service
from console.services.app_actions.properties_changes import PropertiesChanges
from console.services.app_config import AppPortService
from console.services.app_config import env_var_service
from console.services.app_config import mnt_service
from console.services.app_config.app_relation_service import AppServiceRelationService
from console.services.backup_service import groupapp_backup_service as backup_service
from console.services.plugin import app_plugin_service
from console.services.rbd_center_app_service import rbd_center_app_service
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()
app_port_service = AppPortService()
app_relation_service = AppServiceRelationService()


class AppDeployService(object):
    def pre_deploy_action(self, tenant, service, version=None):
        """perform pre-deployment actions"""
        if service.service_source == "market":
            impl = MarketService(tenant, service, version)
        else:
            impl = OhterService(service)
        impl.pre_action()

    def deploy(self, tenant, service, user, is_upgrade, version, committer_name=None):
        """
        After the preparation is completed, emit a deployment task to the data center.
        """
        self.pre_deploy_action(tenant, service, version)
        code, msg, event = app_manage_service.deploy(tenant, service, user, is_upgrade,
                                                     group_version=version,
                                                     committer_name=committer_name)
        return code, msg, event


class OhterService(object):
    """
    Services outside the market service
    """

    def __init__(self, service):
        self.service = service

    def pre_action(self):
        logger.info("type: other; service id: {}; pre-deployment action.".format(
            self.service.service_id))


class MarketService(object):
    """
    Define some methods for upgrading market services.
    """

    def __init__(self, tenant, service, version):
        self.tenant = tenant
        self.service = service
        if version is None:
            service_source = service_source_repo.get_service_source(
                tenant.tenant_id, service.service_id)
            version = service_source.version
        self.version = version
        # data that has been successfully changed
        self.changed = {}
        self.backup = None
        self.update_funcs = self._create_update_funcs()
        self.sync_funcs = self._create_sync_funcs()
        self.resotre_func = self._create_restore_funcs()

    def dummy_func(self, changes):
        pass

    def _create_update_funcs(self):
        return {
            "deploy_version": self._update_deploy_version,
            "app_version": self._update_version,
            "envs": self._update_envs,
            "connect_infos": self._update_envs,
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
            "envs": self._sync_envs,
            "connect_infos": self._sync_envs,
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
            "envs": self._resotre_envs,
            "connect_infos": self._resotre_envs,
            "ports": self._resotre_ports,
            "volumes": self._restore_volumes,
            "probe": self._restore_probe,
            "dep_services": self._restore_dep_services,
            "dep_volumes": self._restore_dep_volumes,
            "plugins": self._restore_plugins,
        }

    def pre_action(self):
        """
        raise RbdAppNotFound
        raise RecordNotFound
        """
        logger.info("type: market; service id: {}; pre-deployment action.".format(
            self.service.service_id))
        backup = self.create_backup()
        logger.info("service id: {}; backup id: {}; backup successfully.".format(
            self.service.service_id, backup.backup_id))

        # list properties changes
        pc = PropertiesChanges(self.service)
        raw_changes = pc.get_property_changes(self.tenant.enterprise_id,
                                              self.version)
        changes = deepcopy(raw_changes)
        logger.debug("service id: {}; dest version: {}; changes: {}".format(
            self.service.service_id, self.version, changes))

        with transaction.atomic():
            self.modify_property(changes)
            self.sync_region_property(changes)

        # self.restore_backup()

    def create_backup(self):
        """
        Create a pre-service backup to prepare for deployment failure
        """
        backup_data = backup_service.get_service_details(self.tenant,
                                                         self.service)
        backup = {
            "region_name": self.tenant.region,
            "tenant_id": self.tenant.tenant_id,
            "service_id": self.service.service_id,
            "backup_id": make_uuid(),
            "backup_data": json.dumps(backup_data),
            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        return service_backup_repo.create(**backup)

    def modify_property(self, changes):
        """
        Perform modifications to the given properties
        """
        service_source = service_source_repo.get_service_source(
            self.tenant.tenant_id, self.service.service_id)
        app = rbd_center_app_service.get_version_app(self.tenant.enterprise_id,
                                                     self.version,
                                                     service_source)
        self._update_service(app)
        self._update_service_source(app, self.version)
        for k, v in changes.items():
            func = self.update_funcs.get(k, None)
            if func is None:
                logger.warning(
                    "key: {}; unsuppurt key for upgrade func".format(k))
                continue
            func(v)

    def sync_region_property(self, changes):
        """
        After modifying the properties on the console side, you need to
        synchronize with the region side.
        raise: RegionApiBaseHttpClient.CallApiError
        """
        for k, v in changes.items():
            func = self.sync_funcs.get(k, None)
            if func is None:
                logger.warning(
                    "key: {}; unsuppurt key for sync func".format(k))
                continue
            func(v)
            self.changed[k] = v

    def restore_backup(self):
        """
        Restore data in the region based on backup information
        when an error occurs during deployment.
        """
        for k, v in self.changed.items():
            func = self.resotre_func.get(k, None)
            if func is None:
                logger.warning("key: {}; unsuppurt key for restore func".format(k))
                continue
            try:
                func(v)
            except RegionApiBaseHttpClient.CallApiError as e:
                # ignore restore error
                logger.error("service id: {}; failed to restore {}; {}".format(
                    self.service.service_id, k, e))

    def _update_service(self, app):
        # TODO: 实例可选项, 内存可选项
        params = {
            "cmd": app.get("cmd", ""),
            "version": app["version"],
            "deploy_version": app["deploy_version"]
        }
        share_image = app.get("share_image", None)
        if share_image:
            params["image"] = share_image
            self.service.image = share_image
        logger.debug("tenant id: {}; service id: {}; data: {}; update service.".format(
            self.tenant.tenant_id, self.service.service_id, params))
        # service_repo.update(self.tenant.tenant_id,
        #                     self.service.service_id,
        #                     **params)
        self.service.cmd = app.get("cmd", "")
        self.service.version = app["version"]
        self.service.deploy_version = app["deploy_version"]
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

        data = {
            "extend_info": json.dumps(new_extend_info),
            "version": version,
        }
        logger.debug("service id: {}; data: {}; update service source.".format(
            self.service.service_id, data))
        service_source_repo.update_service_source(self.tenant.tenant_id,
                                                  self.service.service_id,
                                                  **data)

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

    def _update_envs(self, envs):
        if envs is None:
            return
        logger.debug("service id: {}; update envs; data: {}".format(
            self.service.service_id, envs))
        # create envs
        add = envs.get("add", [])
        for env in add:
            container_port = env.get("container_port", 0)
            if container_port == 0 and env["attr_value"] == "**None**":
                env["attr_value"] = self.service.service_id[:8]
            try:
                env_var_service.create_env_var(self.service, container_port,
                                               env["name"], env["attr_name"],
                                               env["attr_value"], env["is_change"],
                                               "inner")
            except (EnvAlreadyExist, InvalidEnvName) as e:
                logger.warning(
                    "failed to create env: {}; will ignore this env".format(e))

    def _sync_envs(self, envs):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        if envs is None:
            return
        logger.debug("service id: {}; sync envs; data: {}".format(
            self.service.service_id, envs))
        add = envs.get("add", [])
        for env in add:
            container_port = env.get("container_port", 0)
            if container_port == 0 and env["attr_value"] == "**None**":
                env["attr_value"] = self.service.service_id[:8]
            attr = {
                "container_port": container_port,
                "tenant_id": self.service.tenant_id,
                "service_id": self.service.service_id,
                "name": env["name"],
                "attr_name": env["attr_name"],
                "attr_value": str(env["attr_value"]),
                "is_change": True,
                "scope": "inner",  # TODO: do not hard code
                "env_name": env["attr_name"],
                "env_value": str(env["attr_value"]),
                "enterprise_id": self.tenant.enterprise_id
            }
            region_api.add_service_env(self.service.service_region,
                                       self.tenant.tenant_name,
                                       self.service.service_alias, attr)

    def _resotre_envs(self, envs):
        pass

    def _update_ports(self, ports):
        if ports is None:
            return
        add = ports.get("add", [])
        for port in add:
            container_port = int(port["container_port"])
            port_alias = self.service.service_key.upper()[:8]
            port["tenant_id"] = self.tenant.tenant_id
            port["service_id"] = self.service.service_id
            port["mapping_port"] = container_port
            port["port_alias"] = port_alias
            port_repo.add_service_port(**port)
            if port["is_inner_service"]:
                try:
                    env_var_service.create_env_var(self.service, container_port,
                                                   u"连接地址", port_alias + "_HOST",
                                                   "127.0.0.1")
                    env_var_service.create_env_var(self.service, container_port,
                                                   u"端口", port_alias + "_PORT",
                                                   container_port)
                except (EnvAlreadyExist, InvalidEnvName) as e:
                    logger.warning(
                        "failed to create env: {}; will ignore this env".format(e))

    def _sync_ports(self, ports):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        if ports is None:
            return
        add = ports.get("add", [])
        for port in add:
            container_port = int(port["container_port"])
            port_alias = self.service.service_key.upper()[:8]
            port["tenant_id"] = self.tenant.tenant_id
            port["service_id"] = self.service.service_id
            port["mapping_port"] = container_port
            port["port_alias"] = port_alias
        region_api.add_service_port(self.tenant.region, self.tenant.tenant_name,
                                    self.service.service_alias,
                                    {"port": add, "enterprise_id": self.tenant.enterprise_id})

    def _resotre_ports(self, ports):
        # TODO
        pass

    def _update_volumes(self, volumes):
        for volume in volumes.get("add"):
            volume["service_id"] = self.service.service_id
            host_path = "/grdata/tenant/{0}/service/{1}{2}".format(
                self.tenant.tenant_id, self.service.service_id, volume["volume_path"])
            volume["host_path"] = host_path
            file_content = volume["file_content"]
            volume.pop("file_content")
            v = volume_repo.add_service_volume(**volume)
            if not file_content and volume["volume_type"] != "config-file":
                continue
            file_data = {
                "service_id": self.service.service_id,
                "volume_id": v.ID,
                "file_content": file_content
            }
            _ = volume_repo.add_service_config_file(**file_data)
        for volume in volumes.get("upd"):
            # only volume of type config-file can be updated,
            # and only the contents of the configuration file can be updated.
            if not volume["file_content"] and volume["volume_type"] != "config-file":
                continue
            v = volume_repo.get_service_volume_by_name(self.service.service_id,
                                                       volume["volume_name"])
            if not v:
                logger.warning("service id: {}; volume name: {}; failed to update volume: \
                    volume not found.".format(self.service.service_id, volume["volume_name"]))
            cfg = volume_repo.get_service_config_file(v.ID)
            cfg.file_content = volume["file_content"]
            cfg.save()

    def _sync_volumes(self, volumes):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        for volume in volumes.get("add"):
            volume["enterprise_id"] = self.tenant.enterprise_id
            region_api.add_service_volumes(self.service.service_region,
                                           self.tenant.tenant_name,
                                           self.service.service_alias,
                                           volume)

    def _restore_volumes(self, volumes):
        # TODO
        pass

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
            region_api.add_service_probe(self.tenant.region,
                                         self.tenant.tenant_name,
                                         self.service.service_alias,
                                         data)
        upd = probe.get("upd", None)
        if upd:
            region_api.update_service_probec(self.tenant.region,
                                             self.tenant.tenant_name,
                                             self.service.service_alias,
                                             data)

    def _restore_probe(self, probe):
        # TODO
        pass

    def _update_dep_services(self, dep_services):
        def create_dep_service(dep_serivce_id):
            dep_service = service_repo.get_service_by_service_id(dep_serivce_id)
            if dep_service is None:
                return

            try:
                app_relation_service.create_service_relation(
                    self.tenant, self.service, dep_service.service_id)
            except (ServiceRelationAlreadyExist, InnerPortNotFound) as e:
                logger.warning("failed to create service relation: {}".format(e))

        add = dep_services.get("add", [])
        for dep_service in add:
            create_dep_service(dep_service["service_id"])

    def _sync_dep_services(self, dep_services):
        def sync_dep_service(dep_serivce_id):
            """
            raise RegionApiBaseHttpClient.CallApiError
            """
            dep_service = service_repo.get_service_by_service_id(dep_serivce_id)
            if dep_service is None:
                return
            inner_ports = port_repo.list_inner_ports(self.tenant.tenant_id,
                                                     self.service.service_id)
            if not inner_ports:
                logger.warning("failed to sync dependent service: inner ports not found")
            body = dict()
            body["dep_service_id"] = dep_service.service_id
            body["tenant_id"] = self.tenant.tenant_id
            body["dep_service_type"] = dep_service.service_type
            body["enterprise_id"] = self.tenant.enterprise_id

            region_api.add_service_dependency(self.tenant.region,
                                              self.tenant.tenant_name,
                                              self.service.service_alias, body)
        add = dep_services.get("add", [])
        for dep_service in add:
            sync_dep_service(dep_service["service_id"])

    def _restore_dep_services(self, dep_services):
        # TODO
        pass

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
            dep_vol = volume_repo.get_service_volume_by_name(
                dep_vol_info["service_id"], dep_vol_info["mnt_name"])
            if dep_vol is None:
                logger.warning("dep service id: {}; volume name: {}; fail to \
                    sync dep volume: dep volume not found".format(
                    dep_vol_info["service_id"], dep_vol_info["mnt_name"]))
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
            region_api.add_service_dep_volumes(self.tenant.region,
                                               self.tenant.tenant_name,
                                               self.service.service_alias, data)

        add = dep_volumes.get("add", [])
        for dep_vol in add:
            sync_dep_vol(dep_vol)

    def _restore_dep_volumes(self, dep_volumes):
        # TODO
        pass

    def _update_plugins(self, plugins):
        add = plugins.get("add", [])
        app_plugin_service.create_plugin_4marketsvc(
            self.tenant.region, self.tenant, self.service, self.version, add)

        delete = plugins.get("delete", [])
        for plugin in delete:
            app_plugin_service.delete_service_plugin_relation(self.service,
                                                              plugin["plugin_id"])
            app_plugin_service.delete_service_plugin_config(self.service,
                                                            plugin["plugin_id"])

    def _sync_plugins(self, plugins):
        """
        raise RegionApiBaseHttpClient.CallApiError
        """
        add = plugins.get("add", [])
        for plugin in add:
            data = app_plugin_service.build_plugin_data_4marketsvc(
                self.tenant, self.service, plugin)
            region_api.install_service_plugin(
                self.tenant.region, self.tenant.tenant_name, self.service.service_alias, data)

        delete = plugins.get("delete", [])
        for plugin in delete:
            region_api.uninstall_service_plugin(self.tenant.region,
                                                self.tenant.tenant_name,
                                                plugin["plugin_id"],
                                                self.service.service_alias)

    def _restore_plugins(self, plugins):
        # TODO
        pass
