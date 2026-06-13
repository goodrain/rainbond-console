# -*- coding: utf8 -*-

from typing import Any, Dict, List, Tuple

from django.db.models import QuerySet

from console.models.main import ComponentK8sAttributes


class ComponentK8sAttributeRepo(object):
    def create(self, **params: Any) -> ComponentK8sAttributes:
        return ComponentK8sAttributes.objects.create(**params)

    def bulk_create(self, componentK8sAttributes: List[ComponentK8sAttributes]) -> List[ComponentK8sAttributes]:
        return ComponentK8sAttributes.objects.bulk_create(componentK8sAttributes)

    def update(self, component_id: str, name: str, **data: Any) -> int:
        return ComponentK8sAttributes.objects.filter(component_id=component_id, name=name).update(**data)

    def delete(self, component_id: str, name: str) -> Tuple[int, Dict[str, int]]:
        return ComponentK8sAttributes.objects.filter(component_id=component_id, name=name).delete()

    def list_by_component_ids(self, component_ids: List[str]) -> QuerySet:
        return ComponentK8sAttributes.objects.filter(component_id__in=component_ids)

    def get_by_component_id_name(self, component_id: str, name: str) -> QuerySet:
        return ComponentK8sAttributes.objects.filter(component_id=component_id, name=name)

    def get_by_component_id(self, component_id: str) -> QuerySet:
        return ComponentK8sAttributes.objects.filter(component_id=component_id)

    @staticmethod
    def overwrite_by_component_ids(component_ids: List[str], attrs: List[ComponentK8sAttributes]) -> None:
        ComponentK8sAttributes.objects.filter(component_id__in=component_ids).delete()
        ComponentK8sAttributes.objects.bulk_create(attrs)


k8s_attribute_repo = ComponentK8sAttributeRepo()
