# -*- coding: utf-8 -*-
from www.models.main import TenantRegionInfo


class TenantRegionService(object):
    def get_by_tenant_id_and_region_name(self, tenant_id: str, region_name: str) -> TenantRegionInfo:
        return TenantRegionInfo.objects.get(  # type: ignore[return-value]
            tenant_id=tenant_id,
            region_name=region_name,
            is_active=1,  # type: ignore[misc]  # NOTE: BooleanField but legacy code passes int 1
            is_init=1,  # type: ignore[misc]  # NOTE: BooleanField but legacy code passes int 1
        )
