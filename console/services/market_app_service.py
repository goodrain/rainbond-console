# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import datetime
import json
import logging

from django.db import transaction
from django.db.models import Q

from console.constants import AppConstants
from console.enum.component_enum import ComponentType
from console.exception.main import MarketAppLost
from console.exception.main import RbdAppNotFound
from console.exception.main import ServiceHandleException
from console.models.main import RainbondCenterApp
from console.models.main import RainbondCenterAppVersion
from console.repositories.app import app_tag_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import extend_repo
from console.repositories.app_config import volume_repo
from console.repositories.base import BaseConnection
from console.repositories.group import tenant_service_group_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.plugin import plugin_repo
from console.repositories.share_repo import share_repo
from console.repositories.team_repo import team_repo
from console.services.app import app_service, app_market_service
from console.services.app_actions import app_manage_service
from console.services.app_actions.properties_changes import PropertiesChanges
from console.services.app_config import AppMntService
from console.services.app_config import env_var_service
from console.services.app_config import port_service
from console.services.app_config import probe_service
from console.services.app_config import volume_service
from console.services.app_config.app_relation_service import AppServiceRelationService
from console.services.group_service import group_service
from console.services.plugin import app_plugin_service
from console.services.plugin import plugin_config_service
from console.services.plugin import plugin_service
from console.services.plugin import plugin_version_service
from console.services.upgrade_services import upgrade_service
from console.services.user_services import user_services
from console.utils import slug_util
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantEnterprise
from www.models.main import TenantEnterpriseToken
from www.models.main import TenantServiceInfo
from www.models.plugin import ServicePluginConfigVar
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
baseService = BaseTenantService()
app_relation_service = AppServiceRelationService()
region_api = RegionInvokeApi()
mnt_service = AppMntService()


