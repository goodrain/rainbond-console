# -*- coding: utf-8 -*-
import json
import logging
import time

from console.exception.main import AbortRequest
from console.repositories.app import (app_market_repo, service_repo, service_source_repo)
from console.repositories.app_config import (dep_relation_repo, env_var_repo, mnt_repo, port_repo, volume_repo)
from console.repositories.group import group_service_relation_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.service_group_relation_repo import \
    service_group_relation_repo
from console.services.app import app_market_service, app_service
from console.services.app_config.volume_service import AppVolumeService
from console.services.plugin import app_plugin_service
from console.services.rbd_center_app_service import rbd_center_app_service
from console.services.group_service import group_service
from console.services.share_services import share_service
from console.services.app_config.promql_service import promql_service
from console.repositories.component_graph import component_graph_repo
from console.services.app_config.service_monitor import service_monitor_repo

logger = logging.getLogger("default")
volume_service = AppVolumeService()


class PropertiesChanges(object):
    # install_from_cloud do not need any more
    def __init__(self, service, tenant, install_from_cloud=False):
        self.service = service
        self.tenant = tenant
        self.current_version = None
        self.current_app = None
        self.template = None
        self.service_source = service_source_repo.get_service_source(service.tenant_id, service.service_id)
        self.install_from_cloud = False
        self.market_name = None
        self.market = None
        if self.service_source and self.service_source.extend_info:
            self.current_version_str = self.service_source.version
            extend_info = json.loads(self.service_source.extend_info)
            if extend_info and extend_info.get("install_from_cloud", False):
                self.install_from_cloud = True
            if self.install_from_cloud:
                self.market_name = extend_info.get("market_name", None)
                self.market = app_market_repo.get_app_market_by_name(
                    tenant.enterprise_id, self.market_name, raise_exception=True)
            self.__get_current_app_and_version()

    def __get_current_app_and_version(self):
        """
        :return:
        app object
        app_version object
        """
        group_id = service_group_relation_repo.get_group_id_by_service(self.service)
        service_ids = group_service_relation_repo.get_services_by_group(group_id).values_list("service_id", flat=True)
        service_sources = service_source_repo.get_service_sources(self.tenant.tenant_id, service_ids)
        versions = service_sources.exclude(version=None).values_list("version", flat=True)
        if versions:

            def foobar(y):
                try:
                    s = filter(str.isdigit, str(y))
                    return int(s)
                except ValueError:
                    # compatible with old version like 'RELEASE.2018-04-19T2'
                    return -1

            sorted_versions = sorted(versions, key=lambda x: map(foobar, x.split(".")))
            current_version = sorted_versions[-1]
            current_version_source = service_sources.filter(version=current_version).first()
        else:
            current_version = None
            current_version_source = None
        if not self.install_from_cloud:
            app, app_version = rainbond_app_repo.get_rainbond_app_and_version(self.tenant.enterprise_id,
                                                                              self.service_source.group_key, current_version)
        else:
            app, app_version = app_market_service.cloud_app_model_to_db_model(self.market, self.service_source.group_key,
                                                                              current_version)
        if app_version:
            self.template = json.loads(app_version.app_template)
            self.current_app = app
            self.current_version = app_version
            if current_version_source:
                self.service_source.create_time = current_version_source.create_time

    @property
    def get_upgradeable_versions(self):
        """
        对比过的，可升级的版本列表，通过对比upgrade_time对比
        :param current_version:
        :return:
        versions: [0.1, 0.2]

        """
        if not self.service_source:
            return None
        # not found current version
        if not self.current_version:
            return None
        upgradeble_versions = []
        group_id = service_group_relation_repo.get_group_id_by_service(self.service)
        services = group_service.get_rainbond_services(group_id, self.service_source.group_key)
        if not self.install_from_cloud:
            # 获取最新的时间列表, 判断版本号大小，TODO 确认版本号大小
            # 直接查出当前版本，对比时间，对比版本号大小
            app_versions = rainbond_app_repo.get_rainbond_app_versions(self.tenant.enterprise_id, self.service_source.group_key)
            if not app_versions:
                logger.debug("no app versions")
                return None

            for version in app_versions:
                new_version_time = time.mktime(version.update_time.timetuple())
                current_version_time = time.mktime(self.service_source.create_time.timetuple())
                same, max_version = self.checkVersionG2(self.current_version.version, version.version)
                if not same and max_version != self.current_version.version:
                    upgradeble_versions.append(version.version)
                elif same and new_version_time > current_version_time:
                    if self.have_upgrade_info(self.tenant, services, version.version):
                        upgradeble_versions.append(version.version)

        else:
            app_version_list = app_market_service.get_market_app_model_versions(self.market, self.service_source.group_key)
            if not app_version_list:
                return None
            for version in app_version_list:
                new_version_time = time.mktime(version.update_time.timetuple())
                current_version_time = time.mktime(self.current_version.update_time.timetuple())
                same, max_version = self.checkVersionG2(self.current_version.version, version.version)
                if not same and max_version != self.current_version.version:
                    upgradeble_versions.append(version.version)
                elif same and new_version_time > current_version_time:
                    if self.have_upgrade_info(self.tenant, services, version.version):
                        upgradeble_versions.append(version.version)
        return upgradeble_versions

    def have_upgrade_info(self, tenant, services, version):
        from console.services.upgrade_services import upgrade_service
        if not services:
            return False
        for service in services:
            upgrade_info = upgrade_service.get_service_changes(service, tenant, version)
            if upgrade_info:
                return True
        return False

    def checkVersionG2(self, currentversion, expectedversion):
        same = False
        versions = [currentversion, expectedversion]
        sort_versions = sorted(versions, key=lambda x: map(lambda y: int(filter(str.isdigit, str(y))), x.split(".")))
        max_version = sort_versions.pop()
        if currentversion == expectedversion:
            same = True
        return same, max_version

    # This method should be passed in to the app model, which is not necessarily derived from the local database
    # This method should not rely on database resources
    def get_property_changes(self, component=None, plugins=None, level="svc", template=None):
        # when modifying the following properties, you need to
        # synchronize the method 'properties_changes.has_changes'
        if not component:
            return None
        # not found current version
        if not self.current_version:
            return None
        self.plugins = plugins
        result = {}
        deploy_version = self.deploy_version_changes(component.get("deploy_version"))
        if deploy_version:
            result["deploy_version"] = deploy_version
        # source code service does not have 'share_image'
        image = self.image_changes(component.get("share_image", None))
        if image:
            result["image"] = image
        slug_path = self.slug_path_changes(component.get("share_slug_path", None))
        if slug_path:
            result["slug_path"] = slug_path
        envs = self.env_changes(component.get("service_env_map_list", []))
        if envs:
            result["envs"] = envs
        ports = self.port_changes(component.get("port_map_list", []))
        if ports:
            result["ports"] = ports
        connect_infos = self.env_changes(component.get("service_connect_info_map_list", []))
        if connect_infos:
            result["connect_infos"] = connect_infos
        volumes = self.volume_changes(component.get("service_volume_map_list", []))
        if volumes:
            result["volumes"] = volumes
        probe = self.probe_changes(component["probes"])
        if probe:
            result["probe"] = probe
        dep_uuids = []
        if component.get("dep_service_map_list", []):
            dep_uuids = [item["dep_service_key"] for item in component.get("dep_service_map_list")]
        dep_services = self.dep_services_changes(component, dep_uuids, level)
        if dep_services:
            result["dep_services"] = dep_services
        dep_volumes = self.dep_volumes_changes(component.get("mnt_relation_list", []))
        if dep_volumes:
            result["dep_volumes"] = dep_volumes

        plugins = self.plugin_changes(component.get("service_related_plugin_config", []))
        if plugins:
            logger.debug("plugin changes: {}".format(json.dumps(plugins)))
            result["plugins"] = plugins

        app_config_groups = self.app_config_group_changes(component, template)
        if app_config_groups:
            logger.debug("app_config_groups changes: {}".format(json.dumps(app_config_groups)))
            result["app_config_groups"] = app_config_groups

        component_graphs = self.component_graph_changes(component.get("component_graphs", []))
        if component_graphs:
            result["component_graphs"] = component_graphs

        component_monitors = self.component_monitor_changes(component.get("component_monitors", []))
        if component_monitors:
            result["component_monitors"] = component_monitors

        return result

    def app_config_group_changes(self, component, template):
        if not template.get("app_config_groups"):
            return None
        add = []
        # 从数据库获取对当前组件生效的配置组
        old_cgroups = share_service.config_groups(self.service.service_region, [self.service.service_id])
        old_cgroups_name_items = {cgroup["name"]: cgroup["config_items"] for cgroup in old_cgroups}
        for app_config_group in template["app_config_groups"]:
            # 如果当前组件模版中的组件ID不在应用配置组模版包含的生效组件中,跳过该配置组
            if component["service_id"] not in app_config_group["component_ids"]:
                continue
            # 如果模版中的配置组名不存在，记录下变更信息, 修改生效组件ID
            app_config_group["component_ids"] = []
            if not old_cgroups_name_items.get(app_config_group["name"]):
                app_config_group["component_ids"].append(self.service.service_id)
                add.append(app_config_group)
                continue
            # 配置组存在，则比较配置项
            new_items = {}
            for item_key in app_config_group["config_items"]:
                if not old_cgroups_name_items[app_config_group["name"]].get(item_key, ""):
                    new_items.update({item_key: app_config_group["config_items"][item_key]})
            if new_items:
                app_config_group["component_ids"].append(self.service.service_id)
                app_config_group["config_items"] = new_items
                add.append(app_config_group)
        if not add:
            return None
        return {"add": add}

    def component_graph_changes(self, component_graphs):
        if not component_graphs:
            return None

        old_graphs = component_graph_repo.list(self.service.service_id)
        old_promqls = [graph.promql for graph in old_graphs if old_graphs]
        add = []
        for graph in component_graphs:
            try:
                new_promql = promql_service.add_or_update_label(self.service.service_id, graph.get("promql"))
            except AbortRequest as e:
                logger.warning("promql: {}, {}".format(graph.get("promql"), e))
                continue
            if new_promql not in old_promqls:
                add.append(graph)
        if not add:
            return None
        return {"add": add}

    def component_monitor_changes(self, service_monitors):
        if not service_monitors:
            return None
        add = []
        old_monitors = service_monitor_repo.list_by_service_ids(self.tenant.tenant_id, [self.service.service_id])
        old_monitor_names = [monitor.name for monitor in old_monitors if old_monitors]
        for monitor in service_monitors:
            tenant_monitor = service_monitor_repo.get_tenant_service_monitor(self.tenant.tenant_id, monitor["name"])
            if not tenant_monitor and monitor["name"] not in old_monitor_names:
                add.append(monitor)

        if not add:
            return None
        return {"add": add}

    def env_changes(self, envs):
        """
        Environment variables are only allowed to increase, not allowed to
        update and delete. Compare existing environment variables and input
        environment variables to find out which ones need to be added.
        """
        exist_envs = env_var_repo.get_service_env(self.service.tenant_id, self.service.service_id)
        exist_envs_dict = {env.attr_name: env for env in exist_envs}
        add_env = [env for env in envs if exist_envs_dict.get(env["attr_name"], None) is None]
        if not add_env:
            return None
        return {"add": add_env}

    def deploy_version_changes(self, new):
        """
        compare the old and new deploy versions to determine if there is any change
        """
        # deploy_version is Build the app version of the source
        if not new:
            return None
        is_change = self.service.deploy_version < new
        if not is_change:
            return None
        return {"old": self.service.deploy_version, "new": new, "is_change": is_change}

    def app_version_changes(self, new):
        """
        compare the old and new application versions to determine if there is any change.
        application means application from market.
        """
        if self.service_source.version == new:
            return None
        return {"old": self.service_source.version, "new": new, "is_change": self.service_source.version != new}

    def image_changes(self, new):
        """
        compare the old and new image to determine if there is any change.
        """
        if new is None or self.service.image == new:
            return None
        # goodrain.me/bjlaezp3/nginx:20190516112845_v1.0
        if new.rpartition("_")[0] == self.service.image.rpartition("_")[0]:
            return None
        return {"old": self.service.image, "new": new, "is_change": self.service.image != new}

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
        if old_slug_path.rpartition("_")[1] == new.rpartition("_")[1]:
            return None
        return {"old": old_slug_path, "new": new, "is_change": old_slug_path != new}

    def dep_services_changes(self, apps, dep_uuids, level="svc"):
        """
        find out the dependencies that need to be created and
        the dependencies that need to be removed
        """
        dep_relations = dep_relation_repo.get_service_dependencies(self.service.tenant_id, self.service.service_id)
        service_ids = [item.dep_service_id for item in dep_relations]

        # get service_share_uuid by service_id
        service_share_uuids = service_source_repo.get_service_sources_by_service_ids(service_ids).values_list(
            "service_share_uuid", flat=True)

        group_id = service_group_relation_repo.get_group_id_by_service(self.service)
        # dep services from exist service
        new_dep_services = service_repo.list_by_svc_share_uuids(group_id, dep_uuids)
        if level == "app":
            exist_uuids = [svc["service_share_uuid"] for svc in new_dep_services]
            # dep services from apps
            # combine two types of dep_services
            for new_dep_service in self.new_dep_services_from_apps(apps, dep_uuids):
                if new_dep_service["service_share_uuid"] not in exist_uuids:
                    new_dep_services.append(new_dep_service)

        # filter existing dep services
        def dep_service_existed(service):
            if service.get("service_id", None) is None:
                return service["service_share_uuid"] in service_share_uuids
            return service["service_id"] in service_ids

        add = [svc for svc in new_dep_services if not dep_service_existed(svc)]
        if not add:
            return None
        return {
            "add": add,
        }

    def new_dep_services_from_apps(self, apps, dep_uuids):
        result = []
        if not apps:
            return None
        for dep_service in apps["dep_service_map_list"]:
            service_share_uuid = dep_service.get("dep_service_key")
            if service_share_uuid not in dep_uuids:
                continue
            result.append({"service_share_uuid": service_share_uuid, "service_cname": apps["service_cname"]})
        return result

    def port_changes(self, new_ports):
        """port can only be created, cannot be updated and deleted"""
        old_ports = port_repo.get_service_ports(self.service.tenant_id, self.service.service_id)
        old_container_ports = {port.container_port: port for port in old_ports}
        create_ports = [port for port in new_ports if port["container_port"] not in old_container_ports]
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
        old_volumes = volume_repo.get_service_volumes_with_config_file(self.service.service_id)
        old_volume_paths = {volume.volume_path: volume for volume in old_volumes}
        add = []
        update = []
        for new_volume in new_volumes:
            old_volume = old_volume_paths.get(new_volume["volume_path"], None)
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
        if not new_plugins:
            return None
        old_plugins, _ = app_plugin_service.get_plugins_by_service_id(self.service.service_region, self.service.tenant_id,
                                                                      self.service.service_id, "")
        if not old_plugins:
            return None
        old_plugin_keys = {item.origin_share_id: item for item in old_plugins}
        new_plugin_keys = {item["plugin_key"]: item for item in new_plugins}

        plugin_names = {}
        if self.plugins:
            plugin_names = {plugin["plugin_key"]: plugin["plugin_alias"] for plugin in self.plugins}

        add = []
        delete = []
        for new_plugin in new_plugins:
            if new_plugin["plugin_key"] in old_plugin_keys:
                continue
            new_plugin["plugin_alias"] = plugin_names.get(new_plugin["plugin_key"], new_plugin["plugin_key"])
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
            if key in new_probe.keys():
                new_probe.pop(key)
        old_probe = probe_repo.get_probe(self.service.service_id)
        if not old_probe:
            return {"add": new_probe, "upd": []}
        old_probe = old_probe.to_dict()
        for k, v in new_probe.items():
            if key in new_probe.keys() and old_probe[k] != v:
                logger.debug("found a change in the probe; key: {}; \
                    old value: {}; new value: {}".format(k, v, old_probe[k]))
                return {"add": [], "upd": new_probe}
        return None

    def dep_volumes_changes(self, new_dep_volumes):
        def key(sid, mnt_name):
            logger.debug("sid: {}; mnt_name: {}".format(sid, mnt_name))
            return sid + "-" + mnt_name

        old_dep_volumes = mnt_repo.get_service_mnts(self.service.tenant_id, self.service.service_id)
        olds = {key(item.dep_service_id, item.mnt_name): item for item in old_dep_volumes}

        tenant_service_volumes = volume_repo.get_service_volumes(self.service.service_id)
        local_path = [item.volume_path for item in tenant_service_volumes]

        add = []
        for new_dep_volume in new_dep_volumes:
            dep_service = app_service.get_service_by_service_key(self.service, new_dep_volume["service_share_uuid"])
            logger.debug("dep_service: {}".format(dep_service))
            if dep_service is None:
                continue
            if olds.get(key(dep_service["service_id"], new_dep_volume["mnt_name"]), None):
                logger.debug("ignore dep volume: {}; dep volume exist.".format(
                    key(dep_service["service_id"], new_dep_volume["mnt_name"])))
                continue

            volume_service.check_volume_path(self.service, new_dep_volume["mnt_dir"], local_path=local_path)

            new_dep_volume["service_id"] = dep_service["service_id"]
            add.append(new_dep_volume)
        if not add:
            return None
        return {"add": add}


