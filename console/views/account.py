# -*- coding: utf-8 -*-
import logging

from django.http import JsonResponse
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
from www.utils.return_message import general_message
from www.views import BaseView

logger = logging.getLogger('default')

codeRepositoriesService = CodeRepositoriesService()

monitor_hook = MonitorHook()


# class GoorainSsoCallBack(AlowAnyApiView):
#     def get(self, request, *args, **kwargs):
#         """
#         处理SSO回调登陆
#         ---
#         parameter:
#             - name: team_name
#               description: 团队名
#               required: true
#               type: string
#               paramType: path
#         """
#         # 获取sso的user_id
#         sso_user_id = request.COOKIES.get('uid')
#         sso_user_token = request.COOKIES.get('token')
#
#         data = dict()
#
#         logger.debug('cookies.sso_user_id:{}'.format(sso_user_id))
#         logger.debug('cookies.sso_user_token:{}'.format(sso_user_token))
#         if not sso_user_id or not sso_user_token:
#             logger.error('cookies uid or token not specified!')
#             url = "https://sso.goodrain.com/#/login/"
#             data["url"] = url
#             data["is_redirect"] = True
#             result = general_message(400, "cookies uid or token not specified!", "未指定cookie uid或token", bean=data)
#             return Response(result, status=400)
#
#         if sso_user_id == 'null' or sso_user_token == 'null':
#             logger.error('bad uid or token, value is null!')
#             url = "https://sso.goodrain.com/#/login/"
#             data["url"] = url
#             data["is_redirect"] = True
#             result = general_message(400, "bad uid or token, value is null!", "uid或token值为空。", bean=data)
#             return Response(result, status=400)
#
#         api = GoodRainSSOApi(sso_user_id, sso_user_token)
#         if not api.auth_sso_user_token():
#             logger.error('Illegal user token!')
#             url = "https://sso.goodrain.com/#/login/"
#             data["url"] = url
#             data["is_redirect"] = True
#             result = general_message(400, "Illegal user token!", "非法用户令牌", bean=data)
#             return Response(result, status=400)
#
#         # 同步sso_id所代表的企业信息，没有则创建
#         try:
#             user = Users.objects.get(sso_user_id=sso_user_id)
#             if user.sso_user_token != sso_user_token:
#                 user.sso_user_token = sso_user_token
#                 user.save()
#         except Users.DoesNotExist:
#             logger.debug('query user with sso_user_id does not existed, created!')
#             sso_user = api.get_sso_user_info()
#             logger.debug(sso_user)
#             try:
#                 TenantEnterprise.objects.get(enterprise_id=sso_user.eid)
#             except TenantEnterprise.DoesNotExist:
#                 enterprise = TenantEnterprise()
#                 enterprise.enterprise_id = sso_user.eid
#                 enterprise.enterprise_name = sso_user.company
#                 enterprise.enterprise_alias = sso_user.company
#                 enterprise.is_active = 1
#                 enterprise.save()
#                 logger.info(
#                     'create enterprise[{0}] with name {1}'.format(enterprise.enterprise_id,
#                                                                   enterprise.enterprise_name))
#
#             user = Users.objects.create(nick_name=sso_user.name,
#                                         email=sso_user.email or '',
#                                         phone=sso_user.mobile or '',
#                                         password=sso_user.pwd or '',
#                                         sso_user_id=sso_user.uid,
#                                         enterprise_id=sso_user.eid,
#                                         sso_user_token=sso_user_token,
#                                         is_active=False,
#                                         rf='sso')
#             logger.info(
#                 'create user[{0}] with name [{1}] from [{2}] use sso_id [{3}]'.format(user.user_id, user.nick_name,
#                                                                                       user.rf,
#                                                                                       user.sso_user_id))
#             monitor_hook.registerMonitor(user, 'register')
#
#         if not user.is_active:
#             tenant = enterprise_svc.create_and_init_tenant(user.user_id, enterprise_id=user.enterprise_id)
#         else:
#             tenant = user_svc.get_default_tenant_by_user(user.user_id)
#         logger.info(tenant.to_dict())
#
#         # create gitlab user
#         if user.email is not None and user.email != "":
#             codeRepositoriesService.createUser(user, user.email, user.password, user.nick_name, user.nick_name)
#
#         # SSO用户登录
#         user = authenticate(user_id=user.user_id, sso_user_id=user.sso_user_id)
#         login(request, user)
#         self.user = request.user
#
#         next_url = request.GET.get('next')
#         if next_url:
#             result = general_message(200, "success", "跳转到next指向的页面")
#             return Response(result, status=200)
#         result = general_message(200, "success", "跳转到登录成功后的第一个页面")
#         return Response(result, status=200)
class GoorainSsoCallBack(BaseView):
    """
    处理SSO回调登陆
    """

    def get(self, request, *args, **kwargs):
        # 获取sso的user_id
        sso_user_id = request.COOKIES.get('uid')
        sso_user_token = request.COOKIES.get('token')

        logger.debug('cookies.sso_user_id:{}'.format(sso_user_id))
        logger.debug('cookies.sso_user_token:{}'.format(sso_user_token))

        if not sso_user_id or not sso_user_token:
            logger.error('cookies uid or token not specified!')
            return self.redirect_to("/login")

        if sso_user_id == 'null' or sso_user_token == 'null':
            logger.error('bad uid or token, value is null!')
            return self.redirect_to("/login")

        api = GoodRainSSOApi(sso_user_id, sso_user_token)
        if not api.auth_sso_user_token():
            logger.error('Illegal user token!')
            return self.redirect_to("/login")

        # 同步sso_id所代表的企业信息，没有则创建
        try:
            user = Users.objects.get(sso_user_id=sso_user_id)
            if user.sso_user_token != sso_user_token:
                user.sso_user_token = sso_user_token
                user.save()
        except Users.DoesNotExist:
            logger.debug('query user with sso_user_id does not existed, created!')
            sso_user = api.get_sso_user_info()
            logger.debug(sso_user)
            try:
                enterprise = TenantEnterprise.objects.get(enterprise_id=sso_user.eid)
            except TenantEnterprise.DoesNotExist:
                enterprise = TenantEnterprise()
                enterprise.enterprise_id = sso_user.eid
                enterprise.enterprise_name = sso_user.company
                enterprise.enterprise_alias = sso_user.company
                enterprise.is_active = 1
                enterprise.save()
                logger.info(
                    'create enterprise[{0}] with name {1}'.format(enterprise.enterprise_id,
                                                                  enterprise.enterprise_name))

            user = Users.objects.create(nick_name=sso_user.name,
                                        email=sso_user.email or '',
                                        phone=sso_user.mobile or '',
                                        password=sso_user.pwd or '',
                                        sso_user_id=sso_user.uid,
                                        enterprise_id=sso_user.eid,
                                        sso_user_token=sso_user_token,
                                        is_active=False,
                                        rf='sso')
            logger.info(
                'create user[{0}] with name [{1}] from [{2}] use sso_id [{3}]'.format(user.user_id, user.nick_name,
                                                                                      user.rf,
                                                                                      user.sso_user_id))
            monitor_hook.registerMonitor(user, 'register')

        if not user.is_active:
            tenant = enterprise_svc.create_and_init_tenant(user.user_id, enterprise_id=user.enterprise_id)
        else:
            tenant = user_svc.get_default_tenant_by_user(user.user_id)
        logger.info(tenant.to_dict())

        # create gitlab user
        if user.email is not None and user.email != "":
            codeRepositoriesService.createUser(user, user.email, user.password, user.nick_name, user.nick_name)

        # SSO用户登录
        user = authenticate(user_id=user.user_id, sso_user_id=user.sso_user_id)
        jwtlogin(request, user)
        self.user = request.user

        next_url = request.GET.get('next')
        if next_url:
            return self.redirect_to(next_url)
        return self.redirect_to('/apps/{0}/'.format(tenant.tenant_name))


