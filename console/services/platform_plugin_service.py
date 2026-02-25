# -*- coding: utf8 -*-
import json
import logging

from console.appstore.appstore import app_store
from console.exception.main import ServiceHandleException
from console.models.main import AppMarket
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
from console.utils.restful_client import get_market_client
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

MARKET_HOST = "https://hub.grapps.cn"
MARKET_DOMAIN = "enterprise"
PLUGIN_TEAM_NAME = "rbd-plugins"
PLUGIN_TEAM_ALIAS = "平台插件"


class PlatformPluginService(object):
    def list_platform_plugins(self, enterprise_id, region_name):
        """
        List platform plugins by merging license plugin_mapping,
        market app info, and installed RBDPlugin CRs.
        """
        # 1. Get license status for plugin_mapping and access_key
        plugin_mapping = {}
        plugin_names = {}
        access_key = ""
        try:
            body = license_service.get_license_status(
                enterprise_id, region_name)
            bean = body.get("bean", {}) if body else {}
            plugin_mapping = bean.get("plugin_mapping", {})
            plugin_names = bean.get("plugin_names", {})
            access_key = bean.get("access_key", "")
        except Exception as e:
            logger.warning("Failed to get license status: %s", e)

        # 2. Get installed RBDPlugin CRs from region
        installed_plugins = {}
        try:
            _, body = region_api.list_plugins(
                enterprise_id, region_name, False)
            plugins = body.get("list") or []
            for p in plugins:
                installed_plugins[p.get("name", "")] = p
        except Exception as e:
            logger.warning("Failed to list region plugins: %s", e)

        # 3. Map region_app_id → console app_id for installed plugins
        region_app_id_map = {}
        region_app_ids = []
        for p in installed_plugins.values():
            raid = p.get("region_app_id", "")
            if raid:
                region_app_ids.append(raid)
        if region_app_ids:
            try:
                region_apps = region_app_repo.list_by_region_app_ids(region_name, region_app_ids)
                for ra in region_apps:
                    region_app_id_map[ra.region_app_id] = ra.app_id
            except Exception as e:
                logger.warning("Failed to map region_app_ids: %s", e)

        # 4. Fetch market info for each plugin in plugin_mapping
        result = []
        market_client = None
        if access_key:
            try:
                market_client = get_market_client(access_key, MARKET_HOST)
            except Exception as e:
                logger.warning("Failed to create market client: %s", e)

        for plugin_id, app_key in plugin_mapping.items():
            plugin_info = {
                "plugin_id": plugin_id,
                "app_key": app_key,
                "plugin_name": plugin_names.get(plugin_id, plugin_id),
                "description": "",
                "logo": "",
                "installed": False,
                "status": "",
                "latest_version": "",
                "installed_version": "",
                "upgradeable": False,
                "team_name": "",
                "app_id": -1,
                "name": plugin_id,
                "plugin_type": "",
                "plugin_views": [],
            }

            # Try to get app info from market
            if market_client and app_key:
                try:
                    app = market_client.get_user_app_detail(
                        app_id=app_key, market_domain=MARKET_DOMAIN, _return_http_data_only=True)
                    if app:
                        plugin_info["plugin_name"] = getattr(app, "name", "") or plugin_id
                        plugin_info["description"] = getattr(app, "desc", "") or ""
                        plugin_info["logo"] = getattr(app, "logo", "") or ""
                except Exception as e:
                    logger.warning("Failed to get market app info for %s: %s", app_key, e)
                    market_client = None
                # Get latest version separately
                if market_client:
                    try:
                        versions_resp = market_client.get_user_app_versions(
                            app_id=app_key, market_domain=MARKET_DOMAIN, query_all=False, _return_http_data_only=True)
                        if versions_resp and versions_resp.versions:
                            plugin_info["latest_version"] = versions_resp.versions[0].app_version or ""
                    except Exception as e:
                        logger.warning("Failed to get market app versions for %s: %s", app_key, e)
                        market_client = None

            # Check install status from RBDPlugin CRs
            if plugin_id in installed_plugins:
                plugin_info["installed"] = True
                p = installed_plugins[plugin_id]
                plugin_info["status"] = p.get("status", "")
                plugin_info["team_name"] = p.get("team_name", "")
                raid = p.get("region_app_id", "")
                console_app_id = region_app_id_map.get(raid, -1)
                plugin_info["app_id"] = console_app_id
                plugin_info["plugin_type"] = p.get("plugin_type", "")
                plugin_info["plugin_views"] = p.get("plugin_views", [])
                # Get installed version from tenant_service_group
                if console_app_id > 0:
                    cgroups = tenant_service_group_repo.get_group_by_app_id(console_app_id)
                    if cgroups:
                        plugin_info["installed_version"] = cgroups.last().group_version or ""
                # Compare versions
                if plugin_info["latest_version"] and plugin_info["installed_version"]:
                    plugin_info["upgradeable"] = plugin_info["latest_version"] != plugin_info["installed_version"]

            result.append(plugin_info)

        return result

    def install_platform_plugin(self, enterprise_id, region_name, plugin_id, user):
        """
        Install a platform plugin: auto-create team/app, fetch from market, install.
        """
        # 1. Get license status and validate plugin_id
        body = license_service.get_license_status(enterprise_id, region_name)
        bean = body.get("bean", {}) if body else {}
        plugin_mapping = bean.get("plugin_mapping", {})
        plugin_names = bean.get("plugin_names", {})
        access_key = bean.get("access_key", "")

        if plugin_id not in plugin_mapping:
            raise ServiceHandleException(msg="plugin not authorized", msg_show="该插件未授权")
        if not access_key:
            raise ServiceHandleException(msg="no access_key in license", msg_show="授权信息中缺少 access_key")

        app_key = plugin_mapping[plugin_id]
        plugin_name = plugin_names.get(plugin_id, plugin_id)

        # 2. Construct temporary AppMarket (no DB record needed)
        market = AppMarket(
            name="__platform_plugin__",
            url=MARKET_HOST,
            domain=MARKET_DOMAIN,
            access_key=access_key,
        )

        # 3. Get latest version from market
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
