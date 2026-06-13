# -*- coding: utf-8 -*-

from typing import Any, List, Optional

from django.db.models import QuerySet

from www.models.main import ServiceGroupRelation


class ServiceGroupRelationRepositry(object):
    def get_group_id_by_service(self, svc: Any) -> Optional[Any]:
        group = ServiceGroupRelation.objects.filter(
            service_id=svc.service_id, tenant_id=svc.tenant_id, region_name=svc.service_region)
        if group:
            return group[0].group_id
        return None

    def get_group_id_by_service_tenant(self, svc: Any) -> Optional[Any]:
        group = ServiceGroupRelation.objects.filter(service_id=svc.service_id, tenant_id=svc.tenant_id)
        if group:
            return group[0].group_id
        return None

    @staticmethod
    def bulk_create(service_group_rels: List[ServiceGroupRelation]) -> None:
        ServiceGroupRelation.objects.bulk_create(service_group_rels)

    @staticmethod
    def get_components_by_app_id(app_id: str) -> QuerySet:
        return ServiceGroupRelation.objects.filter(group_id=app_id)

    @staticmethod
    def list_by_tenant_ids(tenant_ids: List[str]) -> QuerySet:
        return ServiceGroupRelation.objects.filter(tenant_id__in=tenant_ids)


service_group_relation_repo = ServiceGroupRelationRepositry()
