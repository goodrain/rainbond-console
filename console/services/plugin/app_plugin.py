# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
import logging

from console.constants import PluginCategoryConstants
from console.repositories.plugin import app_plugin_relation_repo, plugin_repo
from console.repositories.app import service_repo
from goodrain_web.tools import JuncheePaginator
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppPluginService(object):
    def get_service_abled_plugin(self, service):
        plugins = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(service.service_id).filter(
            plugin_status=True)
        plugin_ids = [p.plugin_id for p in plugins]
        base_plugins = plugin_repo.get_plugin_by_plugin_ids(plugin_ids)
        return base_plugins

    def get_plugin_used_services(self, plugin_id, tenant_id, page, page_size):
        aprr = app_plugin_relation_repo.get_used_plugin_services(plugin_id)
        service_ids = [r.service_id for r in aprr]
        service_plugin_version_map = {r.service_id: r.build_version for r in aprr}
        services = service_repo.get_services_by_service_ids(*service_ids).filter(tenant_id=tenant_id)
        paginator = JuncheePaginator(services, int(page_size))
        show_apps = paginator.page(int(page))
        data = dict()
        for s in show_apps:
            data["service_id"] = s.service_id
            data["service_alias"] = s.service_alias
            data["service_cname"] = s.service_cname
            data["build_version"] = service_plugin_version_map[s.service_id]
        return data

    def create_service_plugin_relation(self, service_id, plugin_id, build_version, service_meta_type, plugin_status):
        sprs = app_plugin_relation_repo.get_relation_by_service_and_plugin(service_id, plugin_id)
        if sprs:
            return 409, "应用已安装该插件", None
        params = {
            "service_id": service_id,
            "build_version": build_version,
            "service_meta_type": service_meta_type,
            "plugin_status": plugin_status
        }
        spr = app_plugin_relation_repo.create_service_plugin_relation(**params)
        return 200, "success", spr




class PluginService(object):
    def get_plugins_by_service_ids(self, service_ids):
        return plugin_repo.get_plugins_by_service_ids(service_ids)

    def get_plugin_by_plugin_id(self, tenant, plugin):
        plugin = plugin_repo.get_plugin_by_plugin_id(tenant.tenant_id, plugin.plugin_id)
        if plugin:
            return 200, plugin
        else:
            return 404, None

    def create_tenant_plugin(self, tenant, user_id, region, desc, plugin_alias, category, build_source, image,
                             code_repo):
        plugin_id = make_uuid()
        if build_source == "dockerfile":
            if not code_repo:
                return 400, "代码仓库不能为空", None
        if build_source == "image":
            if not image:
                return 400, "镜像地址不能为空", None
        if category not in (
                PluginCategoryConstants.OUTPUT_NET, PluginCategoryConstants.INPUT_NET,
                PluginCategoryConstants.PERFORMANCE_ANALYSIS, PluginCategoryConstants.INIT_TYPE,
                PluginCategoryConstants.COMMON_TYPE):
            return 400, "类别参数错误", None
        plugin_params = {
            "plugin_id": plugin_id,
            "tenant_id": tenant.tenant_id,
            "region": region,
            "create_user": user_id,
            "desc": desc,
            "plugin_name": "gr" + plugin_id[:6],
            "plugin_alias": plugin_alias,
            "category": category,
            "build_source": build_source,
            "image": image,
            "code_repo": code_repo
        }
        tenant_plugin = plugin_repo.create_plugin(**plugin_params)
        return 200, "success", tenant_plugin

    def create_region_plugin(self, region, tenant, tenant_plugin):
        """创建region端插件信息"""
        plugin_data = dict()
        plugin_data["build_model"] = tenant_plugin.build_source
        plugin_data["git_url"] = tenant_plugin.code_repo
        plugin_data["image_url"] = tenant_plugin.image
        plugin_data["plugin_id"] = tenant_plugin.plugin_id
        plugin_data["plugin_info"] = tenant_plugin.desc
        plugin_data["plugin_model"] = tenant_plugin.category
        plugin_data["plugin_name"] = tenant_plugin.plugin_name
        plugin_data["tenant_id"] = tenant.tenant_id
        res, body = region_api.create_plugin(region, tenant.tenant_name, plugin_data)
        logger.debug("plugin.create", "create region plugin {0}".format(body))
        return 200, "success"

    def delete_tenant_plugin(self, plugin_id):
        plugin_repo.delete_by_plugin_id(plugin_id)

    def get_plugin_event_log(self, region, tenant, event_id, level):
        data = {"event_id": event_id, "level": level}
        body = region_api.get_plugin_event_log(region, tenant.tenant_name, data)
        return body["list"]

    def get_tenant_plugins(self, region, tenant):
        return plugin_repo.get_tenant_plugins(tenant.tenant_id, region)

    def build_plugin(self, region, plugin, plugin_version, user, tenant, event_id):

        build_data = dict()

        build_data["build_version"] = plugin_version.build_version
        build_data["event_id"] = event_id
        build_data["info"] = plugin_version.update_info

        build_data["operator"] = user.nick_name
        build_data["plugin_cmd"] = plugin_version.build_cmd
        build_data["plugin_memory"] = plugin_version.min_memory
        build_data["plugin_cpu"] = plugin_version.min_cpu
        build_data["repo_url"] = plugin_version.code_version
        build_data["tenant_id"] = tenant.tenant_id
        build_data["build_image"] = plugin.image
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
