# -*- coding: utf-8 -*-
import logging
import os

from django.conf import settings
from rest_framework.response import Response

from console.repositories.app import service_repo
from console.repositories.perm_repo import service_perm_repo
from console.services.enterprise_services import enterprise_services
from console.services.perm_services import perm_services, app_perm_service
from console.services.plugin import plugin_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.views.base import AlowAnyApiView
from www.apiclient.baseclient import client_auth_service
from www.monitorservice.monitorhook import MonitorHook
from www.services.sso import GoodRainSSOApi
from www.tenantservice.baseservice import CodeRepositoriesService
from www.utils.crypt import AuthCode

logger = logging.getLogger('default')

codeRepositoriesService = CodeRepositoriesService()

monitor_hook = MonitorHook()


class GoodrainSSONotify(AlowAnyApiView):
    def __check_params(self, sso_user_id, sso_user_token, sso_enterprise_id):
        if not sso_user_id or not sso_user_token or not sso_enterprise_id:
            logger.error('account.login', 'post params [uid] or [token] or [eid] not specified!')
            return False, "post params [uid] or [token] or [eid] not specified!"
        if sso_user_id == 'null' or sso_user_token == 'null':
            logger.error('account.login', 'bad uid or token, value is null!')
            return False, "bad uid or token, value is null!"
        return True, "success"

    def __get_auth_user_token(self, sso_user_id, sso_user_token):
        api = GoodRainSSOApi(sso_user_id, sso_user_token)
        if not api.auth_sso_user_token():
            logger.error('account.login', 'Illegal user token!')
            return False, "auth from sso failed!", None
        sso_user = api.get_sso_user_info()
        return True, "success", sso_user

    def __update_user_info(self, sso_user, sso_user_id, sso_user_token, rf):
        sso_eid = sso_user.get('eid')
        sso_username = sso_user.get('name')
        sso_phone = sso_user.get('mobile')
        sso_pwd = sso_user.get('pwd')

        # update or create user
        user = user_services.get_user_by_sso_user_id(sso_user_id)
        if user:
            user.sso_user_token = sso_user_token
            user.password = sso_pwd or ''
            user.phone = sso_phone or ''
            user.nick_name = sso_username
            user.enterprise_id = sso_eid
            user.save()
            logger.debug('account.login', 'query user with sso_user_id existed, updated!')
        else:
            user = user_services.create_user(sso_username, sso_pwd or '', sso_user.get('email') or '', sso_eid, rf)
            user.phone = sso_phone or ''
            user.sso_user_id = sso_user.get('uid')
            user.sso_user_token = sso_user_token
            user.is_active = False
            user.save()
            logger.debug('account.login', 'query user with sso_user_id does not existed, created!')
        return user

    def __process_invite_tenant(self, user, data):
        email, tenant_name, identity = data[1], data[2], data[3]
        tenant = team_services.get_tenant_by_tenant_name(tenant_name)
        tenant_perm = perm_services.get_user_tenant_perm(tenant.ID, user.user_id)
        if not tenant_perm:
            invite_enter = enterprise_services.get_enterprise_by_enterprise_id(tenant.enterprise_id)
            perm_info = {
                "user_id": user.user_id,
                "tenant_id": tenant.ID,
                "identity": identity,
                "enterprise_id": invite_enter.pk
            }
            perm_services.add_user_tenant_perm(perm_info)

    def __process_invite_service(self, user, data):
        email, tenant_name, service_alias, identity = data[1], data[2], data[3], data[4]
        service = service_repo.get_service_by_service_alias(service_alias)
        service_perm = app_perm_service.get_user_service_perm(user.user_id, service.ID)
        if not service_perm:
            service_perm_repo.add_service_perm(user.user_id, service.ID, identity)

    def __init_and_create_user_tenant(self, user, enterprise):
        # 创建租户信息
        code, msg, team = team_services.create_team(user, enterprise)
        if code != 200:
            logger.debug("account.login","create tenant error")
            return code, msg, team
        # 创建用户在团队的权限
        perm_info = {
            "user_id": user.user_id,
            "tenant_id": team.ID,
            "identity": "owner",
            "enterprise_id": enterprise.pk
        }
        perm_services.add_user_tenant_perm(perm_info)
        # 创建用户在企业的权限
        user_services.make_user_as_admin_for_enterprise(user.user_id, enterprise.enterprise_id)
        # 为团队开通默认数据中心并在数据中心创建租户
        code, msg, tenant_region = region_services.create_tenant_on_region(team.tenant_name, team.region)
        if code != 200:
            logger.debug("account.login", "create teanant on region error")
            return code, msg, team
        # 如果没有领过资源包，为默认开通的数据中心领取免费资源包
        result = region_services.get_enterprise_free_resource(tenant_region.tenant_id, enterprise.enterprise_id,
                                                              tenant_region.region_name, user.nick_name)
        logger.debug("account.login", "get free resource on [{}] to team {}: {}".format(tenant_region.region_name,
                                                                                        team.tenant_name,
                                                                                        result))

        user.is_active = True
        user.save()
        return code, msg, team

    def post(self, request, *args, **kwargs):
        try:
            # 获取sso的user_id
            sso_user_id = request.data.get('uid')
            sso_user_token = request.data.get('token')
            sso_enterprise_id = request.data.get('eid')
            rf = request.data.get('rf') or 'sso'
            market_client_id = request.data.get('eid')
            market_client_token = request.data.get('etoken')
            if not market_client_id or not market_client_token:
                msg = "no market_client_id or market_client_token"
                logger.debug('account.login', msg)
                return Response({'success': False, 'msg': msg})
            rf_username = request.data.get('rf_username') or ''
            logger.debug('account.login',
                         'request.sso_user_id:{0}  request.sso_user_token:{1}  request.sso_enterprise_id:{2}'.format(
                             sso_user_id, sso_user_token, sso_enterprise_id))
            is_pass, msg = self.__check_params(sso_user_id, sso_user_token, sso_enterprise_id)
            if not is_pass:
                return Response({'success': False, 'msg': msg})
            is_pass, msg, sso_user = self.__get_auth_user_token(sso_user_id, sso_user_token)
            if not is_pass:
                return Response({'success': False, 'msg': msg})

            enterprise = enterprise_services.get_enterprise_by_enterprise_id(sso_user.get('eid'))
            if not enterprise:
                sso_company = sso_user.get('company')
                enterprise = enterprise_services.create_tenant_enterprise(sso_user.get('eid'), sso_company, sso_company,
                                                                          True)
            user = self.__update_user_info(sso_user, sso_user_id, sso_user_token, rf)
            # 保存访问云市的token
            domain = os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"])
            client_auth_service.save_market_access_token(enterprise.enterprise_id, domain, market_client_id,
                                                         market_client_token)

            key = request.data.get('key')
            logger.debug('invite key: {0}'.format(key))
            if key:
                logger.debug('account.login', 'invite register: {}'.format(key))
                data = AuthCode.decode(str(key), 'goodrain').split(',')
                logger.debug(data)
                action = data[0]
                if action == 'invite_tenant':
                    self.__process_invite_tenant(user, data)
                elif action == 'invite_service':
                    self.__process_invite_service(user, data)
                user.is_active = True
                user.save()
                logger.debug('account.login', 'user invite register successful')
            else:
                logger.debug('account.login', 'register/login user.is_active:{}'.format(user.is_active))
                if not user.is_active:
                    code, msg, team = self.__init_and_create_user_tenant(user, enterprise)
                    if code != 200:
                        return Response({'success': False, 'msg': msg}, status=500)

                    # 如果注册用户是通过云市私有交付创建的企业客户, 则将厂商账户加入到其客户企业的管理员列表
                    agent_sso_user_id = request.data.get('agent_sid')
                    logger.debug('account.login', 'agent_sid: {}'.format(agent_sso_user_id))
                    if agent_sso_user_id:
                        agent_user = user_services.get_user_by_sso_user_id(agent_sso_user_id)
                        if agent_user:
                            # 创建用户在团队的权限
                            perm_info = {
                                "user_id": agent_user.user_id,
                                "tenant_id": team.ID,
                                "identity": "admin",
                                "enterprise_id": enterprise.pk
                            }
                            perm_services.add_user_tenant_perm(perm_info)
                            logger.debug('account.login', 'agent manage team success: {}'.format(perm_info))

            logger.debug('account.login', "enterprise id {0}".format(enterprise.enterprise_id))
            teams = team_services.get_enterprise_teams(enterprise.enterprise_id)
            data_list = [{
                             'uid': user.sso_user_id,
                             'tenant_id': t.tenant_id,
                             'tenant_name': t.tenant_name,
                             'tenant_alias': t.tenant_alias,
                             'eid': t.enterprise_id
                         } for t in teams]
            return Response({'success': True, 'list': data_list}, status=200)

        except Exception as e:
            logger.exception(e)
            return Response({'success': False, 'msg': e.message}, status=500)
