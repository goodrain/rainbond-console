# -*- coding: utf8 -*-
from www.models.main import VirtualMachineImage


class VirtualMachineImageRepo(object):
    def get_vm_images_by_tenant_id(self, tenant_id):
        vm_images = VirtualMachineImage.objects.filter(tenant_id=tenant_id)
        return vm_images.values()

    def get_vm_name_by_tenant_id_image(self, tenant_id, image_url):
        vm_images = VirtualMachineImage.objects.filter(tenant_id=tenant_id, image_url=image_url).first()
        return vm_images.name

    def get_vm_image_url_by_tenant_id_and_name(self, tenant_id, name):
        vm_images = VirtualMachineImage.objects.filter(tenant_id=tenant_id, name=name).first()
        return vm_images.image_url

    def get_vm_image_by_tenant_id_and_name(self, tenant_id, name):
        return VirtualMachineImage.objects.filter(tenant_id=tenant_id, name=name)


vm_repo = VirtualMachineImageRepo()
