# -*- coding: utf-8 -*-
"""Provision ordinary users from explicitly trusted platform GitLab services."""
import re
from typing import Any

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from console.exception.main import ServiceHandleException
from console.models.main import OAuthServices, UserOAuthServices
from www.models.main import TenantEnterprise, Users
from console.services.user_identity import check_login_identifiers_available, gitlab_username


@transaction.atomic
def provision_gitlab_user(service_id: int, identity: Any, access_token: str, refresh_token: str, code: str) -> Users:
    # Share the service-row lock used by Git OAuth reauthorization. It also serializes first logins.
    service = OAuthServices.objects.select_for_update().filter(
        pk=service_id, oauth_type="gitlab", system=True, is_console=True,
        auto_create_user=True, enable=True, is_deleted=False).first()
    if not service or not service.eid:
        raise ServiceHandleException("GitLab provisioning disabled", "该 GitLab 服务未开启自动创建账号", status_code=403)
    if not TenantEnterprise.objects.filter(enterprise_id=service.eid).exists():
        raise ServiceHandleException("enterprise not found", "GitLab 服务所属企业不存在", status_code=403)

    external_id = str(identity.id)
    if not re.fullmatch(r"[1-9][0-9]{0,19}", external_id):
        raise ServiceHandleException("invalid GitLab identity", "GitLab 未返回有效用户身份")
    bindings = list(UserOAuthServices.objects.filter(service_id=service.pk, oauth_user_id=external_id))
    if len(bindings) > 1:
        raise ServiceHandleException("ambiguous OAuth binding", "账号存在重复绑定，请联系管理员处理", status_code=409)
    binding = bindings[0] if bindings else UserOAuthServices(service_id=service.pk, oauth_user_id=external_id)

    if binding.user_id is not None:
        user = Users.objects.select_for_update().filter(pk=binding.user_id, enterprise_id=service.eid).first()
        if not user or not user.is_active:
            raise ServiceHandleException("OAuth user unavailable", "关联的 Rainbond 账号不可用，请联系管理员", status_code=403)
    else:
        # Do not bootstrap an enterprise or trigger the legacy first-user administrator fallback.
        if not Users.objects.filter(enterprise_id=service.eid).exists():
            raise ServiceHandleException("enterprise not initialized", "请先完成平台管理员初始化", status_code=403)
        email = identity.email or ""
        try:
            validate_email(email)
        except ValidationError:
            raise ServiceHandleException("invalid GitLab email", "GitLab 未返回有效邮箱，请补充邮箱后重试")
        max_email_length = Users._meta.get_field("email").max_length
        if max_email_length is not None and len(email) > max_email_length:
            raise ServiceHandleException("invalid GitLab email", "GitLab 返回的邮箱过长，请联系管理员")
        # An email address alone is not proof of ownership of an existing Rainbond account.
        username = gitlab_username(service.pk, external_id)
        if Users.objects.filter(email__iexact=email).exists() or Users.objects.filter(nick_name=username).exists():
            raise ServiceHandleException(
                "existing account requires binding", "账号信息与已有账号冲突，请先登录已有 Rainbond 账号并绑定 GitLab", status_code=409)
        check_login_identifiers_available(nick_name=username, email=email)
        user = Users.objects.create(
            nick_name=username, real_name=(identity.name or "")[:64], email=email,
            enterprise_id=service.eid, is_active=True, sys_admin=False, password=make_password(None))

    binding.user_id = user.pk
    binding.oauth_user_name = (identity.name or "")[:64]
    binding.oauth_user_email = (identity.email or "")[:64]
    binding.access_token = access_token
    binding.refresh_token = refresh_token
    binding.code = code
    binding.is_authenticated = True
    binding.is_expired = False
    binding.save()
    return user
