# -*- coding: utf-8 -*-
"""Single entry point for issuing and decoding console JWT tokens.

All JWT operations in the codebase should go through this module so that the
underlying JWT library can be swapped without touching call sites.

Compatibility contract (relied on by external projects and e2e tests):
- HS256 signed with Django SECRET_KEY
- payload contains user_id / username / email / exp
- long-lived tokens (~10 years), no revocation on logout
"""
import datetime

import jwt as pyjwt
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken

# Keep in sync with the legacy drf-jwt JWT_AUTH settings.
JWT_AUTH_COOKIE = "token"
JWT_AUTH_HEADER_PREFIX = "GRJWT"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = datetime.timedelta(days=3650)  # ~10 years, effectively permanent


class ConsoleAccessToken(AccessToken):
    """Access token carrying the legacy drf-jwt payload fields."""

    lifetime = JWT_EXPIRATION_DELTA

    @classmethod
    def for_user(cls, user):
        token = super(ConsoleAccessToken, cls).for_user(user)
        token["username"] = user.nick_name
        token["email"] = user.email or ""
        return token


def issue_jwt(user):
    """Issue a signed JWT string for the given user."""
    return str(ConsoleAccessToken.for_user(user))


def decode_jwt(raw_token):
    """Validate signature/expiration and return the payload dict.

    Accepts tokens issued by this module, by the legacy drf-jwt stack and by
    external portals (audience is not verified, matching legacy behavior).

    Raises pyjwt exceptions on failure:
    - jwt.ExpiredSignatureError
    - jwt.DecodeError
    - jwt.InvalidTokenError
    """
    if isinstance(raw_token, bytes):
        raw_token = raw_token.decode("utf-8")
    return pyjwt.decode(
        raw_token,
        settings.SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={"verify_aud": False},
    )


def jwt_response_payload(token, user=None, request=None):
    """Build the login response payload (same shape as legacy drf-jwt)."""
    return {"token": token}
