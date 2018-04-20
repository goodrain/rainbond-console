# -*- coding: utf8 -*-
import logging

import os
import datetime
from django.db.models import Q
from django.conf import settings

from openapi.controllers.openservicemanager import OpenTenantServiceManager
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.baseclient import client_auth_service
from www.models import ServiceDomainCertificate, ServiceDomain, make_uuid
from www.services import app_group_svc, tenant_svc, enterprise_svc, user_svc, app_svc

logger = logging.getLogger('default')
LOGGER_TAG = 'marketapi'

manager = OpenTenantServiceManager()
region_api = RegionInvokeApi()

DEFAULT_REGION = 'ali-sh'


class MarketServiceAPIManager(object):
    def get_group_services_by_pk_list(self, group_id_list):
        if not group_id_list:
            return list()

        logger.debug(LOGGER_TAG, 'Get tenant service group, group ids: {0}'.format(group_id_list))

        group_list = app_group_svc.list_group_service_by_ids(group_id_list)

        logger.debug(LOGGER_TAG, 'Tenant servics group:{0}'.format(group_list))

        return group_list

    def get_group_services_by_pk(self, group_id):
        return app_group_svc.get_tenant_service_group_by_pk(int(group_id), True, True, False)

    def list_group_service_by_region(self, tenant, region_name):
        return app_group_svc.list_tenant_service_group_by_region(tenant, region_name, True, True, True)

    def get_service_of_avaliable_port(self, group_id):
        """
        获取可用http端口的服务
        :param group_id:
        :return:
        """
        group = app_group_svc.get_tenant_service_group_by_pk(group_id, True)
        data = []
        for svc in group.service_list:
            http_port_svcs = app_group_svc.get_service_http_port(svc.service_id)
            port = http_port_svcs[0] if http_port_svcs else None
            if port:
                domains = ServiceDomain.objects.filter(
                    service_id=port.service_id,
                    protocol='http'
                )
                ret = {
                    'service_id': svc.service_id,
                    'service_key': svc.service_key,
                    'service_name': svc.service_cname,
                    'service_version': svc.version,
                }
                if not domains:
                    ret.update({'domain': ''})
                else:
                    ret.update({
                        'domain': {
                            'domain_id': domains[0].ID,
                            'domain_url': domains[0].domain_name
                        }
                    })
                data.append(ret)
        return data

    # def get_app_service_group_by_unique(self, group_key, group_version):
    #     return app_group_svc.get_app_service_group_by_unique(group_key, group_version)

    def get_tenant_by_name(self, tenant_name):
        return tenant_svc.get_tenant_by_name(tenant_name)

    def get_tenant_service_by_alias(self, tenant, service_alias):
        return tenant_svc.get_tenant_service_by_alias(tenant, service_alias)

    def get_tenant_group_by_id(self, tenant, group_id, region_name=DEFAULT_REGION):
        return tenant_svc.get_tenant_group_on_region_by_id(tenant, group_id, region_name)

    def get_default_tenant_by_user(self, user_id):
        return user_svc.get_default_tenant_by_user(user_id)

    def list_user_tenants(self, user_id, load_region=False):
        return user_svc.list_user_tenants(user_id, load_region)

    def list_tenant_group(self, tenant):
        return tenant_svc.list_tenant_group_on_region(tenant, DEFAULT_REGION)

    def list_tenant_group_service(self, tenant, group):
        return tenant_svc.list_tenant_group_service(tenant, group)

    def get_access_url(self, tenant, service):
        return tenant_svc.get_access_url(tenant, service)

    def get_tenant_service_status(self, tenant, service):
        return app_svc.get_service_status(tenant, service)

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
            return 'unknow'

        running_count = 0
        closed_count = 0
        starting_count = 0
        undeploy_count = 0
        for status in services_status:
            runtime_status = status['status']
            if runtime_status == 'closed':
                closed_count += 1
            elif runtime_status == 'running':
                running_count += 1
            elif runtime_status == 'starting':
                starting_count += 1
            elif runtime_status == 'undeploy':
                undeploy_count += 1

        service_count = len(services_status)
        if service_count == 0:
            group_status = 'closed'
        elif closed_count > 0 and closed_count == service_count:
            group_status = 'closed'
        elif undeploy_count > 0 and undeploy_count == service_count:
            group_status = 'undeploy'
        elif running_count > 0 and running_count == service_count:
            group_status = 'running'
        elif starting_count > 0:
            group_status = 'starting'
        else:
            group_status = 'unknow'

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

    def build_tenant_service_group(self, user, group_id):
        return app_group_svc.build_tenant_service_group(user, group_id)

    def install_tenant_service_group(self, user, tenant_name, group_key, group_version, region_name):
        logger.debug(
            'prepared install [{}-{}] to [{}] on [{}]'.format(group_key, group_version, tenant_name, region_name))
        if tenant_name:
            tenant = self.get_tenant_by_name(tenant_name)
        else:
            tenant = self.get_default_tenant_by_user(user.user_id)

        if not tenant:
            logger.error('tenant does not existed!')
            return False, '租户不存在', None

        logger.debug('login_user_id: {}'.format(user.user_id))
        logger.debug('login_user: {}'.format(user.nick_name))
        logger.debug('tenant_name: {}'.format(tenant.tenant_name))
        # if app_group_svc.is_tenant_service_group_installed(tenant, region_name, group_key, group_version):
        #     logger.info('group service already installed!')
        #     return False, '应用组已安装, 请卸载后再重装!', None

        # 查看安装的目标数据中心是否已初始化, 如果未初始化则先初始化
        if not tenant_svc.init_region_tenant(tenant, region_name):
            return False, '初始化数据中心失败: {}'.format(region_name), None

        app_service_group = app_group_svc.download_app_service_group_from_market(tenant.tenant_id,
                                                                                 group_key,
                                                                                 group_version)
        if not app_service_group:
            return False, '初始化应用组模板信息失败', None

        success, message, group, installed_services = app_group_svc.install_tenant_service_group(user, tenant,
                                                                                                 region_name,
                                                                                                 app_service_group,
                                                                                                 'cloud')
        group = app_group_svc.get_tenant_service_group_by_pk(group.pk, True, True, True)
        return success, message, group

    def restart_tenant_service_group(self, user, group_id):
        return app_group_svc.restart_tenant_service_group(user, group_id)

    def stop_tenant_service_group(self, user, group_id):
        return app_group_svc.stop_tenant_service_group(user, group_id)

    def delete_tenant_service_group(self, group_id):
        return app_group_svc.delete_tenant_service_group(group_id)

    def get_enterprise_by_id(self, enterprise_id):
        return enterprise_svc.get_enterprise_by_id(enterprise_id)

    def active_market_enterprise(self, sso_user, enterprise_id, market_client_id, market_client_token):
        """
        将sso_user 绑定到指定的enterprise上，并绑定访问云市的认证信息
        :param sso_user: 
        :param enterprise_id: 
        :param market_client_id: 
        :param market_client_token: 
        :return: 
        """
        enterprise = enterprise_svc.get_enterprise_by_id(enterprise_id)
        # 如果要绑定的企业在本地云帮不存在, 且eid与云市eid一致，则创建一个与公有云一致的企业信息
        if not enterprise and enterprise_id == sso_user.eid:
            # 注册一个用户信息
            user = user_svc.register_user_from_sso(sso_user)

            # 创建一个企业信息
            enterprise = enterprise_svc.create_enterprise(enterprise_id=sso_user.eid, enterprise_alias=sso_user.company)
            logger.info(
                'create enterprise[{0}] with name {1}[{2}]'.format(enterprise.enterprise_id,
                                                                   enterprise.enterprise_alias,
                                                                   enterprise.enterprise_name))
            # 绑定用户与企业关系
            user.enterprise_id = enterprise.enterprise_id
            user.save()

            logger.info(
                'create user[{0}] with name [{1}] from [{2}] use sso_id [{3}]'.format(user.user_id,
                                                                                      user.nick_name,
                                                                                      user.rf,
                                                                                      user.sso_user_id))
            # 初始化用户工作环境
            tenant = enterprise_svc.create_and_init_tenant(user_id=user.user_id, enterprise_id=user.enterprise_id)

        domain = os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"])
        return client_auth_service.save_market_access_token(enterprise_id, domain, market_client_id,
                                                            market_client_token)

    def save_region_access_token(self, enterprise_id, region_name, access_url, access_token, key, crt):
        return client_auth_service.save_region_access_token(enterprise_id, region_name, access_url, access_token, key,
                                                            crt)

    def get_certificates(self, alias=None, group_id=None):
        """
        获取证书
        :param alias:
        :param group_id:
        :return:
        """
        q = Q()
        if alias:
            q = q & Q(alias=alias)
        if group_id:
            group = app_group_svc.get_tenant_service_group_by_pk(group_id)
            q = q & Q(tenant_id=group.tenant_id)
        return ServiceDomainCertificate.objects.filter(q)

    def get_binded_domains(self, service_id):
        domains = ServiceDomain.objects.filter(
            service_id=service_id,
            protocol='http'
        )
        return [{'domain_name': d.domain_name, 'domain_id': d.ID, 'service_id': d.service_id} \
                for d in domains]

    def bind_domain(self, service_id, domain_name):
        if ServiceDomain.objects.filter(domain_name=domain_name).count() > 0:
            return False, '域名已存在'

        service = app_svc.get_service_by_id(service_id)
        if not service:
            return False, '应不存在'

        tenant = app_group_svc.get_tenant_by_pk(service.tenant_id)
        user = app_group_svc.get_user_by_eid(tenant.enterprise_id)

        ports = app_group_svc.get_service_http_port(service.service_id)
        if not ports:
            return False, '未开通对外端口'

        data = {
            "uuid": make_uuid(domain_name),
            "domain_name": domain_name,
            "service_alias": service.service_alias,
            "tenant_id": service.tenant_id,
            "tenant_name": tenant.tenant_name,
            "service_port": ports[0].container_port,
            "protocol": "http",
            "add_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "add_user": user.nick_name if user else "",
            "enterprise_id": tenant.enterprise_id,
            "certificate": "",
            "private_key": "",
            "certificate_name": ""
        }

        try:
            region_api.bindDomain(
                service.service_region, tenant.tenant_name, service.service_alias, data
            )
            domain = {
                "service_id": service.service_id,
                "service_name": service.service_alias,
                "domain_name": domain_name,
                "create_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "container_port": ports[0].container_port,
                "protocol": "http", "certificate_id": 0
            }
            domain_info = ServiceDomain(**domain)
            domain_info.save()
            return True, domain_info
        except Exception as e:
            return False, e.message.get('body').get('msgcn') or '绑定域名失败'

    def unbind_domain(self, domain_id, service_id):
        service = app_svc.get_service_by_id(service_id)
        if not service:
            return False, '应用不存在'

        tenant = app_group_svc.get_tenant_by_pk(service.tenant_id)
        domain = ServiceDomain.objects.get(ID=domain_id)

        data = {
            "service_id": domain.service_id,
            "domain": domain.domain_name,
            "pool_name": tenant.tenant_name + "@" + service.service_alias + ".Pool",
            "container_port": domain.container_port,
            "enterprise_id": tenant.enterprise_id}
        try:
            region_api.unbindDomain(
                service.service_region, tenant.tenant_name, service.service_alias, data
            )
            domain.delete()
            return True, None
        except region_api.CallApiError as e:
            return False, '解绑失败'

    def limit_region_resource(self, tenant, region, res):
        tenant_svc.limit_region_resource(tenant, region, res)
        return True, '配置数据中心资源成功'

    def get_tenant_region_resource_usage(self, tenant, region):
        return tenant_svc.get_tenant_region_resource_usage(tenant, region)

    def get_tenant_region_resource_limit(self, tenant, region):
        return tenant_svc.get_tenant_region_resource_limit(tenant, region)

    def install_service_group(self, user, tenant_name, group_key, group_version, region_name, template_version):
        logger.debug(
            'prepared install [{}-{}] to [{}] on [{}]'.format(group_key, group_version, tenant_name, region_name))
        if tenant_name:
            tenant = self.get_tenant_by_name(tenant_name)
        else:
            tenant = self.get_default_tenant_by_user(user.user_id)

        if not tenant:
            logger.error('tenant does not existed!')
            return False, '租户不存在', None
        logger.debug('login_user_id: {}'.format(user.user_id))
        logger.debug('login_user: {}'.format(user.nick_name))
        logger.debug('tenant_name: {}'.format(tenant.tenant_name))

        # 查看安装的目标数据中心是否已初始化, 如果未初始化则先初始化
        if not tenant_svc.init_region_tenant(tenant, region_name):
            return False, '初始化数据中心失败: {}'.format(region_name), None
        app_template_json_str = app_group_svc.get_app_templates(tenant.tenant_id,group_key,group_version,template_version)
        if not app_template_json_str:
            return False, '初始化应用组模板信息失败', None
        success, message, group, installed_services = app_group_svc.install_market_apps_directly(user, tenant,
                                                                                                 region_name,
                                                                                                 app_template_json_str,
                                                                                                 'cloud')
        if group:
            group = app_group_svc.get_tenant_service_group_by_pk(group.pk, True, True, True)
            return success, message, group
        return success, message, group

    def list_enterprise_tenants(self, user, load_region):
        return enterprise_svc.list_enterprise_tenants(user.enterprise_id, load_region)