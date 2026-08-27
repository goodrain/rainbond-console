# -*- coding: utf8 -*-

from typing import Any, Dict, List, Tuple

from django.utils import timezone
from django.db.models import QuerySet

from console.models.main import K8S_RESOURCE_DELETE_STATUS_ACTIVE, K8S_RESOURCE_DELETE_STATUS_DELETING, K8sResource


class AppK8sResourceRepo(object):
    def create(self, **params: Any) -> K8sResource:
        return K8sResource.objects.create(**params)

    def bulk_create(self, app_k8s_resource: List[K8sResource]) -> List[K8sResource]:
        return K8sResource.objects.bulk_create(app_k8s_resource)

    def update(self, app_id: str, name: str, kind: str, **data: Any) -> int:
        return K8sResource.objects.filter(app_id=app_id, name=name, kind=kind).update(**data)

    def delete_by_name(self, app_id: str, kind: str, name: str) -> Tuple[int, Dict[str, int]]:
        return K8sResource.objects.filter(app_id=app_id, kind=kind, name=name).delete()

    def delete_route_by_name(self, name: str) -> Tuple[int, Dict[str, int]]:
        return K8sResource.objects.filter(name=name).delete()

    def get_route_by_name(self, app_id: str, name: str) -> QuerySet:
        return K8sResource.objects.filter(app_id=app_id, name=name)

    def delete_by_kind(self, app_id: str, kind: str) -> Tuple[int, Dict[str, int]]:
        return K8sResource.objects.filter(app_id=app_id, kind=kind).delete()

    def delete_by_id(self, id: str) -> Tuple[int, Dict[str, int]]:
        return K8sResource.objects.filter(ID=id).delete()

    def list_by_app_id(self, app_id: str) -> QuerySet:
        return K8sResource.objects.filter(app_id=app_id)

    def list_by_ids(self, ids: Any, app_id: str = "") -> QuerySet:
        resources = K8sResource.objects.filter(ID__in=ids)
        if app_id:
            resources = resources.filter(app_id=app_id)
        return resources

    def get_by_app_id_kind_name(self, app_id: str, kind: str, name: str) -> K8sResource:
        return K8sResource.objects.get(app_id=app_id, kind=kind, name=name)

    def get_by_id(self, id: str) -> K8sResource:
        return K8sResource.objects.get(ID=id)

    def list_deleting_by_app_id(self, app_id: str) -> QuerySet:
        return K8sResource.objects.filter(
            app_id=app_id,
            delete_status=K8S_RESOURCE_DELETE_STATUS_DELETING,
        )

    def update_delete_lifecycle(self, resource_id: int, region_status: Dict[str, Any], accepted: bool = False) -> int:
        delete_status = int(region_status.get("delete_status", K8S_RESOURCE_DELETE_STATUS_DELETING))
        data = {
            "delete_status": delete_status,
            "delete_error": region_status.get("delete_error", "") or "",
            "delete_generation": int(region_status.get("delete_generation", 0) or 0),
        }
        region_resource_id = region_status.get("resource_id")
        if region_resource_id:
            data["region_resource_id"] = int(region_resource_id)
        if accepted and delete_status == K8S_RESOURCE_DELETE_STATUS_DELETING:
            data["delete_started_at"] = timezone.now()
        return K8sResource.objects.filter(ID=resource_id).update(**data)

    def list_available_resources(self, app_id: str) -> QuerySet:
        # CreateSuccess = 1, UpdateSuccess = 2
        return K8sResource.objects.filter(
            app_id=app_id,
            state__in=[1, 2],
            delete_status=K8S_RESOURCE_DELETE_STATUS_ACTIVE,
        )


k8s_resources_repo = AppK8sResourceRepo()
