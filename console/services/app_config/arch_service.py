import logging
from typing import Any, Optional

from console.repositories.k8s_attribute import k8s_attribute_repo
from console.services.k8s_attribute import k8s_attribute_service
from www.models.main import Tenants
from www.models.main import TenantServiceInfo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

logger = logging.getLogger('default')

class AppArchService(object):
    def update_affinity_by_arch(self, arch: Optional[str], tenant: Tenants, region_name: str, component: TenantServiceInfo) -> None:
        arch = arch if arch else "amd64"
        data = {"arch": arch, "name": "affinity"}
        res, body = region_api.get_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, data)
        attrdata = body.get("bean")  # type: ignore[union-attr]  # NOTE: body may be None if region API returns unexpected shape
        if attrdata.get("component_id", "") == "":  # type: ignore[union-attr]  # NOTE: body["bean"] can be None at runtime if region API returns unexpected shape
            attribute = {
                "tenant_id": tenant.tenant_id,
                "component_id": component.service_id,
                "name": "affinity",
                "save_type": "yaml",
                "attribute_value": attrdata.get("attribute_value"),  # type: ignore[union-attr]  # NOTE: same as above
            }
            k8s_attribute_repo.create(**attribute)
            region_api.create_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, attribute)
        else:
            k8s_attribute_service.update_k8s_attribute(tenant, component, region_name, attrdata)  # type: ignore[arg-type]  # NOTE: attrdata may be None if body["bean"] absent


arch_service = AppArchService()
