# -*- coding: utf8 -*-
from console.services.group_service import group_service
from console.services.app_config import port_service
from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class ApplicationService(object):
    @staticmethod
    def parse_services(region_name: str, tenant_name: str, app_id: int, values: str):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        return region_api.parse_app_services(region_name, tenant_name, region_app_id, values)

    @staticmethod
    def list_releases(region_name: str, tenant_name: str, app_id: int):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        return region_api.list_app_releases(region_name, tenant_name, region_app_id)

    @staticmethod
    def list_access_info(tenant, app_id):
        components = group_service.list_components(app_id)
        result = []
        for cpt in components:
            access_type, data = port_service.get_access_info(tenant, cpt)
            result.append({
                "access_type": access_type,
                "access_info": data,
            })
        return result


application_service = ApplicationService()
