# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""

import logging
from django.db.models import Q
from www.models.main import ServiceGroup, ServiceGroupRelation, TenantServiceGroup

logger = logging.getLogger("default")


class GroupRepository(object):
    def list_tenant_group_on_region(self, tenant, region_name):
        return ServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name).order_by("-order_index")

    def add_group(self, tenant_id, region_name, group_name, group_note="", is_default=False):
        group = ServiceGroup.objects.create(
            tenant_id=tenant_id, region_name=region_name, group_name=group_name, note=group_note, is_default=is_default)
        return group

    def get_group_by_unique_key(self, tenant_id, region_name, group_name):
        groups = ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name, group_name=group_name)
        if groups:
            return groups[0]
        return None

    # get_group_by_pk get group by group id and tenantid and region name
    def get_group_by_pk(self, tenant_id, region_name, group_id):
        try:
            return ServiceGroup.objects.get(tenant_id=tenant_id, region_name=region_name, pk=group_id)
        except ServiceGroup.DoesNotExist:
            return None

    def get_app_by_pk(self, app_id):
        try:
            return ServiceGroup.objects.get(pk=app_id)
        except ServiceGroup.DoesNotExist:
            return None

    def update_group_name(self, group_id, new_group_name, group_note=""):
        ServiceGroup.objects.filter(pk=group_id).update(group_name=new_group_name, note=group_note)

    def delete_group_by_pk(self, group_id):
        logger.debug("delete group id {0}".format(group_id))
        ServiceGroup.objects.filter(pk=group_id).delete()

    def get_group_count_by_team_id_and_group_id(self, team_id, group_id):
        group_count = ServiceGroup.objects.filter(tenant_id=team_id, ID=group_id).count()
        return group_count

    def get_tenant_region_groups(self, team_id, region, query=""):
        return ServiceGroup.objects.filter(
            tenant_id=team_id, region_name=region, group_name__icontains=query).order_by("-order_index")

    def get_tenant_region_groups_count(self, team_id, region):
        return ServiceGroup.objects.filter(tenant_id=team_id, region_name=region).count()

    def get_groups_by_tenant_ids(self, tenant_ids):
        return ServiceGroup.objects.filter(tenant_id__in=tenant_ids).order_by("-order_index")

    def get_group_by_id(self, group_id):
        return ServiceGroup.objects.filter(pk=group_id).first()

    def get_default_by_service(self, service):
        return ServiceGroup.objects.filter(
            tenant_id=service.tenant_id, region_name=service.region_name, is_default=True).first()

    def get_or_create_default_group(self, tenant_id, region_name):
        # 查询是否有团队在当前数据中心是否有默认应用，没有创建
        group = ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name, is_default=True).first()
        if not group:
            return self.add_group(tenant_id=tenant_id, region_name=region_name, group_name="默认应用", is_default=True)
        return group

    def get_apps_list(self, team_id=None, region_name=None, query=None):
        q = None
        if query:
            q = q | Q(group_name__icontains=query)
        if region_name:
            q = q & Q(region_name=region_name)
        if team_id:
            q = q & Q(tenant_id=team_id)
        if q:
            return ServiceGroup.objects.filter(q).order_by("-order_index")
        return ServiceGroup.objects.all().order_by("-order_index")

    def get_multi_app_info(self, app_ids):
        return ServiceGroup.objects.filter(ID__in=app_ids).order_by("-order_index")

    def get_apps_in_multi_team(self, team_ids):
        return ServiceGroup.objects.filter(tenant_id__in=team_ids).order_by("-order_index")


class GroupServiceRelationRepository(object):
    def delete_relation_by_group_id(self, group_id):
        ServiceGroupRelation.objects.filter(group_id=group_id).delete()

    def delete_relation_by_service_id(self, service_id):
        ServiceGroupRelation.objects.filter(service_id=service_id).delete()

    def add_service_group_relation(self, group_id, service_id, tenant_id, region_name):
        sgr = ServiceGroupRelation.objects.create(
            service_id=service_id, group_id=group_id, tenant_id=tenant_id, region_name=region_name)
        return sgr

    def get_group_by_service_id(self, service_id):
        sgrs = ServiceGroupRelation.objects.filter(service_id=service_id)
        if sgrs:
            return sgrs[0]
        return None

    def get_group_info_by_service_id(self, service_id):
        sgrs = ServiceGroupRelation.objects.filter(service_id=service_id)
        if not sgrs:
            return None
        relation = sgrs[0]
        groups = ServiceGroup.objects.filter(ID=relation.group_id)
        if not groups:
            return None
        return groups[0]

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

    def get_service_group_relation_by_groups(self, group_ids):
        return ServiceGroupRelation.objects.filter(group_id__in=group_ids)

    def get_services_by_group(self, group_id):
        return ServiceGroupRelation.objects.filter(group_id=group_id)

    def get_service_by_group(self, group_id):
        return ServiceGroupRelation.objects.filter(group_id=group_id).first()

    def get_services_obj_by_group(self, group_id):
        return ServiceGroupRelation.objects.filter(group_id=group_id).all()

    def update_service_relation(self, group_id, default_group_id):
        ServiceGroupRelation.objects.filter(group_id=group_id).update(group_id=default_group_id)


class TenantServiceGroupRepository(object):
    def delete_tenant_service_group_by_pk(self, pk):
        TenantServiceGroup.objects.filter(ID=pk).delete()

    def create_tenant_service_group(self, **params):
        return TenantServiceGroup.objects.create(**params)

    def get_group_by_service_group_id(self, service_group_id):
        return TenantServiceGroup.objects.filter(ID=service_group_id).first()


group_repo = GroupRepository()
group_service_relation_repo = GroupServiceRelationRepository()
# 应用实体
tenant_service_group_repo = TenantServiceGroupRepository()
