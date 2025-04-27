import logging

from console.repositories.k8s_attribute import k8s_attribute_repo
from console.services.k8s_attribute import k8s_attribute_service
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

logger = logging.getLogger('default')

class AppArchService(object):
    def update_affinity_by_arch(self, arch, tenant, region_name, component):
        arch = arch if arch else "amd64"
        data = {"arch": arch, "name": "affinity"}
        res, body = region_api.get_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, data)
        attrdata = body.get("bean")
        if attrdata.get("component_id", "") == "":
            attribute = {
                "tenant_id": tenant.tenant_id,
                "component_id": component.service_id,
                "name": "affinity",
                "save_type": "yaml",
                "attribute_value": attrdata.get("attribute_value"),
            }
            k8s_attribute_repo.create(**attribute)
            region_api.create_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, attribute)
        else:
            k8s_attribute_service.update_k8s_attribute(tenant, component, region_name, attrdata)


arch_service = AppArchService()
