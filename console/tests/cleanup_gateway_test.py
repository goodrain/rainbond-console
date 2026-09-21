import base64
import hashlib
import hmac
import json
from types import SimpleNamespace
from unittest import TestCase

from console.services.cleanup_gateway import CleanupAccessDenied, CleanupGatewayUnavailable, prepare_cleanup_request


class CleanupGatewayTests(TestCase):
    def request(self):
        return SimpleNamespace(method="POST", body=b'{"scanId":"scan-1"}',
                               user=SimpleNamespace(user_id=7, enterprise_id="enterprise-1"),
                               META={"HTTP_X_CLEANUP_CONTEXT": "untrusted", "HTTP_X_CLEANUP_GATEWAY_KEY": "untrusted",
                                     "HTTP_IDEMPOTENCY_KEY": "request-1", "QUERY_STRING": ""})

    def test_signs_identity_scope_and_exact_body(self):
        req = self.request()
        key = bytes(range(32))
        prepare_cleanup_request(req, "region-1", "api/v1/clusters/region-1/scans", True, True, key, now=1000)
        encoded = req.META["HTTP_X_CLEANUP_CONTEXT"]
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        self.assertEqual(payload["actor"], "7")
        self.assertEqual(payload["region"], "region-1")
        self.assertEqual(payload["bodyHash"], hashlib.sha256(req.body).hexdigest())
        self.assertEqual(req.META["HTTP_X_CLEANUP_SIGNATURE"], hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest())
        self.assertNotIn("HTTP_X_CLEANUP_GATEWAY_KEY", req.META)

    def test_rejects_non_admin_cross_enterprise_and_short_key(self):
        for admin, scope in [(False, True), (True, False)]:
            with self.assertRaises(CleanupAccessDenied):
                prepare_cleanup_request(self.request(), "r", "api/v1/clusters", admin, scope, bytes(32))
        with self.assertRaises(CleanupGatewayUnavailable):
            prepare_cleanup_request(self.request(), "r", "api/v1/clusters", True, True, b"")

    def test_rejects_traversal_and_oversized_body(self):
        for path in ["../api/v1/clusters", "api/v1/../x", "api//v1/x"]:
            with self.assertRaises(CleanupAccessDenied):
                prepare_cleanup_request(self.request(), "r", path, True, True, bytes(32))
        req = self.request()
        req.body = b"x" * ((1 << 20) + 1)
        with self.assertRaises(CleanupAccessDenied):
            prepare_cleanup_request(req, "r", "api/v1/clusters", True, True, bytes(32))


class CleanupProxyIntegrationTests(TestCase):
    """Exercise the actual initial() method without loading unrelated Django apps."""

    def view_class(self, region_allowed):
        import ast
        import os
        from pathlib import Path
        from typing import Any
        from unittest import mock
        from console.services.cleanup_gateway import prepare_cleanup_request

        source = Path(__file__).resolve().parents[1] / "views" / "rbd_plugin.py"
        tree = ast.parse(source.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RainbondPluginBackendView")
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "initial"]
        module = ast.Module(body=[cls], type_ignores=[])

        class Base:
            def initial(self, request, *args, **kwargs):
                self.user = request.user
                self.is_enterprise_admin = request.is_admin

        class Unavailable(Exception):
            def __init__(self, *args, **kwargs):
                self.status_code = kwargs.get("status_code")

        env = {"JWTAuthApiView": Base, "Request": object, "Any": Any, "PermissionDenied": CleanupAccessDenied,
               "ServiceHandleException": Unavailable, "os": os, "CleanupAccessDenied": CleanupAccessDenied,
               "CleanupGatewayUnavailable": CleanupGatewayUnavailable, "prepare_cleanup_request": prepare_cleanup_request,
               "resolve_gateway_key": mock.Mock(side_effect=CleanupGatewayUnavailable),
               "region_repo": SimpleNamespace(get_enterprise_region_by_region_name=mock.Mock(return_value=region_allowed))}
        exec(compile(ast.fix_missing_locations(module), str(source), "exec"), env)
        return env["RainbondPluginBackendView"], Unavailable

    def test_other_plugins_do_not_require_cleanup_configuration(self):
        cls, _ = self.view_class(False)
        req = CleanupGatewayTests().request()
        req.is_admin = False
        cls().initial(req, plugin_name="unrelated", region_name="r1", file_path="api/v1/test")
        self.assertEqual(req.META["HTTP_X_CLEANUP_CONTEXT"], "untrusted")

    def test_admin_and_scope_checked_before_signing(self):
        for admin, scope in [(False, True), (True, False)]:
            cls, _ = self.view_class(scope)
            req = CleanupGatewayTests().request()
            req.is_admin = admin
            with self.assertRaises(CleanupAccessDenied):
                cls().initial(req, plugin_name="rainbond-disk", region_name="r1", file_path="api/v1/clusters")

    def test_missing_key_fails_closed(self):
        import os
        from unittest import mock
        cls, unavailable = self.view_class(True)
        req = CleanupGatewayTests().request()
        req.is_admin = True
        with mock.patch.dict(os.environ, {"CLEANUP_GATEWAY_KEY_FILE": ""}):
            with self.assertRaises(unavailable) as caught:
                cls().initial(req, plugin_name="rainbond-disk", region_name="r1", file_path="api/v1/clusters")
        self.assertEqual(caught.exception.status_code, 503)

    def test_automatic_key_signs_without_console_environment(self):
        from unittest import mock
        cls, _ = self.view_class(True)
        resolver = mock.Mock(return_value=b"x" * 64)
        cls.initial.__globals__["resolve_gateway_key"] = resolver
        req = CleanupGatewayTests().request()
        req.is_admin = True
        cls().initial(req, plugin_name="rainbond-disk", region_name="r1", file_path="api/v1/clusters")
        resolver.assert_called_once_with("enterprise-1", "r1")
        self.assertIn("HTTP_X_CLEANUP_SIGNATURE", req.META)
