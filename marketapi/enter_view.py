# -*- coding: utf8 -*-
import logging
import json

from rest_framework import status

from base_view import BaseMarketAPIView, EnterpriseMarketAPIView
from marketapi.services import MarketServiceAPIManager
from www.services.sso import GoodRainSSOApi
from console.services.app_config import domain_service

logger = logging.getLogger('default')
LOGGER_TAG = 'marketapi'
market_api = MarketServiceAPIManager()


class EnterBindAPIView(BaseMarketAPIView):
    def post(self, request):
        """
        云市企业信息认证绑定接口
        ---
        parameters:
            - name: enterprise_id
              description: 云帮本地企业id
              required: true
              type: string
              paramType: form
            - name: market_client_id
              description: 云市授予的企业身份id
              required: true
              type: string
              paramType: form
            - name: market_client_token
              description: 云市授予的企业访问的token
              required: true
              type: string
              paramType: form
            - name: echostr
              description: 云市随机生成的字符串, 绑定成功后需要原路返回
              required: true
              type: string
              paramType: form
        """
        sso_user_id = request.META.get('HTTP_X_SSO_USER_ID')
        sso_user_token = request.META.get('HTTP_X_SSO_USER_TOKEN')
        if not sso_user_id or not sso_user_token:
            return self.error_response(code=status.HTTP_400_BAD_REQUEST,
                                       msg='X_SSO_USER_ID or X_SSO_USER_TOKEN not specified!')

        api = GoodRainSSOApi(sso_user_id, sso_user_token)
        if not api.auth_sso_user_token():
            logger.error('auth user token from remote failed!')
            logger.debug('sso_user_id:'.format(sso_user_id))
            logger.debug('sso_user_token:'.format(sso_user_token))
            return self.error_response(code=status.HTTP_403_FORBIDDEN, msg='illegal user token!')

        # 获取云市SSO用户信息
        sso_user = api.get_sso_user_info()
        sso_user['sso_user_token'] = sso_user_token

        enterprise_id = request.data.get('enterprise_id')
        market_client_id = request.data.get('market_client_id')
        market_client_token = request.data.get('market_client_token')
        echostr = request.data.get('echostr')

        success = market_api.active_market_enterprise(sso_user, enterprise_id, market_client_id,
                                                      market_client_token)
        if success:
            return self.success_response(data={'echostr': echostr})
        else:
            return self.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, 'enterprise bind failed',
                                       '服务器错误,企业认证绑定失败')


class RegionEnterpriseAccessTokenAPIView(EnterpriseMarketAPIView):
    def post(self, request):
        """
        添加或修改企业访问数据中心认证信息接口, 如果不存在则创建, 存在则修改
        ---
        parameters:
            - name: enterprise_id
              description: 企业id
              required: true
              type: string
              paramType: form
            - name: region_name
              description: 数据中心名称
              required: true
              type: string
              paramType: form
            - name: access_url
              description: 数据中心访问地址
              required: true
              type: string
              paramType: form
            - name: access_token
              description: 数据中心访问token
              required: true
              type: string
              paramType: form
            - name: key
              description: 数据中心访问证书key
              required: false
              type: string
              paramType: form
            - name: crt
              description: 数据中心访问证书crt
              required: false
              type: string
              paramType: form
        """
        enterprise_id = request.data.get('enterprise_id')
        region_name = request.data.get('region_name')
        access_url = request.data.get('access_url')
        access_token = request.data.get('access_token')
        key = request.data.get('key')
        crt = request.data.get('crt')

        if not region_name or not access_url or not access_token:
            return self.error_response(status.HTTP_400_BAD_REQUEST, 'missing parameters', '参数不合法')

        if request.user.enterprise_id != enterprise_id:
            logger.debug('login_user.eid:{}'.format(request.user.enterprise_id))
            logger.debug('param.eid:{}'.format(enterprise_id))
            return self.error_response(status.HTTP_403_FORBIDDEN, 'no access right for this api', '未授权')

        enter = market_api.get_enterprise_by_id(enterprise_id)
        if not enter:
            return self.error_response(status.HTTP_404_NOT_FOUND, 'enterprise not fond!', '企业信息不存在!')

        market_api.save_region_access_token(enterprise_id, region_name, access_url, access_token, key, crt)
        return self.success_response()


