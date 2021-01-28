# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
import copy
import json
import logging
import os

from addict import Dict
from console.constants import (DefaultPluginConstants, PluginCategoryConstants, PluginImage, PluginInjection, PluginMetaType)
from console.exception.bcode import (ErrInternalGraphsNotFound, ErrPluginIsUsed, ErrRepeatMonitoringTarget,
                                     ErrServiceMonitorExists)
from console.exception.main import ServiceHandleException
from console.repositories.app import service_repo
from console.repositories.app_config import port_repo
from console.repositories.base import BaseConnection
from console.repositories.plugin import (app_plugin_attr_repo, app_plugin_relation_repo, config_group_repo, config_item_repo,
                                         plugin_repo, plugin_version_repo, service_plugin_config_repo)
from console.services.app import app_service
from console.services.app_config import port_service
from console.services.app_config.app_relation_service import \
    AppServiceRelationService
from console.services.app_config.component_graph import component_graph_service
from console.services.app_config.service_monitor import service_monitor_repo
from django.db import transaction
from django.db.models import Q
from docker_image import reference
from goodrain_web import settings
from goodrain_web.settings import IMAGE_REPO
from goodrain_web.tools import JuncheePaginator
from www.apiclient.regionapi import RegionInvokeApi
from www.models.plugin import (PluginConfigGroup, PluginConfigItems, ServicePluginConfigVar)
from www.utils.crypt import make_uuid

from .plugin_config_service import PluginConfigService
from .plugin_version import PluginBuildVersionService

region_api = RegionInvokeApi()
logger = logging.getLogger("default")
plugin_config_service = PluginConfigService()
plugin_version_service = PluginBuildVersionService()
dependency_service = AppServiceRelationService()

has_the_same_category_plugin = ServiceHandleException(msg="params error", msg_show="该组件已存在相同功能插件", status_code=400)
allow_plugins = [
    PluginCategoryConstants.OUTPUT_INPUT_NET, PluginCategoryConstants.OUTPUT_NET, PluginCategoryConstants.INPUT_NET,
    PluginCategoryConstants.PERFORMANCE_ANALYSIS, PluginCategoryConstants.INIT_TYPE, PluginCategoryConstants.COMMON_TYPE,
    PluginCategoryConstants.EXPORTER_TYPE
]

default_plugins = [
    DefaultPluginConstants.DOWNSTREAM_NET_PLUGIN, DefaultPluginConstants.PERF_ANALYZE_PLUGIN,
    DefaultPluginConstants.INANDOUT_NET_PLUGIN, DefaultPluginConstants.FILEBEAT_LOG_PLUGIN,
    DefaultPluginConstants.LOGTAIL_LOG_PLUGIN, DefaultPluginConstants.MYSQLD_EXPORTER_PLUGIN
]


