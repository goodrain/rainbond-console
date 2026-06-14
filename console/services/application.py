# -*- coding: utf8 -*-
from typing import Any, Dict, List

from console.services.group_service import group_service
from console.services.app_config import port_service
from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()


class ApplicationService(object):
    @staticmethod
    def parse_services(region_name: str, tenant_name: str, app_id: int, values: str) -> Any:
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)  # type: ignore[arg-type]  # NOTE: get_region_app_id expects str but callers pass int app_id; runtime coercion may occur
        return region_api.parse_app_services(region_name, tenant_name, region_app_id, values)

    @staticmethod
    def list_releases(region_name: str, tenant_name: str, app_id: int) -> Any:
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)  # type: ignore[arg-type]  # NOTE: same int/str mismatch as parse_services
        return region_api.list_app_releases(region_name, tenant_name, region_app_id)

    @staticmethod
    def list_access_info(tenant: Tenants, app_id: int) -> List[Dict[str, Any]]:
        components = group_service.list_components(app_id)  # type: ignore[arg-type]  # NOTE: list_components expects str but callers pass int app_id
        result = []
        for cpt in components:
            access_type, data = port_service.get_access_info(tenant, cpt)
            result.append({
                "access_type": access_type,
                "access_info": data,
            })
        return result


application_service = ApplicationService()
