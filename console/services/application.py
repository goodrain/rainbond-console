# -*- coding: utf8 -*-

from console.exception.bcode import ErrApplicationServiceNotFound
from console.exception.bcode import ErrServiceAddressNotFound

from console.services.app import app_service
from console.services.group_service import group_service


class ApplicationService(object):
    @staticmethod
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

        app_service.create_third_party_service(tenant, component, user.nick_name)


application_service = ApplicationService()
