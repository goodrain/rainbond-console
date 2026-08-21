# -*- coding: utf-8 -*-
from typing import Any

from console.models.main import RegionConfig
from www.models.main import TenantRegionInfo


class TenantRegionRepo(object):
    def count_by_tenant_id(self, tenant_id: str) -> Any:
        region_names = TenantRegionInfo.objects.filter(tenant_id=tenant_id).values_list("region_name", flat=True)
        return RegionConfig.objects.filter(region_name__in=region_names).count()

    def get_by_tenant_id_and_region_name(self, tenant_id: str, region_name: str) -> TenantRegionInfo:
        return TenantRegionInfo.objects.get(
            tenant_id=tenant_id, region_name=region_name, is_active=True, is_init=True)


tenant_region_repo = TenantRegionRepo()
