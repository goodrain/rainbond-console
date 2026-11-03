# -*- coding: utf8 -*-
from typing import Any, Optional

from django.core.exceptions import PermissionDenied
from www.models.main import Users
from console.services.user_identity import resolve_login_user


class ModelBackend(object):
    def authenticate(self, request: Any, username: Optional[str] = None, password: Optional[str] = None,
                     **kwargs: Any) -> Optional[Users]:
        if username is None or password is None:
            return None

        try:
            user_id = kwargs.get("user_id")
            user = (Users.objects.filter(pk=user_id, nick_name=username).first()
                    if user_id is not None else resolve_login_user(username))
            if user and user.check_password(password):
                return user
            if user_id is not None:
                # The login serializer already selected this identity; do not try another user store.
                raise PermissionDenied
        except Users.DoesNotExist:
            pass
        return None

    def get_user(self, user_id: int) -> Optional[Users]:
        try:
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None


class PartnerModelBackend(ModelBackend):
    def authenticate(self, request: Any, username: Optional[str] = None, source: Optional[str] = None,  # type: ignore[override]  # NOTE: intentionally replaces 'password' with 'source'; both are **kwargs in practice
                     **kwargs: Any) -> Optional[Users]:
        if username is None or source is None:
            return None

        try:
            if username.find("@") > 0:
                user = Users.objects.get(email=username)
            else:
                user = Users.objects.get(phone=username)
            if user.password == 'nopass':
                return user
        except Users.DoesNotExist:
            pass
        return None
