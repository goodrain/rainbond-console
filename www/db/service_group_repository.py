# -*- coding: utf-8 -*-
# creater by: barnett
# -*- coding:utf-8 -*-

import logging

from www.models.main import ServiceGroup, ServiceGroupRelation, Tenants

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
        tenant_ids = Tenants.objects.filter(enterprise_id=eid).values_list("tenant_id", flat=True)
        return ServiceGroup.objects.filter(tenant_id__in=tenant_ids, is_default=False).exists()


svc_grop_repo = ServiceGroupRepository()