class RegionEnterResourceAPIView(EnterpriseMarketAPIView):
    def get(self, request):
        """
        获取数据中心资源使用情况接口
        ---
        parameters:
            - name: region
              description: 数据中心名称
              required: true
              type: string
              paramType: query
            - name: tenant_name
              description: 指定团队名称
              required: false
              type: string
              paramType: query
        """
        logger.debug(request.GET)
        region = request.GET.get('region')
        if not region:
            return self.error_response(status.HTTP_400_BAD_REQUEST, 'missing parameters', '参数不合法')

        user = request.user

        tenant_name = request.GET.get('tenant_name', '') or ''
        if tenant_name:
            tenant = market_api.get_tenant_by_name(tenant_name)
        else:
            tenant = market_api.get_default_tenant_by_user(user.user_id)
        if not tenant:
            logger.error(LOGGER_TAG, 'user [{0}] do not have default tenant!'.format(user.user_id))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')
        total_memory, total_disk, total_net = market_api.get_tenant_region_resource_usage(tenant, region)
        limit_memory, limit_disk, limit_net = market_api.get_tenant_region_resource_limit(tenant, region)
        data = {
            'tenant_name': tenant.tenant_name,
            'pay_type': tenant.pay_type,
            'region': region,
            'used_memory': total_memory,
            'used_disk': total_disk,
            'used_net': total_net,
            'limit_disk': limit_disk,
            'limit_memory': limit_memory,
            'limit_net': limit_net,
        }

        logger.debug(data)
        return self.success_response(data=data)

    def put(self, request):
        """
        修改数据中心资源上限接口
        ---
        parameters:
            - name: region
              description: 数据中心名称
              required: true
              type: string
              paramType: form
            - name: res
              description: 资源详情{"memory":{"limit":1024,"stock":0}}
              required: true
              type: string
              paramType: form
        """
        region = request.data.get('region')
        res = request.data.get('res')

        if not region or not res:
            return self.error_response(status.HTTP_400_BAD_REQUEST, 'missing parameters', '参数不合法')

        user = request.user

        enter = market_api.get_enterprise_by_id(user.enterprise_id)
        if not enter:
            return self.error_response(status.HTTP_404_NOT_FOUND, 'enterprise not fond!', '企业信息不存在!')

        tenant = market_api.get_default_tenant_by_user(user.user_id)
        if not tenant:
            logger.error(LOGGER_TAG, 'user [{0}] do not have default tenant!'.format(user.user_id))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')

        if tenant.enterprise_id != enter.enterprise_id:
            logger.error(LOGGER_TAG,
                         'user default tenant: {} not belong to enterprise: {}!'.format(tenant.tenant_name,
                                                                                        enter.enterprise_name))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='user default tenant not belong to self enterprise!',
                                       msg_show='用户默认团队不归属于用户所在企业')

        market_api.limit_region_resource(tenant, region, res)
        return self.success_response()


