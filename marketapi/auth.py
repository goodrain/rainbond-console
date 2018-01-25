# -*- coding: utf8 -*-

import logging

from rest_framework import authentication
from rest_framework import exceptions

from www.models.main import Users, TenantEnterprise
from www.services.sso import GoodRainSSOApi

logger = logging.getLogger('default')


class MarketAPIAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        sso_user_id = request.META.get('HTTP_X_SSO_USER_ID')
        sso_user_token = request.META.get('HTTP_X_SSO_USER_TOKEN')
        if not sso_user_id or not sso_user_token:
            raise exceptions.AuthenticationFailed('X_SSO_USER_ID or X_SSO_USER_TOKEN not specified!')

        # 如果认证的sso用户id已经跟本地用户关联，并完成了企业绑定，则认为是合法用户, 先用本地认证，减少跟SSO的交互提高效率
        try:
            user = Users.objects.get(sso_user_id=sso_user_id)
            if user.sso_user_token == sso_user_token:
                # logger.info('auth user token from local succeed!')
                return user, None

            # 本地验证不相符则进行远程验证
            api = GoodRainSSOApi(sso_user_id, sso_user_token)
            if not api.auth_sso_user_token():
                logger.error('auth user token from remote failed!')
                logger.error('sso_user_id:'.format(sso_user_id))
                logger.error('sso_user_token:'.format(sso_user_token))
                raise exceptions.AuthenticationFailed('Illegal user token!')

            # 本地验证失败，但远程成功, 则使用远程的token来更新本地token
            user.sso_user_token = sso_user_token
            user.save()
            return user, None
        except Users.DoesNotExist:
            raise exceptions.AuthenticationFailed('no local user find to bind with login sso_user!')
