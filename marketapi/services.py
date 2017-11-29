# -*- coding: utf8 -*-
import logging

from openapi.controllers.openservicemanager import OpenTenantServiceManager
from www.apiclient.regionapi import RegionInvokeApi
from www.services import app_group_svc, tenant_svc, enterprise_svc, user_svc
from www.tenantservice.baseservice import TenantAccountService

logger = logging.getLogger('default')
LOGGER_TAG = 'marketapi'

manager = OpenTenantServiceManager()
tenantAccountService = TenantAccountService()
region_api = RegionInvokeApi()

DEFAULT_REGION = 'ali-sh'


class MarketServiceAPIManager(object):

    def get_app_service_group_by_unique(self, group_key, group_version):
        return app_group_svc.get_app_service_group_by_unique(group_key, group_version)

    def get_tenant_by_name(self, tenant_name):
        return tenant_svc.get_tenant_by_name(tenant_name)

    def get_tenant_service_by_alias(self, tenant, service_alias):
        return tenant_svc.get_tenant_service_by_alias(tenant, service_alias)

    def get_tenant_group_by_id(self, tenant, group_id):
        return tenant_svc.get_tenant_group_on_region_by_id(tenant, group_id, DEFAULT_REGION)

    def get_default_tenant_by_user(self, user_id):
        return user_svc.get_default_tenant_by_user(user_id)

    def list_user_tenants(self, user_id):
        return user_svc.list_user_tenants(user_id)

    def list_tenant_group(self, tenant):
        return tenant_svc.list_tenant_group_on_region(tenant, DEFAULT_REGION)

    def list_tenant_group_service(self, tenant, group):
        return tenant_svc.list_tenant_group_service(tenant, group)

    def get_access_url(self, tenant, service):
        return tenant_svc.get_access_url(tenant, service)

    def get_tenant_service_status(self, tenant, service):
        return tenant_svc.get_tenant_service_status(tenant, service)

    def delete_service(self, tenant, service, operator_name):
        if service.service_origin == "cloud":
            logger.debug(LOGGER_TAG, "now remove cloud service")
            # 删除依赖服务
            status, success, msg = manager.remove_service(tenant, service, operator_name)
        else:
            status, success, msg = manager.delete_service(tenant, service, operator_name)

        return status, success, msg

    def restart_service(self, tenant, service, operator_name, limit=False):
        # stop service
        code, is_success, msg = manager.stop_service(service, operator_name, tenant.tenant_id)
        if code == 200:
            code, is_success, msg = manager.start_service(tenant, service, operator_name, limit)
        return code, is_success, msg

    def start_service(self, tenant, service, operator_name, limit=False):
        return manager.start_service(tenant, service, operator_name, limit)

    def stop_service(self, tenant, service, operator_name):
        return manager.stop_service(service, operator_name, tenant.tenant_id)

    def compute_group_service_status(self, services_status):
        if not services_status:
            return 'unkonw'

        running_count = 0
        closed_count = 0
        for status in services_status:
            runtime_status = status['status']
            if runtime_status == 'closed':
                closed_count += 1
            elif runtime_status == 'running':
                running_count += 1

        if len(services_status) == 0:
            group_status = 'closed'
        elif closed_count > 0 and closed_count == len(services_status):
            group_status = 'closed'
        elif running_count > 0 and running_count == len(services_status):
            group_status = 'running'
        else:
            group_status = 'unkonw'

        return group_status

    def restart_group_service(self, tenant, group, operator_name):
        # 查找祖服务中关联的应用对象
        services = tenant_svc.list_tenant_group_service(tenant, group)

        svc_result = []
        for service in services:
            status, success, msg = self.restart_service(tenant, service, operator_name)
            svc_result.append({
                'service_id': service.service_id,
                'status': status,
                'success': success,
                'msg': msg
            })

        result = {
            'group_id': group.ID,
            'svc_result': svc_result
        }
        return result

    def start_group_service(self, tenant, group, operator_name):
        # 查找祖服务中关联的应用对象
        service_list = tenant_svc.list_tenant_group_service(tenant, group)

        svc_result = []
        for service in service_list:
            status, success, msg = manager.start_service(tenant, service, operator_name, False)
            svc_result.append({
                'service_id': service.service_id,
                'status': status,
                'success': success,
                'msg': msg
            })

        result = {
            'group_id': group.ID,
            'svc_result': svc_result
        }
        return result

    def stop_group_service(self, tenant, group, operator_name):
        # 查找祖服务中关联的应用对象
        service_list = tenant_svc.list_tenant_group_service(tenant, group)

        svc_result = []
        for service in service_list:
            status, success, msg = manager.stop_service(service, operator_name, tenant.tenant_id)
            svc_result.append({
                'service_id': service.service_id,
                'status': status,
                'success': success,
                'msg': msg
            })

        result = {
            'group_id': group.ID,
            'svc_result': svc_result
        }
        return result

    def create_and_init_tenant(self, user):
        tenant = enterprise_svc.create_and_init_tenant(user_id=user.user_id, enterprise_id=user.enterprise_id)
        user.is_active = True
        return tenant

    def install_services(self, user, tenant, region_name, app_service_group):
        if not region_name:
            region_name = DEFAULT_REGION

        group, installed_services, urlmap = app_group_svc.install_app_group(user, tenant, region_name, app_service_group)
        svc_result = []
        for service in installed_services:
            svc_result.append({
                'service_id': service.service_id,
                'status': 200,
                'success': True,
                'msg': 'installed succeed!'
            })

        result = {
            'group_id': group.pk,
            'svc_result': svc_result
        }
        return result

