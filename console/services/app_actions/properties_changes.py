# -*- coding: utf-8 -*-
import json
import logging

from console.repositories.app import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import mnt_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import volume_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.services.app import app_service
from console.services.app_config.volume_service import AppVolumeService
from console.services.plugin import app_plugin_service
from console.services.rbd_center_app_service import rbd_center_app_service

logger = logging.getLogger("default")
volume_service = AppVolumeService()


class PropertiesChanges(object):
    def __init__(self, service):
        self.service = service
        self.service_source = service_source_repo.get_service_source(
            service.tenant_id, service.service_id)

    def get_property_changes(self, eid, version):
        """
        get property changes for market service

        raise: RecordNotFound
        raise: RbdAppNotFound
        """
        app = rbd_center_app_service.get_version_app(eid, version,
                                                     self.service_source)
        # when modifying the following properties, you need to
        # synchronize the method 'properties_changes.has_changes'
        result = {}
        deploy_version = self.deploy_version_changes(app["deploy_version"])
        if deploy_version:
            result["deploy_version"] = deploy_version
        app_version = self.app_version_changes(version)
        if app_version is not None:
            result["app_version"] = app_version
        # source code service does not have 'share_image'
        image = self.image_changes(app.get("share_image", None))
        if image:
            result["image"] = image
        slug_path = self.slug_path_changes(app.get("share_slug_path", None))
        if slug_path:
            result["slug_path"] = slug_path
        envs = self.env_changes(app.get("service_env_map_list", []))
        if envs:
            result["envs"] = envs
        ports = self.port_changes(app.get("port_map_list", []))
        if ports:
            result["ports"] = ports
        connect_infos = self.env_changes(app.get("service_connect_info_map_list", []))
        if connect_infos:
            result["connect_infos"] = connect_infos
        volumes = self.volume_changes(app.get("service_volume_map_list", []))
        if volumes:
            result["volumes"] = volumes
        probe = self.probe_changes(app["probes"])
        if probe:
            result["probe"] = probe
        dep_uuids = []
        if app.get("dep_service_map_list", []):
            dep_uuids = [item["dep_service_key"] for item in app.get("dep_service_map_list")]
        dep_services = self.dep_services_changes(dep_uuids)
        if dep_services:
            result["dep_services"] = dep_services
        dep_volumes = self.dep_volumes_changes(app.get("mnt_relation_list", []))
        if dep_volumes:
            result["dep_volumes"] = dep_volumes

        plugins = self.plugin_changes(app.get("service_related_plugin_config", []))
        if plugins:
            logger.debug("plugin changes: {}".format(json.dumps(plugins)))
            result["plugins"] = plugins

        return result

    def env_changes(self, envs):
        """
        Environment variables are only allowed to increase, not allowed to
        update and delete. Compare existing environment variables and input
        environment variables to find out which ones need to be added.
        """
        exist_envs = env_var_repo.get_service_env(self.service.tenant_id,
                                                  self.service.service_id)
        exist_envs_dict = {env.attr_name: env for env in exist_envs}
        add_env = [env for env in envs if exist_envs_dict.get(env["attr_name"], None) is None]
        if not add_env:
            return None
        return {
            "add": add_env
        }

    def deploy_version_changes(self, new):
        """
        compare the old and new deploy versions to determine if there is any change
        """
        return {
            "old": self.service.deploy_version,
            "new": new,
            "is_change": self.service.deploy_version < new
        }

    def app_version_changes(self, new):
        """
        compare the old and new application versions to determine if there is any change.
        application means application from market.
        """
        if self.service_source.version == new:
            return None
        return {
            "old": self.service_source.version,
            "new": new,
            "is_change": self.service_source.version != new
        }

    def image_changes(self, new):
        """
        compare the old and new image to determine if there is any change.
        """
        if new is None or self.service.image == new:
            return None
        return {
            "old": self.service.image,
            "new": new,
            "is_change": self.service.image != new
        }

    def slug_path_changes(self, new):
        """
        compare the old and new slug_path to determine if there is any change.
        """
        if new is None:
            return None
        extend_info = json.loads(self.service_source.extend_info)
        old_slug_path = extend_info.get("slug_path", None)
        if old_slug_path is None or old_slug_path == new:
            return None
        return {
            "old": old_slug_path,
            "new": new,
            "is_change": old_slug_path != new
        }

    def dep_services_changes(self, dep_uuids):
        """
        find out the dependencies that need to be created and
        the dependencies that need to be removed
        """
        dep_relations = dep_relation_repo.get_service_dependencies(
            self.service.tenant_id,
            self.service.service_id)
        service_ids = [item.dep_service_id for item in dep_relations]

        group_id = service_group_relation_repo.get_group_id_by_service(self.service)
        new_dep_services = service_repo.list_by_svc_share_uuids(group_id, dep_uuids)
        add = [svc for svc in new_dep_services if svc.service_id not in service_ids]
        if not add:
            return None
        return {
            "add": add,
        }

    def port_changes(self, new_ports):
        """port can only be created, cannot be updated and deleted"""
        old_ports = port_repo.get_service_ports(self.service.tenant_id,
                                                self.service.service_id)
        old_container_ports = {port.container_port: port for port in old_ports}
        create_ports = [port for port in new_ports
                        if port["container_port"] not in old_container_ports]
        update_ports = []
        for new_port in new_ports:
            if new_port["container_port"] not in old_container_ports:
                continue
            old_port = old_container_ports[new_port["container_port"]]
            if new_port["is_outer_service"] and not old_port.is_outer_service:
                update_ports.append(new_port)
                continue
            if new_port["is_inner_service"] and not old_port.is_inner_service:
                update_ports.append(new_port)
                continue
        if not create_ports and not update_ports:
            return None
        result = {}
        if create_ports:
            result["add"] = create_ports
        if update_ports:
            result["upd"] = update_ports
        logger.debug("ports: {}".format(json.dumps(result)))
        return result

    def volume_changes(self, new_volumes):
        old_volumes = volume_repo.get_service_volumes(self.service.service_id)
        old_volume_names = {
            volume.volume_name: volume for volume in old_volumes
        }
        add = []
        update = []
        for new_volume in new_volumes:
            old_volume = old_volume_names.get(new_volume["volume_name"], None)
            if not old_volume:
                add.append(new_volume)
                continue
            if not new_volume.get("file_content"):
                continue
            old_file_content = volume_repo.get_service_config_file(old_volume.ID)
            if old_file_content.file_content != new_volume["file_content"]:
                update.append(new_volume)
        if not add and not update:
            return None
        return {
            "add": add,
            "upd": update,
        }

    def plugin_changes(self, new_plugins):
        old_plugins, _ = app_plugin_service.get_plugins_by_service_id(
            self.service.service_region, self.service.tenant_id, self.service.service_id, "")
        old_plugin_keys = {item.origin_share_id: item for item in old_plugins}
        new_plugin_keys = {item["plugin_key"]: item for item in new_plugins}
        logger.debug("start getting plugin changes; old_plugin_keys: {}; \
            new_plugin_keys: {}".format(json.dumps(old_plugin_keys), json.dumps(new_plugin_keys)))

        add = []
        delete = []
        for new_plugin in new_plugins:
            if new_plugin["plugin_key"] in old_plugin_keys:
                continue
            add.append(new_plugin)
        for old_plugin in old_plugins:
            if old_plugin.origin_share_id in new_plugin_keys:
                continue
            delete.append({
                "plugin_key": old_plugin.origin_share_id,
                "plugin_id": old_plugin.plugin_id,
            })
        # TODO: if add and delete:
        if not add:
            return None
        return {
            "add": add,
            # "del": delete,
        }

    def probe_changes(self, new_probes):
        if not new_probes:
            return None
        new_probe = new_probes[0]
        # remove redundant keys
        for key in ["ID", "probe_id", "service_id"]:
            new_probe.pop(key)
        old_probe = probe_repo.get_probe(self.service.service_id)
        if not old_probe:
            return {"add": new_probe, "upd": []}
        old_probe = old_probe.to_dict()
        for k, v in new_probe.items():
            if old_probe[k] != v:
                logger.debug("found a change in the probe; key: {}; \
                    old value: {}; new value: {}".format(k, v, old_probe[k]))
                return {"add": [], "upd": new_probe}
        return None

    def dep_volumes_changes(self, new_dep_volumes):
        def key(sid, mnt_name):
            logger.debug("sid: {}; mnt_name: {}".format(sid, mnt_name))
            return sid + "-" + mnt_name

        old_dep_volumes = mnt_repo.get_service_mnts(self.service.tenant_id,
                                                    self.service.service_id)
        olds = {key(item.dep_service_id, item.mnt_name): item for item in old_dep_volumes}

        tenant_service_volumes = volume_repo.get_service_volumes(self.service.service_id)
        local_path = [item.volume_path for item in tenant_service_volumes]

        add = []
        for new_dep_volume in new_dep_volumes:
            dep_service = app_service.get_service_by_service_key(
                self.service, new_dep_volume["service_share_uuid"])
            logger.debug("dep_service: {}".format(dep_service))
            if dep_service is None:
                continue
            if olds.get(key(dep_service["service_id"], new_dep_volume["mnt_name"]), None):
                logger.debug("ignore dep volume: {}; dep volume exist.".format(
                    key(dep_service["service_id"], new_dep_volume["mnt_name"])))
                continue

            code, msg = volume_service.check_volume_path(self.service,
                                                         new_dep_volume["mnt_dir"],
                                                         local_path=local_path)
            if code != 200:
                logger.warning("service id: {}; path: {}; invalid volume: {1}".format(
                    self.service.service_id, new_dep_volume["mnt_dir"], msg))

            new_dep_volume["service_id"] = dep_service["service_id"]
            add.append(new_dep_volume)
        if not add:
            return None
        return {"add": add}


def has_changes(changes):
    def alpha(x):
        return x and x.get("is_change", None)

    def beta(x):
        return x and (x.get("add", None)
                      or x.get("del", None)
                      or x.get("upd", None))

    a = ["deploy_version", "app_version"]
    b = [
        "envs", "connect_infos", "ports", "probe", "volumes", "dep_services",
        "dep_volumes", "plugins"
    ]

    for k, v in changes.items():
        if k in a and alpha(v):
            logger.debug("found a change; key: {}; value: {}".format(k, v))
            return True
        if k in b and beta(v):
            logger.debug("found a change; key: {}; value: {}".format(k, v))
            return True
    return False
