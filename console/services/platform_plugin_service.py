# -*- coding: utf8 -*-
import logging

from console.services.license import license_service
from console.utils.restful_client import get_market_client
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

MARKET_HOST = "https://hub.grapps.cn"


class PlatformPluginService(object):
    def list_platform_plugins(self, enterprise_id, region_name):
        """
        List platform plugins by merging license plugin_mapping,
        market app info, and installed RBDPlugin CRs.
        """
        # 1. Get license status for plugin_mapping and access_key
        plugin_mapping = {}
        access_key = ""
        try:
            body = license_service.get_license_status(
                enterprise_id, region_name)
            bean = body.get("bean", {}) if body else {}
            plugin_mapping = bean.get("plugin_mapping", {})
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

        # 3. Fetch market info for each plugin in plugin_mapping
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
                "plugin_name": plugin_id,
                "description": "",
                "logo": "",
                "installed": False,
                "status": "",
                "version": "",
            }

            # Try to get app info from market
            if market_client and app_key:
                try:
                    app = market_client.get_app_detail(app_key)
                    if app:
                        plugin_info["plugin_name"] = app.app_name or plugin_id
                        plugin_info["description"] = getattr(app, "describe", "") or ""
                        plugin_info["logo"] = getattr(app, "logo", "") or ""
                        plugin_info["version"] = getattr(app, "version", "") or ""
                except Exception as e:
                    logger.warning("Failed to get market app info for %s: %s", app_key, e)

            # Check install status from RBDPlugin CRs
            if plugin_id in installed_plugins:
                plugin_info["installed"] = True
                p = installed_plugins[plugin_id]
                plugin_info["status"] = p.get("status", "")

            result.append(plugin_info)

        return result


platform_plugin_service = PlatformPluginService()
