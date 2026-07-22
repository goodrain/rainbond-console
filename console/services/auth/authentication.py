# -*- coding: utf-8 -*-
import ipaddress
import logging
from typing import Any, Optional, Tuple

from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
from www.models.main import Users

logger = logging.getLogger('default')

# 任一代理头存在，即说明请求经过了 L7 网关/代理，视为集群外来源。
_PROXY_HEADERS = (
    'HTTP_X_FORWARDED_FOR',
    'HTTP_X_REAL_IP',
    'HTTP_X_FORWARDED_HOST',
    'HTTP_FORWARDED',
)


class InternalTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: Any) -> Optional[Tuple[Users, None]]:
        token = request.META.get('HTTP_X_INTERNAL_TOKEN')

        if not token:
            return None

        internal_token = getattr(settings, 'INTERNAL_API_TOKEN', None)

        if not internal_token or token != internal_token:
            return None

        # 如果 Token 匹配，返回一个超级管理员用户
        # 尝试获取系统的第一个超级管理员
        user = Users.objects.filter(sys_admin=True).first()

        if not user:
            # 如果没有超级管理员，抛出异常，因为我们需要一个用户上下文
            logger.error("InternalAuth: No superuser found!")
            raise exceptions.AuthenticationFailed('No superuser found for internal authentication')

        return (user, None)


class AgentRuntimeAuthentication(authentication.BaseAuthentication):
    """Legacy internal-token authentication without predictable ID fallback.

    New Agent runtime endpoints use purpose-bound JWT authentication. This
    class remains for compatibility with older callers, but only an explicitly
    configured INTERNAL_API_TOKEN is accepted; enterprise IDs are scope values,
    never credentials.
    """

    def authenticate(self, request: Any) -> Optional[Tuple[Users, None]]:
        token = request.META.get('HTTP_X_INTERNAL_TOKEN')

        if not token:
            return None

        # 关卡 1：仅允许集群内直连。
        if not self._is_cluster_internal(request):
            logger.warning("AgentRuntimeAuth: rejected non-cluster-internal request")
            raise exceptions.AuthenticationFailed(
                'agent runtime config endpoint is reachable from inside the cluster only')

        # 关卡 2：token 必须能标识本 console。
        if not self._token_allowed(token):
            return None

        user = Users.objects.filter(sys_admin=True).first()

        if not user:
            logger.error("AgentRuntimeAuth: No superuser found!")
            raise exceptions.AuthenticationFailed('No superuser found for internal authentication')

        return (user, None)

    @staticmethod
    def _is_cluster_internal(request: Any) -> bool:
        # 任一代理头存在 = 经过了网关 = 判定为外部。网关对这些头只追加不能删除，
        # 所以外部调用方无法靠去掉该头来伪装成内部。
        if any(request.META.get(h) for h in _PROXY_HEADERS):
            return False
        # 直连对端必须是私网/回环地址(集群 Pod 网络)。console 被 NodePort 等
        # 方式直接暴露到公网时，外部直连的对端是公网 IP，可据此挡掉。
        try:
            ip = ipaddress.ip_address(request.META.get('REMOTE_ADDR') or '')
        except ValueError:
            return False
        return ip.is_private or ip.is_loopback

    @staticmethod
    def _token_allowed(token: str) -> bool:
        legacy_token = getattr(settings, 'INTERNAL_API_TOKEN', None)
        return bool(legacy_token and token == legacy_token)
