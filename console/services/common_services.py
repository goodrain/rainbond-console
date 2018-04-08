# -*- coding: utf-8 -*-
import logging

from www.apiclient.regionapi import RegionInvokeApi
from www.models import TenantRegionInfo
from www.region import RegionInfo

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class CommonServices(object):
    def calculate_real_used_resource(self, tenant):
        totalMemory = 0
        totalDisk = 0
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True, is_init=True)
        for tenant_region in tenant_region_list:
            logger.debug(tenant_region.region_name)
            if tenant_region.region_name in RegionInfo.valid_regions():
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
        return totalMemory,totalDisk

    def calculate_cpu(self, region, memory):
        """根据内存和数据中心计算cpu"""
        min_cpu = int(memory) * 20 / 128
        if region == "ali-hz":
            min_cpu = min_cpu * 2
        return min_cpu


common_services = CommonServices()
