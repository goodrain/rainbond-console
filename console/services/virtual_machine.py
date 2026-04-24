from console.repositories.virtual_machine import vm_repo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class VirtualMachineService(object):
    def list_vm_image(self, tenant_id):
        component_list = vm_repo.get_vm_images_by_tenant_id(tenant_id)
        return component_list


vms = VirtualMachineService()
