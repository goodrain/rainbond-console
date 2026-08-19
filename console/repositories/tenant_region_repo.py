# -*- coding: utf-8 -*-
from typing import Any

from www.db.base import BaseConnection
from www.models.main import TenantRegionInfo


class TenantRegionRepo(object):
    def count_by_tenant_id(self, tenant_id: str) -> Any:
        sql = """
        SELECT
            count( * ) as total
        FROM
            region_info a
            LEFT JOIN tenant_region b ON a.region_name = b.region_name
        WHERE
            b.tenant_id = %s
        """
        conn = BaseConnection()
        result = conn.query(sql, [tenant_id])
        return result[0]["total"]

    def get_by_tenant_id_and_region_name(self, tenant_id: str, region_name: str) -> TenantRegionInfo:
        return TenantRegionInfo.objects.get(
            tenant_id=tenant_id, region_name=region_name, is_active=True, is_init=True)


tenant_region_repo = TenantRegionRepo()
