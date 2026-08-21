# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rainskills_device_test_settings")

import django  # noqa: E402
from django.conf import settings  # noqa: E402
from django.test import TestCase, override_settings  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.utils import jwt_issuer  # noqa: E402
from console.models.main import MCPDeviceAuthorization  # noqa: E402
from console.services import mcp_device_authorization as device_auth  # noqa: E402
from console.views.mcp_device_authorization import (  # noqa: E402
    MCPDeviceAuthorizeView,
    MCPDeviceCodeView,
    MCPDeviceInspectView,
    MCPDeviceTokenView,
)
from www.models.main import Users  # noqa: E402


@override_settings(
    RAINBOND_MCP_DEVICE_PUBLIC_ORIGIN="https://rainbond.example.com",
    RAINBOND_MCP_TOKEN_LIFETIME_DAYS=365,
)
class MCPDeviceAuthorizationViewTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = Users.objects.create(
            email="device@example.com",
            nick_name="device-user",
            password="unused",
            is_active=True,
            enterprise_id="enterprise-7",
        )
        self.console_token = jwt_issuer.issue_jwt(self.user)

    def post_form(self, view, body, **extra):
        request = self.factory.post(
            "/console/mcp/device/test",
            data=body,
            content_type="application/x-www-form-urlencoded",
            **extra
        )
        return view.as_view()(request)

    def create_code(self):
        response = self.post_form(MCPDeviceCodeView, "client_id=rainskills&scope=mcp&ignored=value")
        self.assertEqual(response.status_code, 200)
        return response.data

    def auth_headers(self, **extra):
        headers = {
            "HTTP_AUTHORIZATION": "GRJWT {}".format(self.console_token),
            "HTTP_ORIGIN": "https://rainbond.example.com",
        }
        headers.update(extra)
        return headers

    def test_feature_is_enabled_by_default(self):
        self.assertTrue(settings.RAINBOND_MCP_DEVICE_FLOW_ENABLED)

    def test_code_contract_and_cache_headers(self):
        response = self.post_form(MCPDeviceCodeView, "client_id=rainskills&scope=mcp&ignored=value")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user_code"].count("-"), 1)
        self.assertEqual(response.data["expires_in"], 600)
        self.assertEqual(response.data["interval"], 5)
        self.assertEqual(response.data["verification_uri"], "https://rainbond.example.com/#/device")
        self.assertIn("user_code=", response.data["verification_uri_complete"])
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response["Pragma"], "no-cache")

    @override_settings(RAINBOND_MCP_DEVICE_FLOW_ENABLED=False)
    def test_disabled_feature_returns_verified_legacy_not_found(self):
        response = self.post_form(MCPDeviceCodeView, "client_id=rainskills&scope=mcp")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b"Not Found")
        self.assertTrue(response["Content-Type"].startswith("text/plain"))

    def test_code_rejects_duplicate_required_parameter_and_json_body(self):
        duplicate = self.post_form(
            MCPDeviceCodeView, "client_id=rainskills&client_id=other&scope=mcp")
        json_request = self.factory.post(
            "/console/mcp/device/code",
            data={"client_id": "rainskills", "scope": "mcp"},
            format="json",
        )
        invalid_content_type = MCPDeviceCodeView.as_view()(json_request)

        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.data["error"], "invalid_request")
        self.assertEqual(invalid_content_type.status_code, 400)
        self.assertEqual(invalid_content_type.data["error"], "invalid_request")

    def test_pending_then_browser_approval_then_one_time_token_exchange(self):
        created = self.create_code()
        pending = self.post_form(
            MCPDeviceTokenView,
            "grant_type=urn:ietf:params:oauth:grant-type:device_code&client_id=rainskills&device_code={}".format(
                created["device_code"]),
        )
        self.assertEqual(pending.status_code, 400)
        self.assertIn(pending.data["error"], ("authorization_pending", "slow_down"))

        inspect_request = self.factory.post(
            "/console/mcp/device/inspect",
            data={"user_code": created["user_code"]},
            format="json",
            **self.auth_headers()
        )
        inspected = MCPDeviceInspectView.as_view()(inspect_request)
        self.assertEqual(inspected.status_code, 200)
        self.assertEqual(inspected.data["data"]["bean"]["client_name"], "Rainskills")
        self.assertEqual(inspected.data["data"]["bean"]["scope"], "mcp")

        authorize_request = self.factory.post(
            "/console/mcp/device/authorize",
            data={"user_code": created["user_code"], "decision": "approve"},
            format="json",
            **self.auth_headers()
        )
        authorized = MCPDeviceAuthorizeView.as_view()(authorize_request)
        self.assertEqual(authorized.status_code, 200)
        self.assertEqual(authorized.data["data"]["bean"]["status"], "approved")

        exchanged = self.post_form(
            MCPDeviceTokenView,
            "grant_type=urn:ietf:params:oauth:grant-type:device_code&client_id=rainskills&device_code={}".format(
                created["device_code"]),
        )
        self.assertEqual(exchanged.status_code, 200)
        self.assertEqual(exchanged.data["token_type"], "Bearer")
        self.assertEqual(exchanged.data["expires_in"], 365 * 24 * 60 * 60)
        payload = jwt_issuer.decode_jwt(exchanged.data["access_token"])
        self.assertEqual(payload["scope"], "mcp")
        self.assertEqual(payload["enterprise_id"], "enterprise-7")

        repeated = self.post_form(
            MCPDeviceTokenView,
            "grant_type=urn:ietf:params:oauth:grant-type:device_code&client_id=rainskills&device_code={}".format(
                created["device_code"]),
        )
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(repeated.data["error"], "invalid_grant")

    def test_browser_endpoints_reject_cookie_only_but_allow_any_origin_with_header_jwt(self):
        created = self.create_code()
        cookie_request = self.factory.post(
            "/console/mcp/device/inspect", data={"user_code": created["user_code"]}, format="json")
        cookie_request.COOKIES["token"] = self.console_token
        cookie_response = MCPDeviceInspectView.as_view()(cookie_request)

        origin_request = self.factory.post(
            "/console/mcp/device/inspect",
            data={"user_code": created["user_code"]},
            format="json",
            **self.auth_headers(HTTP_ORIGIN="https://attacker.example")
        )
        origin_response = MCPDeviceInspectView.as_view()(origin_request)

        self.assertEqual(cookie_response.status_code, 401)
        self.assertEqual(origin_response.status_code, 200)

    def test_deactivated_approver_is_denied_before_token_issuance(self):
        created = self.create_code()
        authorize_request = self.factory.post(
            "/console/mcp/device/authorize",
            data={"user_code": created["user_code"], "decision": "approve"},
            format="json",
            **self.auth_headers()
        )
        self.assertEqual(MCPDeviceAuthorizeView.as_view()(authorize_request).status_code, 200)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        exchanged = self.post_form(
            MCPDeviceTokenView,
            "grant_type=urn:ietf:params:oauth:grant-type:device_code&client_id=rainskills&device_code={}".format(
                created["device_code"]),
        )

        self.assertEqual(exchanged.status_code, 400)
        self.assertEqual(exchanged.data["error"], "access_denied")
        record = MCPDeviceAuthorization.objects.get(device_code_hash=device_auth.hash_device_code(created["device_code"]))
        self.assertEqual(record.status, MCPDeviceAuthorization.STATUS_DENIED)

    def test_configured_public_origin_ignores_host_and_forwarded_host(self):
        response = self.post_form(
            MCPDeviceCodeView,
            "client_id=rainskills&scope=mcp",
            HTTP_HOST="attacker.example",
            HTTP_X_FORWARDED_HOST="forwarded-attacker.example",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["verification_uri"].startswith("https://rainbond.example.com/"))

    def test_route_file_registers_all_device_endpoints_before_generic_query(self):
        route_path = os.path.join(os.path.dirname(__file__), "..", "urls", "__init__.py")
        with open(route_path, "r", encoding="utf-8") as route_file:
            routes = route_file.read()

        code_index = routes.index("mcp/device/code")
        self.assertLess(code_index, routes.index("mcp/query"))
        self.assertIn("mcp/device/token", routes)
        self.assertIn("mcp/device/inspect", routes)
        self.assertIn("mcp/device/authorize", routes)
