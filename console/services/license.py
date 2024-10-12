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
    def get_licenses(self):
        authz = ConsoleSysConfig.objects.filter(key="AUTHZ_CODE").first()
        end_time = os.getenv("END_TIME", "2024-12-13 11:01:15")
        company = os.getenv("COMPANY", "好雨科技")
        contact = os.getenv("CONTACT", "020-12345678")
        expect_cluster = int(os.getenv("EXPECT_CLUSTER", 3))
        actual_cluster = int(os.getenv("ACTUAL_CLUSTER", 2))
        expect_node = int(os.getenv("EXPECT_NODE", -1))
        actual_node = int(os.getenv("ACTUAL_NODE", 3))
        expect_memory = int(os.getenv("EXPECT_MEMORY", -1))
        actual_memory = int(os.getenv("ACTUAL_MEMORY", 54))
        resp = {
            "authz_code": authz.value if authz else "",
            "end_time": end_time,
            "company": company,
            "contact": contact,
            "expect_cluster": expect_cluster,
            "actual_cluster": actual_cluster,
            "expect_node": expect_node,
            "actual_node": actual_node,
            "expect_memory": expect_memory,
            "actual_memory": actual_memory,
        }
        return resp

    def update_license(self, enterprise_id, authz_code):
        config = ConsoleSysConfig.objects.update_or_create(key="AUTHZ_CODE", enterprise_id=enterprise_id, defaults={"value": authz_code})
        config_dict = {
            "id": config[0].ID,
            "key": config[0].key,
            "value": config[0].value
        }
        return config_dict


license_service = LicenseService()
