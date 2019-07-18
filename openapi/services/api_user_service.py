# -*- coding: utf-8 -*-
# creater by: barnett

from www.models.main import Users
from rest_framework.authtoken.models import Token
from console.services.user_services import user_services


class ErrorUser(Exception):
    def __init__(self, message):
        self.message = message


class APIUserService(object):
    def get_token(self, user):
        if not isinstance(user, Users):
            raise ErrorUser("user is not rainbond user")
        token, created = Token.objects.get_or_create(user=user)
        return token.key

    def get_user_by_token(self, token):
        tokenmodel = Token.objects.filter(key=token)
        if tokenmodel and len(tokenmodel) > 0:
            user_id = tokenmodel[0].user_id
            return user_services.get_user_by_user_id(user_id)
        return None

    def get_permissions_by_user(self, user, enterprise_id):
        if not isinstance(user, Users):
            raise ErrorUser("user is not rainbond user")
        # TODO:impl rbac
        if user_services.is_user_admin_in_current_enterprise(user, enterprise_id):
            return ["all"]
        return None


apiUserService = APIUserService()
