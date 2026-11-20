# -*- coding: utf8 -*-

from typing import Any, Dict, List, Tuple

from django.db import transaction
from django.db.models import QuerySet

from console.exception.main import ServiceHandleException
from console.models.main import ComponentK8sAttributes
from console.utils.vm_restore_attributes import is_private_vm_attribute, public_attribute_fields, reject_private_vm_attribute
from www.models.main import TenantServiceInfo


class ComponentK8sAttributeRepo(object):
    def create(self, **params: Any) -> ComponentK8sAttributes:
        reject_private_vm_attribute(params.get("name", ""))
        return ComponentK8sAttributes.objects.create(**params)

    def bulk_create(self, componentK8sAttributes: List[ComponentK8sAttributes]) -> List[ComponentK8sAttributes]:
        attrs = list(componentK8sAttributes)
        with transaction.atomic(using=ComponentK8sAttributes.objects.db):
            services = self._lock_components([attr.component_id for attr in attrs])
            copies = self._public_copies(attrs, services)
            return ComponentK8sAttributes.objects.bulk_create(copies)

    def update(self, component_id: str, name: str, **data: Any) -> int:
        reject_private_vm_attribute(name)
        if set(data) - {"attribute_value", "save_type"}:
            raise ServiceHandleException(msg="Invalid attribute update fields", status_code=403)
        ids = [
            row.pk for row in self.get_by_component_id_name(component_id, name)
            if row.name == name and not is_private_vm_attribute(row.name)
        ]
        return ComponentK8sAttributes.objects.filter(component_id=component_id, pk__in=ids).update(**data)

    def delete(self, component_id: str, name: str) -> Tuple[int, Dict[str, int]]:
        reject_private_vm_attribute(name)
        ids = [
            row.pk for row in self.get_by_component_id_name(component_id, name)
            if row.name == name and not is_private_vm_attribute(row.name)
        ]
        return ComponentK8sAttributes.objects.filter(component_id=component_id, pk__in=ids).delete()

    def list_by_component_ids(self, component_ids: List[str]) -> QuerySet:
        return ComponentK8sAttributes.objects.filter(component_id__in=component_ids)

    def get_by_component_id_name(self, component_id: str, name: str) -> QuerySet:
        return ComponentK8sAttributes.objects.filter(component_id=component_id, name=name)

    def get_by_component_id(self, component_id: str) -> QuerySet:
        return ComponentK8sAttributes.objects.filter(component_id=component_id)

    @classmethod
    def overwrite_by_component_ids(cls, component_ids: List[str], attrs: List[ComponentK8sAttributes]) -> None:
        # Match the private writer's lock order: live service, then attributes.
        # Use observed PKs, never SQL LIKE/name comparisons under a permissive
        # MySQL collation. An empty public payload still preserves all controls.
        with transaction.atomic(using=ComponentK8sAttributes.objects.db):
            services = cls._lock_components(component_ids)
            copies = cls._public_copies(attrs, services)
            existing = list(ComponentK8sAttributes.objects.select_for_update().filter(component_id__in=services).order_by("pk"))
            for attr in existing:
                if attr.tenant_id != services[attr.component_id].tenant_id:
                    raise ServiceHandleException(msg="Attribute tenant scope conflict", status_code=409)
            ids = [attr.pk for attr in existing if not is_private_vm_attribute(attr.name)]
            ComponentK8sAttributes.objects.filter(component_id__in=services, pk__in=ids).delete()
            ComponentK8sAttributes.objects.bulk_create(copies)

    @staticmethod
    def _public_copies(attrs: List[ComponentK8sAttributes], services: Dict[str,
                                                                           TenantServiceInfo]) -> List[ComponentK8sAttributes]:
        copies = []
        for attr in attrs:
            fields = public_attribute_fields(attr)
            service = services.get(attr.component_id)
            if service is None:
                raise ServiceHandleException(msg="Attribute component scope mismatch", status_code=403)
            copies.append(ComponentK8sAttributes(tenant_id=service.tenant_id, component_id=service.service_id, **fields))
        return copies

    @staticmethod
    def _lock_components(component_ids: List[str]) -> Dict[str, TenantServiceInfo]:
        ids = sorted(set(component_ids))
        services = list(TenantServiceInfo.objects.select_for_update().filter(service_id__in=ids).order_by("service_id"))
        if {service.service_id for service in services} != set(ids):
            raise ServiceHandleException(msg="Attribute component scope conflict", status_code=409)
        return {service.service_id: service for service in services}


k8s_attribute_repo = ComponentK8sAttributeRepo()
