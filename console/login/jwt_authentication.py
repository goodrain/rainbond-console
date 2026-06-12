# -*- coding: utf8 -*-
"""JWT authentication classes.

Kept in a standalone module (no rest_framework.views import) so it can be
referenced from REST_FRAMEWORK DEFAULT_AUTHENTICATION_CLASSES without
creating a circular import through console.views.base.
"""
import logging

import jwt
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from console.exception.exceptions import AuthenticationInfoHasExpiredError
from console.login.jwt_manager import JwtManager
from console.login.login_event import LoginEvent
from console.repositories.login_event import login_event_repo
from console.utils import jwt_issuer
from www.models.main import Users

logger = logging.getLogger("default")


class JSONWebTokenAuthentication(BaseAuthentication):
    """
    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string specified in the setting
    `JWT_AUTH_HEADER_PREFIX`. For example:

        Authorization: JWT eyJhbGciOiAiSFMyNTYiLCAidHlwIj
    """
    www_authenticate_realm = 'api'

    def get_jwt_value(self, request):
        auth = get_authorization_header(request).split()
        auth_header_prefix = jwt_issuer.JWT_AUTH_HEADER_PREFIX.lower()
        # Also accept standard 'jwt' prefix for external tokens (e.g., from Rainbill portal)
        valid_prefixes = [auth_header_prefix, 'jwt']
        request_path = getattr(request, 'path', '') or getattr(request, 'path_info', '')
        is_resource_center_log_request = '/resource-center/pods/' in request_path and request_path.endswith('/logs')

        if is_resource_center_log_request:
            logger.info(
                "resource center log auth request path=%s auth_header_present=%s token_cookie_present=%s team_cookie_present=%s",
                request.get_full_path(),
                bool(auth),
                bool(request.COOKIES.get(jwt_issuer.JWT_AUTH_COOKIE)),
                bool(request.COOKIES.get('team') or request.COOKIES.get('team_name')),
            )

        if not auth:
            if jwt_issuer.JWT_AUTH_COOKIE:
                return request.COOKIES.get(jwt_issuer.JWT_AUTH_COOKIE)
            return None

        if smart_text(auth[0].lower()) not in valid_prefixes:
            return None

        if len(auth) == 1:
            msg = _('请求头不合法，未提供认证信息')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("请求头不合法")
            raise exceptions.AuthenticationFailed(msg)
        return auth[1]

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            msg = _('未提供验证信息')
            raise AuthenticationInfoHasExpiredError(msg)

        try:
            # jwt_issuer.decode_jwt verifies signature/expiration and skips audience
            # verification (compatible with external portal tokens and legacy tokens)
            payload = jwt_issuer.decode_jwt(jwt_value)
        except jwt.ExpiredSignatureError:
            msg = _('认证信息已过期')
            raise AuthenticationInfoHasExpiredError(msg)
        except jwt.DecodeError:
            msg = _('认证信息错误')
            raise AuthenticationInfoHasExpiredError(msg)
        except jwt.InvalidTokenError:
            msg = _('认证信息错误,请求Token不合法')
            raise AuthenticationInfoHasExpiredError(msg)

        user = self.authenticate_credentials(payload)
        
        # Store token in jwt_manager for session tracking
        jwt_manager = JwtManager()
        jwt_manager.set(jwt_value, user.user_id)
        
        login_event = LoginEvent(user, login_event_repo)
        login_event.active()
        return user, jwt_value

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        username = payload.get('username')

        user_id = payload.get('user_id')
        if not username and not user_id:
            msg = _('认证信息不合法.')
            # raise exceptions.AuthenticationFailed(msg)
            logger.debug('==========================>{}'.format(msg))
            raise AuthenticationInfoHasExpiredError(msg)

        if user_id:
            try:
                user = Users.objects.filter(user_id=int(user_id)).first()
            except (TypeError, ValueError):
                user = None
            if user:
                if username and user.nick_name != username:
                    msg = _('认证信息不合法.')
                    logger.warning("jwt payload user mismatch: user_id=%s username=%s db_username=%s", user_id, username,
                                   user.nick_name)
                    raise AuthenticationInfoHasExpiredError(msg)
                if not user.is_active:
                    msg = _('用户身份未激活.')
                    raise AuthenticationInfoHasExpiredError(msg)
                return user

        try:
            user = Users.objects.get(nick_name=username)
        except Users.DoesNotExist:
            msg = _('签名不合法.')
            raise AuthenticationInfoHasExpiredError(msg)

        if not user.is_active:
            msg = _('用户身份未激活.')
            raise AuthenticationInfoHasExpiredError(msg)

        return user


class JWTAuthenticationSafe(JSONWebTokenAuthentication):
    """
    Use authentication_classes=[] in the view, but this always bypasses JWT authentication,
    even when there is a valid Authorization-header with a token.
    This class can obtain relevant user information when it has a token,
    and is used for apis that do not require authentication
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request=request)
        except AuthenticationInfoHasExpiredError:
            return None
