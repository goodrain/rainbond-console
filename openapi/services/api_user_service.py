# -*- coding: utf-8 -*-
# creater by: barnett

from console.services.user_services import user_services
from www.models.main import Users


class ErrorUser(Exception):
    def __init__(self, message):
        self.message = message


class APIUserService(object):
    def get_token(self, user):
        if not isinstance(user, Users):
            raise ErrorUser("user is not rainbond user")
        return user_services.get_administrator_user_token(user)

    def get_user_by_token(self, token):
        return user_services.get_user_by_openapi_token(token)

    def login_api_user(self, username, password):
        user = user_services.get_user_by_username(username)
        if not user:
            return None
        if not user.check_password(password):
            return None
        if user_services.is_user_admin_in_current_enterprise(user, user.enterprise_id):
            return self.get_token(user)
        return None

    def get_permissions_by_user(self, user, enterprise_id):
        if not isinstance(user, Users):
            raise ErrorUser("user is not rainbond user")
        # TODO:impl rbac
        # TODO: get perm list by user_services.get_user_in_enterprise_perm
        if user_services.is_user_admin_in_current_enterprise(user, enterprise_id):
            return ["all"]
        return ["common"]


apiUserService = APIUserService()
