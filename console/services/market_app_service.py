# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import datetime
import json
import logging

from django.db.models import Q

from console.constants import AppConstants
from console.repositories.app import service_source_repo, service_repo
from console.repositories.app_config import extend_repo
from console.repositories.group import tenant_service_group_repo
from console.repositories.market_app_repo import rainbond_app_repo, app_export_record_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from console.services.app_config import env_var_service, port_service, volume_service, label_service, probe_service
from console.services.app_config.app_relation_service import AppServiceRelationService
from console.services.group_service import group_service
from console.utils.timeutil import current_time_str
from www.apiclient.marketclient import MarketOpenAPI
from www.apiclient.regionapi import RegionInvokeApi
from www.models import TenantServiceInfo, PluginConfigGroup, PluginConfigItems, ServicePluginConfigVar
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid
from console.models.main import RainbondCenterApp
from console.services.common_services import common_services
from console.repositories.plugin import plugin_repo
from console.services.plugin import plugin_version_service, plugin_service, plugin_config_service, app_plugin_service
from console.repositories.share_repo import share_repo

logger = logging.getLogger("default")
baseService = BaseTenantService()
app_relation_service = AppServiceRelationService()
market_api = MarketOpenAPI()
region_api = RegionInvokeApi()


class MarketAppService(object):
    def install_service(self, tenant, region, user, group_id, market_app,
                        is_deploy):
        service_list = []
        service_key_dep_key_map = {}
        key_service_map = {}
        tenant_service_group = None
        service_probe_map = {}
        app_plugin_map = {}  # 新装服务对应的安装的插件映射
        old_new_id_map = {}  # 新旧服务映射关系
        try:
            app_templates = json.loads(market_app.app_template)
            apps = app_templates["apps"]
            tenant_service_group = self.__create_tenant_service_group(
                region, tenant.tenant_id, group_id, market_app.group_key,
                market_app.version, market_app.group_name)

            status, msg = self.__create_plugin_for_tenant(
                region, user, tenant, app_templates.get("plugins", []))
            if status != 200:
                raise Exception(msg)

            for app in apps:
                ts = self.__init_market_app(tenant, region, user, app,
                                            tenant_service_group.ID)
                group_service.add_service_to_group(tenant, region, group_id,
                                                   ts.service_id)
                service_list.append(ts)
                old_new_id_map[app["service_id"]] = ts

                # 先保存env,再保存端口，因为端口需要处理env
                code, msg = self.__save_env(
                    tenant, ts, app["service_env_map_list"],
                    app["service_connect_info_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_port(tenant, ts, app["port_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_volume(tenant, ts,
                                               app["service_volume_map_list"])
                if code != 200:
                    raise Exception(msg)

                # 保存应用探针信息
                probe_infos = app.get("probes", None)
                if probe_infos:
                    service_probe_map[ts.service_id] = probe_infos

                self.__save_extend_info(ts, app["extend_method_map"])
                if app.get("service_share_uuid", None):
                    dep_apps_key = app.get("dep_service_map_list", None)
                    if dep_apps_key:
                        service_key_dep_key_map[app.get(
                            "service_share_uuid")] = dep_apps_key
                    key_service_map[app.get("service_share_uuid")] = ts
                else:
                    dep_apps_key = app.get("dep_service_map_list", None)
                    if dep_apps_key:
                        service_key_dep_key_map[ts.service_key] = dep_apps_key
                    key_service_map[ts.service_key] = ts
                app_plugin_map[ts.service_id] = app.get(
                    "service_related_plugin_config")

            # 保存依赖关系
            self.__save_service_deps(tenant, service_key_dep_key_map,
                                     key_service_map)

            # 数据中心创建应用
            new_service_list = self.__create_region_services(
                tenant, user, service_list, service_probe_map)
            # 创建应用插件
            self.__create_service_plugins(region, tenant, service_list,
                                          app_plugin_map, old_new_id_map)
            if is_deploy:
                # 部署所有应用
                self.__deploy_services(tenant, user, new_service_list)
            return tenant_service_group
        except Exception as e:
            logger.exception(e)
            if tenant_service_group:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(
                    tenant_service_group.ID)
            for service in service_list:
                try:
                    app_manage_service.truncate_service(tenant, service)
                except Exception as le:
                    logger.exception(le)
            raise e

    def __create_service_plugins(self, region, tenant, service_list,
                                 app_plugin_map, old_new_id_map):
        try:
            plugin_version_service.update_plugin_build_status(region, tenant)

            for service in service_list:
                plugins = app_plugin_map.get(service.service_id)
                if plugins:
                    for plugin_config in plugins:
                        plugin_key = plugin_config["plugin_key"]
                        p = plugin_repo.get_plugin_by_origin_share_id(
                            tenant.tenant_id, plugin_key)
                        plugin_id = p[0].plugin_id
                        service_plugin_config_vars = plugin_config["attr"]
                        plugin_version = plugin_version_service.get_newest_plugin_version(
                            plugin_id)
                        build_version = plugin_version.build_version

                        self.__save_service_config_values(
                            service, plugin_id, build_version,
                            service_plugin_config_vars, old_new_id_map)

                        # 2.从console数据库取数据生成region数据
                        region_config = app_plugin_service.get_region_config_from_db(
                            service, plugin_id, build_version)

                        data = dict()
                        data["plugin_id"] = plugin_id
                        data["switch"] = True
                        data["version_id"] = build_version
                        data.update(region_config)
                        code, msg, relation = app_plugin_service.create_service_plugin_relation(
                            service.service_id, plugin_id, build_version, "",
                            True)
                        if code != 200:
                            raise Exception("msg")

                        region_api.install_service_plugin(
                            service.service_region, tenant.tenant_name,
                            service.service_alias, data)

        except Exception as e:
            logger.exception(e)

    def __save_service_config_values(self, service, plugin_id, build_version,
                                     service_plugin_config_vars,
                                     old_new_id_map):
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

    def __create_plugin_for_tenant(self, region_name, user, tenant, plugins):
        for plugin in plugins:
            # 对需要安装的插件查看本地是否有安装
            tenant_plugin = plugin_repo.get_plugin_by_origin_share_id(
                tenant.tenant_id, plugin["plugin_key"])
            # 如果本地没有安装，进行安装操作
            if not tenant_plugin:
                try:
                    status, msg = self.__install_plugin(
                        region_name, user, tenant, plugin)
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

        status, msg, plugin_base_info = plugin_service.create_tenant_plugin(
            tenant, user.user_id, region_name, plugin_template["desc"],
            plugin_template["plugin_alias"], plugin_template["category"],
            "image", image, plugin_template["code_repo"])
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

        plugin_config_service.create_config_groups(
            plugin_base_info.plugin_id, build_version, share_config_groups)

        event_id = make_uuid()
        plugin_build_version.event_id = event_id
        plugin_build_version.plugin_version_status = "fixed"

        plugin_service.create_region_plugin(
            region_name, tenant, plugin_base_info, image_tag=image_tag)

        ret = plugin_service.build_plugin(
            region_name, plugin_base_info, plugin_build_version, user, tenant,
            event_id, plugin_template.get("plugin_image", None))
        plugin_build_version.build_status = ret.get('bean').get('status')
        plugin_build_version.save()
        return 200, "success"

    def __create_tenant_service_group(self, region, tenant_id, group_id,
                                      group_key, group_version, group_alias):
        group_name = self.__generator_group_name("gr")
        params = {
            "tenant_id": tenant_id,
            "group_name": group_name,
            "group_alias": group_alias,
            "group_key": group_key,
            "group_version": group_version,
            "region_name": region,
            "service_group_id": 0 if group_id == -1 else group_id
        }
        return tenant_service_group_repo.create_tenant_service_group(**params)

    def __generator_group_name(self, group_name):
        return '_'.join([group_name, make_uuid()[-4:]])

    def __create_region_services(self, tenant, user, service_list,
                                 service_probe_map):
        service_prob_id_map = {}
        new_service_list = []
        try:
            for service in service_list:
                # 数据中心创建应用
                new_service = app_service.create_region_service(
                    tenant, service, user.nick_name)
                # 为服务添加探针
                probe_data = service_probe_map.get(service.service_id)
                probe_ids = []
                if probe_data:
                    for data in probe_data:
                        code, msg, probe = probe_service.add_service_probe(
                            tenant, service, data)
                        if code == 200:
                            probe_ids.append(probe.probe_id)
                else:
                    code, msg, probe = app_service.add_service_default_porbe(
                        tenant, service)
                    if probe:
                        probe_ids.append(probe.probe_id)
                if probe_ids:
                    service_prob_id_map[service.service_id] = probe_ids

                # 添加服务有无状态标签
                label_service.update_service_state_label(tenant, new_service)
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
                                    probe_service.delete_service_probe(
                                        tenant, service, probe_id)
                                except Exception as le:
                                    logger.exception(
                                        "local market install app delete service probe {0}"
                                        .format(le))
            raise e

    def __deploy_services(self, tenant, user, service_list):
        try:
            body = dict()
            code, data = app_manage_service.deploy_services_info(body, service_list, tenant, user)
            if code == 200:
                # 获取数据中心信息
                one_service = service_list[0]
                region_name = one_service.service_region
                try:
                    region_api.batch_operation_service(region_name, tenant.tenant_name, data)
                except region_api.CallApiError as e:
                    logger.exception(e)
        except Exception as e:
            logger.exception("batch deploy service error {0}".format(e))

    def __save_service_deps(self, tenant, service_key_dep_key_map,
                            key_service_map):
        if service_key_dep_key_map:
            for service_key in service_key_dep_key_map.keys():
                ts = key_service_map[service_key]
                dep_keys = service_key_dep_key_map[service_key]
                for dep_key in dep_keys:
                    dep_service = key_service_map[dep_key["dep_service_key"]]
                    code, msg, d = app_relation_service.add_service_dependency(
                        tenant, ts, dep_service.service_id)
                    if code != 200:
                        logger.error(
                            "compose add service error {0}".format(msg))
                        return code, msg
        return 200, "success"

    def __save_env(self, tenant, service, inner_envs, outer_envs):
        if not inner_envs and not outer_envs:
            return 200, "success"
        for env in inner_envs:
            code, msg, env_data = env_var_service.add_service_env_var(
                tenant, service, 0, env["name"], env["attr_name"],
                env["attr_value"], env["is_change"], "inner")
            if code != 200:
                logger.error("save market app env error {0}".format(msg))
                return code, msg
        for env in outer_envs:
            container_port = env.get("container_port", 0)
            if container_port == 0:
                if env["attr_value"] == "**None**":
                    env["attr_value"] = service.service_id[:8]
                code, msg, env_data = env_var_service.add_service_env_var(
                    tenant, service, container_port, env["name"],
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
            code, msg, port_data = port_service.add_service_port(
                tenant, service, int(port["container_port"]), port["protocol"],
                port["port_alias"], port["is_inner_service"],
                port["is_outer_service"])
            if code != 200:
                logger.error("save market app port error".format(msg))
                return code, msg
        return 200, "success"

    def __save_volume(self, tenant, service, volumes):
        if not volumes:
            return 200, "success"
        for volume in volumes:
            if "file_content" in volume.keys():
                code, msg, volume_data = volume_service.add_service_volume(
                    tenant, service, volume["volume_path"],
                    volume["volume_type"], volume["volume_name"],
                    volume["file_content"])
            else:
                code, msg, volume_data = volume_service.add_service_volume(
                    tenant, service, volume["volume_path"],
                    volume["volume_type"], volume["volume_name"])
            if code != 200:
                logger.error("save market app volume error".format(msg))
                return code, msg
        return 200, "success"

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

    def __init_market_app(self, tenant, region, user, app,
                          tenant_service_group_id):
        """
        初始化应用市场创建的应用默认数据
        """
        # 判断分享类型是否为slug包
        share_type = app.get("share_type")
        if share_type:
            is_slug = bool(share_type == "slug")
        else:
            is_slug = bool(app["image"].startswith('goodrain.me/runner')
                           and app["language"] not in ("dockerfile", "docker"))

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
        tenant_service.extend_method = app["extend_method"]
        tenant_service.env = ","
        tenant_service.min_node = app["extend_method_map"]["min_node"]
        tenant_service.min_memory = app["extend_method_map"]["min_memory"]
        tenant_service.min_cpu = baseService.calculate_service_cpu(
            region, tenant_service.min_memory)
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
        tenant_service.create_time = datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = ""
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
        self.__init_service_source(tenant_service, app)
        # 存储并返回
        tenant_service.save()
        return tenant_service

    def save_max_node_in_extend_method(self, service_key, app):
        extend_method_obj = share_repo.get_service_extend_method_by_key(
            service_key)
        if extend_method_obj:
            for ex_me in extend_method_obj:
                if app["extend_method_map"]["max_node"]:
                    ex_me.max_node = app["extend_method_map"]["max_node"]
                    ex_me.save()

    def __init_service_source(self, ts, app):
        is_slug = bool(
            ts.image.startswith('goodrain.me/runner')
            and app["language"] not in ("dockerfile", "docker"))
        if is_slug:
            extend_info = app["service_slug"]
            extend_info["slug_path"] = app.get("share_slug_path", "")
        else:
            extend_info = app["service_image"]
        extend_info["source_deploy_version"] = app.get("deploy_version")
        extend_info["source_service_share_uuid"] = app.get("service_share_uuid") if app.get("service_share_uuid", None)\
            else app.get("service_key", "")

        service_source_params = {
            "team_id": ts.tenant_id,
            "service_id": ts.service_id,
            "user_name": "",
            "password": "",
            "extend_info": json.dumps(extend_info)
        }
        service_source_repo.create_service_source(**service_source_params)

    def check_package_app_resource(self, tenant, region, market_app):
        app_templates = json.loads(market_app.app_template)
        apps = app_templates["apps"]
        total_memory = 0
        for app in apps:
            extend_method = app.get("extend_method_map", None)
            if not extend_method:
                min_node = 1
                min_memory = 128
            else:
                min_node = int(extend_method.get("min_node", 1))
                min_memory = int(extend_method.get("min_memory", 128))
            total_memory += min_node * min_memory
        allow_create, tips = app_service.verify_source(
            tenant, region, total_memory, "market_app_create")
        return allow_create, tips, total_memory

    def get_visiable_apps(self, tenant, scope, app_name):

        if scope == "team":
            rt_apps = self.get_current_team_shared_apps(
                tenant.enterprise_id, tenant.tenant_name)
        elif scope == "goodrain":
            rt_apps = self.get_public_market_shared_apps(tenant.enterprise_id)
        elif scope == "enterprise":
            rt_apps = self.get_current_enterprise_shared_apps(
                tenant.enterprise_id)
        else:
            rt_apps = self.get_team_visiable_apps(tenant)
        if app_name:
            rt_apps = rt_apps.filter(Q(group_name__icontains=app_name))
        return rt_apps

    def get_current_team_shared_apps(self, enterprise_id, current_team_name):
        return rainbond_app_repo.get_current_enter_visable_apps(
            enterprise_id).filter(share_team=current_team_name)

    def get_current_enterprise_shared_apps(self, enterprise_id):
        tenants = team_repo.get_teams_by_enterprise_id(enterprise_id)
        tenant_names = [t.tenant_name for t in tenants]
        # 获取企业分享的应用，并且排除返回在团队内的
        return rainbond_app_repo.get_current_enter_visable_apps(
            enterprise_id).filter(share_team__in=tenant_names).exclude(
                scope="team")

    def get_public_market_shared_apps(self, enterprise_id):
        return rainbond_app_repo.get_current_enter_visable_apps(
            enterprise_id).filter(scope="goodrain")

    def get_team_visiable_apps(self, tenant):
        tenants = team_repo.get_teams_by_enterprise_id(tenant.enterprise_id)
        tenant_names = [t.tenant_name for t in tenants]
        public_apps = Q(scope="goodrain")
        enterprise_apps = Q(share_team__in=tenant_names, scope="enterprise")
        team_apps = Q(share_team=tenant.tenant_name, scope="team")

        return rainbond_app_repo.get_current_enter_visable_apps(
            tenant.enterprise_id).filter(public_apps | enterprise_apps
                                         | team_apps)

    def get_rain_bond_app_by_pk(self, pk):
        app = rainbond_app_repo.get_rainbond_app_by_id(pk)
        if not app:
            return 404, None
        return 200, app

    def get_rain_bond_app_by_key_and_version(self, group_key, group_version):
        app = rainbond_app_repo.get_rainbond_app_by_key_and_version(group_key, group_version)
        if not app:
            return 404, None
        return 200, app

    def get_all_goodrain_market_apps(self, app_name, is_complete):
        if app_name:
            return rainbond_app_repo.get_all_rainbond_apps().filter(
                scope="goodrain",
                source="market",
                group_name__icontains=app_name)
        if is_complete:
            if is_complete == "true":
                return rainbond_app_repo.get_all_rainbond_apps().filter(
                    scope="goodrain", source="market", is_complete=True)
            else:
                return rainbond_app_repo.get_all_rainbond_apps().filter(
                    scope="goodrain", source="market", is_complete=False)
        return rainbond_app_repo.get_all_rainbond_apps().filter(
            scope="goodrain", source="market")

    def get_remote_market_apps(self, tenant, page, page_size, app_name):
        body = market_api.get_service_group_list(tenant.tenant_id, page,
                                                 page_size, app_name)
        remote_apps = body["data"]['list']
        total = body["data"]['total']
        # 创造数据格式app_list = [{group_key:xxx, "group_version_list":[]}, {}]
        app_list = []
        result_list = []
        group_key_list = []
        for app in remote_apps:
            if app["group_key"] not in group_key_list:
                group_key_list.append(app["group_key"])
        logger.debug('==========0=================0{0}'.format(group_key_list))
        if group_key_list:
            for group_key in group_key_list:
                app_dict = dict()
                group_version_list = []
                for app in remote_apps:
                    if app["group_key"] == group_key:
                        if app["group_version"] not in group_version_list:
                            group_version_list.append(app["group_version"])
                group_version_list.sort(reverse=True)
                logger.debug('----------group_version_list------__>{0}'.format(group_version_list))
                logger.debug('----------group_key------__>{0}'.format(group_key))

                for app in remote_apps:
                    if app["group_version"] == group_version_list[0] and app["group_key"] == group_key:
                        app_dict["group_key"] = group_key
                        app_dict["group_version_list"] = group_version_list
                        app_dict["update_version"] = app["update_version"]
                        app_dict["group_name"] = app["group_name"]
                        app_dict["pic"] = app["pic"]
                        app_dict["info"] = app["info"]
                        app_dict["template_version"] = app.get("template_version", "")
                        app_dict["is_official"] = app["is_official"]
                        app_dict["desc"] = app["desc"]
                        app_dict["update_version"] = app["update_version"]
                        app_list.append(app_dict)

        for app in app_list:
            rbc = rainbond_app_repo.get_enterpirse_app_by_key_and_version(tenant.enterprise_id, app["group_key"],
                                                                      app["group_version_list"][0])

            is_upgrade = 0
            is_complete = False
            if rbc:
                if rbc.is_complete:
                    is_complete = True
            if rbc and rbc.source != "local" and rbc.upgrade_time:
                # 判断云市应用是否有小版本更新
                try:
                    old_version = int(rbc.upgrade_time)
                    new_version = int(app["update_version"])
                    if old_version < new_version:
                        is_upgrade = 1
                except Exception as e:
                    logger.exception(e)
            rbapp = {
                "group_key": app["group_key"],
                "group_name": app["group_name"],
                "version": app["group_version_list"],
                "source": "market",
                "scope": "goodrain",
                "pic": app['pic'],
                "describe": app['info'],
                "template_version": app.get("template_version", ""),
                "is_complete": is_complete,
                "is_official": app["is_official"],
                "details": app["desc"],
                "upgrade_time": app["update_version"],
                "is_upgrade": is_upgrade
            }
            result_list.append(rbapp)
        return total, result_list

    def get_market_version_apps(self, tenant, app_name, group_key, version):
        body = market_api.get_service_group_list(tenant.tenant_id, 1, 20, app_name)
        remote_apps = body["data"]['list']
        total = body["data"]['total']
        result_list = []
        app_list = []
        for app in remote_apps:
            if app["group_key"] == group_key and app["group_version"] == version:
                app_list.append(app)
        if len(app_list) > 0:
            for app in app_list:
                rbc = rainbond_app_repo.get_enterpirse_app_by_key_and_version(tenant.enterprise_id, app["group_key"],
                                                                              app["group_version"])
                is_upgrade = 0
                is_complete = False
                if rbc:
                    if rbc.is_complete:
                        is_complete = True
                if rbc and rbc.source != "local" and rbc.upgrade_time:
                    # 判断云市应用是否有小版本更新
                    try:
                        old_version = int(rbc.upgrade_time)
                        new_version = int(app["update_version"])
                        if old_version < new_version:
                            is_upgrade = 1
                    except Exception as e:
                        logger.exception(e)
                rbapp = {
                    "group_key": app["group_key"],
                    "group_name": app["group_name"],
                    "version": app["group_version"],
                    "source": "market",
                    "scope": "goodrain",
                    "pic": app['pic'],
                    "describe": app['info'],
                    "template_version": app.get("template_version", ""),
                    "is_complete": is_complete,
                    "is_official": app["is_official"],
                    "details": app["desc"],
                    "upgrade_time": app["update_version"],
                    "is_upgrade": is_upgrade
                }
                result_list.append(rbapp)
        return total, result_list


class MarketTemplateTranslateService(object):
    # 需要特殊处理的service_key
    SPECIAL_PROCESS = (
        "mysql", "postgresql", "6f7edb496760bb1965bdce1135883b29",
        "2dd630b20396c26dc437fdcf2b98fb63", "eae2d4ba183a8e3c41f2239d1a687ce8",
        "df98c419c98cc6f1488fc83e13e0244a", "bf22929d36d217b77d27813e6ae1508b",
        "1fecc863b04c0cd24cee1403ba238f2e", "915cc8a5cd81f28aa7f0daba314204c2",
        "231c92c7fa4f7c1df76c889c84dcf4e7", "edde97105d55d4301b9cddf15e139981",
        "d261fa2e90c84131df33644ad0b6e5c5", "7045a899df1369f30e1adce1cbbeb15b",
        "45081d62105d2f18a487f06dabf9de6a", "efc18a5358b5dabb50fb813f5d46458b",
        "711657b065fa265c17a8fd265c32ec5b", "eefca5b538fb6cf7d187b738e7fe035e",
        "88064c83f0e5a6a5c9b73b57dbb0d6ff", "88bd3a92b128445af53923ee2edc975c")

    def v1_to_v2(self, old_templete, region=""):
        """旧版本模板转换为新版本数据"""
        new_templet = dict()
        # 服务组的基础信息
        new_templet["group_version"] = old_templete["group_version"]
        new_templet["group_name"] = old_templete["group_name"]
        new_templet["group_key"] = old_templete["group_key"]
        new_templet["template_version"] = "v2"
        new_templet["describe"] = old_templete["info"]
        new_templet["pic"] = old_templete["pic"]
        new_templet["is_official"] = old_templete["is_official"]
        new_templet["desc"] = old_templete["desc"]
        # process apps
        apps = old_templete["apps"]
        new_apps = []
        for app in apps:
            new_apps.append(self.__v1_2_v2_translate_app(app, region))
        new_templet["apps"] = new_apps
        new_templet["share_user"] = 0
        new_templet["share_team"] = ""
        if new_apps:
            new_templet["share_user"] = new_apps[0]["creater"]
            tenant_id = new_apps[0]["tenant_id"]
            team = team_repo.get_team_by_team_id(tenant_id)
            if team:
                new_templet["share_team"] = team.tenant_name
        return new_templet

    def __v1_2_v2_translate_app(self, app, region):

        new_app = dict()
        new_app["service_type"] = app["service_type"]
        new_app["service_cname"] = app["service_name"]
        new_app["deploy_version"] = current_time_str("%Y%m%d%H%M%S")
        # 老版本如果slug信息有值，则
        slug = app.get("slug", None)
        new_app["language"] = ""
        service_image = {}
        service_slug = {}
        share_slug_path = ""
        if slug:
            new_app["language"] = ""
            service_slug = self.__generate_slug_info()
            share_slug_path = slug
        else:
            service_image["hub_url"] = "hub.goodrain.com"
            service_image["namespace"] = "goodrain"
            # 云市镜像存储
            new_app["share_image"] = app["image"].replace(
                "goodrain.me", "hub.goodrain.com/goodrain")
        if share_slug_path:
            new_app["share_slug_path"] = share_slug_path
        new_app["service_image"] = service_image
        new_app["service_slug"] = service_slug
        new_app["version"] = app["version"]
        new_app["need_share"] = True
        new_app["service_key"] = app["service_key"]
        new_app["service_alias"] = "gr" + app["service_key"][-6:]
        new_app["extend_method"] = app["extend_method"]
        category = app["category"]
        new_app["category"] = category
        new_app[
            "service_source"] = "source_code" if category == "appliaction" else "market"
        new_app["creater"] = app["creater"]
        new_app["tenant_id"] = app.get("tenant_id", "")
        new_app["service_region"] = region
        new_app["service_id"] = ""
        new_app["memory"] = app["min_memory"]
        new_app["image"] = app["image"]
        new_app["plugin_map_list"] = []
        new_app["probes"] = []
        # 扩展信息
        new_app["extend_method_map"] = self.__v1_2_v2_extends_info(app)
        # 依赖信息
        new_app["dep_service_map_list"] = self.__v1_2_v2_dependencies(app)
        # 端口信息
        service_env_map_list = []
        service_connect_info_map_list = []
        new_app["port_map_list"] = self.__v1_2_v2_ports(
            app, service_connect_info_map_list)
        # 持久化信息
        new_app["service_volume_map_list"] = self.__v1_2_v2_volumes(app)
        # 环境变量信息
        self.__v1_2_v2_envs(app, service_env_map_list,
                            service_connect_info_map_list)
        new_app["service_env_map_list"] = service_env_map_list
        new_app[
            "service_connect_info_map_list"] = service_connect_info_map_list
        return new_app

    def __v1_2_v2_extends_info(self, app):
        extends_info_list = app["extends"]
        extend_method_map = {}
        if extends_info_list:
            extends_info = extends_info_list[0]
            extend_method_map["min_node"] = extends_info["min_node"]
            extend_method_map["max_memory"] = extends_info["max_memory"]
            extend_method_map["step_node"] = extends_info["step_node"]
            extend_method_map["max_node"] = extends_info["max_node"]
            extend_method_map["step_memory"] = extends_info["step_memory"]
            extend_method_map["min_memory"] = extends_info["min_memory"]
            extend_method_map["is_restart"] = extends_info["is_restart"]
        else:
            extend_method_map["min_node"] = 1
            extend_method_map["max_memory"] = 65536
            extend_method_map["step_node"] = 1
            extend_method_map["max_node"] = 20
            extend_method_map["step_memory"] = 128
            extend_method_map["min_memory"] = 512
            extend_method_map["is_restart"] = False
        return extend_method_map

    def __v1_2_v2_dependencies(self, app):
        dep_service_list = []
        dep_relations = app["dep_relations"]
        if dep_relations:
            dep_service_list = [{
                "dep_service_key": dep["dep_service_key"]
            } for dep in dep_relations]
        return dep_service_list

    def __v1_2_v2_ports(self, app, service_connect_info_map_list):
        port_map_list = []
        ports = app["ports"]
        if ports:
            for port in ports:
                port_alias = port["port_alias"]
                port_map_list.append({
                    "is_outer_service":
                    port["is_outer_service"],
                    "protocol":
                    port["protocol"],
                    "port_alias":
                    port_alias,
                    "is_inner_service":
                    port["is_inner_service"],
                    "container_port":
                    port["container_port"]
                })
                if app["is_init_accout"]:
                    temp_alias = "gr" + make_uuid()[-6:]
                    env_prefix = port_alias.upper() if bool(
                        port_alias) else temp_alias.upper()
                    service_connect_info_map_list.append({
                        "name":
                        "用户名",
                        "attr_name":
                        env_prefix + "_USER",
                        "is_change":
                        False,
                        "attr_value":
                        "admin"
                    })
                    service_connect_info_map_list.append({
                        "name":
                        "密码",
                        "attr_name":
                        env_prefix + "_PASS",
                        "is_change":
                        False,
                        "attr_value":
                        "**None**"
                    })
        return port_map_list

    def __v1_2_v2_volumes(self, app):
        service_volume_map_list = []
        volumes = app["volumes"]
        if volumes:
            service_volume_map_list = [{
                "category": volume["category"],
                "volume_path": volume["volume_path"],
                "volume_type": volume["volume_type"],
                "volume_name": volume["volume_name"]
            } for volume in volumes]
        else:
            volume_mount_path = app.get("volume_mount_path", None)
            if volume_mount_path:
                service_volume_map_list.append({
                    "category": app["category"],
                    "volume_path": volume_mount_path,
                    "volume_type": "share-file",
                    "volume_name": make_uuid()[:7]
                })
        return service_volume_map_list

    def __v1_2_v2_envs(self, app, service_env_map_list,
                       service_connect_info_map_list):
        envs = app["envs"]
        if envs:
            for env in envs:

                if env["scope"] == "inner":
                    service_env_map_list.append({
                        "name":
                        env["name"] if env["name"] else env["attr_name"],
                        "attr_name":
                        env["attr_name"],
                        "is_change":
                        env["is_change"],
                        "attr_value":
                        env["attr_value"]
                    })
                else:
                    service_connect_info_map_list.append({
                        "name":
                        env["name"] if env["name"] else env["attr_name"],
                        "attr_name":
                        env["attr_name"],
                        "is_change":
                        env["is_change"],
                        "attr_value":
                        env["attr_value"]
                    })

    def __generate_slug_info(self):
        service_slug = dict()
        service_slug["ftp_host"] = "139.196.88.57"
        service_slug["ftp_port"] = "10022"
        service_slug["ftp_username"] = "goodrain"
        service_slug["ftp_password"] = "goodrain123465"
        service_slug["namespace"] = "app-publish/"
        return service_slug


class AppMarketSynchronizeService(object):
    def download_app_service_group_from_market(self, user, tenant, group_key,
                                               group_version):
        rainbond_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(
            group_key, group_version)
        if rainbond_app and rainbond_app.is_complete:
            return rainbond_app
        try:
            rainbond_app = self.down_market_group_app_detail(
                user, tenant, group_key, group_version, "v2")
            return rainbond_app
        except Exception as e:
            logger.exception(e)
            logger.error(
                'download app_group[{0}-{1}] from market failed!'.format(
                    group_key, group_version))
            return None

    def down_market_group_app_detail(self, user, tenant, group_key,
                                     group_version, template_version):
        data = market_api.get_remote_app_templates(tenant.tenant_id, group_key,
                                                   group_version)
        return self.save_market_app_template(user, tenant, data)

    def save_market_app_template(self, user, tenant, app_templates):
        template_version = app_templates["template_version"]
        is_v1 = bool(template_version == "v1")
        if is_v1:
            v2_template = template_transform_service.v1_to_v2(app_templates)
        else:
            v2_template = app_templates
        rainbond_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(
            tenant.enterprise_id, v2_template["group_key"],
            v2_template["group_version"])

        if not rainbond_app:
            if common_services.is_public() and user.is_sys_admin:
                enterprise_id = "public"
            else:
                enterprise_id = tenant.enterprise_id
            rainbond_app = RainbondCenterApp(
                group_key=app_templates["group_key"],
                group_name=app_templates["group_name"],
                version=app_templates['group_version'],
                share_user=0,
                record_id=0,
                share_team="",
                source="market",
                scope="goodrain",
                describe=app_templates["info"],
                pic=app_templates["pic"],
                app_template="",
                enterprise_id=enterprise_id,
                template_version=app_templates.get("template_version", ""),
                is_official=app_templates["is_official"],
                details=app_templates["desc"],
                upgrade_time=app_templates["update_version"])
        if is_v1:
            rainbond_app.share_user = v2_template["share_user"]
            rainbond_app.share_team = v2_template["share_team"]
            rainbond_app.pic = v2_template["pic"]
            rainbond_app.describe = v2_template["describe"]
            rainbond_app.app_template = json.dumps(v2_template)
            rainbond_app.is_complete = True
            rainbond_app.update_time = current_time_str("%Y-%m-%d %H:%M:%S")
            rainbond_app.is_official = v2_template["is_official"]
            rainbond_app.details = v2_template["desc"]
            rainbond_app.upgrade_time = v2_template.get("update_version", "0")
            rainbond_app.save()
        else:
            user_name = v2_template.get("publish_user", None)
            user_id = 0
            if user_name:
                try:
                    user = user_repo.get_user_by_username(user_name)
                    user_id = user.user_id
                except Exception as e:
                    logger.exception(e)
            rainbond_app.share_user = user_id
            rainbond_app.share_team = v2_template.get("publish_team", "")
            rainbond_app.pic = v2_template.get("pic", rainbond_app.pic)
            rainbond_app.describe = v2_template.get("update_note",
                                                    rainbond_app.describe)
            rainbond_app.app_template = v2_template["template_content"]
            rainbond_app.is_complete = True
            rainbond_app.update_time = current_time_str("%Y-%m-%d %H:%M:%S")
            rainbond_app.is_official = v2_template.get("is_official", 0)
            rainbond_app.details = v2_template.get("desc", "")
            rainbond_app.upgrade_time = v2_template.get("update_version", "")
            rainbond_app.save()
        return rainbond_app


market_app_service = MarketAppService()
template_transform_service = MarketTemplateTranslateService()
market_sycn_service = AppMarketSynchronizeService()
