# -*- coding: utf8 -*-
from typing import Any, Iterator

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class ComponentLogService(object):
    @staticmethod
    def get_component_log_stream(tenant_name: str, region_name: str, service_alias: str, pod_name: str,
                                 container_name: str, follow: bool) -> Iterator[Any]:
        r = region_api.get_component_log(tenant_name, region_name, service_alias, pod_name, container_name, follow)
        for chunk in r.stream(1024):
            yield chunk

    @staticmethod
    def get_rbd_log_stream(region_name: str, pod_name: str, follow: bool) -> Iterator[Any]:
        r = region_api.get_rbd_pod_log(region_name, pod_name, follow)
        for chunk in r.stream(1024):
            yield chunk


component_log_service = ComponentLogService()
