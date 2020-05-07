# -*- coding: utf-8 -*-
from www.db.base import BaseConnection
from www.models.main import TenantRegionInfo


class TenantRegionRepo(object):
    def count_by_tenant_id(self, tenant_id):
        sql = """
        SELECT
            count( * ) as total
        FROM
            region_info a
            LEFT JOIN tenant_region b ON a.region_name = b.region_name
        WHERE
            b.tenant_id = "{tenant_id}"
        """.format(tenant_id=tenant_id)
        conn = BaseConnection()
        result = conn.query(sql)
        return result[0]["total"]

    def get_by_tenant_id_and_region_name(self, tenant_id, region_name):
        return TenantRegionInfo.objects.get(tenant_id=tenant_id, region_name=region_name, is_active=1, is_init=1)


tenant_region_repo = TenantRegionRepo()
