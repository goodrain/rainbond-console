# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".venv", "src", "openapi-client")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402
from django.test import SimpleTestCase, override_settings  # noqa: E402

django.setup()

from console.exception.exceptions import AuthenticationInfoHasExpiredError  # noqa: E402
from console.login.jwt_authentication import JSONWebTokenAuthentication  # noqa: E402
from console.utils import jwt_issuer  # noqa: E402


class MCPTokenScopeTests(SimpleTestCase):

    def setUp(self):
        self.user = SimpleNamespace(
            user_id=42,
            nick_name="device-user",
            email="device@example.com",
            enterprise_id="enterprise-42",
        )

    @override_settings(RAINBOND_MCP_TOKEN_LIFETIME_DAYS=365)
    def test_issue_mcp_jwt_has_scoped_claims_and_one_year_lifetime(self):
        raw_token = jwt_issuer.issue_mcp_jwt(self.user)
        payload = jwt_issuer.decode_jwt(raw_token)

        self.assertEqual(payload["token_use"], "mcp")
        self.assertEqual(payload["scope"], "mcp")
        self.assertEqual(payload["aud"], "rainbond-mcp")
        self.assertEqual(payload["enterprise_id"], "enterprise-42")
        self.assertEqual(payload["exp"] - payload["iat"], 365 * 24 * 60 * 60)

    def test_general_console_authentication_rejects_mcp_token_payload(self):
        payload = jwt_issuer.decode_jwt(jwt_issuer.issue_mcp_jwt(self.user))

        with self.assertRaises(AuthenticationInfoHasExpiredError):
            JSONWebTokenAuthentication().validate_token_payload(payload)

    def test_mcp_payload_validator_accepts_scoped_and_legacy_tokens(self):
        scoped = jwt_issuer.decode_jwt(jwt_issuer.issue_mcp_jwt(self.user))
        legacy = jwt_issuer.decode_jwt(jwt_issuer.issue_jwt(self.user))

        self.assertTrue(jwt_issuer.is_valid_mcp_token_payload(scoped))
        self.assertTrue(jwt_issuer.is_valid_mcp_token_payload(legacy, allow_legacy=True))

    def test_mcp_payload_validator_rejects_partial_or_wrong_scope(self):
        self.assertFalse(jwt_issuer.is_valid_mcp_token_payload({
            "token_use": "mcp",
            "scope": "mcp",
        }))
        self.assertFalse(jwt_issuer.is_valid_mcp_token_payload({
            "token_use": "mcp",
            "scope": "console",
            "aud": "rainbond-mcp",
        }))
        self.assertFalse(jwt_issuer.is_valid_mcp_token_payload({
            "token_use": "console",
            "scope": "mcp",
            "aud": "rainbond-mcp",
        }))

    @override_settings(RAINBOND_MCP_TOKEN_LIFETIME_DAYS=0)
    def test_mcp_token_lifetime_rejects_non_positive_configuration(self):
        with self.assertRaises(ValueError):
            jwt_issuer.get_mcp_token_lifetime()
