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
            "end_time": bean.get("end_time", ""),
            "company": bean.get("company", ""),
            "contact": bean.get("contact", ""),
            "expect_cluster": bean.get("expect_cluster", 0),
            "actual_cluster": bean.get("actual_cluster", 0),
            "expect_node": bean.get("expect_node", 0),
            "actual_node": bean.get("actual_node", 0),
            "expect_memory": bean.get("expect_memory", 0),
            "actual_memory": bean.get("actual_memory", 0),
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


license_service = LicenseService()
