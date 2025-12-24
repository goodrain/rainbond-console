# -*- coding: utf-8 -*-
# creater by: barnett

import logging
import os

from rest_framework import authentication, exceptions

from openapi.services.api_user_service import apiUserService
from www.models.main import Users, TenantEnterprise

logger = logging.getLogger("default")


class OpenAPIAuthentication(authentication.TokenAuthentication):
    def authenticate(self, request):
        # 优先检查 X-Internal-Token (内部服务调用)
        internal_token = request.META.get('HTTP_X_INTERNAL_TOKEN')
        if internal_token:
            expected_token = os.environ.get("INTERNAL_API_TOKEN", "")
            if expected_token and internal_token == expected_token:
                # 获取第一个企业的 enterprise_id 用于内部调用
                enterprise = TenantEnterprise.objects.first()
                enterprise_id = enterprise.enterprise_id if enterprise else ""
                # 创建一个虚拟的管理员用户用于内部调用
                user = Users(nick_name="InternalAPI", user_id=0, enterprise_id=enterprise_id)
                return (user, None)
            raise exceptions.AuthenticationFailed('Invalid internal token')

        # 常规 Token 认证
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            raise exceptions.AuthenticationFailed('No token')
        try:
            user = apiUserService.get_user_by_token(token)
        except Exception as e:
            logger.exception(e)
            raise exceptions.AuthenticationFailed('No such user')
        if not user:
            raise exceptions.AuthenticationFailed('No such user or user is not admin')
        return (user, None)


class OpenAPIManageAuthentication(authentication.TokenAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            raise exceptions.AuthenticationFailed('No token')
        manage_token = os.environ.get("MANAGE_TOKEN", "")
        if not manage_token or manage_token != token:
            raise exceptions.AuthenticationFailed('token is invalid')
        user = Users(nick_name="ManageOpenAPI")
        return (user, None)
