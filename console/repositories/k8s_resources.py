# -*- coding: utf8 -*-

from typing import Any, List

from django.db.models import QuerySet

from console.models.main import K8sResource


class AppK8sResourceRepo(object):
    def create(self, **params: Any) -> K8sResource:
        return K8sResource.objects.create(**params)

    def bulk_create(self, app_k8s_resource: List[K8sResource]) -> List[K8sResource]:
        return K8sResource.objects.bulk_create(app_k8s_resource)

    def update(self, app_id: str, name: str, kind: str, **data: Any) -> int:
        return K8sResource.objects.filter(app_id=app_id, name=name, kind=kind).update(**data)

    def delete_by_name(self, app_id: str, kind: str, name: str) -> tuple[int, dict[str, int]]:
        return K8sResource.objects.filter(app_id=app_id, kind=kind, name=name).delete()

    def delete_route_by_name(self, name: str) -> tuple[int, dict[str, int]]:
        return K8sResource.objects.filter(name=name).delete()

    def get_route_by_name(self, app_id: str, name: str) -> QuerySet[K8sResource]:
        return K8sResource.objects.filter(app_id=app_id, name=name)

    def delete_by_kind(self, app_id: str, kind: str) -> tuple[int, dict[str, int]]:
        return K8sResource.objects.filter(app_id=app_id, kind=kind).delete()

    def delete_by_id(self, id: str) -> tuple[int, dict[str, int]]:
        return K8sResource.objects.filter(ID=id).delete()

    def list_by_app_id(self, app_id: str) -> QuerySet[K8sResource]:
        return K8sResource.objects.filter(app_id=app_id)

    def list_by_ids(self, ids: Any) -> QuerySet[K8sResource]:
        return K8sResource.objects.filter(ID__in=ids)

    def get_by_app_id_kind_name(self, app_id: str, kind: str, name: str) -> K8sResource:
        return K8sResource.objects.get(app_id=app_id, kind=kind, name=name)

    def get_by_id(self, id: str) -> K8sResource:
        return K8sResource.objects.get(ID=id)

    def list_available_resources(self, app_id: str) -> QuerySet[K8sResource]:
        # CreateSuccess = 1, UpdateSuccess = 2
        return K8sResource.objects.filter(app_id=app_id, state__in=[1, 2])


k8s_resources_repo = AppK8sResourceRepo()
