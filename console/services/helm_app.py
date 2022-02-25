# -*- coding: utf8 -*-
import json

# service
from console.services.group_service import group_service
from console.services.app import app_service
# repository
from console.repositories.region_app import region_app_repo
from console.repositories.app_config import service_endpoints_repo
# model
from www.models.main import Tenants
from www.models.main import ServiceGroup
# exception
from console.exception.bcode import ErrThirdComponentStartFailed
# www
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class HelmAppService(object):
    def list_components(self, tenant: Tenants, region_name: str, user, app: ServiceGroup):
        # list kubernetes service
        services = self.list_services(tenant.tenant_name, region_name, app.app_id)
        # list components
        components = group_service.list_components(app.app_id)
        components = [cpt.to_dict() for cpt in components]
        # relations between components and services
        relations = self._list_component_service_relations([cpt["service_id"] for cpt in components])

        # create third components for services
        orphan_services = [service for service in services if service["service_name"] not in relations.values()]
        for service in orphan_services:
            service["namespace"] = tenant.namespace
        error = {}
        try:
            app_service.create_third_components(tenant, region_name, user, app, "kubernetes", orphan_services)
        except ErrThirdComponentStartFailed as e:
            error["code"] = e.error_code
            error["msg"] = e.msg

        # list components again
        components = group_service.list_components(app.app_id)
        components = [cpt.to_dict() for cpt in components]
        self._merge_component_service(components, services, relations)
        return components, error

    @staticmethod
    def list_services(tenant_name, region_name, app_id):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        services = region_api.list_app_services(region_name, tenant_name, region_app_id)
        return services if services else []

    @staticmethod
    def _list_component_service_relations(component_ids):
        endpoints = service_endpoints_repo.list_by_component_ids(component_ids)
        relations = {}
        for endpoint in endpoints:
            ep = json.loads(endpoint.endpoints_info)
            service_name = ep.get("serviceName")
            relations[endpoint.service_id] = service_name
        return relations

    @staticmethod
    def _merge_component_service(components, services, relations):
        services = {service["service_name"]: service for service in services}
        for component in components:
            service_name = relations.get(component["service_id"])
            if not service_name:
                continue
            component["service"] = services.get(service_name)


helm_app_service = HelmAppService()
