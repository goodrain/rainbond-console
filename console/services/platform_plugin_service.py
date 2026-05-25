# -*- coding: utf8 -*-
import json
import logging
import os
import threading
import time

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
from console.utils.offline import is_cloud_market_disabled
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

MARKET_HOST = "https://hub.grapps.cn"
MARKET_DOMAIN = "enterprise"
PLUGIN_TEAM_NAME = "rbd-plugins"
PLUGIN_TEAM_ALIAS = "平台插件"
MARKET_PLUGIN_CACHE_TTL_SECONDS = 60


class PlatformPluginService(object):
    ARCH_PLUGIN_SUFFIXES = ("-ARM64", "-AMD64")

    def __init__(self):
        self._market_plugin_cache = {}
        self._market_plugin_cache_lock = threading.Lock()

    def clear_market_plugin_cache(self):
        with self._market_plugin_cache_lock:
            self._market_plugin_cache.clear()

    @staticmethod
    def _get_market_plugin_cache_ttl_seconds():
        try:
            return int(os.environ.get("MARKET_PLUGIN_CACHE_TTL_SECONDS", MARKET_PLUGIN_CACHE_TTL_SECONDS))
        except (TypeError, ValueError):
            return MARKET_PLUGIN_CACHE_TTL_SECONDS

    @staticmethod
    def _copy_market_plugins(plugins):
        return [dict(item) if isinstance(item, dict) else item for item in (plugins or [])]

    def _strip_plugin_arch_suffix(self, plugin_id):
        plugin_id = str(plugin_id or "").strip()
        upper_plugin_id = plugin_id.upper()
        for suffix in self.ARCH_PLUGIN_SUFFIXES:
            if upper_plugin_id.endswith(suffix):
                return plugin_id[:-len(suffix)]
        return plugin_id

    def _resolve_plugin_mapping_app_key(self, plugin_mapping, plugin_id):
        plugin_id = str(plugin_id or "").strip()
        if not plugin_id or not plugin_mapping:
            return None
        if plugin_id in plugin_mapping:
            return plugin_mapping[plugin_id]
        normalized_plugin_id = self._strip_plugin_arch_suffix(plugin_id)
        for mapping_plugin_id, app_key in plugin_mapping.items():
            if self._strip_plugin_arch_suffix(mapping_plugin_id) == normalized_plugin_id:
                return app_key
        return None

    def _is_plugin_authorized(self, plugin_mapping, plugin_id):
        return bool(self._resolve_plugin_mapping_app_key(plugin_mapping, plugin_id))

    def _extract_arch_hint(self, plugin_info):
        if not isinstance(plugin_info, dict):
            return ""
        arch_keys = [
            "arch",
            "architecture",
            "architectures",
            "arches",
            "supported_arch",
            "supported_arches",
            "supported_architectures",
            "support_arch",
            "support_arches",
            "support_architectures",
            "build_arch",
            "build_arches",
            "version_arch",
            "version_arches",
            "latest_version_arch",
            "latest_version_arches",
            "template_arch",
            "template_arches",
        ]
        for key in arch_keys:
            value = plugin_info.get(key)
            if value not in (None, "", [], {}):
                return value
        return ""

    def _plugin_debug_summary(self, plugin_info):
        if not plugin_info:
            return {}
        return {
            "plugin_id": plugin_info.get("plugin_id", ""),
            "app_key": plugin_info.get("appKeyID") or plugin_info.get("app_key", ""),
            "app_level": self._normalize_app_level(plugin_info),
            "plugin_name": plugin_info.get("plugin_name") or plugin_info.get("name", ""),
            "latest_version": plugin_info.get("latest_version", ""),
            "arch_hint": self._extract_arch_hint(plugin_info),
            "keys": sorted(plugin_info.keys()),
        }

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

    def _build_platform_market(self, enterprise_id):
        default_market = self._get_default_market(enterprise_id)
        return AppMarket(
            name="__platform_plugin__",
            url=default_market.url or MARKET_HOST,
            domain=MARKET_DOMAIN,
            access_key=default_market.access_key,
        )

    def _get_market_platform_plugins(self, enterprise_id):
        market = self._build_platform_market(enterprise_id)
        if is_cloud_market_disabled():
            logger.info("platform plugin market fetch skipped because cloud market is disabled enterprise_id=%s", enterprise_id)
            return market, []
        logger.info(
            "platform plugin market fetch enterprise_id=%s market_url=%s market_domain=%s has_access_key=%s",
            enterprise_id,
            market.url,
            market.domain,
            bool(market.access_key),
        )
        data = app_store.get_platform_plugins(market, page=1, page_size=-1)
        plugins = data.get("plugins", []) if data else []
        logger.info(
            "platform plugin market fetch result enterprise_id=%s plugin_count=%s",
            enterprise_id,
            len(plugins),
        )
        return market, plugins

    def _get_market_platform_plugins_cached(self, enterprise_id, now=None):
        ttl = self._get_market_plugin_cache_ttl_seconds()
        if ttl <= 0:
            return self._get_market_platform_plugins(enterprise_id)

        now = time.time() if now is None else now
        cache_key = enterprise_id
        with self._market_plugin_cache_lock:
            entry = self._market_plugin_cache.get(cache_key)
            if entry and entry["expires_at"] > now:
                logger.info(
                    "platform plugin market cache hit enterprise_id=%s plugin_count=%s ttl_remaining_ms=%.1f",
                    enterprise_id,
                    len(entry["plugins"]),
                    (entry["expires_at"] - now) * 1000,
                )
                return entry["market"], self._copy_market_plugins(entry["plugins"])

        logger.info("platform plugin market cache miss enterprise_id=%s", enterprise_id)
        market, plugins = self._get_market_platform_plugins(enterprise_id)
        cached_plugins = self._copy_market_plugins(plugins)
        with self._market_plugin_cache_lock:
            self._market_plugin_cache[cache_key] = {
                "expires_at": now + ttl,
                "market": market,
                "plugins": cached_plugins,
            }
        return market, self._copy_market_plugins(cached_plugins)

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

    def _select_market_plugin(self, market_plugins, plugin_id, plugin_mapping):
        candidates = [item for item in market_plugins if item.get("plugin_id") == plugin_id]
        if not candidates:
            logger.info("platform plugin select plugin_id=%s reason=no_candidates", plugin_id)
            return None

        candidate_summaries = [self._plugin_debug_summary(item) for item in candidates]
        free_candidates = [item for item in candidates if self._normalize_app_level(item) == "free"]
        if free_candidates:
            selected = free_candidates[0]
            logger.info(
                "platform plugin select plugin_id=%s reason=prefer_free candidates=%s selected=%s",
                plugin_id,
                json.dumps(candidate_summaries, ensure_ascii=False, sort_keys=True),
                json.dumps(self._plugin_debug_summary(selected), ensure_ascii=False, sort_keys=True),
            )
            return selected

        app_key = self._resolve_plugin_mapping_app_key(plugin_mapping, plugin_id)
        if app_key:
            for item in candidates:
                item_app_key = item.get("appKeyID") or item.get("app_key")
                if item_app_key == app_key:
                    logger.info(
                        "platform plugin select plugin_id=%s reason=match_license_app_key candidates=%s selected=%s",
                        plugin_id,
                        json.dumps(candidate_summaries, ensure_ascii=False, sort_keys=True),
                        json.dumps(self._plugin_debug_summary(item), ensure_ascii=False, sort_keys=True),
                    )
                    return item

        selected = candidates[0]
        logger.info(
            "platform plugin select plugin_id=%s reason=first_candidate candidates=%s selected=%s",
            plugin_id,
            json.dumps(candidate_summaries, ensure_ascii=False, sort_keys=True),
            json.dumps(self._plugin_debug_summary(selected), ensure_ascii=False, sort_keys=True),
        )
        return selected

    def list_platform_plugins(self, enterprise_id, region_name):
        """
        List platform plugins from app store.

        Rules:
        - 未授权前：展示应用市场中的全部平台插件
        - 已授权后：只展示免费插件 + 已授权企业插件
        """
        if is_cloud_market_disabled():
            logger.info(
                "platform plugin list skipped because cloud market is disabled enterprise_id=%s region_name=%s",
                enterprise_id,
                region_name,
            )
            return []
        bean = self._get_license_bean(enterprise_id, region_name)
        plugin_mapping = bean.get("plugin_mapping", {}) or {}
        has_valid_license = bool(bean.get("valid"))
        installed_plugins = self._get_installed_plugins(enterprise_id, region_name)
        region_app_id_map = self._get_region_app_id_map(region_name, installed_plugins)
        try:
            _, market_plugins = self._get_market_platform_plugins_cached(enterprise_id)
        except Exception as e:
            logger.warning("Failed to get market platform plugins: %s", e)
            market_plugins = []

        logger.info(
            "platform plugin list source summary enterprise_id=%s region_name=%s "
            "license_valid=%s mapping_keys=%s market_plugin_count=%s",
            enterprise_id,
            region_name,
            has_valid_license,
            list(plugin_mapping.keys()),
            len(market_plugins),
        )
        logger.info(
            "platform plugin list market raw enterprise_id=%s region_name=%s plugins=%s",
            enterprise_id,
            region_name,
            json.dumps(
                [self._plugin_debug_summary(item) for item in market_plugins],
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

        result = []
        selected_plugins = {}
        for market_plugin in market_plugins:
            plugin_id = market_plugin.get("plugin_id", "")
            if not plugin_id:
                continue
            if plugin_id not in selected_plugins:
                selected_plugins[plugin_id] = self._select_market_plugin(market_plugins, plugin_id, plugin_mapping)
        for plugin_id, market_plugin in selected_plugins.items():
            if not market_plugin:
                continue

            app_level = self._normalize_app_level(market_plugin)
            if has_valid_license and app_level != "free" and not self._is_plugin_authorized(
                    plugin_mapping, plugin_id):
                logger.info(
                    "platform plugin filtered by license enterprise_id=%s region_name=%s "
                    "plugin_id=%s app_level=%s mapping_keys=%s",
                    enterprise_id,
                    region_name,
                    plugin_id,
                    app_level,
                    list(plugin_mapping.keys()),
                )
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

        logger.info(
            "platform plugin list result summary enterprise_id=%s region_name=%s result_count=%s result_plugins=%s",
            enterprise_id,
            region_name,
            len(result),
            [item.get("plugin_id", "") for item in result],
        )
        return result

    def install_platform_plugin(self, enterprise_id, region_name, plugin_id, user):
        """
        Install a platform plugin: auto-create team/app, fetch from market, install.
        """
        bean = self._get_license_bean(enterprise_id, region_name)
        plugin_mapping = bean.get("plugin_mapping", {}) or {}
        plugin_names = bean.get("plugin_names", {}) or {}
        license_access_key = bean.get("access_key", "")

        platform_market, market_plugins = self._get_market_platform_plugins(enterprise_id)
        logger.info(
            "platform plugin install request enterprise_id=%s region_name=%s plugin_id=%s license_valid=%s mapping_keys=%s",
            enterprise_id,
            region_name,
            plugin_id,
            bool(bean.get("valid")),
            list(plugin_mapping.keys()),
        )
        logger.info(
            "platform plugin install market candidates plugin_id=%s candidates=%s",
            plugin_id,
            json.dumps(
                [self._plugin_debug_summary(item) for item in market_plugins if item.get("plugin_id") == plugin_id],
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        market_plugin = self._select_market_plugin(market_plugins, plugin_id, plugin_mapping)
        if not market_plugin:
            raise ServiceHandleException(msg="plugin not found", msg_show="应用市场中未找到该插件", status_code=404)

        app_level = self._normalize_app_level(market_plugin)
        plugin_name = market_plugin.get("plugin_name") or plugin_names.get(plugin_id, plugin_id)
        logger.info(
            "platform plugin install selected plugin plugin_id=%s selected=%s",
            plugin_id,
            json.dumps(self._plugin_debug_summary(market_plugin), ensure_ascii=False, sort_keys=True),
        )

        if app_level == "free":
            market = platform_market
            app_key = market_plugin.get("appKeyID") or market_plugin.get("app_key")
            logger.info(
                "platform plugin install resolved as free plugin plugin_id=%s app_key=%s latest_version=%s",
                plugin_id,
                app_key,
                market_plugin.get("latest_version", ""),
            )
        else:
            authorized_app_key = self._resolve_plugin_mapping_app_key(plugin_mapping, plugin_id)
            if not authorized_app_key:
                logger.warning(
                    "platform plugin install unauthorized enterprise plugin plugin_id=%s selected=%s mapping_keys=%s",
                    plugin_id,
                    json.dumps(self._plugin_debug_summary(market_plugin), ensure_ascii=False, sort_keys=True),
                    list(plugin_mapping.keys()),
                )
                raise ServiceHandleException(msg="plugin not authorized", msg_show="该插件未授权")
            if not license_access_key:
                raise ServiceHandleException(msg="no access_key in license", msg_show="授权信息中缺少 access_key")
            app_key = authorized_app_key
            market = AppMarket(
                name="__platform_plugin__",
                url=MARKET_HOST,
                domain=MARKET_DOMAIN,
                access_key=license_access_key,
            )
            logger.info(
                "platform plugin install resolved as enterprise plugin plugin_id=%s app_key=%s latest_version=%s",
                plugin_id,
                app_key,
                market_plugin.get("latest_version", ""),
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
