# -*- coding: utf-8 -*-
import json

from console.exception.main import RbdAppNotFound
from console.exception.main import RecordNotFound
from console.repositories.app import service_source_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import port_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.repositories.service_repo import service_repo


class PropertiesChanges(object):
    def __init__(self, service):
        self.service = service
        self.service_source = service_source_repo.get_service_source(
            service.tenant_id, service.service_id)

    def get_property_changes(self, eid, version):
        """
        get property changes for market service
        """
        rain_app = rainbond_app_repo. \
            get_enterpirse_app_by_key_and_version(
                eid, self.service_source.group_key, version)
        if rain_app is None:
            raise RecordNotFound("Enterprice id: {0}; Group key: {1}; version: {2}; \
                RainbondCenterApp not found.".format(eid, self.service_source.group_key, version))

        apps_template = json.loads(rain_app.app_template)
        apps = apps_template.get("apps")
        app = next(iter(filter(lambda x: x["service_share_uuid"]
                               == self.service_source.service_share_uuid, apps)), None)
        if app is None:
            fmt = "Group key: {0}; version: {1}; service_share_uuid: {2}; \
                Rainbond app not found."
            raise RbdAppNotFound(fmt.format(self.service_source.group_key,
                                            version,
                                            self.service_source.service_share_uuid))

        # when modifying the following properties, you need to
        # synchronize the method 'properties_changes.has_changes'
        deploy_version = self.deploy_version_changes(app["deploy_version"])
        app_version = self.app_version_changes(version)
        envs = self.env_changes(app.get("service_env_map_list"))
        ports = self.port_changes(app.get("port_map_list"))

        dep_service_map_list = app.get("dep_service_map_list", None)
        dep_uuids = []
        if dep_service_map_list:
            dep_uuids = [item["dep_service_key"]
                         for item in dep_service_map_list]
        dep_services = self.dep_services_changes(dep_uuids)

        return {
            "deploy_version": deploy_version,
            "app_version": app_version,
            "envs": envs,
            "dep_services": dep_services,
            "ports": ports,
        }

    def env_changes(self, envs):
        """
        Environment variables are only allowed to increase, not allowed to
        update and delete. Compare existing environment variables and input
        environment variables to find out which ones need to be added.
        """
        exist_envs = env_var_repo.get_service_env_by_scope(
            self.service.tenant_id, self.service.service_id, "outer")
        exist_envs_dict = {env.attr_name: env for env in exist_envs}
        add_env = [env for env in envs if exist_envs_dict
                   .get(env["attr_name"], None) is None]
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
            "is_change": self.service.deploy_version == new
        }

    def app_version_changes(self, new):
        """
        compare the old and new application versions to determine if there is any change.
        application means application from market.
        """
        return {
            "old": self.service_source.version,
            "new": new,
            "is_change": self.service_source.version == new
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
        dep_services = service_repo.list_by_ids(service_ids)

        uuids = "'{}'".format("','".join(str(uuid)
                                         for uuid in dep_uuids))
        group_id = service_group_relation_repo.get_group_id_by_service(self.service)
        new_dep_services = service_repo.list_by_svc_share_uuids(
            group_id, uuids)
        new_service_ids = [svc.service_id for svc in new_dep_services]

        add = [svc for svc in new_dep_services if svc.service_id not in service_ids]
        delete = [
            {
                "service_id": svc.service_id,
                "service_cname": svc.service_cname
            } for svc in dep_services if svc.service_id not in new_service_ids
        ]
        return {
            "add": add,
            "del": delete,
        }

    def port_changes(self, new_ports):
        """port can only be created, cannot be updated and deleted"""
        old_ports = port_repo.get_service_ports(self.service.tenant_id,
                                                self.service.service_id)
        old_container_ports = [port.container_port for port in old_ports]
        create_ports = [port for port in new_ports
                        if port["container_port"] not in old_container_ports]
        return {
            "add": create_ports
        }


def has_changes(data):
    def alpha(x): return x and x.get("is_change", None)
    if alpha(data.get("deploy_version", None)):
        return True
    if alpha(data.get("app_version", None)):
        return True

    def beta(x): return x and (x.get("add", None) or x.get("del", None)
                               or x.get("upd", None))
    if beta(data.get("envs", None)):
        return True
    if beta(data.get("ports", None)):
        return True
    if beta(data.get("dep_services", None)):
        return True
    return False
