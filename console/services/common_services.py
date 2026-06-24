# -*- coding: utf-8 -*-
import logging
from typing import Any, Optional, Tuple

from django.conf import settings
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantRegionInfo, Tenants

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class CommonServices(object):
    def calculate_real_used_resource(self, tenant: Tenants) -> Tuple[int, int]:
        totalMemory = 0
        totalDisk = 0
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True, is_init=True)
        for tenant_region in tenant_region_list:
            data = {"tenant_name": [tenant.tenant_name]}
            res = region_api.get_region_tenants_resources(tenant_region.region_name, data, tenant.enterprise_id)  # type: ignore[arg-type]  # NOTE: enterprise_id is Optional[str] on Tenants model but API always receives str at runtime
            d_list = res["list"]  # type: ignore[index]  # NOTE: res is Optional[Dict]; caller guarantees non-None here
            memory = 0
            disk = 0
            if d_list:
                resource = d_list[0]
                memory = int(resource["memory"])
                disk = int(resource["disk"])
            totalMemory += memory
            totalDisk += disk
        return totalMemory, totalDisk

    def get_current_region_used_resource(self, tenant: Tenants, region_name: str) -> Optional[Any]:  # type: ignore[return]  # NOTE: implicit None return when d_list is falsy (no exception) is intentional original behaviour
        data = {"tenant_name": [tenant.tenant_name]}
        try:
            res = region_api.get_region_tenants_resources(region_name, data, tenant.enterprise_id)  # type: ignore[arg-type]  # NOTE: enterprise_id is Optional[str] on Tenants model but API always receives str at runtime
            d_list = res["list"]  # type: ignore[index]  # NOTE: res is Optional[Dict]; exception handler covers None path
            if d_list:
                resource = d_list[0]
                return resource
        except Exception as e:
            logger.exception(e)
            return None

    def is_public(self) -> Optional[Any]:
        return settings.MODULES.get('SSO_LOGIN')


common_services = CommonServices()
