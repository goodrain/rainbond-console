# -*- coding: utf8 -*-

# exception
from console.exception.main import AbortRequest
# service
from console.services.group_service import group_service
# repository
from console.repositories.app import service_source_repo
# model
from www.models.main import TenantServiceGroup


class ComponentGroup(object):
    def __init__(self, enterprise_id, component_group: TenantServiceGroup, version=None, need_save=True):
        self.enterprise_id = enterprise_id
        self.component_group = component_group
        self.app_id = self.component_group.service_group_id
        self.app_model_key = self.component_group.group_key
        self.upgrade_group_id = self.component_group.ID
        self.version = version if version else component_group.group_version
        self.need_save = need_save

    def is_install_from_cloud(self):
        source = self.app_template_source()
        return source.is_install_from_cloud()

    def app_template_source(self):
        """
        Optimization: the component group should save the source of the app template itself.
        """
        components = group_service.get_rainbond_services(self.app_id, self.app_model_key, self.upgrade_group_id)
        if not components:
            raise AbortRequest("components not found", "找不到组件", status_code=404, error_code=404)
        component = components[0]
        component_source = service_source_repo.get_service_source(component.tenant_id, component.service_id)
        return component_source

    def save(self):
        if not self.need_save:
            return
        self.component_group.save()