class EnterGroupServiceListAPIView(EnterpriseMarketAPIView):
    def get(self, request):
        """
        获取云市企业下的应用组列表
        """
        group_ids = request.data.get('group_ids')
        region_name = request.data.get('region_name')

        if group_ids:
            logger.debug(LOGGER_TAG, 'Receive request from market, group ids:{0}'.format(group_ids))
            group_list = market_api.get_group_services_by_pk_list(group_ids)
        elif region_name:
            logger.debug(LOGGER_TAG, 'Receive request from market, region_name:{0}'.format(region_name))

            user = request.user
            tenant = market_api.get_default_tenant_by_user(user.user_id)
            if not tenant:
                logger.error(LOGGER_TAG, 'user [{0}] do not have default tenant!'.format(user.user_id))
                return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                           msg='tenant does not exist!',
                                           msg_show='租户不存在')

            group_list = market_api.list_group_service_by_region(tenant, region_name)
        else:
            group_list = list()

        ret_data = list()
        for group in group_list:
            service_list = list()
            if hasattr(group, 'service_list'):
                for s in group.service_list:
                    service_list.append({
                        'service_name': s.service_cname,
                        'service_version': s.version,
                        'service_status': s.status,
                        'access_url': s.access_url if s.status == 'running' else '',
                    })

            ret_data.append({
                'group_id': group.ID,
                'group_name': group.group_name,
                'region': group.region_name,
                'tenant_name': group.tenant.tenant_name,
                'group_status': group.status,
                'category_id': group.service_group_id,
                'service_list': service_list
            })

        return self.success_response(data=ret_data)

    def post(self, request):
        """
        在云市企业下创建应用组
        ---
        parameters:
            - name: group_key
              description: 应用组key
              required: true
              type: string
              paramType: form
            - name: group_version
              description: 应用组version
              required: true
              type: string
              paramType: form
            - name: region
              description: 安装到指定的数据中心
              required: true
              type: string
              paramType: form
            - name: tenant_name
              description: 安装到指定的租户上
              required: false
              type: string
              paramType: form
            - name: template_version
              description: 模板版本
              required: false
              type: string
              paramType: form
        """
        group_key = request.data.get('group_key')
        group_version = request.data.get('group_version')
        region_name = request.data.get('region_name')
        tenant_name = request.data.get('tenant_name')
        template_version = request.data.get('template_version', "v1")
        if not group_key or not group_version or not region_name:
            return self.error_response(code=status.HTTP_400_BAD_REQUEST,
                                       msg='group_key or group_version or region can not be null',
                                       msg_show='参数不合法')

        # success, message, group = market_api.install_tenant_service_group(request.user, tenant_name, group_key,
        #                                                                   group_version, region_name)
        group = None
        message = "安装失败"
        try:
            success, message, group = market_api.install_service_group(request.user, tenant_name, group_key,
                                                                       group_version, region_name,template_version)
        except Exception as e:
            logger.exception(e)
            success = False
        if success:
            result = {
                'group_id': group.pk,
                'svc_result': [{
                    'service_id': service.service_id,
                    'service_key': service.service_key,
                    'service_version': service.version,
                    'access_url': service.access_url,
                    'msg': 'installed succeed!',
                } for service in group.service_list]
            }
            return self.success_response(data=result, msg_show=message)
        else:
            return self.error_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg_show=message)


class EnterGroupServiceAPIView(EnterpriseMarketAPIView):
    def get(self, request, group_id):
        """
        获取云市应用组详情
        ---
        parameters:
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: path
        """
        user = request.user

        group = market_api.get_group_services_by_pk(group_id)
        if not group:
            logger.error(LOGGER_TAG, "Group {} is not exists".format(group_id))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='group does not exist!',
                                       msg_show='组应用不存在')

        return self.success_response(data={
            'group_id': group.ID,
            'group_name': group.group_name,
            'region': group.region_name,
            'tenant_name': group.tenant.tenant_name,
            'group_status': group.status,
            'category_id': group.service_group_id,
            'memory': group.memory,
            'net': group.net,
            'disk': group.disk
        })

    def put(self, request, group_id):
        """
        云市应用组生命周期状态操作接口
        restart: 重启组应用中包含的所有服务
        stop: 停止组应用中包含的所有服务
        ---
        parameters:
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: path
            - name: action
              description: 应用组实施操作类型
              required: true
              type: string
              paramType: form
        """
        action = request.data.get('action')

        if not self.__allowed_action(action):
            return self.error_response(code=status.HTTP_400_BAD_REQUEST,
                                       msg='not support operation!',
                                       msg_show='不支持的操作请求类型')

        success, message = True, '操作成功'
        if action == 'restart':
            success, message = market_api.restart_tenant_service_group(request.user, group_id)
        elif action == 'stop':
            success, message = market_api.stop_tenant_service_group(request.user, group_id)
        elif action == 'build':
            success, message = market_api.build_tenant_service_group(request.user, group_id)

        if success:
            return self.success_response(msg_show=message)
        else:
            return self.error_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg_show=message)

    def __allowed_action(self, action):
        return action in ('restart', 'stop', 'build')

    def delete(self, request, group_id):
        """
        删除云市应用组
        ---
        parameters:
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: path
        """
        success, message = market_api.delete_tenant_service_group(group_id)
        if success:
            return self.success_response(msg_show=message)
        else:
            return self.error_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg_show=message)


class EnterAppHttpPortAPIView(EnterpriseMarketAPIView):
    def get(self, request, group_id):
        """
        获取企业下端口是http的应用
        """
        http_port_svcs = market_api.get_service_of_avaliable_port(group_id)
        return self.success_response(data=http_port_svcs)


