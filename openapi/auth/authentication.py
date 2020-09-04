# -*- coding: utf-8 -*-
# creater by: barnett

import logging
import os

from rest_framework import authentication, exceptions

from openapi.services.api_user_service import apiUserService
from www.models.main import Users

logger = logging.getLogger("default")


class OpenAPIAuthentication(authentication.TokenAuthentication):
    def authenticate(self, request):
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
