# -*- coding: utf8 -*-

from console.exception.bcode import ErrApplicationServiceNotFound
from console.exception.bcode import ErrServiceAddressNotFound

from django.db import transaction

from console.services.app import app_service
from console.services.group_service import group_service
from console.repositories.service_component import service_component_repo
from console.repositories.service_repo import service_repo
from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class ApplicationService(object):
    @transaction.atomic
    def create_thirdparty_component(self, user, region_name, tenant, app_id, service_name, port):
        # service address
        service = group_service.get_service(tenant, region_name, app_id, service_name)
        if not service:
            raise ErrApplicationServiceNotFound
        address = service.get("address")
        if not address:
            raise ErrServiceAddressNotFound

        self._create_thirdparty_component(user, region_name, tenant, app_id, service_name, port, address)

    @transaction.atomic
    def batch_create_thirdparty_components(self, user, region_name, tenant, app_id, services):
        # TODO: Kill for loop
        for service in services:
            for port in service["ports"]:
                self._create_thirdparty_component(user, region_name, tenant, app_id,
                                                  service["service_name"], port, service["address"])

    @staticmethod
    def _create_thirdparty_component(user, region_name, tenant, app_id, service_name, port, address):
        endpoints = [address + ":" + str(port)]
        component_name = service_name + "-" + str(port)

        component = app_service.create_third_party_app(region_name,
                                                       tenant,
                                                       user,
                                                       component_name,
                                                       endpoints,
                                                       "static",
                                                       is_inner_service=True,
                                                       component_type="helm")
        group_service.add_component_to_app(tenant, region_name, app_id, component.component_id)
        service_component_repo.create(app_id, service_name, component.component_id, port)

        app_service.create_third_party_service(tenant, component, user.nick_name, is_inner_service=True)


    @staticmethod
    def list_components_by_service_name(region_name: str, tenant: object, app_id: int, service_name: str):
        service = group_service.get_service(tenant, region_name, app_id, service_name)
        if not service:
            raise ErrApplicationServiceNotFound

        service_components = service_component_repo.list_by_service_name(app_id, service_name)
        component_ids = [sc.component_id for sc in service_components]
        components = service_repo.list_by_component_ids(component_ids)
        return [{"component_name": cpt.service_cname, "component_alias": cpt.service_alias} for cpt in components]

    @staticmethod
    def list_orphan_components(region_name: str, tenant, app_id: int):
        services = group_service.list_services(tenant.tenant_name, region_name, app_id)
        service_names = []
        if services:
            service_names = [svc.get("service_name") for svc in services]
        service_components = service_component_repo.list_by_app_id(app_id)
        service_components = service_components.exclude(service_name__in=service_names)
        component_ids = [sc.component_id for sc in service_components]
        components = service_repo.list_by_component_ids(component_ids)
        return [{"component_name": cpt.service_cname, "component_alias": cpt.service_alias} for cpt in components]

    @staticmethod
    def ensure_name(region_name: str, tenant_name: str, app_name: str):
        return region_api.ensure_app_name(region_name, tenant_name, app_name)

    @staticmethod
    def parse_services(region_name: str, tenant_name: str, app_id: int, values: str):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        return region_api.parse_app_services(region_name, tenant_name, region_app_id, values)

    @staticmethod
    def list_helm_releases(region_name: str, tenant_name: str, app_id: int):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        return region_api.list_app_helm_releases(region_name, tenant_name, region_app_id)


application_service = ApplicationService()