class AppPluginService(object):
    def get_service_abled_plugin(self, service):
        plugins = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(
            service.service_id).filter(plugin_status=True)
        plugin_ids = [p.plugin_id for p in plugins]
        base_plugins = plugin_repo.get_plugin_by_plugin_ids(plugin_ids)
        return base_plugins

    def get_plugin_used_services(self, plugin_id, tenant_id, page, page_size):
        aprr = app_plugin_relation_repo.get_used_plugin_services(plugin_id)
        service_ids = [r.service_id for r in aprr]
        service_plugin_version_map = {r.service_id: r.build_version for r in aprr}
        services = service_repo.get_services_by_service_ids(service_ids).filter(tenant_id=tenant_id)
        paginator = JuncheePaginator(services, int(page_size))
        total = paginator.count
        show_apps = paginator.page(int(page))
        result_list = []
        for s in show_apps:
            data = dict()
            data["service_id"] = s.service_id
            data["service_alias"] = s.service_alias
            data["service_cname"] = s.service_cname
            data["build_version"] = service_plugin_version_map[s.service_id]
            result_list.append(data)
        return result_list, total

    def create_service_plugin_relation(self,
                                       tenant_id,
                                       service_id,
                                       plugin_id,
                                       build_version,
                                       service_meta_type="",
                                       plugin_status=True):
        sprs = app_plugin_relation_repo.get_relation_by_service_and_plugin(service_id, plugin_id)
        if sprs:
            raise ServiceHandleException(msg="plugin has installed", status_code=409, msg_show="组件已安装该插件")
        plugin_version_info = plugin_version_repo.get_by_id_and_version(tenant_id, plugin_id, build_version)
        min_memory = plugin_version_info.min_memory
        min_cpu = plugin_version_info.min_cpu
        params = {
            "service_id": service_id,
            "build_version": build_version,
            "service_meta_type": service_meta_type,
            "plugin_id": plugin_id,
            "plugin_status": plugin_status,
            "min_memory": min_memory,
            "min_cpu": min_cpu,
        }
        return app_plugin_relation_repo.create_service_plugin_relation(**params)

    def get_plugins_by_service_id(self, region, tenant_id, service_id, category):
        """获取组件已开通和未开通的插件"""

        QUERY_INSTALLED_SQL = """
        SELECT
            tp.plugin_id AS plugin_id,
            tp.DESC AS "desc",
            tp.plugin_alias AS plugin_alias,
            tp.category AS category,
            tp.origin_share_id AS origin_share_id,
            pbv.build_version AS build_version,
            tsp.min_memory AS min_memory,
            tsp.plugin_status AS plugin_status
        FROM
            tenant_service_plugin_relation tsp
            LEFT JOIN plugin_build_version pbv ON tsp.plugin_id = pbv.plugin_id
            AND tsp.build_version = pbv.build_version
            JOIN tenant_plugin tp ON tp.plugin_id = tsp.plugin_id
            AND tp.tenant_id = pbv.tenant_id
        WHERE
            tsp.service_id = "{0}"
            AND tp.region = "{1}"
            AND tp.tenant_id = "{2}" """.format(service_id, region, tenant_id)

        QUERI_UNINSTALLED_SQL = """
            SELECT
                tp.plugin_id AS plugin_id,
                tp.DESC AS "desc",
                tp.plugin_alias AS plugin_alias,
                tp.category AS category,
                pbv.build_version AS build_version
            FROM
                tenant_plugin AS tp
                JOIN plugin_build_version AS pbv ON tp.plugin_id = pbv.plugin_id
                AND tp.tenant_id = pbv.tenant_id
            WHERE
                pbv.plugin_id NOT IN ( SELECT plugin_id FROM tenant_service_plugin_relation WHERE service_id = "{0}" )
                AND tp.tenant_id = "{1}"
                AND tp.region = "{2}"
                AND pbv.build_status = "{3}"
        """.format(service_id, tenant_id, region, "build_success")

        if category == "analysis":
            query_installed_plugin = """{0} AND tp.category="{1}" """.format(QUERY_INSTALLED_SQL, "analyst-plugin:perf")

            query_uninstalled_plugin = """{0} AND tp.category="{1}" """.format(QUERI_UNINSTALLED_SQL, "analyst-plugin:perf")

        elif category == "net_manage":
            query_installed_plugin = """{0} AND tp.category in {1} """.format(
                QUERY_INSTALLED_SQL, '("net-plugin:down","net-plugin:up","net-plugin:in-and-out")')
            query_uninstalled_plugin = """ {0} AND tp.category in {1} """.format(
                QUERI_UNINSTALLED_SQL, '("net-plugin:down","net-plugin:up","net-plugin:in-and-out")')
        else:
            query_installed_plugin = QUERY_INSTALLED_SQL
            query_uninstalled_plugin = QUERI_UNINSTALLED_SQL

        dsn = BaseConnection()
        installed_plugins = dsn.query(query_installed_plugin)
        uninstalled_plugins = dsn.query(query_uninstalled_plugin)
        return installed_plugins, uninstalled_plugins

    def get_service_plugin_relation(self, service_id, plugin_id):
        relations = app_plugin_relation_repo.get_relation_by_service_and_plugin(service_id, plugin_id)
        if relations:
            return relations[0]
        return None

    def start_stop_service_plugin(self, service_id, plugin_id, is_active, cpu, memory):
        """启用停用插件"""
        app_plugin_relation_repo.update_service_plugin_status(service_id, plugin_id, is_active, cpu, memory)

    @transaction.atomic
    def install_new_plugin(self, region, tenant, service, plugin_id, plugin_version=None, user=None):
        if not plugin_version:
            plugin_version = plugin_version_service.get_newest_usable_plugin_version(tenant.tenant_id, plugin_id)
            plugin_version = plugin_version.build_version
        logger.debug("start install plugin ! plugin_id {0}  plugin_version {1}".format(plugin_id, plugin_version))
        # 1.生成console数据，存储
        self.save_default_plugin_config(tenant, service, plugin_id, plugin_version)
        # 2.从console数据库取数据生成region数据
        region_config = self.get_region_config_from_db(service, plugin_id, plugin_version, user)

        # 3. create monitor resources, such as: service monitor, component graphs
        plugin = plugin_repo.get_by_plugin_id(tenant.tenant_id, plugin_id)
        self.create_monitor_resources(tenant, service, plugin.origin_share_id, user)

        data = dict()
        data["plugin_id"] = plugin_id
        data["switch"] = True
        data["version_id"] = plugin_version
        data["operator"] = user.nick_name if user else None
        data.update(region_config)
        self.create_service_plugin_relation(tenant.tenant_id, service.service_id, plugin_id, plugin_version)
        try:
            region_api.install_service_plugin(region, tenant.tenant_name, service.service_alias, data)
        except region_api.CallApiError as e:
            if "body" in e.message and "msg" in e.message["body"] \
                    and "a same kind plugin has been linked" in e.message["body"]["msg"]:
                raise ServiceHandleException(msg="install plugin fail", msg_show="网络类插件不能重复安装", status_code=409)

    def save_default_plugin_config(self, tenant, service, plugin_id, build_version):
        """console层保存默认的数据"""
        config_groups = plugin_config_service.get_config_group(plugin_id, build_version)
        service_plugin_var = []
        for config_group in config_groups:
            items = plugin_config_service.get_config_items(plugin_id, build_version, config_group.service_meta_type)
            if config_group.service_meta_type == PluginMetaType.UNDEFINE:
                attrs_map = {item.attr_name: item.attr_default_value for item in items}
                service_plugin_var.append(
                    ServicePluginConfigVar(
                        service_id=service.service_id,
                        plugin_id=plugin_id,
                        build_version=build_version,
                        service_meta_type=config_group.service_meta_type,
                        injection=config_group.injection,
                        dest_service_id="",
                        dest_service_alias="",
                        container_port=0,
                        attrs=json.dumps(attrs_map),
                        protocol=""))

            if config_group.service_meta_type == PluginMetaType.UPSTREAM_PORT:
                ports = port_repo.get_service_ports(service.tenant_id, service.service_id)
                if not self.__check_ports_for_config_items(ports, items):
                    raise ServiceHandleException(msg="do not support protocol", status_code=409, msg_show="插件支持的协议与组件端口协议不一致")
                for port in ports:
                    attrs_map = dict()
                    for item in items:
                        if item.protocol == "" or (port.protocol in item.protocol.split(",")):
                            attrs_map[item.attr_name] = item.attr_default_value
                    service_plugin_var.append(
                        ServicePluginConfigVar(
                            service_id=service.service_id,
                            plugin_id=plugin_id,
                            build_version=build_version,
                            service_meta_type=config_group.service_meta_type,
                            injection=config_group.injection,
                            dest_service_id="",
                            dest_service_alias="",
                            container_port=port.container_port,
                            attrs=json.dumps(attrs_map),
                            protocol=port.protocol))

            if config_group.service_meta_type == PluginMetaType.DOWNSTREAM_PORT:
                dep_services = dependency_service.get_service_dependencies(tenant, service)
                if not dep_services:
                    raise ServiceHandleException(msg="can't use this plugin", status_code=409, msg_show="组件没有依赖其他组件，不能安装此插件")
                for dep_service in dep_services:
                    ports = port_repo.get_service_ports(dep_service.tenant_id, dep_service.service_id)
                    if not self.__check_ports_for_config_items(ports, items):
                        raise ServiceHandleException(
                            msg="do not support protocol", status_code=409, msg_show="该组件依赖的组件的端口协议与插件支持的协议不一致")
                    for port in ports:
                        attrs_map = dict()
                        for item in items:
                            if item.protocol == "" or (port.protocol in item.protocol.split(",")):
                                attrs_map[item.attr_name] = item.attr_default_value
                        service_plugin_var.append(
                            ServicePluginConfigVar(
                                service_id=service.service_id,
                                plugin_id=plugin_id,
                                build_version=build_version,
                                service_meta_type=config_group.service_meta_type,
                                injection=config_group.injection,
                                dest_service_id=dep_service.service_id,
                                dest_service_alias=dep_service.service_alias,
                                container_port=port.container_port,
                                attrs=json.dumps(attrs_map),
                                protocol=port.protocol))
        # 保存数据
        ServicePluginConfigVar.objects.bulk_create(service_plugin_var)

    def __check_ports_for_config_items(self, ports, items):
        for item in items:
            if item.protocol == "":
                return True
            else:
                protocols = item.protocol.split(",")
                for port in ports:
                    if port.protocol in protocols:
                        return True
        return False

    def get_region_config_from_db(self, service, plugin_id, build_version, user=None):
        attrs = service_plugin_config_repo.get_service_plugin_config_var(service.service_id, plugin_id, build_version)
        normal_envs = []
        base_normal = dict()
        # 上游组件
        base_ports = []
        # 下游组件
        base_services = []
        region_env_config = dict()
        for attr in attrs:
            if attr.service_meta_type == PluginMetaType.UNDEFINE:
                if attr.injection == PluginInjection.EVN:
                    attr_map = json.loads(attr.attrs)
                    for k, v in list(attr_map.items()):
                        normal_envs.append({"env_name": k, "env_value": v})
                else:
                    base_normal["options"] = json.loads(attr.attrs)
            if attr.service_meta_type == PluginMetaType.UPSTREAM_PORT:
                base_ports.append({
                    "service_id": service.service_id,
                    "options": json.loads(attr.attrs),
                    "protocol": attr.protocol,
                    "port": attr.container_port,
                    "service_alias": service.service_alias
                })
            if attr.service_meta_type == PluginMetaType.DOWNSTREAM_PORT:
                base_services.append({
                    "depend_service_alias": attr.dest_service_alias,
                    "protocol": attr.protocol,
                    "service_alias": service.service_alias,
                    "options": json.loads(attr.attrs),
                    "service_id": service.service_id,
                    "depend_service_id": attr.dest_service_id,
                    "port": attr.container_port,
                })

        config_envs = dict()
        complex_envs = dict()
        config_envs["normal_envs"] = normal_envs
        complex_envs["base_ports"] = base_ports
        complex_envs["base_services"] = base_services
        complex_envs["base_normal"] = base_normal
        config_envs["complex_envs"] = complex_envs
        region_env_config["tenant_id"] = service.tenant_id
        region_env_config["config_envs"] = config_envs
        region_env_config["service_id"] = service.service_id
        region_env_config["operator"] = user.nick_name if user else None

        return region_env_config

    def create_monitor_resources(self, tenant, service, plugin_name, user=None):
        # service monitor
        try:
            self.__create_service_monitor(tenant, service, plugin_name, user)
        except ErrServiceMonitorExists:
            # try again
            self.__create_service_monitor(tenant, service, plugin_name, user)

        # component graphs
        self.__create_component_graphs(service.service_id, plugin_name)

    @staticmethod
    def __create_service_monitor(tenant, service, plugin_name, user=None):
        user_name = user.nick_name if user else ''
        path = "/metrics"
        if plugin_name == "mysqld_exporter":
            port = 9104
            show_name = "MySQL-Metrics"
        else:
            return
        # create internal port
        port_service.create_internal_port(tenant, service, port, user_name)
        try:
            service_monitor_repo.create_component_service_monitor(tenant, service, "mysqldexporter-" + make_uuid()[0:4], path,
                                                                  port, show_name, "10s", user)
        except ErrRepeatMonitoringTarget as e:
            logger.debug(e)

    @staticmethod
    def __create_component_graphs(component_id, plugin_name):
        try:
            component_graph_service.create_internal_graphs(component_id, plugin_name)
        except ErrInternalGraphsNotFound as e:
            logger.warning("plugin name '{}': {}", plugin_name, e)

    def delete_service_plugin_config(self, service, plugin_id):
        service_plugin_config_repo.delete_service_plugin_config_var(service.service_id, plugin_id)

    def delete_service_plugin_relation(self, service, plugin_id):
        app_plugin_relation_repo.delete_service_plugin(service.service_id, plugin_id)

    def get_service_plugin_config(self, tenant, service, plugin_id, build_version):
        config_groups = plugin_config_service.get_config_group(plugin_id, build_version)
        service_plugin_vars = service_plugin_config_repo.get_service_plugin_config_var(service.service_id, plugin_id,
                                                                                       build_version)
        result_bean = dict()

        undefine_env = dict()
        upstream_env_list = []
        downstream_env_list = []

        for config_group in config_groups:
            items = plugin_config_service.get_config_items(plugin_id, build_version, config_group.service_meta_type)
            if config_group.service_meta_type == PluginMetaType.UNDEFINE:
                options = []
                normal_envs = service_plugin_vars.filter(service_meta_type=PluginMetaType.UNDEFINE)
                undefine_options = None
                if normal_envs:
                    normal_env = normal_envs[0]
                    undefine_options = json.loads(normal_env.attrs)
                for item in items:
                    item_option = {
                        "attr_info": item.attr_info,
                        "attr_name": item.attr_name,
                        "attr_value": item.attr_default_value,
                        "attr_alt_value": item.attr_alt_value,
                        "attr_type": item.attr_type,
                        "attr_default_value": item.attr_default_value,
                        "is_change": item.is_change
                    }
                    if undefine_options:
                        item_option["attr_value"] = undefine_options.get(item.attr_name, item.attr_default_value)
                    options.append(item_option)
                undefine_env.update({
                    "service_id": service.service_id,
                    "service_meta_type": config_group.service_meta_type,
                    "injection": config_group.injection,
                    "service_alias": service.service_alias,
                    "config": copy.deepcopy(options),
                    "config_group_name": config_group.config_name,
                })
            if config_group.service_meta_type == PluginMetaType.UPSTREAM_PORT:
                ports = port_repo.get_service_ports(service.tenant_id, service.service_id)
                for port in ports:
                    upstream_envs = service_plugin_vars.filter(
                        service_meta_type=PluginMetaType.UPSTREAM_PORT, container_port=port.container_port)
                    upstream_options = None
                    if upstream_envs:
                        upstream_env = upstream_envs[0]
                        upstream_options = json.loads(upstream_env.attrs)
                    options = []
                    for item in items:
                        item_option = {
                            "attr_info": item.attr_info,
                            "attr_name": item.attr_name,
                            "attr_value": item.attr_default_value,
                            "attr_alt_value": item.attr_alt_value,
                            "attr_type": item.attr_type,
                            "attr_default_value": item.attr_default_value,
                            "is_change": item.is_change
                        }
                        if upstream_options:
                            item_option["attr_value"] = upstream_options.get(item.attr_name, item.attr_default_value)
                        if item.protocol == "" or (port.protocol in item.protocol.split(",")):
                            options.append(item_option)
                    upstream_env_list.append({
                        "config_group_name": config_group.config_name,
                        "service_id": service.service_id,
                        "service_meta_type": config_group.service_meta_type,
                        "injection": config_group.injection,
                        "service_alias": service.service_alias,
                        "protocol": port.protocol,
                        "port": port.container_port,
                        "config": copy.deepcopy(options)
                    })
            if config_group.service_meta_type == PluginMetaType.DOWNSTREAM_PORT:
                dep_services = dependency_service.get_service_dependencies(tenant, service)
                for dep_service in dep_services:
                    ports = port_repo.list_inner_ports(dep_service.tenant_id, dep_service.service_id)
                    for port in ports:
                        downstream_envs = service_plugin_vars.filter(
                            service_meta_type=PluginMetaType.DOWNSTREAM_PORT,
                            dest_service_id=dep_service.service_id,
                            container_port=port.container_port)
                        downstream_options = None
                        if downstream_envs:
                            downstream_env = downstream_envs[0]
                            downstream_options = json.loads(downstream_env.attrs)
                        options = []
                        for item in items:
                            item_option = {
                                "attr_info": item.attr_info,
                                "attr_name": item.attr_name,
                                "attr_value": item.attr_default_value,
                                "attr_alt_value": item.attr_alt_value,
                                "attr_type": item.attr_type,
                                "attr_default_value": item.attr_default_value,
                                "is_change": item.is_change
                            }
                            if downstream_options:
                                item_option["attr_value"] = downstream_options.get(item.attr_name, item.attr_default_value)
                            if item.protocol == "" or (port.protocol in item.protocol.split(",")):
                                options.append(item_option)
                        downstream_env_list.append({
                            "config_group_name": config_group.config_name,
                            "service_id": service.service_id,
                            "service_meta_type": config_group.service_meta_type,
                            "injection": config_group.injection,
                            "service_alias": service.service_alias,
                            "protocol": port.protocol,
                            "port": port.container_port,
                            "config": copy.deepcopy(options),
                            "dest_service_id": dep_service.service_id,
                            "dest_service_cname": dep_service.service_cname,
                            "dest_service_alias": dep_service.service_alias
                        })

        result_bean["undefine_env"] = undefine_env
        result_bean["upstream_env"] = upstream_env_list
        result_bean["downstream_env"] = downstream_env_list
        return result_bean

    @transaction.atomic
    def update_service_plugin_config(self, tenant, service, plugin_id, build_version, config, response_region):
        # delete old config
        self.delete_service_plugin_config(service, plugin_id)
        # 全量插入新配置
        self.__update_service_plugin_config(service, plugin_id, build_version, config)
        # 更新数据中心配置
        region_config = self.get_region_config_from_db(service, plugin_id, build_version)
        region_api.update_service_plugin_config(response_region, tenant.tenant_name, service.service_alias, plugin_id,
                                                region_config)

    def __update_service_plugin_config(self, service, plugin_id, build_version, config_bean):
        config_bean = Dict(config_bean)
        service_plugin_var = []
        undefine_env = config_bean.undefine_env
        if undefine_env:
            attrs_map = {c.attr_name: c.attr_value for c in undefine_env.config}
            service_plugin_var.append(
                ServicePluginConfigVar(
                    service_id=service.service_id,
                    plugin_id=plugin_id,
                    build_version=build_version,
                    service_meta_type=undefine_env.service_meta_type,
                    injection=undefine_env.injection,
                    dest_service_id="",
                    dest_service_alias="",
                    container_port=0,
                    attrs=json.dumps(attrs_map),
                    protocol=""))
        upstream_config_list = config_bean.upstream_env
        for upstream_config in upstream_config_list:
            attrs_map = {c.attr_name: c.attr_value for c in upstream_config.config}
            service_plugin_var.append(
                ServicePluginConfigVar(
                    service_id=service.service_id,
                    plugin_id=plugin_id,
                    build_version=build_version,
                    service_meta_type=upstream_config.service_meta_type,
                    injection=upstream_config.injection,
                    dest_service_id="",
                    dest_service_alias="",
                    container_port=upstream_config.port,
                    attrs=json.dumps(attrs_map),
                    protocol=upstream_config.protocol))
        dowstream_config_list = config_bean.downstream_env
        for dowstream_config in dowstream_config_list:
            attrs_map = {c.attr_name: c.attr_value for c in dowstream_config.config}
            service_plugin_var.append(
                ServicePluginConfigVar(
                    service_id=service.service_id,
                    plugin_id=plugin_id,
                    build_version=build_version,
                    service_meta_type=dowstream_config.service_meta_type,
                    injection=dowstream_config.injection,
                    dest_service_id=dowstream_config.dest_service_id,
                    dest_service_alias=dowstream_config.dest_service_alias,
                    container_port=dowstream_config.port,
                    attrs=json.dumps(attrs_map),
                    protocol=dowstream_config.protocol))

        ServicePluginConfigVar.objects.bulk_create(service_plugin_var)

    def create_plugin_4marketsvc(self, region_name, tenant, service, version, components, plugins):
        plugin_version_service.update_plugin_build_status(region_name, tenant)
        plugins = plugins if plugins is not None else []
        for plugin in plugins:
            data = self.build_plugin_data_4marketsvc(tenant, service, plugin)
            if data:
                service_plugin_config_vars = plugin["attr"]
                self.create_plugin_cfg_4marketsvc(tenant, service, version, data["plugin_id"], data["version_id"], components,
                                                  service_plugin_config_vars)
                self.create_service_plugin_relation(tenant.tenant_id, service.service_id, data["plugin_id"], data["version_id"])

    def build_plugin_data_4marketsvc(self, tenant, service, plugin):
        plugin_key = plugin["plugin_key"]
        p = plugin_repo.get_plugin_by_origin_share_id(tenant.tenant_id, plugin_key)
        if not p:
            logger.warning("open plugin failure , plugin {} not found in tenant {}".format(plugin_key, tenant.tenant_id))
            return
        plugin_id = p[0].plugin_id
        plugin_version = plugin_version_service.get_newest_plugin_version(tenant.tenant_id, plugin_id)
        build_version = plugin_version.build_version

        region_config = self.get_region_config_from_db(service, plugin_id, build_version)
        data = dict()
        data["plugin_id"] = plugin_id
        data["switch"] = True
        data["version_id"] = build_version
        data.update(region_config)
        return data

    def create_plugin_cfg_4marketsvc(self, tenant, service, version, plugin_id, build_version, components,
                                     service_plugin_config_vars):
        config_list = []
        component_id_key_map = {}
        for com in components:
            component_id_key_map[com["service_d"]] = com["service_share_uuid"]
        for config in service_plugin_config_vars:
            dest_service_id, dest_service_alias = "", ""
            if config["service_meta_type"] == "downstream_port":
                # step1: get dep component key
                dep_service_key = component_id_key_map.get(config["dest_service_id"])
                dest_service = app_service.get_service_by_service_key(service, dep_service_key)
                if dest_service:
                    dest_service_id = dest_service.get("service_id", "")
                    dest_service_alias = dest_service.get("service_alias", "")

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
        if config_list and len(config_list) > 0:
            ServicePluginConfigVar.objects.bulk_create(config_list)

    def check_the_same_plugin(self, plugin_id, tenant_id, service_id):
        plugin_ids = []
        categories = []
        service_plugins = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(service_id)
        if not service_plugins:
            """ component has not installed plugin"""
            return
        """ filter the same category plugin"""
        for i in service_plugins:
            plugin_ids.append(i.plugin_id)
        plugins = plugin_repo.get_plugin_by_plugin_ids(plugin_ids)
        for i in plugins:
            categories.append(i.category)

        # the trend to install plugin
        plugin_info = plugin_repo.get_plugin_by_plugin_id(tenant_id, plugin_id)

        category_info = plugin_info.category.split(":")
        if category_info[0] == "net-plugin":
            if plugin_info.category in categories:
                raise has_the_same_category_plugin
            if category_info[1] == "in-and-out" and ("net-plugin:up" in categories or "net-plugin:down" in categories):
                raise has_the_same_category_plugin

    # if have export network plugin, will change config
    def update_config_if_have_export_plugin(self, tenant, service):
        plugins = self.get_service_abled_plugin(service)
        for plugin in plugins:
            if PluginCategoryConstants.OUTPUT_NET == plugin.category or \
                    PluginCategoryConstants.OUTPUT_INPUT_NET == plugin.category:
                pbv = plugin_version_service.get_newest_usable_plugin_version(tenant.tenant_id, plugin.plugin_id)
                if pbv:
                    configs = self.get_service_plugin_config(tenant, service, plugin.plugin_id, pbv.build_version)
                    self.update_service_plugin_config(tenant, service, plugin.plugin_id, pbv.build_version, configs,
                                                      service.service_region)

    # if have entrance network plugin, will change config
    def update_config_if_have_entrance_plugin(self, tenant, service):
        plugins = self.get_service_abled_plugin(service)
        for plugin in plugins:
            if PluginCategoryConstants.INPUT_NET == plugin.category:
                pbv = plugin_version_service.get_newest_usable_plugin_version(tenant.tenant_id, plugin.plugin_id)
                if pbv:
                    configs = self.get_service_plugin_config(tenant, service, plugin.plugin_id, pbv.build_version)
                    self.update_service_plugin_config(tenant, service, plugin.plugin_id, pbv.build_version, configs,
                                                      service.service_region)


