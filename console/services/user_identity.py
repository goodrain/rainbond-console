# -*- coding: utf-8 -*-
"""Creation-only username rules and unambiguous login identity lookup."""
import hashlib
import re
from typing import Any, Optional

from django.db.models import Q

from console.exception.main import ServiceHandleException
from www.models.main import Users


USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 24


def validate_new_username(value: Any) -> None:
    if not isinstance(value, str) or not USERNAME_MIN_LENGTH <= len(value) <= USERNAME_MAX_LENGTH:
        raise ServiceHandleException("invalid username", "用户名必须为3-24位字符串")
    if not re.fullmatch(r"[a-zA-Z0-9_\-\u4e00-\u9fa5]+", value):
        raise ServiceHandleException("invalid username", "用户名只支持中英文、数字、下划线和中划线")


def check_login_identifiers_available(nick_name: Any = None, email: Any = None, phone: Any = None,
                                      user_id: Any = None) -> None:
    query = Q()
    for value in (nick_name, email, phone):
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise ServiceHandleException("invalid login identifier", "账号、邮箱和手机号必须为字符串")
        query |= Q(nick_name=value) | Q(email=value) | Q(phone=value)
    if not query:
        return
    users = Users.objects.filter(query)
    if user_id is not None:
        users = users.exclude(pk=user_id)
    if users.exists():
        raise ServiceHandleException("login identifier already exists", "账号、邮箱或手机号已被其他用户使用", status_code=409)


def resolve_login_user(identifier: Any) -> Optional[Users]:
    if not isinstance(identifier, str) or not identifier.strip():
        return None
    identifier = identifier.strip()
    users = list(Users.objects.filter(Q(nick_name=identifier) | Q(email=identifier) | Q(phone=identifier))[:2])
    return users[0] if len(users) == 1 else None


def gitlab_username(service_id: int, external_id: str) -> str:
    name = "gitlab-{}-{}".format(service_id, external_id)
    if len(name) <= USERNAME_MAX_LENGTH:
        return name
    # Identity reuse still relies on the full service/external IDs in the OAuth binding.
    digest = hashlib.sha256("{}:{}".format(service_id, external_id).encode("utf-8")).hexdigest()[:16]
    return "gitlab-" + digest