class EnterDomainAPIView(EnterpriseMarketAPIView):
    def post(self, request, service_id):
        domain_name = request.data.get('domain')
        ret, data = market_api.bind_domain(service_id, domain_name)
        if ret:
            return self.success_response(data={
                'service_id': data.service_id, 'domain_id': data.ID
            })
        return self.error_response(msg_show=data)

    def delete(self, request, service_id):
        domain_id = request.data.get('domain_id')
        ret, msg = market_api.unbind_domain(domain_id, service_id)
        if ret:
            return self.success_response()
        return self.error_response(msg_show=msg)


class EnterTenantsAPIView(EnterpriseMarketAPIView):
    def get(self, request):
        """
        获取企业管理数据中心列表
        """
        user = request.user
        # tenants = market_api.list_user_tenants(user.user_id, True)
        tenants = market_api.list_enterprise_tenants(user, True)

        data = []
        for tenant in tenants:
            data.append({
                'tenant_id': tenant.tenant_id,
                'tenant_name': tenant.tenant_name,
                'tenant_alias': tenant.tenant_alias,
                'balance': tenant.balance,
                'pay_type': tenant.pay_type,
                'is_default': True if tenant.creater == user.user_id else False,
                'tenant_regions': [{
                    'region': tr.region_name,
                    'is_active': tr.is_active,
                    'service_status': tr.service_status,
                    'is_init': tr.is_init
                } for tr in tenant.regions]
            })
        return self.success_response(data=data)


# class EnterEventAPIView(EnterpriseMarketAPIView):
#     def get(self, request):
#         """
#         获取异步事件的运行状态
#         ---
#         parameters:
#             - name: event_id
#               description: 事件ID
#               required: true
#               type: string
#               paramType: form
#         """
#         group_ids = request.data.get('group_ids')
#         region_name = request.data.get('region_name')
#
#         if group_ids:
#             logger.debug(LOGGER_TAG, 'Receive request from market, group ids:{0}'.format(group_ids))
#             group_list = market_api.get_group_services_by_pk_list(group_ids)
#         elif region_name:
#             logger.debug(LOGGER_TAG, 'Receive request from market, region_name:{0}'.format(region_name))
#
#             user = request.user
#             tenant = market_api.get_default_tenant_by_user(user.user_id)
#             if not tenant:
#                 logger.error(LOGGER_TAG, 'user [{0}] do not have default tenant!'.format(user.user_id))
#                 return self.error_response(code=status.HTTP_404_NOT_FOUND,
#                                            msg='tenant does not exist!',
#                                            msg_show='租户不存在')
#
#             group_list = market_api.list_group_service_by_region(tenant, region_name)
#         else:
#             group_list = list()
#
#         ret_data = list()
#         for group in group_list:
#             ret_data.append({
#                 'group_id': group.ID,
#                 'group_name': group.group_name,
#                 'region': group.region_name,
#                 'tenant_name': group.tenant.tenant_name,
#                 'group_status': group.status,
#                 'category_id': group.service_group_id,
#             })
#
#         return self.success_response(data=ret_data)
#
#     def post(self, request):
#         """
#         创建一个企业异步操作事件
#         ---
#         parameters:
#             - name: event_id
#               description: 事件ID
#               required: true
#               type: string
#               paramType: form
#             - name: event_type
#               description: 事件类型
#               required: true
#               type: string
#               paramType: form
#             - name: event_data
#               description: 事件请求数据
#               required: true
#               type: string
#               paramType: form
#         """
#         group_key = request.data.get('group_key')
#         group_version = request.data.get('group_version')
#         region_name = request.data.get('region_name')
#         tenant_name = request.data.get('tenant_name')
#         if not group_key or not group_version or not region_name:
#             return self.error_response(code=status.HTTP_400_BAD_REQUEST,
#                                        msg='group_key or group_version or region can not be null',
#                                        msg_show='参数不合法')
#
#         success, message, group = market_api.install_tenant_service_group(request.user, tenant_name, group_key,
#                                                                           group_version, region_name)
#         if success:
#             result = {
#                 'group_id': group.pk,
#                 'svc_result': [{
#                     'service_id': service.service_id,
#                     'service_key': service.service_key,
#                     'service_version': service.version,
#                     'access_url': service.access_url,
#                     'msg': 'installed succeed!',
#                 } for service in group.service_list]
#             }
#             return self.success_response(data=result, msg_show=message)
#         else:
#             return self.error_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg_show=message)