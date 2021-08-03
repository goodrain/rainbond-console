# -*- coding: utf8 -*-
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class ComponentLogService(object):
    @staticmethod
    def get_component_log_stream(tenant_name, region_name, service_alias, pod_name, container_name):
        r = region_api.get_component_log(tenant_name, region_name, service_alias, pod_name, container_name)
        for chunk in r.stream(1024):
            yield chunk


component_log_service = ComponentLogService()
