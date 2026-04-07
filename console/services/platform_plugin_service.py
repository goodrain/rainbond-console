# -*- coding: utf8 -*-
import json
import logging

from console.appstore.appstore import app_store
from console.exception.main import ServiceHandleException
from console.models.main import AppMarket
from console.repositories.app import app_market_repo
from console.repositories.group import group_repo, tenant_service_group_repo
from console.repositories.region_app import region_app_repo
from console.repositories.region_repo import region_repo
from console.services.app import app_market_service
from console.services.group_service import group_service
from console.services.license import license_service
from console.services.market_app.app_upgrade import AppUpgrade
from console.services.market_app_service import market_app_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

MARKET_HOST = "https://hub.grapps.cn"
MARKET_DOMAIN = "enterprise"
PLUGIN_TEAM_NAME = "rbd-plugins"
PLUGIN_TEAM_ALIAS = "平台插件"


class PlatformPluginService(object):
    def _get_license_bean(self, enterprise_id, region_name):
        try:
            body = license_service.get_license_status(enterprise_id, region_name)
            return body.get("bean", {}) if body else {}
        except Exception as e:
            logger.warning("Failed to get license status: %s", e)
            return {}

    def _get_default_market(self, enterprise_id):
        markets = app_market_repo.get_app_markets(enterprise_id)
        app_market_repo.create_default_app_market_if_not_exists(markets, enterprise_id, None)
        market = app_market_repo.get_app_markets(enterprise_id).first()
        if not market:
            raise ServiceHandleException(msg="no found app market", msg_show="默认应用市场不存在", status_code=404)
        return market

    def _get_market_platform_plugins(self, enterprise_id):
        market = self._get_default_market(enterprise_id)
        data = app_store.get_platform_plugins(market, page=1, page_size=-1)
        plugins = data.get("plugins", []) if data else []
        return market, plugins

    def _get_installed_plugins(self, enterprise_id, region_name):
        installed_plugins = {}
        try:
            _, body = region_api.list_plugins(enterprise_id, region_name, False)
            plugins = body.get("list") or []
            for plugin in plugins:
                installed_plugins[plugin.get("name", "")] = plugin
        except Exception as e:
            logger.warning("Failed to list region plugins: %s", e)
        return installed_plugins

    def _get_region_app_id_map(self, region_name, installed_plugins):
        region_app_id_map = {}
        region_app_ids = []
        for plugin in installed_plugins.values():
            region_app_id = plugin.get("region_app_id", "")
            if region_app_id:
                region_app_ids.append(region_app_id)
        if not region_app_ids:
            return region_app_id_map
        try:
            region_apps = region_app_repo.list_by_region_app_ids(region_name, region_app_ids)
            for region_app in region_apps:
                region_app_id_map[region_app.region_app_id] = region_app.app_id
        except Exception as e:
            logger.warning("Failed to map region_app_ids: %s", e)
        return region_app_id_map

    def _normalize_app_level(self, plugin_info):
        return plugin_info.get("appLevel") or plugin_info.get("app_level") or "enterprise"

    def list_platform_plugins(self, enterprise_id, region_name):
        """
        List platform plugins from app store.

        Rules:
        - 未授权前：展示应用市场中的全部平台插件
        - 已授权后：只展示免费插件 + 已授权企业插件
        """
        bean = self._get_license_bean(enterprise_id, region_name)
        plugin_mapping = bean.get("plugin_mapping", {}) or {}
        has_valid_license = bool(bean.get("valid"))
        installed_plugins = self._get_installed_plugins(enterprise_id, region_name)
        region_app_id_map = self._get_region_app_id_map(region_name, installed_plugins)
        try:
            _, market_plugins = self._get_market_platform_plugins(enterprise_id)
        except Exception as e:
            logger.warning("Failed to get market platform plugins: %s", e)
            market_plugins = []

        result = []
        for market_plugin in market_plugins:
            plugin_id = market_plugin.get("plugin_id", "")
            if not plugin_id:
                continue

            app_level = self._normalize_app_level(market_plugin)
            if has_valid_license and app_level != "free" and plugin_id not in plugin_mapping:
                continue

            plugin_info = {
                "plugin_id": plugin_id,
                "app_key": market_plugin.get("appKeyID") or market_plugin.get("app_key", ""),
                "plugin_name": market_plugin.get("plugin_name") or plugin_id,
                "name": market_plugin.get("name") or plugin_id,
                "description": market_plugin.get("description", ""),
                "logo": market_plugin.get("logo", ""),
                "app_level": app_level,
                "latest_version": market_plugin.get("latest_version", ""),
                "plugin_type": market_plugin.get("plugin_type", ""),
                "plugin_views": market_plugin.get("plugin_views", []),
                "frontend_component": market_plugin.get("frontend_component", ""),
                "entry_path": market_plugin.get("entry_path", ""),
                "menu_title": market_plugin.get("menu_title", ""),
                "route_path": market_plugin.get("route_path", ""),
                "installed": False,
                "status": "",
                "installed_version": "",
                "upgradeable": False,
                "can_upgrade": False,
                "team_name": "",
                "app_id": -1,
                "author": "Rainbond 官方",
            }

            # Check install status from RBDPlugin CRs
            if plugin_id in installed_plugins:
                plugin_info["installed"] = True
                installed_plugin = installed_plugins[plugin_id]
                plugin_info["status"] = installed_plugin.get("status", "")
                plugin_info["team_name"] = installed_plugin.get("team_name", "")
                region_app_id = installed_plugin.get("region_app_id", "")
                console_app_id = region_app_id_map.get(region_app_id, -1)
                plugin_info["app_id"] = console_app_id
                plugin_info["plugin_type"] = installed_plugin.get("plugin_type", plugin_info["plugin_type"])
                plugin_info["plugin_views"] = installed_plugin.get("plugin_views", plugin_info["plugin_views"])
                # Get installed version from tenant_service_group
                if console_app_id > 0:
                    cgroups = tenant_service_group_repo.get_group_by_app_id(console_app_id)
                    if cgroups:
                        plugin_info["installed_version"] = cgroups.last().group_version or ""
                # Compare versions
                if plugin_info["latest_version"] and plugin_info["installed_version"]:
                    plugin_info["upgradeable"] = plugin_info["latest_version"] != plugin_info["installed_version"]
                    plugin_info["can_upgrade"] = plugin_info["upgradeable"]

            result.append(plugin_info)

        return result

    def install_platform_plugin(self, enterprise_id, region_name, plugin_id, user):
        """
        Install a platform plugin: auto-create team/app, fetch from market, install.
        """
        bean = self._get_license_bean(enterprise_id, region_name)
        plugin_mapping = bean.get("plugin_mapping", {}) or {}
        plugin_names = bean.get("plugin_names", {}) or {}
        license_access_key = bean.get("access_key", "")

        default_market, market_plugins = self._get_market_platform_plugins(enterprise_id)
        market_plugin = None
        for item in market_plugins:
            if item.get("plugin_id") == plugin_id:
                market_plugin = item
                break
        if not market_plugin:
            raise ServiceHandleException(msg="plugin not found", msg_show="应用市场中未找到该插件", status_code=404)

        app_level = self._normalize_app_level(market_plugin)
        plugin_name = market_plugin.get("plugin_name") or plugin_names.get(plugin_id, plugin_id)

        if app_level == "free":
            market = default_market
            app_key = market_plugin.get("appKeyID") or market_plugin.get("app_key")
        else:
            if plugin_id not in plugin_mapping:
                raise ServiceHandleException(msg="plugin not authorized", msg_show="该插件未授权")
            if not license_access_key:
                raise ServiceHandleException(msg="no access_key in license", msg_show="授权信息中缺少 access_key")
            app_key = plugin_mapping[plugin_id]
            market = AppMarket(
                name="__platform_plugin__",
                url=MARKET_HOST,
                domain=MARKET_DOMAIN,
                access_key=license_access_key,
            )

        latest_version = market_plugin.get("latest_version", "")
        if not latest_version:
            versions_data = app_store.get_app_versions(market, app_key)
            if not versions_data or not versions_data.versions:
                raise ServiceHandleException(msg="no versions found", msg_show="应用市场中未找到该插件的版本")
            latest_version = versions_data.versions[0].app_version

        # 4. Find or create the "rbd-plugins" team
        tenant = self._ensure_plugin_team(enterprise_id, region_name, user)

        # 5. Find or create app group for this plugin
        region = region_repo.get_enterprise_region_by_region_name(enterprise_id, region_name)
        if not region:
            raise ServiceHandleException(msg="region not found", msg_show="集群不存在")
        app = self._ensure_plugin_app(tenant, region_name, plugin_name, enterprise_id, plugin_id)

        # 6. Get app template from market
        market_app, app_version = app_market_service.cloud_app_model_to_db_model(
            market, app_key, latest_version, for_install=True)
        if not app_version:
            raise ServiceHandleException(msg="app version not found", msg_show="未找到插件版本模板")

        app_template = json.loads(app_version.app_template)
        app_template["update_time"] = app_version.update_time
        app_template["arch"] = app_version.arch

        # 7. Create component group and install
        component_group = market_app_service._create_tenant_service_group(
            region_name, tenant.tenant_id, app.ID, market_app.app_id,
            latest_version, market_app.app_name)

        app_upgrade = AppUpgrade(
            enterprise_id, tenant, region, user, app,
            latest_version, component_group, app_template,
            True, "__platform_plugin__", is_deploy=True)
        app_upgrade.install()

        # 8. Create RBDPlugin CR if template has platform_plugin info
        market_app_service._create_rbdplugin_if_needed(tenant, region, app_template, app.ID)

        return {
            "plugin_id": plugin_id,
            "plugin_name": plugin_name,
            "version": latest_version,
            "team_name": tenant.tenant_name,
            "app_id": app.ID,
        }

    def _ensure_plugin_team(self, enterprise_id, region_name, user):
        """Find or create the rbd-plugins team and ensure it's initialized on the region."""
        try:
            tenant = Tenants.objects.get(namespace=PLUGIN_TEAM_NAME, enterprise_id=enterprise_id)
        except Tenants.DoesNotExist:
            from www.models.main import TenantEnterprise
            enterprise = TenantEnterprise.objects.get(enterprise_id=enterprise_id)
            tenant = team_services.create_team(
                user, enterprise, team_alias=PLUGIN_TEAM_ALIAS, namespace=PLUGIN_TEAM_NAME)
        # Ensure tenant is initialized on the region
        region_services.create_tenant_on_region(enterprise_id, tenant.tenant_name, region_name, PLUGIN_TEAM_NAME)
        return tenant

    def _ensure_plugin_app(self, tenant, region_name, plugin_name, eid, plugin_id):
        """Find or create an app group for the plugin under the rbd-plugins team."""
        apps = group_repo.get_tenant_region_groups(tenant.tenant_id, region_name)
        for app in apps:
            if app.group_name == plugin_name:
                return app
        result = group_service.create_app(tenant, region_name, plugin_name, eid=eid, k8s_app=plugin_id)
        return group_repo.get_group_by_id(result["app_id"])


platform_plugin_service = PlatformPluginService()
