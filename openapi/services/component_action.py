# -*- coding: utf-8 -*-
# creater by: barnett
from console.constants import AppConstants
from console.exception.main import ServiceHandleException
from console.repositories.app import service_source_repo
from console.services.app_actions import app_manage_service
from www.models.main import Tenants, TenantServiceInfo, Users


class ComponnetActionService(object):
    def component_build(self, tenant: Tenants, component: TenantServiceInfo, user: Users, build_info):
        if component.create_status != "complete":
            raise ServiceHandleException(
                msg="component create status is " + component.create_status, msg_show="组件未完成创建，禁止构建", status_code=400)
        # if build_info.server_type:
        # change component server type

        if build_info.get("repo_url"):
            if component.service_source == AppConstants.SOURCE_CODE:
                # change component repo_url
                component.git_url = build_info.get("repo_url")
                # code_version must set default value
                component.code_version = build_info.get("branch", "master")
            if component.service_source == AppConstants.DOCKER_RUN \
                    or component.service_source == AppConstants.DOCKER_COMPOSE \
                    or component.service_source == AppConstants.DOCKER_IMAGE:
                component.image = build_info.get("repo_url")
            service_source = service_source_repo.get_service_source(component.tenant_id, component.service_id)
            if service_source:
                service_source.user_name = build_info.get("username")
                service_source.password = build_info.get("password")
                service_source.save()
            component.save()
        code, message, event_id = app_manage_service.deploy(tenant, component, user)
        if code == 200:
            return event_id
        raise ServiceHandleException(msg=message, msg_show=message, status_code=code)


component_action_service = ComponnetActionService()
