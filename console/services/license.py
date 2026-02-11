# -*- coding: utf8 -*-
import os
import logging

from console.services.config_service import EnterpriseConfigService
from console.models.main import ConsoleSysConfig
from console.repositories.region_repo import region_repo
from www.apiclient.regionapi import RegionInvokeApi
from console.exception.main import ServiceHandleException

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class LicenseService(object):
    def get_licenses(self, enterprise_id):
        authz = ConsoleSysConfig.objects.filter(key="AUTHZ_CODE").first()
        if not authz or not authz.value:
            return "", None
        region = region_repo.get_usable_regions(enterprise_id)
        code, resp = region_api.get_region_license(region=region.first())
        if code != 200:
            return authz.value, None
        if not resp.get("bean"):
            return authz.value, None
        bean = resp["bean"]
        resp = {
            "authz_code": authz.value,
            "valid": bean.get("valid", False),
            "reason": bean.get("reason", ""),
            "code": bean.get("code", ""),
            "company": bean.get("company", ""),
            "contact": bean.get("contact", ""),
            "tier": bean.get("tier", ""),
            "cluster_id": bean.get("cluster_id", ""),
            "start_at": bean.get("start_at", 0),
            "expire_at": bean.get("expire_at", 0),
            "subscribe_until": bean.get("subscribe_until", 0),
            "node_limit": bean.get("node_limit", 0),
            "memory_limit": bean.get("memory_limit", 0),
            "cpu_limit": bean.get("cpu_limit", 0),
        }
        return authz.value, resp

    def update_license(self, enterprise_id, authz_code):
        config = ConsoleSysConfig.objects.update_or_create(key="AUTHZ_CODE", enterprise_id=enterprise_id, defaults={"value": authz_code})
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
