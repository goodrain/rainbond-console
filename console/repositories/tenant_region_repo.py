# -*- coding: utf-8 -*-
from www.models.main import TenantRegionInfo


class TenantRegionRepo(object):

    def count_by_tenant_id(self, tenant_id):
        return TenantRegionInfo.objects.filter(tenant_id=tenant_id).count()

    def get_by_tenant_id_and_region_name(self, tenant_id, region_name):
        return TenantRegionInfo.objects.get(tenant_id=tenant_id, region_name=region_name, is_active=1, is_init=1)


tenant_region_repo = TenantRegionRepo()