class GoodrainSsoNotify(BaseView):
    def post(self, request, *args, **kwargs):
        """
        SSO通知，用户信息同步回来
        """
        # 获取sso的user_id
        sso_user_id = request.POST.get('uid')
        sso_user_token = request.POST.get('token')
        sso_enterprise_id = request.POST.get('eid')

        logger.debug('request.sso_user_id:{}'.format(sso_user_id))
        logger.debug('request.sso_user_token:{}'.format(sso_user_token))
        logger.debug('request.sso_enterprise_id:{}'.format(sso_enterprise_id))

        if not sso_user_id or not sso_user_token or not sso_enterprise_id:
            logger.error('post params [uid] or [token] or [eid] not specified!')
            return JsonResponse({'success': False, 'msg': 'post params [uid] or [token] or [eid] not specified!'})

        if sso_user_id == 'null' or sso_user_token == 'null':
            logger.error('bad uid or token, value is null!')
            return JsonResponse({"success": False, 'msg': 'bad uid or token, value is null!'})

        api = GoodRainSSOApi(sso_user_id, sso_user_token)
        if not api.auth_sso_user_token():
            logger.error('Illegal user token!')
            return JsonResponse({"success": False, 'msg': 'auth from sso failed!'})

        sso_user = api.get_sso_user_info()
        logger.debug(sso_user)
        # 同步sso_id所代表的用户与企业信息，没有则创建
        sso_eid = sso_user.get('eid')
        sso_company = sso_user.get('company')
        sso_username = sso_user.get('name')
        sso_phone = sso_user.get('mobile')
        sso_pwd = sso_user.get('pwd')
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_id=sso_eid)
            logger.debug('query enterprise does existed, updated!')
        except TenantEnterprise.DoesNotExist:
            logger.debug('query enterprise does not existed, created!')
            enterprise = TenantEnterprise()
            enterprise.enterprise_id = sso_eid
            enterprise.enterprise_name = sso_company
            enterprise.enterprise_alias = sso_company
            enterprise.is_active = 1
            enterprise.save()
            logger.info(
                'create enterprise[{0}] with name {1}'.format(enterprise.enterprise_id,
                                                              enterprise.enterprise_name))

        try:
            user = Users.objects.get(sso_user_id=sso_user_id)
            user.sso_user_token = sso_user_token
            user.password = sso_pwd or ''
            user.phone = sso_phone or ''
            user.nick_name = sso_username
            user.enterprise_id = sso_eid
            user.save()

            logger.debug('query user with sso_user_id existed, updated!')
        except Users.DoesNotExist:
            logger.debug('query user with sso_user_id does not existed, created!')
            user = Users.objects.create(nick_name=sso_username,
                                        email=sso_user.get('email') or '',
                                        phone=sso_phone or '',
                                        password=sso_pwd or '',
                                        sso_user_id=sso_user.get('uid'),
                                        enterprise_id=sso_eid,
                                        sso_user_token=sso_user_token,
                                        is_active=False,
                                        rf='sso')
            logger.info(
                'create user[{0}] with name [{1}] from [{2}] use sso_id [{3}]'.format(user.user_id, user.nick_name,
                                                                                      user.rf,
                                                                                      user.sso_user_id))
            monitor_hook.registerMonitor(user, 'register')

        logger.debug('user.is_active:{}'.format(user.is_active))
        if not user.is_active:
            tenant = enterprise_svc.create_and_init_team(user.user_id, enterprise_id=user.enterprise_id)
        else:
            tenant = user_svc.get_default_tenant_by_user(user.user_id)
        logger.info(tenant.to_dict())

        key = request.POST.get('key')
        logger.debug('invite key: {}'.format(key))
        if key:
            data = AuthCode.decode(str(key), 'goodrain').split(',')
            logger.debug(data)
            action = data[0]
            if action == 'invite_tenant':
                email, tenant_name, identity = data[1], data[2], data[3]
                tenant = Tenants.objects.get(tenant_name=tenant_name)
                if PermRelTenant.objects.filter(user_id=user.user_id, tenant_id=tenant.pk).count() == 0:
                    invite_enter = TenantEnterprise.objects.get(enterprise_id=tenant.enterprise_id)
                    PermRelTenant.objects.create(user_id=user.user_id, tenant_id=tenant.pk, identity=identity,
                                                 enterprise_id=invite_enter.pk)

            elif action == 'invite_service':
                email, tenant_name, service_alias, identity = data[1], data[2], data[3], data[4]
                tenant_service = TenantServiceInfo.objects.get(service_alias=service_alias)
                if PermRelService.objects.filter(user_id=user.user_id, service_id=tenant_service.pk).count() == 0:
                    PermRelService.objects.create(user_id=user.user_id, service_id=tenant_service.pk, identity=identity)

            logger.debug('user invite sucess')
        return JsonResponse({"success": True})
