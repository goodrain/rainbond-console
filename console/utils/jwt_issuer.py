# -*- coding: utf-8 -*-
"""Single entry point for issuing and decoding console JWT tokens.

All JWT operations in the codebase should go through this module so that the
underlying JWT library can be swapped without touching call sites.

Compatibility contract (relied on by external projects and e2e tests):
- HS256 signed with Django SECRET_KEY
- payload contains user_id / username / email / exp
- general Console tokens remain long-lived (~10 years), with no logout revocation
- MCP tokens are separately scoped and default to a one-year lifetime
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
MCP_TOKEN_DEFAULT_LIFETIME_DAYS = 365
MCP_TOKEN_USE = "mcp"
MCP_TOKEN_SCOPE = "mcp"
MCP_TOKEN_AUDIENCE = "rainbond-mcp"


def get_mcp_token_lifetime():
    lifetime_days = int(getattr(
        settings,
        "RAINBOND_MCP_TOKEN_LIFETIME_DAYS",
        MCP_TOKEN_DEFAULT_LIFETIME_DAYS,
    ))
    if lifetime_days < 1:
        raise ValueError("RAINBOND_MCP_TOKEN_LIFETIME_DAYS must be at least 1")
    return datetime.timedelta(days=lifetime_days)


class ConsoleAccessToken(AccessToken):
    """Access token carrying the legacy drf-jwt payload fields."""

    lifetime = JWT_EXPIRATION_DELTA

    @classmethod
    def for_user(cls, user):
        token = super(ConsoleAccessToken, cls).for_user(user)
        token["username"] = user.nick_name
        token["email"] = user.email or ""
        return token


class MCPAccessToken(ConsoleAccessToken):
    """One-year access token accepted only by Rainbond MCP endpoints."""

    lifetime = datetime.timedelta(days=MCP_TOKEN_DEFAULT_LIFETIME_DAYS)

    @classmethod
    def for_user(cls, user):
        token = super(MCPAccessToken, cls).for_user(user)
        token.set_exp(lifetime=get_mcp_token_lifetime())
        token["token_use"] = MCP_TOKEN_USE
        token["scope"] = MCP_TOKEN_SCOPE
        token["aud"] = MCP_TOKEN_AUDIENCE
        token["enterprise_id"] = user.enterprise_id or ""
        return token


def issue_jwt(user):
    """Issue a signed JWT string for the given user."""
    return str(ConsoleAccessToken.for_user(user))


def issue_mcp_jwt(user):
    """Issue a signed token whose use is restricted to Rainbond MCP."""
    return str(MCPAccessToken.for_user(user))


def is_mcp_token_payload(payload):
    """Return whether any claim marks this payload as an MCP token."""
    return (
        payload.get("token_use") == MCP_TOKEN_USE
        or payload.get("scope") == MCP_TOKEN_SCOPE
        or payload.get("aud") == MCP_TOKEN_AUDIENCE
    )


def is_valid_mcp_token_payload(payload, allow_legacy=False):
    """Validate an MCP-scoped payload, optionally accepting old unscoped JWTs."""
    has_scope_claim = (
        "token_use" in payload
        or "scope" in payload
        or payload.get("aud") == MCP_TOKEN_AUDIENCE
    )
    if allow_legacy and not has_scope_claim:
        return True
    return (
        payload.get("token_use") == MCP_TOKEN_USE
        and payload.get("scope") == MCP_TOKEN_SCOPE
        and payload.get("aud") == MCP_TOKEN_AUDIENCE
    )


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
