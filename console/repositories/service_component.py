# -*- coding: utf-8 -*-

from console.models.main import ServiceComponents


class ServiceComponentsRepository(object):
    @staticmethod
    def create(app_id: int, service_name: str, component_id: str):
        ServiceComponents.objects.create(
            app_id=app_id,
            service_name=service_name,
            component_id=component_id,
        )

    @staticmethod
    def list_by_service_name(app_id: int, service_name: str):
        return ServiceComponents.objects.filter(app_id=app_id, service_name=service_name)

    @staticmethod
    def list_by_app_id(app_id: int):
        return ServiceComponents.objects.filter(app_id=app_id)


service_component_repo = ServiceComponentsRepository()
