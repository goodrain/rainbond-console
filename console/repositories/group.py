# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""

import logging

from www.models import ServiceGroup, ServiceGroupRelation, TenantServiceGroup

logger = logging.getLogger("default")


class GroupRepository(object):
    def list_tenant_group_on_region(self, tenant, region_name):
        return ServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name)

    def add_group(self, tenant_id, region_name, group_name):
        group = ServiceGroup.objects.create(tenant_id=tenant_id, region_name=region_name, group_name=group_name)
        return group

    def get_group_by_unique_key(self, tenant_id, region_name, group_name):
        groups = ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name, group_name=group_name)
        if groups:
            return groups[0]
        return None

    def get_group_by_pk(self, tenant_id, region_name, group_id):
        try:
            return ServiceGroup.objects.get(tenant_id=tenant_id, region_name=region_name, pk=group_id)
        except ServiceGroup.DoesNotExist:
            return None

    def update_group_name(self, group_id, new_group_name):
        ServiceGroup.objects.filter(pk=group_id).update(group_name=new_group_name)

    def delete_group_by_pk(self, group_id):
        logger.debug("delete group id {0}".format(group_id))
        ServiceGroup.objects.filter(pk=group_id).delete()

    def get_group_count_by_team_id_and_group_id(self, team_id, group_id):
        group_count = ServiceGroup.objects.filter(tenant_id=team_id, ID=group_id).count()
        return group_count

    def get_tenant_region_groups(self,team_id,region):
        return ServiceGroup.objects.filter(tenant_id=team_id,region_name=region)

    def get_group_by_id(self, group_id):
        return ServiceGroup.objects.filter(pk=group_id).filter()

class GroupServiceRelationRepository(object):
    def delete_relation_by_group_id(self, group_id):
        ServiceGroupRelation.objects.filter(group_id=group_id).delete()

    def delete_relation_by_service_id(self, service_id):
        ServiceGroupRelation.objects.filter(service_id=service_id).delete()

    def add_service_group_relation(self, group_id, service_id, tenant_id, region_name):
        sgr = ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id, tenant_id=tenant_id,
                                                  region_name=region_name)
        return sgr

    def get_group_by_service_id(self, service_id):
        sgrs = ServiceGroupRelation.objects.filter(service_id=service_id)
        if sgrs:
            return sgrs[0]
        return None

    def get_group_by_service_ids(self, service_ids):
        sgr = ServiceGroupRelation.objects.filter(service_id__in=service_ids)
        sgr_map = {s.service_id: s.group_id for s in sgr}
        group_ids = [g.group_id for g in sgr]
        groups = ServiceGroup.objects.filter(ID__in=group_ids)
        group_map = {g.ID: g.group_name for g in groups}
        result_map = {}
        for service_id in service_ids:
            group_id = sgr_map.get(service_id, None)
            group_info = dict()
            if group_id:
                group_info["group_name"] = group_map[group_id]
                group_info["group_id"] = group_id
                result_map[service_id] = group_info
            else:
                group_info["group_name"] = "未分组"
                group_info["group_id"] = -1
                result_map[service_id] = group_info

        return result_map

    def create_service_group_relation(self, **params):
        return ServiceGroupRelation.objects.create(**params)

    def get_service_group_relation_by_groups(self,group_ids):
        return ServiceGroupRelation.objects.filter(group_id__in=group_ids)

    def get_services_by_group(self, group_id):
        return ServiceGroupRelation.objects.filter(group_id=group_id)

class TenantServiceGroupRepository(object):
    def delete_tenant_service_group_by_pk(self, pk):
        TenantServiceGroup.objects.filter(ID=pk).delete()

    def create_tenant_service_group(self, **params):
        return TenantServiceGroup.objects.create(**params)


group_repo = GroupRepository()
group_service_relation_repo = GroupServiceRelationRepository()
# 应用组实体
tenant_service_group_repo = TenantServiceGroupRepository()
