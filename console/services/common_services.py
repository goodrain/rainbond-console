# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantRegionInfo

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class CommonServices(object):
    def calculate_real_used_resource(self, tenant):
        totalMemory = 0
        totalDisk = 0
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True, is_init=True)
        for tenant_region in tenant_region_list:
            data = {"tenant_name": [tenant.tenant_name]}
            res = region_api.get_region_tenants_resources(tenant_region.region_name, data, tenant.enterprise_id)
            d_list = res["list"]
            memory = 0
            disk = 0
            if d_list:
                resource = d_list[0]
                memory = int(resource["memory"])
                disk = int(resource["disk"])
            totalMemory += memory
            totalDisk += disk
        return totalMemory, totalDisk

    def get_current_region_used_resource(self, tenant, region_name):
        data = {"tenant_name": [tenant.tenant_name]}
        try:
            res = region_api.get_region_tenants_resources(region_name, data, tenant.enterprise_id)
            d_list = res["list"]
            if d_list:
                resource = d_list[0]
                return resource
        except Exception as e:
            logger.exception(e)
            return None

    def calculate_cpu(self, memory):
        """根据内存和数据中心计算cpu"""
        min_cpu = int(memory) * 30 / 128
        return min_cpu

    def is_public(self):
        return settings.MODULES.get('SSO_LOGIN')


common_services = CommonServices()
