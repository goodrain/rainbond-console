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

        api = GoodRainSSOApi(sso_user_id, sso_user_token)
        # 如果认证的sso用户id已经跟本地用户关联，并完成了企业绑定，则认为是合法用户, 先用本地认证，减少跟SSO的交互提高效率
        try:
            user = Users.objects.get(sso_user_id=sso_user_id)
            if user.sso_user_token == sso_user_token:
                logger.info('auth user token from local succeed!')
                return user, None

            # 本地验证不相符则进行远程验证
            if not api.auth_sso_user_token():
                logger.error('auth user token from remote failed!')
                logger.debug('sso_user_id:'.format(sso_user_id))
                logger.debug('sso_user_token:'.format(sso_user_token))
                raise exceptions.AuthenticationFailed('Illegal user token!')

            # 本地验证失败，但远程成功, 则使用远程的token来更新本地token
            user.sso_user_token = sso_user_token
            user.save()
        except Users.DoesNotExist:
            # 如果本地关联用户不存在，先通过远程来校验用户信息
            if not api.auth_sso_user_token():
                logger.error('auth user token from remote failed!')
                logger.debug('sso_user_id:'.format(sso_user_id))
                logger.debug('sso_user_token:'.format(sso_user_token))
                raise exceptions.AuthenticationFailed('Illegal user token!')

            # 同步sso_id所代表的用户与企业信息
            sso_user = api.get_sso_user_info()
            logger.debug(sso_user)
            try:
                enterprise = TenantEnterprise.objects.get(enterprise_id=sso_user.eid)
                logger.info('enterprise[{0}] already existed!'.format(enterprise.enterprise_id))
            except TenantEnterprise.DoesNotExist:
                enterprise = TenantEnterprise.objects.create(enterprise_id=sso_user.eid,
                                                             enterprise_name=sso_user.company,
                                                             enterprise_alias=sso_user.company,
                                                             enterprise_token=sso_user_token,
                                                             is_active=1)
                logger.info(
                    'create enterprise[{0}] with name {1}'.format(enterprise.enterprise_id,
                                                                  enterprise.enterprise_name))

            user = Users.objects.create(nick_name=sso_user.username,
                                        password=sso_user.pwd,
                                        email=sso_user.email or '',
                                        phone=sso_user.mobile or '',
                                        sso_user_id=sso_user.uid,
                                        sso_user_token=sso_user_token,
                                        enterprise_id=sso_user.eid,
                                        is_active=False,
                                        rf='sso')
            logger.info(
                'create user[{0}] with name [{1}] from [{2}] use sso_id [{3}]'.format(user.user_id,
                                                                                      user.nick_name,
                                                                                      user.rf,
                                                                                      user.sso_user_id))

        return user, None
