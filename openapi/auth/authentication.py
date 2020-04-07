# -*- coding: utf-8 -*-
# creater by: barnett

import logging
import os
from openapi.services.api_user_service import apiUserService
from www.models.main import Users
from rest_framework import authentication
from rest_framework import exceptions
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


class EnterOpenAPIAuthentication(authentication.TokenAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION')
        user = None
        if not token:
            raise exceptions.AuthenticationFailed('No Token')
        try:
            if token == os.getenv("CONSOLE_API_TOKEN", "yBZ7LcveQNyjXuLjU3c3JmBARdNQnRUY7UqUKYpPn8g"):
                user = Users(user_id=-1)
            print user
            if not user:
                raise exceptions.AuthenticationFailed('No such user')
        except Exception as e:
            logger.exception(e)
            raise exceptions.AuthenticationFailed('No such user')
        return (user, None)
