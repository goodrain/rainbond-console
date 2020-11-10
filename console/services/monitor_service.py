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
        return region_api.get_monitor_metrics(region_name, tenant, target, region_app_id, component_id)


monitor_service = MonitorService()