class MarketAppService(object):
    def install_service(self,
                        tenant,
                        region,
                        user,
                        group_id,
                        market_app,
                        market_app_version,
                        is_deploy,
                        install_from_cloud,
                        market_name=None):
        service_list = []
        service_key_dep_key_map = {}
        key_service_map = {}
        tenant_service_group = None
        service_probe_map = {}
        app_plugin_map = {}  # 新装组件对应的安装的插件映射
        old_new_id_map = {}  # 新旧组件映射关系
        try:
            app_templates = json.loads(market_app_version.app_template)
            apps = app_templates["apps"]
            tenant_service_group = self.__create_tenant_service_group(region, tenant.tenant_id, group_id, market_app.app_id,
                                                                      market_app_version.version, market_app.app_name)
            plugins = app_templates.get("plugins", [])
            if plugins:
                status, msg = self._create_plugin_for_tenant(region, user, tenant, plugins)
                if status != 200:
                    raise Exception(msg)

            app_map = {}
            for app in apps:
                app_map[app.get("service_share_uuid")] = app
                ts = self.__init_market_app(tenant, region, user, app, tenant_service_group.ID, install_from_cloud, market_name)
                # Record the application's installation source information
                service_source_data = {
                    "group_key":
                    market_app.app_id,
                    "version":
                    market_app_version.version,
                    "service_share_uuid":
                    app.get("service_share_uuid") if app.get("service_share_uuid", None) else app.get("service_key"),
                }
                service_source_repo.update_service_source(ts.tenant_id, ts.service_id, **service_source_data)
                group_service.add_service_to_group(tenant, region, group_id, ts.service_id)
                service_list.append(ts)
                old_new_id_map[app["service_id"]] = ts

                # 先保存env,再保存端口，因为端口需要处理env
                code, msg = self.__save_env(tenant, ts, app["service_env_map_list"], app["service_connect_info_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_port(tenant, ts, app["port_map_list"])
                if code != 200:
                    raise Exception(msg)
                self.__save_volume(tenant, ts, app["service_volume_map_list"])

                # 保存组件探针信息
                probe_infos = app.get("probes", None)
                if probe_infos:
                    service_probe_map[ts.service_id] = probe_infos

                self.__save_extend_info(ts, app["extend_method_map"])
                if app.get("service_share_uuid", None):
                    dep_apps_key = app.get("dep_service_map_list", None)
                    if dep_apps_key:
                        service_key_dep_key_map[app.get("service_share_uuid")] = dep_apps_key
                    key_service_map[app.get("service_share_uuid")] = ts
                else:
                    dep_apps_key = app.get("dep_service_map_list", None)
                    if dep_apps_key:
                        service_key_dep_key_map[ts.service_key] = dep_apps_key
                    key_service_map[ts.service_key] = ts
                app_plugin_map[ts.service_id] = app.get("service_related_plugin_config")

            # 保存依赖关系
            self.__save_service_deps(tenant, service_key_dep_key_map, key_service_map)

            # 数据中心创建组件
            new_service_list = self.__create_region_services(tenant, user, service_list, service_probe_map)
            # 创建组件插件
            self.__create_service_plugins(region, tenant, service_list, app_plugin_map, old_new_id_map)

            # dependent volume
            self.__create_dep_mnt(tenant, apps, app_map, key_service_map)

            events = []
            if is_deploy:
                # 部署所有组件
                events = self.__deploy_services(tenant, user, new_service_list)
            return tenant_service_group, events
        except Exception as e:
            logger.exception(e)
            if tenant_service_group:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(tenant_service_group.ID)
            for service in service_list:
                try:
                    app_manage_service.truncate_service(tenant, service)
                except Exception as le:
                    logger.exception(le)
            raise e

    def install_service_when_upgrade_app(self,
                                         tenant,
                                         region,
                                         user,
                                         group_id,
                                         market_app,
                                         old_app,
                                         services,
                                         is_deploy,
                                         install_from_cloud=False,
                                         market_name=None):
        service_list = []
        service_key_dep_key_map = {}
        key_service_map = {}
        tenant_service_group = None
        service_probe_map = {}
        app_plugin_map = {}  # 新装组件对应的安装的插件映射
        old_new_id_map = {}  # 新旧组件映射关系

        for service in services:
            service_share_uuid = service.service_source_info.service_share_uuid
            if service_share_uuid:
                key_service_map[service_share_uuid] = service
            else:
                key_service_map[service.service_key] = service

        app_map = {app.get('service_share_uuid'): app for app in json.loads(old_app.template)["apps"]}

        try:
            app_templates = json.loads(market_app.template)
            apps = app_templates["apps"]
            tenant_service_group = self.__create_tenant_service_group(region, tenant.tenant_id, group_id, market_app.app_id,
                                                                      market_app.version, market_app.app_name)

            status, msg = self._create_plugin_for_tenant(region, user, tenant, app_templates.get("plugins", []))
            if status != 200:
                raise Exception(msg)

            for app in apps:
                ts = self.__init_market_app(
                    tenant,
                    region,
                    user,
                    app,
                    tenant_service_group.ID,
                    install_from_cloud=install_from_cloud,
                    market_name=market_name)
                service_source_data = {
                    "group_key":
                    market_app.app_id,
                    "version":
                    market_app.version,
                    "service_share_uuid":
                    app.get("service_share_uuid") if app.get("service_share_uuid", None) else app.get("service_key")
                }
                service_source_repo.update_service_source(ts.tenant_id, ts.service_id, **service_source_data)
                group_service.add_service_to_group(tenant, region, group_id, ts.service_id)
                service_list.append(ts)
                old_new_id_map[app["service_id"]] = ts

                # 先保存env,再保存端口，因为端口需要处理env
                code, msg = self.__save_env(tenant, ts, app["service_env_map_list"], app["service_connect_info_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_port(tenant, ts, app["port_map_list"])
                if code != 200:
                    raise Exception(msg)
                self.__save_volume(tenant, ts, app["service_volume_map_list"])

                # 保存组件探针信息
                probe_infos = app.get("probes", None)
                if probe_infos:
                    service_probe_map[ts.service_id] = probe_infos

                self.__save_extend_info(ts, app["extend_method_map"])
                if app.get("service_share_uuid", None):
                    dep_apps_key = app.get("dep_service_map_list", None)
                    if dep_apps_key:
                        service_key_dep_key_map[app.get("service_share_uuid")] = dep_apps_key
                    key_service_map[app.get("service_share_uuid")] = ts
                else:
                    dep_apps_key = app.get("dep_service_map_list", None)
                    if dep_apps_key:
                        service_key_dep_key_map[ts.service_key] = dep_apps_key
                    key_service_map[ts.service_key] = ts
                app_plugin_map[ts.service_id] = app.get("service_related_plugin_config")

            # 数据中心创建组件
            new_service_list = self.__create_region_services(tenant, user, service_list, service_probe_map)
            # 创建组件插件
            for app in apps:
                service = old_new_id_map[app["service_id"]]
                plugins = app_plugin_map[service.service_id]
                self.__create_service_pluginsv2(tenant, service, market_app.version, plugins)

            events = {}
            if is_deploy:
                # 部署所有组件
                events = self.__deploy_services(tenant, user, new_service_list)
            return {
                "tenant_service_group": tenant_service_group,
                "events": events,
                "service_key_dep_key_map": service_key_dep_key_map,
                "key_service_map": key_service_map,
                "apps": apps,
                "app_map": app_map,
            }
        except Exception as e:
            logger.exception(e)
            if tenant_service_group:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(tenant_service_group.ID)
            for service in service_list:
                try:
                    app_manage_service.truncate_service(tenant, service)
                except Exception as le:
                    logger.exception(le)
            raise e

    def save_service_deps_when_upgrade_app(self, tenant, service_key_dep_key_map, key_service_map, apps, app_map):
        # 保存依赖关系
        self.__save_service_deps(tenant, service_key_dep_key_map, key_service_map)
        # dependent volume
        self.__create_dep_mnt(tenant, apps, app_map, key_service_map)

    def __create_dep_mnt(self, tenant, apps, app_map, key_service_map):
        for app in apps:
            # dependent volume
            dep_mnts = app.get("mnt_relation_list", None)
            service = key_service_map.get(app.get("service_share_uuid"))
            if dep_mnts:
                for item in dep_mnts:
                    dep_service = key_service_map.get(item["service_share_uuid"])
                    if not dep_service:
                        logger.info("Service share uuid: {}; dependent service not found".format(item["service_share_uuid"]))
                        continue
                    dep_app = app_map.get(item["service_share_uuid"])
                    if not dep_app:
                        logger.debug("Service share uuid: {}; ; app not found".format(item["service_share_uuid"]))
                        continue
                    volume_list = dep_app.get("service_volume_map_list")
                    if volume_list:
                        for volume in volume_list:
                            if volume["volume_name"] == item["mnt_name"]:
                                dep_volume = volume_repo.get_by_sid_name(dep_service.service_id, item["mnt_name"])
                                code, msg = mnt_service.add_service_mnt_relation(tenant, service, item["mnt_dir"], dep_volume)
                                if code != 200:
                                    logger.info("fail to mount relative volume: {}".format(msg))

    def __create_service_plugins(self, region, tenant, service_list, app_plugin_map, old_new_id_map):
        try:
            plugin_version_service.update_plugin_build_status(region, tenant)

            for service in service_list:
                plugins = app_plugin_map.get(service.service_id)
                if plugins:
                    for plugin_config in plugins:
                        plugin_key = plugin_config["plugin_key"]
                        p = plugin_repo.get_plugin_by_origin_share_id(tenant.tenant_id, plugin_key)
                        plugin_id = p[0].plugin_id
                        service_plugin_config_vars = plugin_config["attr"]
                        plugin_version = plugin_version_service.get_newest_plugin_version(tenant.tenant_id, plugin_id)
                        build_version = plugin_version.build_version

                        self.__save_service_config_values(service, plugin_id, build_version, service_plugin_config_vars,
                                                          old_new_id_map)

                        # 2.从console数据库取数据生成region数据
                        region_config = app_plugin_service.get_region_config_from_db(service, plugin_id, build_version)

                        data = dict()
                        data["plugin_id"] = plugin_id
                        data["switch"] = True
                        data["version_id"] = build_version
                        data.update(region_config)
                        app_plugin_service.create_service_plugin_relation(tenant.tenant_id, service.service_id, plugin_id,
                                                                          build_version)

                        region_api.install_service_plugin(service.service_region, tenant.tenant_name, service.service_alias,
                                                          data)

        except Exception as e:
            logger.exception(e)

    def __create_service_pluginsv2(self, tenant, service, version, plugins):
        try:
            app_plugin_service.create_plugin_4marketsvc(tenant.region, tenant, service, version, plugins)
        except ServiceHandleException as e:
            logger.warning("plugin data: {}; failed to create plugin: {}", plugins, e)

    def __save_service_config_values(self, service, plugin_id, build_version, service_plugin_config_vars, old_new_id_map):
        config_list = []

        for config in service_plugin_config_vars:
            dest_service_id, dest_service_alias = "", ""
            if config["service_meta_type"] == "downstream_port":
                ts = old_new_id_map[config["dest_service_id"]]
                if ts:
                    dest_service_id, dest_service_alias = ts.service_id, ts.service_alias
            config_list.append(
                ServicePluginConfigVar(
                    service_id=service.service_id,
                    plugin_id=plugin_id,
                    build_version=build_version,
                    service_meta_type=config["service_meta_type"],
                    injection=config["injection"],
                    dest_service_id=dest_service_id,
                    dest_service_alias=dest_service_alias,
                    container_port=config["container_port"],
                    attrs=config["attrs"],
                    protocol=config["protocol"]))
        ServicePluginConfigVar.objects.bulk_create(config_list)

    def _create_plugin_for_tenant(self, region_name, user, tenant, plugins):
        for plugin in plugins:
            # 对需要安装的插件查看本地是否有安装
            tenant_plugin = plugin_repo.get_plugin_by_origin_share_id(tenant.tenant_id, plugin["plugin_key"])
            # 如果本地没有安装，进行安装操作
            if not tenant_plugin:
                try:
                    status, msg = self.__install_plugin(region_name, user, tenant, plugin)
                    if status != 200:
                        return status, msg
                except Exception as e:
                    logger.exception(e)
                    return 500, "create plugin error"
        return 200, "success"

    def __install_plugin(self, region_name, user, tenant, plugin_template):
        image = None
        image_tag = None
        if plugin_template["share_image"]:
            image_and_tag = plugin_template["share_image"].rsplit(":", 1)
            if len(image_and_tag) > 1:
                image = image_and_tag[0]
                image_tag = image_and_tag[1]
            else:
                image = image_and_tag[0]
                image_tag = "latest"

        plugin_params = {
            "tenant_id": tenant.tenant_id,
            "region": region_name,
            "create_user": user.user_id,
            "desc": plugin_template["desc"],
            "plugin_alias": plugin_template["plugin_alias"],
            "category": plugin_template["category"],
            "build_source": "image",
            "image": image,
            "code_repo": plugin_template["code_repo"],
            "username": "",
            "password": ""
        }
        status, msg, plugin_base_info = plugin_service.create_tenant_plugin(plugin_params)
        if status != 200:
            return status, msg

        plugin_base_info.origin = 'local_market'
        plugin_base_info.origin_share_id = plugin_template.get("plugin_key")
        plugin_base_info.save()

        build_version = plugin_template.get('build_version')
        min_memory = plugin_template.get('min_memory', 128)

        plugin_build_version = plugin_version_service.create_build_version(
            region_name,
            plugin_base_info.plugin_id,
            tenant.tenant_id,
            user.user_id,
            "",
            "unbuild",
            min_memory,
            image_tag=image_tag,
            code_version="",
            build_version=build_version)

        share_config_groups = plugin_template.get('config_groups', [])

        plugin_config_service.create_config_groups(plugin_base_info.plugin_id, build_version, share_config_groups)

        event_id = make_uuid()
        plugin_build_version.event_id = event_id
        plugin_build_version.plugin_version_status = "fixed"

        plugin_service.create_region_plugin(region_name, tenant, plugin_base_info, image_tag=image_tag)

        ret = plugin_service.build_plugin(region_name, plugin_base_info, plugin_build_version, user, tenant, event_id,
                                          plugin_template.get("plugin_image", None))
        plugin_build_version.build_status = ret.get('bean').get('status')
        plugin_build_version.save()
        return 200, "success"

    def __create_tenant_service_group(self, region, tenant_id, group_id, app_key, app_version, app_name):
        group_name = self.__generator_group_name("gr")
        params = {
            "tenant_id": tenant_id,
            "group_name": group_name,
            "group_alias": app_name,
            "group_key": app_key,
            "group_version": app_version,
            "region_name": region,
            "service_group_id": 0 if group_id == -1 else group_id
        }
        return tenant_service_group_repo.create_tenant_service_group(**params)

    def __generator_group_name(self, group_name):
        return '_'.join([group_name, make_uuid()[-4:]])

    def __create_region_services(self, tenant, user, service_list, service_probe_map):
        service_prob_id_map = {}
        new_service_list = []
        try:
            for service in service_list:
                # 数据中心创建组件
                new_service = app_service.create_region_service(tenant, service, user.nick_name)
                # 为组件添加探针
                probe_data = service_probe_map.get(service.service_id)
                probe_ids = []
                if probe_data:
                    for data in probe_data:
                        code, msg, probe = probe_service.add_service_probe(tenant, service, data)
                        if code == 200:
                            probe_ids.append(probe.probe_id)
                else:
                    code, msg, probe = app_service.add_service_default_porbe(tenant, service)
                    if probe:
                        probe_ids.append(probe.probe_id)
                if probe_ids:
                    service_prob_id_map[service.service_id] = probe_ids

                new_service_list.append(new_service)
            return new_service_list
        except Exception as e:
            logger.exception("local market install app error {0}".format(e))
            if service_list:
                for service in service_list:
                    if service_prob_id_map:
                        probe_ids = service_prob_id_map.get(service.service_id)
                        if probe_ids:
                            for probe_id in probe_ids:
                                try:
                                    probe_service.delete_service_probe(tenant, service, probe_id)
                                except Exception as le:
                                    logger.exception("local market install app delete service probe {0}".format(le))
            raise e

    def __deploy_services(self, tenant, user, service_list):
        try:
            body = dict()
            code, data = app_manage_service.deploy_services_info(body, service_list, tenant, user, oauth_instance=None)
            if code == 200:
                # 获取数据中心信息
                one_service = service_list[0]
                region_name = one_service.service_region
                try:
                    _, body = region_api.batch_operation_service(region_name, tenant.tenant_name, data)
                    result = body["bean"]["batche_result"]
                    events = {item.event_id: item.service_id for item in result}
                    return events
                except region_api.CallApiError as e:
                    logger.debug(data)
                    logger.exception(e)
                    return {}
        except Exception as e:
            logger.exception("batch deploy service error {0}".format(e))
            return {}

    def __save_service_deps(self, tenant, service_key_dep_key_map, key_service_map):
        if service_key_dep_key_map:
            for service_key in service_key_dep_key_map.keys():
                ts = key_service_map[service_key]
                dep_keys = service_key_dep_key_map[service_key]
                for dep_key in dep_keys:
                    dep_service = key_service_map[dep_key["dep_service_key"]]
                    code, msg, d = app_relation_service.add_service_dependency(tenant, ts, dep_service.service_id)
                    if code != 200:
                        logger.error("compose add service error {0}".format(msg))
                        return code, msg
        return 200, "success"

    def __save_env(self, tenant, service, inner_envs, outer_envs):
        if not inner_envs and not outer_envs:
            return 200, "success"
        for env in inner_envs:
            code, msg, env_data = env_var_service.add_service_env_var(tenant, service, 0, env["name"], env["attr_name"],
                                                                      env["attr_value"], env["is_change"], "inner")
            if code != 200:
                logger.error("save market app env error {0}".format(msg))
                return code, msg
        for env in outer_envs:
            container_port = env.get("container_port", 0)
            if container_port == 0:
                if env["attr_value"] == "**None**":
                    env["attr_value"] = service.service_id[:8]
                code, msg, env_data = env_var_service.add_service_env_var(tenant, service, container_port, env["name"],
                                                                          env["attr_name"], env["attr_value"], env["is_change"],
                                                                          "outer")
                if code != 200:
                    logger.error("save market app env error {0}".format(msg))
                    return code, msg
        return 200, "success"

    def __save_port(self, tenant, service, ports):
        if not ports:
            return 200, "success"
        for port in ports:
            code, msg, port_data = port_service.add_service_port(tenant, service, int(port["container_port"]), port["protocol"],
                                                                 port["port_alias"], port["is_inner_service"],
                                                                 port["is_outer_service"])
            if code != 200:
                logger.error("save market app port error: {}".format(msg))
                return code, msg
        return 200, "success"

    def __save_volume(self, tenant, service, volumes):
        if not volumes:
            return 200, "success"
        for volume in volumes:
            if "file_content" in volume.keys() and volume["file_content"] != "":
                volume_service.add_service_volume(tenant, service, volume["volume_path"], volume["volume_type"],
                                                  volume["volume_name"], volume["file_content"])
            else:
                settings = volume_service.get_best_suitable_volume_settings(tenant, service, volume["volume_type"],
                                                                            volume.get("access_mode"),
                                                                            volume.get("share_policy"),
                                                                            volume.get("backup_policy"), None,
                                                                            volume.get("volume_provider_name"))
                if settings["changed"]:
                    logger.debug('volume type changed from {0} to {1}'.format(volume["volume_type"], settings["volume_type"]))
                    volume["volume_type"] = settings["volume_type"]
                    if volume["volume_type"] == "share-file":
                        volume["volume_capacity"] = 0
                else:
                    settings["volume_capacity"] = volume.get("volume_capacity", 0)
                volume_service.add_service_volume(tenant, service, volume["volume_path"], volume["volume_type"],
                                                  volume["volume_name"], None, settings)

    def __save_extend_info(self, service, extend_info):
        if not extend_info:
            return 200, "success"
        params = {
            "service_key": service.service_key,
            "app_version": service.version,
            "min_node": extend_info["min_node"],
            "max_node": extend_info["max_node"],
            "step_node": extend_info["step_node"],
            "min_memory": extend_info["min_memory"],
            "max_memory": extend_info["max_memory"],
            "step_memory": extend_info["step_memory"],
            "is_restart": extend_info["is_restart"]
        }
        extend_repo.create_extend_method(**params)

    def __init_market_app(self, tenant, region, user, app, tenant_service_group_id, install_from_cloud=False, market_name=None):
        """
        初始化应用市场创建的应用默认数据
        """
        # 判断分享类型是否为slug包
        share_type = app.get("share_type")
        if share_type:
            is_slug = bool(share_type == "slug")
        else:
            is_slug = bool(slug_util.is_slug(app["image"], app["language"]))

        tenant_service = TenantServiceInfo()
        tenant_service.tenant_id = tenant.tenant_id
        tenant_service.service_id = make_uuid()
        tenant_service.service_cname = app["service_cname"]
        tenant_service.service_alias = "gr" + tenant_service.service_id[-6:]
        tenant_service.creater = user.pk
        if is_slug:
            tenant_service.image = app["image"]
        else:
            tenant_service.image = app.get("share_image", app["image"])
        tenant_service.cmd = app.get("cmd", "")
        tenant_service.service_region = region
        tenant_service.service_key = app["service_key"]
        tenant_service.desc = "market app "
        tenant_service.category = "app_publish"
        tenant_service.setting = ""
        # handle service type
        extend_method = app["extend_method"]
        if extend_method:
            if extend_method == "state":
                tenant_service.extend_method = ComponentType.state_multiple.value
            elif extend_method == "stateless":
                tenant_service.extend_method = ComponentType.stateless_multiple.value
            else:
                tenant_service.extend_method = extend_method

        tenant_service.env = ","
        tenant_service.min_node = app["extend_method_map"]["min_node"]
        tenant_service.min_memory = app["extend_method_map"]["min_memory"]
        tenant_service.min_cpu = baseService.calculate_service_cpu(region, tenant_service.min_memory)
        tenant_service.inner_port = 0
        tenant_service.version = app["version"]
        if is_slug:
            if app.get("service_slug", None):
                tenant_service.namespace = app["service_slug"]["namespace"]
        else:
            if app.get("service_image", None):
                tenant_service.namespace = app["service_image"]["namespace"]
        tenant_service.update_version = 1
        tenant_service.port_type = "multi_outer"
        tenant_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = app["deploy_version"]
        tenant_service.git_project_id = 0
        tenant_service.service_type = "application"
        tenant_service.total_memory = tenant_service.min_node * tenant_service.min_memory
        tenant_service.volume_mount_path = ""
        tenant_service.host_path = ""
        tenant_service.code_from = ""
        tenant_service.language = ""
        tenant_service.service_source = AppConstants.MARKET
        tenant_service.create_status = "creating"
        tenant_service.tenant_service_group_id = tenant_service_group_id
        self.__init_service_source(tenant_service, app, install_from_cloud, market_name)
        # 存储并返回
        tenant_service.save()
        return tenant_service

    def save_max_node_in_extend_method(self, service_key, app):
        extend_method_obj = share_repo.get_service_extend_method_by_key(service_key)
        if extend_method_obj:
            for ex_me in extend_method_obj:
                if app["extend_method_map"]["max_node"]:
                    ex_me.max_node = app["extend_method_map"]["max_node"]
                    ex_me.save()

    def __init_service_source(self, ts, app, install_from_cloud=False, market_name=None):
        slug = app.get("service_slug", None)
        extend_info = {}
        if slug:
            extend_info = slug
            extend_info["slug_path"] = app.get("share_slug_path", "")
        else:
            extend_info = app.get("service_image")
        extend_info["source_deploy_version"] = app.get("deploy_version")
        extend_info["source_service_share_uuid"] = app.get("service_share_uuid") if app.get(
            "service_share_uuid", None) else app.get("service_key", "")
        if install_from_cloud:
            extend_info["install_from_cloud"] = True
            extend_info["market"] = "default"
            extend_info["market_name"] = market_name
        service_source_params = {
            "team_id": ts.tenant_id,
            "service_id": ts.service_id,
            "user_name": "",
            "password": "",
            "extend_info": json.dumps(extend_info)
        }
        service_source_repo.create_service_source(**service_source_params)

    def get_visiable_apps(self, user, eid, scope, app_name, tag_names=None, is_complete=True, page=1, page_size=10):
        if scope == "team":
            # prepare teams
            is_admin = user_services.is_user_admin_in_current_enterprise(user, eid)
            if is_admin:
                teams = team_repo.get_team_by_enterprise_id(eid)
            else:
                teams = team_repo.get_tenants_by_user_id(user.user_id)
            if teams:
                teams = [team.tenant_name for team in teams]
            apps = rainbond_app_repo.get_rainbond_app_in_teams_by_querey(eid, teams, app_name, tag_names, page, page_size)
            count = rainbond_app_repo.get_rainbond_app_total_count(eid, "team", teams, app_name, tag_names)
        else:
            # default scope is enterprise
            apps = rainbond_app_repo.get_rainbond_app_in_enterprise_by_query(eid, app_name, tag_names, page, page_size)
            count = rainbond_app_repo.get_rainbond_app_total_count(eid, "enterprise", None, app_name, tag_names)
        if not apps:
            return [], count[0].total

        self._patch_rainbond_app_tag(eid, apps)
        self._patch_rainbond_app_versions(eid, apps, is_complete)
        return apps, count[0].total

    # patch rainbond app tag
    def _patch_rainbond_app_tag(self, eid, apps):
        app_ids = [app.app_id for app in apps]
        tags = app_tag_repo.get_multi_apps_tags(eid, app_ids)
        if not tags:
            return
        app_with_tags = dict()
        for tag in tags:
            if not app_with_tags.get(tag.app_id):
                app_with_tags[tag.app_id] = []
            app_with_tags[tag.app_id].append({"tag_id": tag.ID, "name": tag.name})

        for app in apps:
            app.tags = app_with_tags.get(app.app_id)

    def _get_rainbond_app_min_memory(self, apps_model_versions):
        apps_min_memory = dict()
        for app_model_version in apps_model_versions:
            if not apps_min_memory.get(app_model_version.app_id):
                min_memory = 0
                try:
                    app_temp = json.loads(app_model_version.app_template)
                    for app in app_temp.get("apps"):
                        if app.get("extend_method_map"):
                            min_memory += int(app.get("extend_method_map").get("min_memory"))
                    apps_min_memory[app_model_version.app_id] = min_memory
                except ValueError:
                    apps_min_memory[app_model_version.app_id] = min_memory
        return apps_min_memory

    # patch rainbond app versions
    def _patch_rainbond_app_versions(self, eid, apps, is_complete=None):
        app_ids = [app.app_id for app in apps]
        versions = rainbond_app_repo.get_rainbond_app_version_by_app_ids(eid, app_ids, is_complete)
        if not versions:
            return

        app_with_versions = dict()
        for version in versions:
            if not app_with_versions.get(version.app_id):
                app_with_versions[version.app_id] = []
            version_info = {
                "is_complete": version.is_complete,
                "version": version.version,
                "version_alias": version.version_alias,
            }
            if version_info not in app_with_versions[version.app_id]:
                app_with_versions[version.app_id].append(version_info)
        apps_min_memory = self._get_rainbond_app_min_memory(versions)
        for app in apps:
            versions_info = app_with_versions.get(app.app_id)
            if versions_info:
                # sort rainbond app versions by version
                versions_info.sort(lambda x, y: cmp(x["version"], y["version"]))
            app.versions_info = versions_info
            app.min_memory = apps_min_memory.get(app.app_id, 0)

    def get_visiable_apps_v2(self, tenant, scope, app_name, dev_status, page, page_size):
        limit = ""
        where = 'WHERE A.is_complete=1 AND A.enterprise_id in ("public", "{}")'.format(tenant.enterprise_id)
        if scope:
            if scope == "team":
                where += ' AND A.share_team="{}"'.format(tenant.tenant_name)
            else:
                where += ' AND A.scope="{}"'.format(scope)
        else:
            where += ' AND ((A.share_team="{}") OR (A.scope in ("goodrain", "enterprise")))'.format(tenant.tenant_name)
        if app_name:
            where += ' AND A.group_name like "{}%"'.format(app_name)
        if dev_status:
            where += ' AND A.dev_status="{}"'.format(dev_status)
        if page is not None and page_size is not None:
            page = (page - 1) * page_size
            limit = "LIMIT {page}, {page_size}".format(page=page, page_size=page_size)
        sql = """
                SELECT
                    A.*,
                    CONCAT('[',
                        GROUP_CONCAT(
                        CONCAT('{"tag_id":"',C.ID,'"'),',',
                        CONCAT('"name":"',C.name),'"}')
                    ,']') as tags
                FROM rainbond_center_app A
                LEFT JOIN rainbond_center_app_tag_relation B
                ON A.group_key = B.group_key and A.enterprise_id = B.enterprise_id
                LEFT JOIN rainbond_center_app_tag C
                ON B.tag_id = C.ID
                """
        sql1 = """
                GROUP BY
                    A.group_key, A.version
                ORDER BY
                    A.create_time DESC
                """
        sql += where
        sql += sql1
        sql += limit
        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def get_current_team_shared_apps(self, enterprise_id, current_team_name):
        return rainbond_app_repo.get_current_enter_visable_apps(enterprise_id).filter(share_team=current_team_name)

    def get_current_enterprise_shared_apps(self, enterprise_id):
        tenants = team_repo.get_teams_by_enterprise_id(enterprise_id)
        tenant_names = [t.tenant_name for t in tenants]
        # 获取企业分享的应用，并且排除返回在团队内的
        return rainbond_app_repo.get_current_enter_visable_apps(enterprise_id).filter(share_team__in=tenant_names).exclude(
            scope="team")

    def get_public_market_shared_apps(self, enterprise_id):
        return rainbond_app_repo.get_current_enter_visable_apps(enterprise_id).filter(scope="goodrain")

    def get_team_visiable_apps(self, tenant):
        tenants = team_repo.get_teams_by_enterprise_id(tenant.enterprise_id)
        tenant_names = [t.tenant_name for t in tenants]
        public_apps = Q(scope="goodrain")
        enterprise_apps = Q(share_team__in=tenant_names, scope="enterprise")
        team_apps = Q(share_team=tenant.tenant_name, scope="team")

        return rainbond_app_repo.get_current_enter_visable_apps(
            tenant.enterprise_id).filter(public_apps | enterprise_apps | team_apps)

    def get_rain_bond_app_by_pk(self, pk):
        app = rainbond_app_repo.get_rainbond_app_by_id(pk)
        if not app:
            return 404, None
        return 200, app

    def check_market_service_info(self, tenant, service):
        app_not_found = MarketAppLost("当前云市应用已删除")
        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        if not service_source:
            logger.info("app has been delete on market:{0}".format(service.service_cname))
            raise app_not_found
        extend_info_str = service_source.extend_info
        extend_info = json.loads(extend_info_str)
        if not extend_info.get("install_from_cloud", False):
            rainbond_app, rainbond_app_version = market_app_service.get_rainbond_app_and_version(
                tenant.enterprise_id, service_source.group_key, service_source.version)
            if not rainbond_app or not rainbond_app_version:
                logger.info("app has been delete on market:{0}".format(service.service_cname))
                raise app_not_found
        else:
            # get from cloud
            try:
                market = app_market_service.get_app_market_by_name(
                    tenant.enterprise_id, extend_info.get("market_name"), raise_exception=True)
                resp = app_market_service.get_market_app_model_version(market, service_source.group_key, service_source.version)
                if not resp:
                    raise app_not_found
            except region_api.CallApiError as e:
                logger.exception("get market app failed: {0}".format(e))
                if e.status == 404:
                    raise app_not_found
                raise MarketAppLost("云市应用查询失败")

    def get_rainbond_app_and_version(self, enterprise_id, app_id, app_version):
        app, app_version = rainbond_app_repo.get_rainbond_app_and_version(enterprise_id, app_id, app_version)
        if not app or not app_version:
            raise RbdAppNotFound("未找到该应用")
        return app, app_version

    def get_rainbond_app_version(self, eid, app_id, app_version):
        app_versions = rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version(eid, app_id, app_version)
        if not app_versions:
            return None
        return app_versions

    def update_rainbond_app_install_num(self, enterprise_id, app_id, app_version):
        rainbond_app_repo.add_rainbond_install_num(enterprise_id, app_id, app_version)

    def get_service_app_from_cloud(self, tenant, group_key, group_version, service_source):
        extent_info = json.loads(service_source.extend_info)
        market = app_market_service.get_app_market_by_name(
            tenant.enterprise_id, extent_info.get("market_name"), raise_exception=True)
        _, market_app_version = app_market_service.cloud_app_model_to_db_model(market, group_key, group_version)
        if market_app_version:
            apps_template = json.loads(market_app_version.app_template)
            apps = apps_template.get("apps")

            def func(x):
                result = x.get("service_share_uuid", None) == service_source.service_share_uuid \
                    or x.get("service_key", None) == service_source.service_share_uuid
                return result

            app = next(iter(filter(lambda x: func(x), apps)), None)
        if app is None:
            fmt = "Group key: {0}; version: {1}; service_share_uuid: {2}; Rainbond app not found."
            raise RbdAppNotFound(fmt.format(service_source.group_key, group_version, service_source.service_share_uuid))
        return app

    def conversion_cloud_version_to_app(self, cloud_version):
        app = RainbondCenterApp(app_id=cloud_version.app_key_id, app_name="", source="cloud", scope="market")
        app_version = RainbondCenterAppVersion(
            app_id=cloud_version.app_key_id,
            version=cloud_version.app_version,
            share_user=0,
            record_id=0,
            source="cloud",
            scope="market",
            app_template=json.dumps(cloud_version.templete.to_dict()),
            is_complete=True,
            template_version=cloud_version.templete_version)
        return app, app_version

    def get_all_goodrain_market_apps(self, app_name, is_complete):
        if app_name:
            return rainbond_app_repo.get_all_rainbond_apps().filter(
                scope="goodrain", source="market", group_name__icontains=app_name)
        if is_complete:
            if is_complete == "true":
                return rainbond_app_repo.get_all_rainbond_apps().filter(scope="goodrain", source="market", is_complete=True)
            else:
                return rainbond_app_repo.get_all_rainbond_apps().filter(scope="goodrain", source="market", is_complete=False)
        return rainbond_app_repo.get_all_rainbond_apps().filter(scope="goodrain", source="market")

    def list_upgradeable_versions(self, tenant, service):
        pc = PropertiesChanges(service, tenant)
        upgradeable_versions = pc.get_upgradeable_versions
        if not upgradeable_versions:
            upgradeable_versions = []
        return upgradeable_versions

    def get_enterprise_access_token(self, enterprise_id, access_target):
        enter = TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        try:
            return TenantEnterpriseToken.objects.get(enterprise_id=enter.pk, access_target=access_target)
        except TenantEnterpriseToken.DoesNotExist:
            return None

    def get_market_apps_in_app(self, region, tenant, group):
        service_group_keys = set(group_service.get_group_service_sources(group.ID).values_list('group_key', flat=True))
        iterator = self.yield_app_info(service_group_keys, tenant, group)
        app_info_list = [app_info for app_info in iterator]
        return app_info_list

    def yield_app_info(self, services_app_model_ids, tenant, group):
        for services_app_model_id in services_app_model_ids:
            group_key = services_app_model_id
            group_name = None
            share_user = None
            share_team = None
            tenant_service_group_id = None
            pic = None
            source = None
            market_name = None
            describe = None
            enterprise_id = None
            is_official = None
            details = None
            min_memory = None
            services = group_service.get_rainbond_services(group.ID, group_key)
            for service in services:
                pc = PropertiesChanges(service, tenant)
                if not pc.current_app:
                    continue
                if pc.current_app.app_id == services_app_model_id:
                    group_name = pc.current_app.app_name
                    share_user = pc.current_app.create_user
                    share_team = pc.current_app.create_team
                    tenant_service_group_id = group.ID
                    pic = pc.current_app.pic
                    source = pc.current_app.source
                    market_name = pc.market_name
                    describe = pc.current_app.describe
                    enterprise_id = pc.current_app.enterprise_id
                    is_official = pc.current_app.is_official
                    details = pc.current_app.details
                    min_memory = group_service.get_service_group_memory(pc.template)
                    break
            if not pc.current_app or not pc.current_version:
                continue
            dat = {
                'group_key': group_key,
                'group_name': group_name,
                'app_model_name': group_name,
                'app_model_id': group_key,
                'share_user': share_user,
                'share_team': share_team,
                'tenant_service_group_id': tenant_service_group_id,
                'pic': pic,
                'source': source,
                'market_name': market_name,
                'describe': describe,
                'enterprise_id': enterprise_id,
                'is_official': is_official,
                'details': details,
                'min_memory': min_memory,
            }
            not_upgrade_record = upgrade_service.get_app_not_upgrade_record(tenant.tenant_id, group.ID, group_key)
            dat.update({
                'current_version': pc.current_version.version,
                'can_upgrade': bool(pc.get_upgradeable_versions),
                'upgrade_versions': (set(pc.get_upgradeable_versions) if pc.get_upgradeable_versions else []),
                'not_upgrade_record_id': not_upgrade_record.ID,
                'not_upgrade_record_status': not_upgrade_record.status,
            })
            yield dat

    def delete_rainbond_app_all_info_by_id(self, enterprise_id, app_id):
        sid = transaction.savepoint()
        try:
            rainbond_app_repo.delete_app_tag_by_id(enterprise_id, app_id)
            rainbond_app_repo.delete_app_version_by_id(enterprise_id, app_id)
            rainbond_app_repo.delete_app_by_id(enterprise_id, app_id)
            transaction.savepoint_commit(sid)
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)

    @transaction.atomic
    def update_rainbond_app(self, enterprise_id, app_id, app_info):
        app = rainbond_app_repo.get_rainbond_app_by_app_id(enterprise_id, app_id)
        if not app:
            raise RbdAppNotFound(msg="app not found")
        app.app_name = app_info.get("name")
        app.describe = app_info.get("describe")
        app.pic = app_info.get("pic")
        app.details = app_info.get("details")
        app.dev_status = app_info.get("dev_status")
        app_tag_repo.create_app_tags_relation(app, app_info.get("tag_ids"))
        app.scope = app_info.get("scope")
        if app.scope == "team":
            create_team = app_info.get("create_team")
            team = team_repo.get_team_by_team_name(create_team)
            if not team:
                raise ServiceHandleException(msg="can't get create team", msg_show="找不到团队")
            app.create_team = create_team
        app.save()

    @transaction.atomic
    def create_rainbond_app(self, enterprise_id, app_info):
        app_id = make_uuid()
        app = RainbondCenterApp(
            app_id=app_id,
            app_name=app_info.get("app_name"),
            create_user=app_info.get("create_user"),
            create_team=app_info.get("create_team"),
            pic=app_info.get("pic"),
            source=app_info.get("source"),
            dev_status=app_info.get("dev_status"),
            scope=app_info.get("scope"),
            describe=app_info.get("describe"),
            enterprise_id=enterprise_id,
            details=app_info.get("details"),
        )
        app.save()
        # save app and tag relation
        if app_info.get("tag_ids"):
            app_tag_repo.create_app_tags_relation(app, app_info.get("tag_ids"))


market_app_service = MarketAppService()
