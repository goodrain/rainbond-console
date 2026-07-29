# -*- coding: utf8 -*-
from typing import Any, Dict, Optional, Tuple

from django.db.models import QuerySet

from www.models.main import VirtualMachineImage


class VirtualMachineImageRepo(object):
    def get_vm_images_by_tenant_id(self, tenant_id: str) -> QuerySet:
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id).order_by("-ID")

    def get_vm_name_by_tenant_id_image(self, tenant_id: str, image_url: str) -> str:
        vm_images = VirtualMachineImage.objects.filter(tenant_id=tenant_id, image_url=image_url).first()
        return vm_images.name if vm_images else ""

    def get_vm_image_url_by_tenant_id_and_name(self, tenant_id: str, name: str) -> str:
        vm_images = VirtualMachineImage.objects.filter(tenant_id=tenant_id, name=name).first()
        return vm_images.image_url if vm_images else ""

    def get_vm_image_by_tenant_id_and_name(self, tenant_id: str, name: str) -> QuerySet:
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id, name=name)

    def get_vm_image_instance_by_tenant_id_and_name(self, tenant_id: str,
                                                    name: str) -> Optional[VirtualMachineImage]:
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id, name=name).first()

    def get_vm_image_instance_by_id(self, tenant_id: str, asset_id: str) -> Optional[VirtualMachineImage]:
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id, ID=asset_id).first()

    def get_vm_image_instance_by_tenant_id_and_image_url(self, tenant_id: str,
                                                         image_url: str) -> Optional[VirtualMachineImage]:
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id, image_url=image_url).order_by("-ID").first()

    def get_vm_image_count_by_image_url(self, tenant_id: str, image_url: str) -> int:
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id, image_url=image_url).count()

    def create_vm_image(self, **params: Any) -> VirtualMachineImage:
        return VirtualMachineImage.objects.create(**params)

    def delete_vm_image_by_id(self, tenant_id: str, asset_id: str) -> Tuple[int, Dict[str, int]]:
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id, ID=asset_id).delete()

    def delete_vm_image_by_image_url(self, tenant_id: str, image_url: str) -> Tuple[int, Dict[str, int]]:
        vm_images = VirtualMachineImage.objects.filter(tenant_id=tenant_id, image_url=image_url)
        if vm_images.count() <= 1:
            return vm_images.delete()
        return 0, {}


vm_repo = VirtualMachineImageRepo()
