# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
import logging

from datetime import datetime
from typing import Any, Dict, List, Optional

from console.exception.bcode import ErrComponentGroupNotFound
from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi
from django.db.models import Count, Q, QuerySet
from www.models.main import (ServiceGroup, ServiceGroupRelation, TenantServiceGroup, Tenants, Users)

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class GroupRepository(object):
    @staticmethod
    def create(app: ServiceGroup) -> None:
        app.save()

    def get_app_by_pk(self, app_id: str) -> Optional[ServiceGroup]:
        try:
            return ServiceGroup.objects.get(pk=app_id)
        except ServiceGroup.DoesNotExist:
            return None

    @staticmethod
    def update(app_id: str, **data: Any) -> None:
        ServiceGroup.objects.filter(pk=app_id).update(**data)

    def list_tenant_group_on_region(self, tenant: Tenants, region_name: str) -> QuerySet:
        return ServiceGroup.objects.filter(
            tenant_id=tenant.tenant_id, region_name=region_name).order_by("-update_time", "-order_index")

    def get_tenant_group_on_region(self, app_id: str) -> ServiceGroup:
        return ServiceGroup.objects.get(ID=app_id)

    def add_group(self, tenant: Tenants, region_name: str, group_name: str, group_note: str = "",
                  is_default: bool = False, username: str = "") -> ServiceGroup:
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

    def update_group_time(self, group_id: str) -> None:
        ServiceGroup.objects.filter(pk=group_id).update(update_time=datetime.now())

    def get_group_by_unique_key(self, tenant_id: str, region_name: str, group_name: str) -> Optional[ServiceGroup]:
        groups = ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name, group_name=group_name)
        if groups:
            return groups[0]
        return None

    def is_k8s_app_duplicate(self, tenant_id: str, region_name: str, k8s_app: str,
                             app_id: Optional[str] = None) -> bool:
        if not k8s_app:
            return False
        if app_id:
            return ServiceGroup.objects.filter(
                tenant_id=tenant_id, region_name=region_name, k8s_app=k8s_app).exclude(ID=app_id).count() > 0
        return ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name, k8s_app=k8s_app).count() > 0

    # get_group_by_pk get group by group id and tenantid and region name
    def get_group_by_pk(self, tenant_id: str, region_name: str, app_id: str) -> Optional[ServiceGroup]:
        try:
            return ServiceGroup.objects.get(tenant_id=tenant_id, region_name=region_name, pk=app_id)
        except ServiceGroup.DoesNotExist:
            return None

    def update_group_name(self, group_id: str, new_group_name: str, group_note: str = "") -> None:
        ServiceGroup.objects.filter(pk=group_id).update(group_name=new_group_name, note=group_note, update_time=datetime.now())

    def update_governance_mode(self, tenant_id: str, region_name: str, app_id: str, governance_mode: str) -> None:
        ServiceGroup.objects.filter(pk=app_id).update(
            tenant_id=tenant_id, region_name=region_name, governance_mode=governance_mode, update_time=datetime.now())

    def delete_group_by_pk(self, group_id: str) -> None:
        logger.debug("delete group id {0}".format(group_id))
        ServiceGroup.objects.filter(pk=group_id).delete()

    def get_group_count_by_team_id_and_group_id(self, team_id: str, group_id: str) -> int:
        group_count = ServiceGroup.objects.filter(tenant_id=team_id, ID=group_id).count()
        return group_count

    def get_tenant_region_groups(self, team_id: str, region: str, query: str = "", app_type: str = "",
                                 app_ids: List[int] = []) -> QuerySet:
        q = Q(tenant_id=team_id, region_name=region)
        if app_type:
            q &= Q(app_type=app_type)
        if app_ids and app_ids[0] != -1:
            q &= Q(ID__in=app_ids)
        if query:
            q &= Q(group_name__icontains=query)
        return ServiceGroup.objects.filter(q).order_by("-update_time")

    def get_tenant_region_groups_count(self, team_id: str, region: str) -> int:
        return ServiceGroup.objects.filter(tenant_id=team_id, region_name=region).count()

    def get_tenant_groups_count(self, team_id: str) -> int:
        return ServiceGroup.objects.filter(tenant_id=team_id).count()

    def get_groups_by_tenant_ids(self, tenant_ids: List[str]) -> QuerySet:
        return ServiceGroup.objects.filter(tenant_id__in=tenant_ids).order_by("-update_time", "-order_index")

    def get_groups_by_tenant_id(self, tenant_id: str) -> QuerySet:
        return ServiceGroup.objects.filter(tenant_id=tenant_id)

    def get_group_by_id(self, group_id: str) -> Optional[ServiceGroup]:
        return ServiceGroup.objects.filter(pk=group_id).first()

    def get_default_by_service(self, service: Any) -> Optional[ServiceGroup]:
        return ServiceGroup.objects.filter(
            tenant_id=service.tenant_id, region_name=service.service_region, is_default=True).first()

    def get_or_create_default_group(self, tenant: Tenants, region_name: str) -> ServiceGroup:
        # 查询是否有团队在当前数据中心是否有默认应用，没有创建
        group = ServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name).first()
        if not group:
            return self.add_group(tenant=tenant, region_name=region_name, group_name="默认应用", is_default=True)
        return group

    def create_region_app(self, tenant: Tenants, region_name: str, app: ServiceGroup, eid: str = "") -> None:
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

    def get_apps_list(self, team_id: Optional[str] = None, region_name: Optional[str] = None,
                      query: Optional[str] = None) -> QuerySet:
        q = Q(region_name=region_name) & Q(tenant_id=team_id)
        if query:
            q = q & Q(group_name__icontains=query)
        return ServiceGroup.objects.filter(q).order_by("-update_time", "-order_index")

    def get_multi_app_info(self, app_ids: List[int]) -> QuerySet:
        return ServiceGroup.objects.filter(ID__in=app_ids).order_by("-update_time", "-order_index")

    def get_apps_in_multi_team(self, team_ids: List[str], region_names: List[str]) -> QuerySet:
        return ServiceGroup.objects.filter(
            tenant_id__in=team_ids, region_name__in=region_names).order_by("-update_time", "-order_index")

    def get_by_service_id(self, tenant_id: str, service_id: str) -> ServiceGroup:
        try:
            rel = ServiceGroupRelation.objects.get(tenant_id=tenant_id, service_id=service_id)
            return ServiceGroup.objects.get(tenant_id=tenant_id, pk=rel.group_id)
        except ServiceGroupRelation.DoesNotExist:
            raise ServiceGroup.DoesNotExist

    def get_app_principal(self, app: ServiceGroup) -> Users:
        return Users.objects.get(nick_name=app.username)

    @staticmethod
    def count_app_nums_by_tenant_ids(tenant_ids: List[str]) -> Any:
        # values().annotate() returns a dict-shaped QuerySet, not model instances
        return ServiceGroup.objects.filter(tenant_id__in=tenant_ids).values("tenant_id").annotate(counts=Count("tenant_id"))

    @staticmethod
    def count_apps() -> int:
        return ServiceGroup.objects.count()


