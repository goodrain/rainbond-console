# -*- coding: utf8 -*-

from console.exception.bcode import ErrApplicationServiceNotFound
from console.exception.bcode import ErrServiceAddressNotFound

from django.db import transaction

from console.services.app import app_service
from console.services.group_service import group_service
from console.repositories.service_component import service_component_repo
from console.repositories.service_repo import service_repo


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

        component = app_service.create_third_party_app(region_name, tenant, user, component_name, endpoints, "static")
        group_service.add_component_to_app(tenant, region_name, app_id, component.component_id)
        service_component_repo.create(app_id, service_name, component.component_id)

        app_service.create_third_party_service(tenant, component, user.nick_name)

    @staticmethod
    def list_components_by_service(region_name: str, tenant: object, app_id: int, service_name: str):
        service = group_service.get_service(tenant, region_name, app_id, service_name)
        if not service:
            raise ErrApplicationServiceNotFound

        service_components = service_component_repo.list_by_service_name(app_id, service_name)
        component_ids = [sc.component_id for sc in service_components]
        components = service_repo.list_by_component_ids(component_ids)
        return [{"component_name": cpt.service_cname, "component_alias": cpt.service_alias} for cpt in components]


application_service = ApplicationService()
