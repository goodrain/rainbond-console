# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
from console.constants import AppConstants
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.team_repo import team_repo
from django.db.models import Q
import logging
import json
import datetime
from console.repositories.app import service_source_repo
from www.models import TenantServiceInfo
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid
from console.services.group_service import group_service
from console.services.app_config import env_var_service, port_service, volume_service, label_service, probe_service
from console.services.app import app_service
from console.services.app_config.app_relation_service import AppServiceRelationService
from console.services.app_actions import app_manage_service
from console.repositories.group import tenant_service_group_repo
from console.repositories.app_config import extend_repo

logger = logging.getLogger("default")
baseService = BaseTenantService()
app_relation_service = AppServiceRelationService()


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
                ts = self.__init_market_app(tenant.tenant_id, region, user, app, tenant_service_group.ID)
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
            # 构建应用
            self.__build_services(tenant, user, service_list, service_probe_map)
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

    def __build_services(self, tenant, user, service_list, service_probe_map):
        service_prob_map = {}
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
                if probe_ids:
                    service_probe_map[service.service_id] = probe_ids

                # 添加服务有无状态标签
                label_service.update_service_state_label(tenant, new_service)
                # 部署应用
                app_manage_service.deploy(tenant, new_service, user)
        except Exception as e:
            logger.exception(e)
            if service_list:
                for service in service_list:
                    if service_prob_map:
                        probe_ids = service_prob_map.get(service.service_id)
                        if probe_ids:
                            for probe_id in probe_ids:
                                try:
                                    probe_service.delete_service_probe(tenant, service, probe_id)
                                except Exception as le:
                                    logger.exception(le)
            raise e

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
            if env["container_port"] == 0:
                if env["attr_name"] == "**None**":
                    env["attr_name"] = service[:8]
                code, msg, env_data = env_var_service.add_service_env_var(tenant, service, env["container_port"],
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

    def __init_market_app(self, tenant_id, region, user, app, tenant_service_group_id):
        """
        初始化应用市场创建的应用默认数据
        """
        is_slug = bool(app["image"].startswith('goodrain.me/runner') and app["language"] not in ("dockerfile", "docker"))

        tenant_service = TenantServiceInfo()
        tenant_service.tenant_id = tenant_id
        tenant_service.service_id = make_uuid()
        tenant_service.service_cname = app["service_cname"]
        tenant_service.service_alias = "gr" + tenant_service.service_id[-6:]
        tenant_service.creater = user.pk
        if is_slug:
            tenant_service.image = app["image"]
        else:
            tenant_service.image = app.get("share_image", app["image"])
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
            if app.get("service_slug",None):
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
        tenant_service.host_path = "/grdata/tenant/" + tenant_id + "/service/" + tenant_service.service_id
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
        logger.debug("======> {0}".format(json.dumps(app)))
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

    def check_package_app_resource(self, tenant, market_app):
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
        allow_create, tips = app_service.check_tenant_resource(tenant, total_memory)
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


market_app_service = MarketAppService()
