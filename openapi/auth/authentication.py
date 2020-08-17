# -*- coding: utf-8 -*-
# creater by: barnett

import logging
from www.models.main import Users
from openapi.services.api_user_service import apiUserService
from rest_framework import authentication
from rest_framework import exceptions
import os
logger = logging.getLogger("default")


class OpenAPIAuthentication(authentication.TokenAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            raise exceptions.AuthenticationFailed('No token')
        try:
            user = apiUserService.get_user_by_token(token)
            if not user:
                raise exceptions.AuthenticationFailed('No such user or user is not admin')
        except Exception as e:
            logger.exception(e)
            raise exceptions.AuthenticationFailed('No such user')
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
