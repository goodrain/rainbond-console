# -*- coding: utf8 -*-
import base64
import json
import os
import logging

from console.services.config_service import EnterpriseConfigService
from console.models.main import ConsoleSysConfig
from console.repositories.region_repo import region_repo
from www.apiclient.regionapi import RegionInvokeApi
from console.exception.main import ServiceHandleException

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


def _decode_authz_code(authz_code):
    """Decode base64 authz_code to extract plugin info locally (no verification)."""
    try:
        data = base64.b64decode(authz_code)
        return json.loads(data)
    except Exception:
        return {}


def _build_plugins_list(plugin_mapping, plugin_names):
    """Build plugins list from plugin_mapping + plugin_names."""
    plugins = []
    for pid, app_key in plugin_mapping.items():
        plugins.append({
            "plugin_id": pid,
            "app_key": app_key,
            "name": plugin_names.get(pid, pid),
        })
    return plugins


class LicenseService(object):
    def get_licenses(self, enterprise_id):
        authz = ConsoleSysConfig.objects.filter(key="AUTHZ_CODE").first()
        if not authz or not authz.value:
            return "", None
        regions = region_repo.get_usable_regions(enterprise_id)
        region = regions.first()
        if not region:
            # No cluster: decode authz_code locally for plugin info
            token = _decode_authz_code(authz.value)
            pm = token.get("plugin_mapping", {})
            pn = token.get("plugin_names", {})
            return authz.value, {
                "authz_code": authz.value,
                "valid": False,
                "reason": "no_region",
                "plugins": _build_plugins_list(pm, pn),
            }
        bean = {}
        try:
            body = region_api.get_license_status(enterprise_id, region.region_name)
            bean = body.get("bean", {}) if body else {}
        except Exception as e:
            logger.warning("get license status from region %s: %s", region.region_name, e)
        # Auto-activate: if cluster has no valid license but DB has authz_code
        if not bean.get("valid") and authz.value:
            reason = bean.get("reason", "")
            if "no license" in reason or not bean:
                try:
                    logger.info("auto-activating license on region %s", region.region_name)
                    region_api.activate_license(enterprise_id, region.region_name, authz.value)
                    body = region_api.get_license_status(enterprise_id, region.region_name)
                    bean = body.get("bean", {}) if body else {}
                except Exception as e:
                    logger.warning("auto-activate license on region %s failed: %s", region.region_name, e)
        plugin_mapping = bean.get("plugin_mapping", {})
        plugin_names = bean.get("plugin_names", {})
        resp = {
            "authz_code": authz.value,
            "valid": bean.get("valid", False),
            "reason": bean.get("reason", ""),
            "code": bean.get("code", ""),
            "enterprise_id": bean.get("enterprise_id", ""),
            "company": bean.get("company", ""),
            "contact": bean.get("contact", ""),
            "tier": bean.get("tier", ""),
            "cluster_id": bean.get("cluster_id", ""),
            "plugin_mapping": plugin_mapping,
            "plugins": _build_plugins_list(plugin_mapping, plugin_names),
            "start_at": bean.get("start_at", 0),
            "expire_at": bean.get("expire_at", 0),
            "subscribe_until": bean.get("subscribe_until", 0),
            "cluster_limit": bean.get("cluster_limit", 0),
            "node_limit": bean.get("node_limit", 0),
            "memory_limit": bean.get("memory_limit", 0),
            "cpu_limit": bean.get("cpu_limit", 0),
            "access_key": bean.get("access_key", ""),
        }
        return authz.value, resp

    def update_license(self, enterprise_id, authz_code):
        config = ConsoleSysConfig.objects.update_or_create(key="AUTHZ_CODE", enterprise_id=enterprise_id, defaults={"value": authz_code})
        # Try to activate on all available regions
        regions = region_repo.get_usable_regions(enterprise_id)
        for region in regions:
            try:
                region_api.activate_license(enterprise_id, region.region_name, authz_code)
                logger.info("license activated on region %s", region.region_name)
            except Exception as e:
                logger.warning("failed to activate license on region %s: %s", region.region_name, e)
        config_dict = {
            "id": config[0].ID,
            "key": config[0].key,
            "value": config[0].value
        }
        return config_dict

    def get_cluster_id(self, enterprise_id, region_name):
        body = region_api.get_license_cluster_id(enterprise_id, region_name)
        return body

    def activate_license(self, enterprise_id, region_name, license_code):
        body = region_api.activate_license(enterprise_id, region_name, license_code)
        return body

    def get_license_status(self, enterprise_id, region_name):
        body = region_api.get_license_status(enterprise_id, region_name)
        return body


license_service = LicenseService()
