# -*- coding: utf-8 -*-
import logging

from django.http import JsonResponse
from django.views.generic import View
from rest_framework.response import Response

from console.views.base import AlowAnyApiView
from www.auth import authenticate, login, jwtlogin
from www.models import Users, Tenants, TenantServiceInfo, PermRelTenant, \
    PermRelService, TenantEnterprise
from www.monitorservice.monitorhook import MonitorHook
from www.services import enterprise_svc, user_svc
from www.services.sso import GoodRainSSOApi
from www.tenantservice.baseservice import CodeRepositoriesService
from www.utils.crypt import AuthCode
from www.utils.return_message import general_message, error_message
from www.views import BaseView
from console.services.enterprise_services import enterprise_services
from console.services.user_services import user_services
from console.services.team_services import team_services
from console.services.perm_services import perm_services,app_perm_service
from console.repositories.app import service_repo
from console.repositories.perm_repo import service_perm_repo

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

    def __update_user_info(self,sso_user,sso_user_id,sso_user_token,rf):
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
        service_perm = app_perm_service.get_user_service_perm(user.user_id,service.ID)
        if not service_perm:
            service_perm_repo.add_service_perm(user.user_id, service.ID, identity)

    def post(self, request, *args, **kwargs):
        try:
            # 获取sso的user_id
            sso_user_id = request.POST.get('uid')
            sso_user_token = request.POST.get('token')
            sso_enterprise_id = request.POST.get('eid')
            rf = request.POST.get('rf') or 'sso'
            rf_username = request.POST.get('rf_username') or ''
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
                enterprise = enterprise_services.create_tenant_enterprise(sso_user.get('eid'),sso_company,sso_company,True)
            user = self.__update_user_info(sso_user,sso_user_id,sso_user_token,rf)

            key = request.POST.get('key')
            logger.debug('invite key: {0}'.format(key))
            if key:
                logger.debug('account.login', 'invite register: {}'.format(key))
                data = AuthCode.decode(str(key), 'goodrain').split(',')
                logger.debug(data)
                action = data[0]
                if action == 'invite_tenant':
                    self.__process_invite_tenant(user, data)
                elif action == 'invite_service':
                    self.__process_invite_service(user,data)
                user.is_active = True
                user.save()
                logger.debug('account.login', 'user invite register successful')
            else:
                logger.debug('account.login', 'register/login user.is_active:{}'.format(user.is_active))
                if not user.is_active:
                    # 初始化数据中心并创建租户信息
                    # TODO
                    pass



        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)
