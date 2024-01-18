# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
import logging

from datetime import datetime
from django.db.models import Q

from console.exception.bcode import ErrComponentGroupNotFound
from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import (ServiceGroup, ServiceGroupRelation, TenantServiceGroup)

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class GroupRepository(object):
    @staticmethod
    def create(app):
        app.save()

    @staticmethod
    def update(app_id, **data):
        ServiceGroup.objects.filter(pk=app_id).update(**data)

    def list_tenant_group_on_region(self, tenant, region_name):
        return ServiceGroup.objects.filter(
            tenant_id=tenant.tenant_id, region_name=region_name).order_by("-update_time", "-order_index")

    def add_group(self, tenant, region_name, group_name, group_note="", is_default=False, username=""):
        group = ServiceGroup.objects.create(
            tenant_id=tenant.tenant_id,
            region_name=region_name,
            group_name=group_name,
            note=group_note,
            is_default=is_default,
            username=username,
            update_time=datetime.now(),
            create_time=datetime.now())
        self.create_region_app(tenant, region_name, group, "")
        return group

    def update_group_time(self, group_id):
        ServiceGroup.objects.filter(pk=group_id).update(update_time=datetime.now())

    def get_group_by_unique_key(self, tenant_id, region_name, group_name):
        groups = ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name, group_name=group_name)
        if groups:
            return groups[0]
        return None

    def is_k8s_app_duplicate(self, tenant_id, region_name, k8s_app, app_id=None):
        if not k8s_app:
            return False
        if app_id:
            return ServiceGroup.objects.filter(
                tenant_id=tenant_id, region_name=region_name, k8s_app=k8s_app).exclude(ID=app_id).count() > 0
        return ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name, k8s_app=k8s_app).count() > 0

    # get_group_by_pk get group by group id and tenantid and region name
    def get_group_by_pk(self, tenant_id, region_name, app_id):
        try:
            return ServiceGroup.objects.get(tenant_id=tenant_id, region_name=region_name, pk=app_id)
        except ServiceGroup.DoesNotExist:
            return None

    def update_group_name(self, group_id, new_group_name, group_note=""):
        ServiceGroup.objects.filter(pk=group_id).update(group_name=new_group_name, note=group_note, update_time=datetime.now())

    def update_governance_mode(self, tenant_id, region_name, app_id, governance_mode):
        ServiceGroup.objects.filter(pk=app_id).update(
            tenant_id=tenant_id, region_name=region_name, governance_mode=governance_mode, update_time=datetime.now())

    def delete_group_by_pk(self, group_id):
        logger.debug("delete group id {0}".format(group_id))
        ServiceGroup.objects.filter(pk=group_id).delete()

    def get_group_count_by_team_id_and_group_id(self, team_id, group_id):
        group_count = ServiceGroup.objects.filter(tenant_id=team_id, ID=group_id).count()
        return group_count

    def get_tenant_region_groups(self, team_id, region, query="", app_type=""):
        q = Q(tenant_id=team_id, region_name=region, group_name__icontains=query)
        if app_type:
            q &= Q(app_type=app_type)
        return ServiceGroup.objects.filter(q).order_by("-update_time", "-order_index")

    def get_tenant_region_groups_count(self, team_id, region):
        return ServiceGroup.objects.filter(tenant_id=team_id, region_name=region).count()

    def get_tenant_groups_count(self, team_id):
        return ServiceGroup.objects.filter(tenant_id=team_id).count()

    def get_groups_by_tenant_ids(self, tenant_ids):
        return ServiceGroup.objects.filter(tenant_id__in=tenant_ids).order_by("-update_time", "-order_index")

    def get_group_by_id(self, group_id):
        return ServiceGroup.objects.filter(pk=group_id).first()

    def get_default_by_service(self, service):
        return ServiceGroup.objects.filter(
            tenant_id=service.tenant_id, region_name=service.service_region, is_default=True).first()

    def get_or_create_default_group(self, tenant, region_name):
        # 查询是否有团队在当前数据中心是否有默认应用，没有创建
        group = ServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name).first()
        if not group:
            return self.add_group(tenant=tenant, region_name=region_name, group_name="默认应用", is_default=True)
        return group

    def create_region_app(self, tenant, region_name, app, eid=""):
        region_app = region_api.create_application(
            region_name, tenant.tenant_name, {
                "eid": eid,
                "app_name": app.group_name,
                "app_type": app.app_type,
                "app_store_name": app.app_store_name,
                "app_store_url": app.app_store_url,
                "app_template_name": app.app_template_name,
                "version": app.version,
                "k8s_app": app.k8s_app,
            })

        # record the dependencies between region app and console app
        data = {
            "region_name": region_name,
            "region_app_id": region_app["app_id"],
            "app_id": app.ID,
        }
        region_app_repo.create(**data)
        # 集群端创建完应用后，再更新控制台的应用名称
        app.k8s_app = region_app["k8s_app"]
        app.save()

    def get_apps_list(self, team_id=None, region_name=None, query=None):
        q = Q(region_name=region_name) & Q(tenant_id=team_id)
        if query:
            q = q & Q(group_name__icontains=query)
        return ServiceGroup.objects.filter(q).order_by("-update_time", "-order_index")

    def get_multi_app_info(self, app_ids):
        return ServiceGroup.objects.filter(ID__in=app_ids).order_by("-update_time", "-order_index")

    def get_apps_in_multi_team(self, team_ids, region_names):
        return ServiceGroup.objects.filter(
            tenant_id__in=team_ids, region_name__in=region_names).order_by("-update_time", "-order_index")

    def get_by_service_id(self, tenant_id, service_id):
        try:
            rel = ServiceGroupRelation.objects.get(tenant_id=tenant_id, service_id=service_id)
            return ServiceGroup.objects.get(tenant_id=tenant_id, pk=rel.group_id)
        except ServiceGroupRelation.DoesNotExist:
            raise ServiceGroup.DoesNotExist


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
        group_name_map = {g.ID: g.group_name for g in groups}
        group_k8s_app_map = {g.ID: g.k8s_app for g in groups}
        result_map = {}
        for service_id in service_ids:
            group_id = sgr_map.get(service_id, None)
            group_info = dict()
            if group_id:
                group_info["group_name"] = group_name_map.get(group_id, "")
                group_info["group_id"] = group_id
                group_info["k8s_app"] = group_k8s_app_map.get(group_id, "")
                result_map[service_id] = group_info
            else:
                group_info["group_name"] = "未分组"
                group_info["k8s_app"] = "default"
                group_info["group_id"] = -1
                result_map[service_id] = group_info
        return result_map

    def create_service_group_relation(self, **params):
        return ServiceGroupRelation.objects.create(**params)

    def get_service_group_relation_by_groups(self, group_ids):
        return ServiceGroupRelation.objects.filter(group_id__in=group_ids)

    def get_services_by_group(self, group_id):
        return ServiceGroupRelation.objects.filter(group_id=group_id)

    @staticmethod
    def list_serivce_ids_by_app_id(tenant_id, region_name, app_id):
        relations = ServiceGroupRelation.objects.filter(tenant_id=tenant_id, region_name=region_name, group_id=app_id)
        if not relations:
            return []
        return relations.values_list("service_id", flat=True)

    @staticmethod
    def count_service_by_app_id(app_id):
        return ServiceGroupRelation.objects.filter(group_id=app_id).count()

    def get_service_by_group(self, group_id):
        return ServiceGroupRelation.objects.filter(group_id=group_id).first()

    @staticmethod
    def list_service_groups(group_id):
        return ServiceGroupRelation.objects.filter(group_id=group_id).all()

    def update_service_relation(self, group_id, default_group_id):
        ServiceGroupRelation.objects.filter(group_id=group_id).update(group_id=default_group_id)


class TenantServiceGroupRepository(object):
    def delete_tenant_service_group_by_pk(self, pk):
        TenantServiceGroup.objects.filter(ID=pk).delete()

    def create_tenant_service_group(self, **params):
        return TenantServiceGroup.objects.create(**params)

    @staticmethod
    def get_component_group(service_group_id):
        component_group = TenantServiceGroup.objects.filter(ID=service_group_id).first()
        if not component_group:
            raise ErrComponentGroupNotFound
        return component_group

    def get_group_by_app_id(self, app_id):
        return TenantServiceGroup.objects.filter(service_group_id=app_id)


group_repo = GroupRepository()
group_service_relation_repo = GroupServiceRelationRepository()
# 应用实体
tenant_service_group_repo = TenantServiceGroupRepository()
