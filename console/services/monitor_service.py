# -*- coding: utf8 -*-

from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_app import region_app_repo

region_api = RegionInvokeApi()


class MonitorService(object):
    @staticmethod
    def get_monitor_metrics(region_name, tenant, target, app_id="", component_id=""):
        region_app_id = ""
        if app_id:
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        data = region_api.get_monitor_metrics(region_name, tenant, target, region_app_id, component_id)
        if not data:
            return None
        return data.get("list", [])


monitor_service = MonitorService()
