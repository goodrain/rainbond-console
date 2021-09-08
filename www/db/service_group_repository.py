# -*- coding: utf-8 -*-
# creater by: barnett
# -*- coding:utf-8 -*-

import logging

from www.db.base import BaseConnection
from www.models.main import ServiceGroup, ServiceGroupRelation

logger = logging.getLogger("default")


class ServiceGroupRepository(object):
    def get_rel_region(self, service_id, tenant_id, region):
        try:
            return ServiceGroupRelation.objects.get(service_id=service_id, tenant_id=tenant_id, region_name=region)
        except ServiceGroupRelation.DoesNotExist:
            return None

    def get_by_pk(self, pk):
        try:
            return ServiceGroup.objects.get(pk=pk)
        except ServiceGroup.DoesNotExist:
            return None

    def check_non_default_group_by_eid(self, eid):
        conn = BaseConnection()
        sql = """
        SELECT
            group_name
        FROM
            service_group a,
            tenant_info b
        WHERE
            a.tenant_id = b.tenant_id
            AND a.is_default = 0
            AND b.enterprise_id = "{eid}"
        LIMIT 1;
        """.format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False


svc_grop_repo = ServiceGroupRepository()
