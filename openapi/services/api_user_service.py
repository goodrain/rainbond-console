# -*- coding: utf-8 -*-
# creater by: barnett

from typing import Any, Optional
from console.services.user_services import user_services
from www.models.main import Users


class ErrorUser(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class APIUserService(object):
    def get_token(self, user: Any) -> Any:
        if not isinstance(user, Users):
            raise ErrorUser("user is not rainbond user")
        return user_services.get_administrator_user_token(user)

    def get_user_by_token(self, token: str) -> Any:
        return user_services.get_user_by_openapi_token(token)

    def login_api_user(self, username: str, password: str) -> Optional[Any]:
        user = user_services.get_user_by_username(username)
        if not user:
            return None
        if not user.check_password(password):
            return None
        # NOTE: enterprise_id typed str|None by stubs; runtime always str.
        if user_services.is_user_admin_in_current_enterprise(user, user.enterprise_id):  # type: ignore[arg-type]
            return self.get_token(user)
        return None

    def get_permissions_by_user(self, user: Any, enterprise_id: str) -> list:
        if not isinstance(user, Users):
            raise ErrorUser("user is not rainbond user")
        # TODO:impl rbac
        # TODO: get perm list by user_services.get_user_in_enterprise_perm
        if user_services.is_user_admin_in_current_enterprise(user, enterprise_id):
            return ["all"]
        return ["common"]


apiUserService = APIUserService()
