# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

from django.db import transaction

from console.exception.main import EnvAlreadyExist
from console.exception.main import InvalidEnvName
from console.repositories.app import service_source_repo
from console.repositories.app_config import port_repo
from console.repositories.service_backup_repo import service_backup_repo
from console.services.app_actions import app_manage_service
from console.services.app_actions.properties_changes import PropertiesChanges
from console.services.app_config import AppPortService
from console.services.app_config import env_var_service
from console.services.backup_service import groupapp_backup_service as backup_service
from console.services.rbd_center_app_service import rbd_center_app_service
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()
app_port_service = AppPortService()


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
        self.update_funcs = {
            "envs": self._update_envs,
            "ports": self._update_ports,
        }
        self.sync_funcs = {
            "envs": self._sync_envs,
            "ports": self._sync_ports,
        }
        self.resotre_func = {
            "envs": self._resotre_envs,
            "ports": self._resotre_ports,
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
        changes = pc.get_property_changes(self.tenant.enterprise_id,
                                          self.version)
        logger.debug("service id: {}; dest version: {}; changes: {}".format(
            self.service.service_id, self.version, changes))

        with transaction.atomic():
            self.modify_property(changes)
            self.sync_region_property(changes)

        self.restore_backup()

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
            # TODO: deep copy
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
            # TODO: deep copy
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
                logger.warning(
                    "key: {}; unsuppurt key for restore func".format(k))
                continue
            try:
                func(v)
            except RegionApiBaseHttpClient.CallApiError as e:
                # ignore restore error
                logger.error("service id: {}; failed to restore {}; {}".format(
                    self.service.service_id, k, e))

    def _update_service(self, app):
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
        logger.debug("service id: {}; data: {};update service source.".format(
            self.service.service_id, data))
        service_source_repo.update_service_source(self.tenant.tenant_id,
                                                  self.service.service_id,
                                                  **data)

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
        if self.backup is None:
            logger.warning("service id: {}; can't find any backup to restore envs.".format(
                self.service.service_id))
            return
        # TODO
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
