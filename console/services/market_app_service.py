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
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from console.services.app_config import env_var_service, port_service, volume_service, label_service, probe_service
from console.services.app_config.app_relation_service import AppServiceRelationService
from console.services.group_service import group_service
from console.utils.timeutil import current_time_str
from www.apiclient.marketclient import MarketOpenAPI
from www.models import TenantServiceInfo
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid
from console.models.main import RainbondCenterApp

logger = logging.getLogger("default")
baseService = BaseTenantService()
app_relation_service = AppServiceRelationService()
market_api = MarketOpenAPI()


class MarketAppService(object):
    def install_service(self, tenant, region, user, group_id, market_app):
        service_list = []
        service_key_dep_key_map = {}
        key_service_map = {}
        tenant_service_group = None
        service_probe_map = {}
        try:
            app_templates = json.loads(market_app.app_template)
            apps = app_templates["apps"]
            tenant_service_group = self.__create_tenant_service_group(region, tenant.tenant_id, group_id,
                                                                      market_app.group_key, market_app.version,
                                                                      market_app.group_name)
            for app in apps:
                ts = self.__init_market_app(tenant, region, user, app, tenant_service_group.ID)
                group_service.add_service_to_group(tenant, region, group_id, ts.service_id)
                service_list.append(ts)

                # 先保存env,再保存端口，因为端口需要处理env
                code, msg = self.__save_env(tenant, ts, app["service_env_map_list"],
                                            app["service_connect_info_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_port(tenant, ts, app["port_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_volume(tenant, ts, app["service_volume_map_list"])
                if code != 200:
                    raise Exception(msg)

                # 保存应用探针信息
                probe_infos = app.get("probes", None)
                if probe_infos:
                    service_probe_map[ts.service_id] = probe_infos

                self.__save_extend_info(ts, app["extend_method_map"])

                dep_apps_key = app.get("dep_service_map_list", None)
                if dep_apps_key:
                    service_key_dep_key_map[ts.service_key] = dep_apps_key
                key_service_map[ts.service_key] = ts
            # 保存依赖关系
            self.__save_service_deps(tenant, service_key_dep_key_map, key_service_map)

            # 数据中心创建应用
            new_service_list = self.__create_region_services(tenant, user, service_list, service_probe_map)
            # 部署所有应
            self.__deploy_services(tenant, user, new_service_list)
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

    def __create_tenant_service_group(self, region, tenant_id, group_id, group_key, group_version, group_alias):
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

    def __create_region_services(self, tenant, user, service_list, service_probe_map):
        service_prob_id_map = {}
        new_service_list = []
        try:
            for service in service_list:
                # 数据中心创建应用
                new_service = app_service.create_region_service(tenant, service, user.nick_name)
                # 为服务添加探针
                probe_data = service_probe_map.get(service.service_id)
                probe_ids = []
                if probe_data:
                    for data in probe_data:
                        code, msg, probe = probe_service.add_service_probe(tenant, service, data)
                        if code == 200:
                            probe_ids.append(probe.probe_id)
                else:
                    code, msg, probe = app_service.add_service_default_porbe(tenant, service)
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
                                    probe_service.delete_service_probe(tenant, service, probe_id)
                                except Exception as le:
                                    logger.exception("local market install app delete service probe {0}".format(le))
            raise e

    def __deploy_services(self, tenant, user, service_list):
        for service in service_list:
            try:
                app_manage_service.deploy(tenant, service, user)
            except Exception as e:
                logger.exception("batch deploy service error {0}".format(e))
                continue

    def __save_service_deps(self, tenant, service_key_dep_key_map, key_service_map):
        if service_key_dep_key_map:
            for service_key in service_key_dep_key_map.keys():
                ts = key_service_map[service_key]
                dep_keys = service_key_dep_key_map[service_key]
                for dep_key in dep_keys:
                    dep_service = key_service_map[dep_key["dep_service_key"]]
                    code, msg, d = app_relation_service.add_service_dependency(tenant, ts,
                                                                               dep_service.service_id)
                    if code != 200:
                        logger.error("compose add service error {0}".format(msg))
                        return code, msg
        return 200, "success"

    def __save_env(self, tenant, service, inner_envs, outer_envs):
        if not inner_envs and not outer_envs:
            return 200, "success"
        for env in inner_envs:
            code, msg, env_data = env_var_service.add_service_env_var(tenant, service, 0, env["name"], env["attr_name"],
                                                                      env["attr_value"], env["is_change"],
                                                                      "inner")
            if code != 200:
                logger.error("save market app env error {0}".format(msg))
                return code, msg
        for env in outer_envs:
            container_port = env.get("container_port", 0)
            if container_port == 0:
                if env["attr_value"] == "**None**":
                    env["attr_value"] = service.service_id[:8]
                code, msg, env_data = env_var_service.add_service_env_var(tenant, service, container_port,
                                                                          env["name"], env["attr_name"],
                                                                          env["attr_value"], env["is_change"],
                                                                          "outer")
                if code != 200:
                    logger.error("save market app env error {0}".format(msg))
                    return code, msg
        return 200, "success"

    def __save_port(self, tenant, service, ports):
        if not ports:
            return 200, "success"
        for port in ports:
            code, msg, port_data = port_service.add_service_port(tenant, service,
                                                                 int(port["container_port"]),
                                                                 port["protocol"],
                                                                 port["port_alias"],
                                                                 port["is_inner_service"],
                                                                 port["is_outer_service"])
            if code != 200:
                logger.error("save market app port error".format(msg))
                return code, msg
        return 200, "success"

    def __save_volume(self, tenant, service, volumes):
        if not volumes:
            return 200, "success"
        for volume in volumes:
            code, msg, volume_data = volume_service.add_service_volume(tenant, service, volume["volume_path"],
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

    def __init_market_app(self, tenant, region, user, app, tenant_service_group_id):
        """
        初始化应用市场创建的应用默认数据
        """
        is_slug = bool(
            app["image"].startswith('goodrain.me/runner') and app["language"] not in ("dockerfile", "docker"))

        tenant_service = TenantServiceInfo()
        tenant_service.tenant_id = tenant.tenant_id
        tenant_service.service_id = make_uuid()
        tenant_service.service_cname = app_service.generate_service_cname(tenant, app["service_cname"], region)
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

    def __init_service_source(self, ts, app):
        is_slug = bool(ts.image.startswith('goodrain.me/runner') and app["language"] not in ("dockerfile", "docker"))
        if is_slug:
            extend_info = app["service_slug"]
            extend_info["slug_path"] = app.get("share_slug_path", "")
        else:
            extend_info = app["service_image"]

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
        allow_create, tips = app_service.verify_source(tenant, region, total_memory, "应用市场创建")
        return allow_create, tips, total_memory

    def get_visiable_apps(self, tenant, scope, app_name):

        if scope == "team":
            rt_apps = self.get_current_team_shared_apps(tenant.tenant_name)
        elif scope == "goodrain":
            rt_apps = self.get_public_market_shared_apps()
        elif scope == "enterprise":
            rt_apps = self.get_current_enterprise_shared_apps(tenant.enterprise_id)
        else:
            rt_apps = self.get_team_visiable_apps(tenant)
        if app_name:
            rt_apps = rt_apps.filter(Q(group_name__icontains=app_name))
        return rt_apps

    def get_current_team_shared_apps(self, current_team_name):
        return rainbond_app_repo.get_complete_rainbond_apps().filter(share_team=current_team_name)

    def get_current_enterprise_shared_apps(self, enterprise_id):
        tenants = team_repo.get_teams_by_enterprise_id(enterprise_id)
        tenant_names = [t.tenant_name for t in tenants]
        # 获取企业分享的应用，并且排除返回在团队内的
        return rainbond_app_repo.get_complete_rainbond_apps().filter(share_team__in=tenant_names).exclude(scope="team")

    def get_public_market_shared_apps(self):
        return rainbond_app_repo.get_complete_rainbond_apps().filter(scope="goodrain")

    def get_team_visiable_apps(self, tenant):
        tenants = team_repo.get_teams_by_enterprise_id(tenant.enterprise_id)
        tenant_names = [t.tenant_name for t in tenants]
        public_apps = Q(scope="goodrain")
        enterprise_apps = Q(share_team__in=tenant_names, scope="enterprise")
        team_apps = Q(share_team=tenant.tenant_name, scope="team")

        return rainbond_app_repo.get_complete_rainbond_apps().filter(public_apps | enterprise_apps | team_apps)

    def get_rain_bond_app_by_pk(self, pk):
        app = rainbond_app_repo.get_rainbond_app_by_id(pk)
        if not app:
            return 404, None
        return 200, app

    def get_all_goodrain_market_apps(self, app_name, is_complete):
        if app_name:
            return rainbond_app_repo.get_all_rainbond_apps().filter(scope="goodrain", source="market",
                                                                    group_name__icontains=app_name)
        if is_complete:
            if is_complete == "true":
                return rainbond_app_repo.get_all_rainbond_apps().filter(scope="goodrain", source="market",
                                                                        is_complete=True)
            else:
                return rainbond_app_repo.get_all_rainbond_apps().filter(scope="goodrain", source="market",
                                                                        is_complete=False)
        return rainbond_app_repo.get_all_rainbond_apps().filter(scope="goodrain", source="market")


class MarketTemplateTranslateService(object):
    # 需要特殊处理的service_key
    SPECIAL_PROCESS = ("mysql",
                       "postgresql",
                       "6f7edb496760bb1965bdce1135883b29",
                       "2dd630b20396c26dc437fdcf2b98fb63",
                       "eae2d4ba183a8e3c41f2239d1a687ce8",
                       "df98c419c98cc6f1488fc83e13e0244a",
                       "bf22929d36d217b77d27813e6ae1508b",
                       "1fecc863b04c0cd24cee1403ba238f2e",
                       "915cc8a5cd81f28aa7f0daba314204c2",
                       "231c92c7fa4f7c1df76c889c84dcf4e7",
                       "edde97105d55d4301b9cddf15e139981",
                       "d261fa2e90c84131df33644ad0b6e5c5",
                       "7045a899df1369f30e1adce1cbbeb15b",
                       "45081d62105d2f18a487f06dabf9de6a",
                       "efc18a5358b5dabb50fb813f5d46458b",
                       "711657b065fa265c17a8fd265c32ec5b",
                       "eefca5b538fb6cf7d187b738e7fe035e",
                       "88064c83f0e5a6a5c9b73b57dbb0d6ff",
                       "88bd3a92b128445af53923ee2edc975c")

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
            new_app["share_image"] = app["image"].replace("goodrain.me", "hub.goodrain.com/goodrain")
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
        new_app["service_source"] = "source_code" if category == "appliaction" else "market"
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
        new_app["port_map_list"] = self.__v1_2_v2_ports(app, service_connect_info_map_list)
        # 持久化信息
        new_app["service_volume_map_list"] = self.__v1_2_v2_volumes(app)
        # 环境变量信息
        self.__v1_2_v2_envs(app, service_env_map_list, service_connect_info_map_list)
        new_app["service_env_map_list"] = service_env_map_list
        new_app["service_connect_info_map_list"] = service_connect_info_map_list
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
            dep_service_list = [{"dep_service_key": dep["dep_service_key"]} for dep in dep_relations]
        return dep_service_list

    def __v1_2_v2_ports(self, app, service_connect_info_map_list):
        port_map_list = []
        ports = app["ports"]
        if ports:
            for port in ports:
                port_alias = port["port_alias"]
                port_map_list.append({"is_outer_service": port["is_outer_service"],
                                      "protocol": port["protocol"],
                                      "port_alias": port_alias,
                                      "is_inner_service": port["is_inner_service"],
                                      "container_port": port["container_port"]})
                if app["is_init_accout"]:
                    temp_alias = "gr" + make_uuid()[-6:]
                    env_prefix = port_alias.upper() if bool(port_alias) else temp_alias.upper()
                    service_connect_info_map_list.append({
                        "name": "用户名",
                        "attr_name": env_prefix + "_USER",
                        "is_change": False,
                        "attr_value": "admin"
                    })
                    service_connect_info_map_list.append({
                        "name": "密码",
                        "attr_name": env_prefix + "_PASS",
                        "is_change": False,
                        "attr_value": "**None**"
                    })
        return port_map_list

    def __v1_2_v2_volumes(self, app):
        service_volume_map_list = []
        volumes = app["volumes"]
        if volumes:
            service_volume_map_list = [
                {
                    "category": volume["category"],
                    "volume_path": volume["volume_path"],
                    "volume_type": volume["volume_type"],
                    "volume_name": volume["volume_name"]
                } for volume in volumes
                ]
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

    def __v1_2_v2_envs(self, app, service_env_map_list, service_connect_info_map_list):
        envs = app["envs"]
        if envs:
            for env in envs:

                if env["scope"] == "inner":
                    service_env_map_list.append({
                        "name": env["name"] if env["name"] else env["attr_name"],
                        "attr_name": env["attr_name"],
                        "is_change": env["is_change"],
                        "attr_value": env["attr_value"]
                    })
                else:
                    service_connect_info_map_list.append({
                        "name": env["name"] if env["name"] else env["attr_name"],
                        "attr_name": env["attr_name"],
                        "is_change": env["is_change"],
                        "attr_value": env["attr_value"]
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
    def down_market_group_list(self, tenant):
        app_group_list = market_api.get_service_group_list(tenant.tenant_id)
        rainbond_apps = []
        for app_group in app_group_list:
            rbc = rainbond_app_repo.get_rainbond_app_by_key_and_version(app_group["group_key"],
                                                                        app_group["group_version"])
            if rbc:
                rbc.describe = app_group["info"] if app_group["info"] else rbc.describe
                rbc.pic = app_group["pic"] if app_group["pic"] else rbc.pic
                rbc.update_time = current_time_str("%Y-%m-%d %H:%M:%S")
                rbc.template_version = app_group.get("template_version", rbc.template_version)
                rbc.save()
            else:
                rainbond_app = RainbondCenterApp(
                    group_key=app_group["group_key"],
                    group_name=app_group["group_name"],
                    version=app_group['group_version'],
                    share_user=0,
                    record_id=0,
                    share_team="",
                    source="market",
                    scope="goodrain",
                    describe=app_group["info"],
                    pic=app_group["pic"],
                    app_template="",
                    template_version=app_group.get("template_version", "")
                )
                rainbond_apps.append(rainbond_app)
        rainbond_app_repo.bulk_create_rainbond_apps(rainbond_apps)

    def batch_down_market_group_app_details(self, tenant, data):
        app_group_detail_templates = market_api.batch_get_group_details(tenant.tenant_id, data)
        for app_templates in app_group_detail_templates:
            self.save_market_app_template(app_templates)

    def down_market_group_app_detail(self, tenant, group_key, group_version, template_version):
        data = market_api.get_service_group_detail(tenant.tenant_id, group_key, group_version, template_version)
        self.save_market_app_template(data)

    def save_market_app_template(self, app_templates):
        template_version = app_templates["template_version"]
        is_v1 = bool(template_version == "v1")
        if is_v1:
            v2_template = template_transform_service.v1_to_v2(app_templates)
        else:
            v2_template = app_templates
        rainbond_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(v2_template["group_key"],
                                                                             v2_template["group_version"])
        logger.debug("=========> {0}".format(json.dumps(v2_template)))
        if rainbond_app:
            if is_v1:
                rainbond_app.share_user = v2_template["share_user"]
                rainbond_app.share_team = v2_template["share_team"]
                rainbond_app.pic = v2_template["pic"]
                rainbond_app.describe = v2_template["describe"]
                rainbond_app.app_template = json.dumps(v2_template)
                rainbond_app.is_complete = True
                rainbond_app.update_time = current_time_str("%Y-%m-%d %H:%M:%S")
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
                rainbond_app.describe = v2_template.get("update_note", rainbond_app.describe)
                rainbond_app.app_template = v2_template["template_content"]
                rainbond_app.is_complete = True
                rainbond_app.update_time = current_time_str("%Y-%m-%d %H:%M:%S")
                rainbond_app.save()


market_app_service = MarketAppService()
template_transform_service = MarketTemplateTranslateService()
market_sycn_service = AppMarketSynchronizeService()