class GroupServiceRelationRepository(object):
    def delete_relation_by_group_id(self, group_id: str) -> None:
        ServiceGroupRelation.objects.filter(group_id=group_id).delete()

    def get_relation_by_tenant_id(self, tenant_id: str) -> QuerySet:
        return ServiceGroupRelation.objects.filter(tenant_id=tenant_id)

    def delete_relation_by_service_id(self, service_id: str) -> None:
        ServiceGroupRelation.objects.filter(service_id=service_id).delete()

    def add_service_group_relation(self, group_id: str, service_id: str, tenant_id: str,
                                   region_name: str) -> ServiceGroupRelation:
        sgr = ServiceGroupRelation.objects.create(
            service_id=service_id, group_id=group_id, tenant_id=tenant_id, region_name=region_name)
        return sgr

    def get_group_by_service_id(self, service_id: str) -> Optional[ServiceGroupRelation]:
        sgrs = ServiceGroupRelation.objects.filter(service_id=service_id)
        if sgrs:
            return sgrs[0]
        return None

    def get_group_info_by_service_id(self, service_id: str) -> Optional[ServiceGroup]:
        sgrs = ServiceGroupRelation.objects.filter(service_id=service_id)
        if not sgrs:
            return None
        relation = sgrs[0]
        groups = ServiceGroup.objects.filter(ID=relation.group_id)
        if not groups:
            return None
        return groups[0]

    def get_group_by_service_ids(self, service_ids: List[str]) -> Dict[str, dict]:
        sgr = ServiceGroupRelation.objects.filter(service_id__in=service_ids)
        sgr_map = {s.service_id: s.group_id for s in sgr}
        group_ids = [g.group_id for g in sgr]
        groups = ServiceGroup.objects.filter(ID__in=group_ids)
        group_name_map = {g.ID: g.group_name for g in groups}
        group_k8s_app_map = {g.ID: g.k8s_app for g in groups}
        result_map: Dict[str, dict] = {}
        for service_id in service_ids:
            group_id = sgr_map.get(service_id, None)
            group_info: Dict[str, Any] = dict()
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

    def create_service_group_relation(self, **params: Any) -> ServiceGroupRelation:
        return ServiceGroupRelation.objects.create(**params)

    def get_service_group_relation_by_groups(self, group_ids: List[int]) -> QuerySet:
        return ServiceGroupRelation.objects.filter(group_id__in=group_ids)

    def get_services_by_group(self, group_id: str) -> QuerySet:
        return ServiceGroupRelation.objects.filter(group_id=group_id)

    def get_service_number(self, region_name: str) -> int:
        return ServiceGroupRelation.objects.filter(region_name=region_name).count()

    @staticmethod
    def list_serivce_ids_by_app_id(tenant_id: str, region_name: str, app_id: str) -> Any:
        relations = ServiceGroupRelation.objects.filter(tenant_id=tenant_id, region_name=region_name, group_id=app_id)
        if not relations:
            return []
        return relations.values_list("service_id", flat=True)

    @staticmethod
    def count_service_by_app_id(app_id: str) -> int:
        return ServiceGroupRelation.objects.filter(group_id=app_id).count()

    def get_service_by_group(self, group_id: str) -> Optional[ServiceGroupRelation]:
        return ServiceGroupRelation.objects.filter(group_id=group_id).first()

    @staticmethod
    def list_service_groups(group_id: str) -> QuerySet:
        return ServiceGroupRelation.objects.filter(group_id=group_id).all()

    def update_service_relation(self, group_id: str, default_group_id: str) -> None:
        ServiceGroupRelation.objects.filter(group_id=group_id).update(group_id=default_group_id)


class TenantServiceGroupRepository(object):
    def delete_tenant_service_group_by_pk(self, pk: str) -> None:
        TenantServiceGroup.objects.filter(ID=pk).delete()

    def create_tenant_service_group(self, **params: Any) -> TenantServiceGroup:
        return TenantServiceGroup.objects.create(**params)

    @staticmethod
    def get_component_group(service_group_id: str) -> TenantServiceGroup:
        component_group = TenantServiceGroup.objects.filter(ID=service_group_id).first()
        if not component_group:
            raise ErrComponentGroupNotFound
        return component_group

    def get_group_by_app_id(self, app_id: str) -> QuerySet:
        return TenantServiceGroup.objects.filter(service_group_id=app_id)


group_repo = GroupRepository()
group_service_relation_repo = GroupServiceRelationRepository()
# 应用实体
tenant_service_group_repo = TenantServiceGroupRepository()