def has_changes(changes):
    def alpha(x):
        return x and x.get("is_change", None)

    def beta(x):
        return x and (x.get("add", None) or x.get("del", None) or x.get("upd", None))

    a = ["deploy_version", "app_version"]
    b = ["envs", "connect_infos", "ports", "probe", "volumes", "dep_services", "dep_volumes", "plugins"]

    for k, v in changes.items():
        if k in a and alpha(v):
            logger.debug("found a change; key: {}; value: {}".format(k, v))
            return True
        if k in b and beta(v):
            logger.debug("found a change; key: {}; value: {}".format(k, v))
            return True
    return False


def get_upgrade_app_version_template_app(tenant, version, pc):
    if pc.install_from_cloud:
        data = app_market_service.get_market_app_model_version(pc.market, pc.current_app.app_id, version, get_template=True)
        template = json.loads(data.template)
        apps = template.get("apps")

        def func(x):
            result = x.get("service_share_uuid", None) == pc.service_source.service_share_uuid \
                     or x.get("service_key", None) == pc.service_source.service_share_uuid
            return result

        app = next(iter(filter(lambda x: func(x), apps)), None)
    else:
        app = rbd_center_app_service.get_version_app(tenant.enterprise_id, version, pc.service_source)
    return app


def get_upgrade_app_template(tenant, version, pc):
    if pc.install_from_cloud:
        data = app_market_service.get_market_app_model_version(pc.market, pc.current_app.app_id, version, get_template=True)
        template = json.loads(data.template)
    else:
        data = rainbond_app_repo.get_enterpirse_app_by_key_and_version(tenant.enterprise_id, pc.service_source.group_key,
                                                                       version)
        template = json.loads(data.app_template)
    return template
