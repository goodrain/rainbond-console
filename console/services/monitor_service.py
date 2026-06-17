# -*- coding: utf8 -*-

from typing import Any, List, Optional

from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants
from console.repositories.region_app import region_app_repo

region_api = RegionInvokeApi()


class MonitorService(object):
    @staticmethod
    def get_monitor_metrics(
        region_name: str,
        tenant: Tenants,
        target: str,
        app_id: str = "",
        component_id: str = "",
    ) -> Optional[List[Any]]:
        region_app_id = ""
        if app_id:
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        data = region_api.get_monitor_metrics(region_name, tenant, target, region_app_id, component_id)
        if not data:
            return None
        return data.get("list", [])


monitor_service = MonitorService()