class PluginService(object):
    def get_plugins_by_service_ids(self, service_ids):
        return plugin_repo.get_plugins_by_service_ids(service_ids)

    def get_plugin_by_plugin_id(self, tenant, plugin_id):
        return plugin_repo.get_plugin_by_plugin_id(tenant.tenant_id, plugin_id)

    def create_tenant_plugin(self, plugin_params):
        plugin_id = make_uuid()
        plugin_params["plugin_id"] = plugin_id
        plugin_params["plugin_name"] = "gr" + plugin_id[:6]
        if plugin_params["build_source"] == "dockerfile" and not plugin_params["code_repo"]:
            return 400, "代码仓库不能为空", None
        if plugin_params["build_source"] == "image" and not plugin_params["image"]:
            return 400, "镜像地址不能为空", None
        if plugin_params["category"] not in allow_plugins:
            return 400, "插件类别参数不支持", None
        tenant_plugin = plugin_repo.create_plugin(**plugin_params)
        return 200, "success", tenant_plugin

    def create_region_plugin(self, region, tenant, tenant_plugin, image_tag="latest"):
        """创建region端插件信息"""
        plugin_data = dict()
        plugin_data["build_model"] = tenant_plugin.build_source
        plugin_data["git_url"] = tenant_plugin.code_repo
        plugin_data["image_url"] = "{0}:{1}".format(tenant_plugin.image, image_tag)
        plugin_data["plugin_id"] = tenant_plugin.plugin_id
        plugin_data["plugin_info"] = tenant_plugin.desc
        plugin_data["plugin_model"] = tenant_plugin.category
        plugin_data["plugin_name"] = tenant_plugin.plugin_name
        plugin_data["tenant_id"] = tenant.tenant_id
        region_api.create_plugin(region, tenant.tenant_name, plugin_data)
        return 200, "success"

    def delete_console_tenant_plugin(self, tenant_id, plugin_id):
        plugin_repo.delete_by_plugin_id(tenant_id, plugin_id)

    def get_plugin_event_log(self, region, tenant, event_id, level):
        data = {"event_id": event_id, "level": level}
        body = region_api.get_plugin_event_log(region, tenant.tenant_name, data)
        return body["list"]

    def get_tenant_plugins(self, region, tenant):
        return plugin_repo.get_tenant_plugins(tenant.tenant_id, region)

    def build_plugin(self, region, plugin, plugin_version, user, tenant, event_id, image_info=None):

        build_data = dict()

        build_data["build_version"] = plugin_version.build_version
        build_data["event_id"] = event_id
        build_data["info"] = plugin_version.update_info

        build_data["operator"] = user.nick_name
        build_data["plugin_cmd"] = plugin_version.build_cmd
        build_data["plugin_memory"] = int(plugin_version.min_memory)
        build_data["plugin_cpu"] = int(plugin_version.min_cpu)
        build_data["repo_url"] = plugin_version.code_version
        build_data["username"] = plugin.username  # git username
        build_data["password"] = plugin.password  # git password
        build_data["tenant_id"] = tenant.tenant_id
        build_data["ImageInfo"] = image_info
        build_data["build_image"] = "{0}:{1}".format(plugin.image, plugin_version.image_tag)
        origin = plugin.origin
        if origin == "local_market":
            plugin_from = "yb"
        elif origin == "market":
            plugin_from = "ys"
        else:
            plugin_from = None
        build_data["plugin_from"] = plugin_from

        body = region_api.build_plugin(region, tenant.tenant_name, plugin.plugin_id, build_data)
        return body

    all_default_config = None
    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir, 'default_config.json')
    with open(file_path) as f:
        all_default_config = json.load(f)

    def add_default_plugin(self, user, tenant, region, plugin_type="perf_analyze_plugin"):
        plugin_base_info = None
        try:
            if not self.all_default_config:
                raise Exception("no config was found")
            needed_plugin_config = self.all_default_config[plugin_type]
            image = needed_plugin_config.get("image", "")
            build_source = needed_plugin_config.get("build_source", "")
            image_tag = "latest"
            if image and build_source and build_source == "image":
                ref = reference.Reference.parse(image)
                if ref["tag"]:
                    image_tag = ref["tag"]
                if "goodrain.me" in image:
                    _, name = ref.split_hostname()
                    image = settings.IMAGE_REPO + "/" + name
                else:
                    image = image.split(":")[0]
            plugin_params = {
                "tenant_id": tenant.tenant_id,
                "region": region,
                "create_user": user.user_id,
                "desc": needed_plugin_config["desc"],
                "plugin_alias": needed_plugin_config["plugin_alias"],
                "category": needed_plugin_config["category"],
                "build_source": build_source,
                "image": image,
                "code_repo": needed_plugin_config["code_repo"],
                "username": "",
                "password": ""
            }
            code, msg, plugin_base_info = self.create_tenant_plugin(plugin_params)
            plugin_base_info.origin = "local_market"
            plugin_base_info.origin_share_id = plugin_type
            plugin_base_info.save()

            plugin_build_version = plugin_version_service.create_build_version(
                region, plugin_base_info.plugin_id, tenant.tenant_id, user.user_id, "", "unbuild", 64, image_tag=image_tag)

            plugin_config_meta_list = []
            config_items_list = []
            config_group = needed_plugin_config.get("config_group")
            if config_group:
                for config in config_group:
                    options = config["options"]
                    plugin_config_meta = PluginConfigGroup(
                        plugin_id=plugin_build_version.plugin_id,
                        build_version=plugin_build_version.build_version,
                        config_name=config["config_name"],
                        service_meta_type=config["service_meta_type"],
                        injection=config["injection"])
                    plugin_config_meta_list.append(plugin_config_meta)

                    for option in options:
                        config_item = PluginConfigItems(
                            plugin_id=plugin_build_version.plugin_id,
                            build_version=plugin_build_version.build_version,
                            service_meta_type=config["service_meta_type"],
                            attr_name=option["attr_name"],
                            attr_alt_value=option["attr_alt_value"],
                            attr_type=option.get("attr_type", "string"),
                            attr_default_value=option.get("attr_default_value", None),
                            is_change=option.get("is_change", False),
                            attr_info=option.get("attr_info", ""),
                            protocol=option.get("protocol", ""))
                        config_items_list.append(config_item)

                config_group_repo.bulk_create_plugin_config_group(plugin_config_meta_list)
                config_item_repo.bulk_create_items(config_items_list)

            event_id = make_uuid()
            plugin_build_version.event_id = event_id
            plugin_build_version.plugin_version_status = "fixed"

            self.create_region_plugin(region, tenant, plugin_base_info)

            self.build_plugin(region, plugin_base_info, plugin_build_version, user, tenant, event_id)
            plugin_build_version.build_status = "build_success"
            plugin_build_version.save()
        except Exception as e:
            logger.exception(e)
            if plugin_base_info:
                self.delete_plugin(region, tenant, plugin_base_info.plugin_id, is_force=True)
            raise e

    def update_region_plugin_info(self, region, tenant, tenant_plugin, plugin_build_version):
        data = dict()
        data["build_model"] = tenant_plugin.build_source
        data["git_url"] = tenant_plugin.code_repo
        data["image_url"] = "{0}:{1}".format(tenant_plugin.image, plugin_build_version.image_tag)
        data["plugin_info"] = tenant_plugin.desc
        data["plugin_model"] = tenant_plugin.category
        data["plugin_name"] = tenant_plugin.plugin_name
        region_api.update_plugin_info(region, tenant.tenant_name, tenant_plugin.plugin_id, data)

    @transaction.atomic
    def delete_plugin(self, region, team, plugin_id, ignore_cluster_resource=False, is_force=False):
        services = app_plugin_relation_repo.get_used_plugin_services(plugin_id)
        if services and not is_force:
            raise ErrPluginIsUsed
        if not ignore_cluster_resource:
            try:
                region_api.delete_plugin(region, team.tenant_name, plugin_id)
            except region_api.CallApiError as e:
                if e.status != 404:
                    raise ServiceHandleException(msg="delete plugin form cluster failure", msg_show="从集群删除插件失败")
        app_plugin_relation_repo.delete_service_plugin_relation_by_plugin_id(plugin_id)
        app_plugin_attr_repo.delete_attr_by_plugin_id(plugin_id)
        plugin_version_repo.delete_build_version_by_plugin_id(team.tenant_id, plugin_id)
        plugin_repo.delete_by_plugin_id(team.tenant_id, plugin_id)
        config_item_repo.delete_config_items_by_plugin_id(plugin_id)
        config_group_repo.delete_config_group_by_plugin_id(plugin_id)

    def get_default_plugin(self, region, tenant):
        # 兼容3.5版本升级
        plugins = plugin_repo.get_tenant_plugins(tenant.tenant_id,
                                                 region).filter(origin_share_id__in=[plugin for plugin in default_plugins])
        if plugins:
            return plugins
        else:
            q = Q(category="analyst-plugin:perf", image=PluginImage.RUNNER)
            q |= Q(category="analyst-plugin:perf", image=IMAGE_REPO)
            return plugin_repo.get_tenant_plugins(tenant.tenant_id, region).filter(q)

    def get_default_plugin_from_cache(self, region, tenant):
        if not self.all_default_config:
            raise Exception("no config was found")

        default_plugin_list = []
        for plugin in self.all_default_config:
            default_plugin_list.append({
                "category": plugin,
                "plugin_alias": self.all_default_config[plugin].get("plugin_alias"),
                "desc": self.all_default_config[plugin].get("desc"),
                "plugin_type": self.all_default_config[plugin].get("category"),
            })

        installed_default_plugins = self.get_default_plugin(region, tenant)
        installed_default_plugin_alias_list = [plugin.plugin_alias for plugin in installed_default_plugins]

        for plugin in default_plugin_list:
            plugin["has_install"] = False
            if plugin["plugin_alias"] in installed_default_plugin_alias_list:
                plugin["has_install"] = True

        return default_plugin_list
