# -*- coding: utf8 -*-

from console.exception.bcode import ErrApplicationServiceNotFound
from console.exception.bcode import ErrServiceAddressNotFound

from django.db import transaction

from console.services.app import app_service
from console.services.group_service import group_service
from console.repositories.service_component import service_component_repo
from console.repositories.service_repo import service_repo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class ApplicationService(object):
    @staticmethod
    @transaction.atomic
    def create_thirdparty_component(user, region_name, tenant, app_id, service_name, port):
        # service address
        service = group_service.get_service(tenant, region_name, app_id, service_name)
        if not service:
            raise ErrApplicationServiceNotFound
        address = service.get("address")
        if not address:
            raise ErrServiceAddressNotFound

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
        service_component_repo.create(app_id, service_name, component.component_id)

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
    def list_orphan_components(region_name: str, tenant: object, app_id: int):
        services = group_service.list_services(tenant, region_name, app_id)
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


application_service = ApplicationService()
