# -*- coding: utf-8 -*-
import datetime
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rainskills_device_test_settings")

import django  # noqa: E402
from django.test import TestCase, override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

django.setup()

from console.models.main import MCPDeviceAuthorization, MCPDeviceAuthorizationRateLimit  # noqa: E402
from console.services import mcp_device_authorization as device_auth  # noqa: E402


class MCPDeviceAuthorizationServiceTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.user = SimpleNamespace(user_id=17, enterprise_id="enterprise-17", is_active=True)

    def create_grant(self, **kwargs):
        values = {
            "client_id": "rainskills",
            "client_name": "Rainskills",
            "scope": "mcp",
            "source": "192.0.2.10",
            "now": self.now,
        }
        values.update(kwargs)
        return device_auth.create_device_authorization(**values)

    @patch("console.services.mcp_device_authorization.secrets.choice")
    def test_user_code_has_eight_independent_characters(self, choose):
        choose.side_effect = list("23456789")

        code = device_auth.generate_user_code()

        self.assertEqual(code, "2345-6789")
        self.assertEqual(choose.call_count, 8)
        for call in choose.call_args_list:
            self.assertEqual(call.args[0], "23456789BCDFGHJKMNPQRTVWXY")

    def test_code_hashes_are_domain_separated_and_plaintext_is_not_a_model_field(self):
        device_hash = device_auth.hash_device_code("secret-code")
        user_hash = device_auth.hash_user_code("BCDF-GHJK")

        self.assertEqual(len(device_hash), 64)
        self.assertEqual(len(user_hash), 64)
        self.assertNotEqual(device_hash, user_hash)
        field_names = {field.name for field in MCPDeviceAuthorization._meta.fields}
        self.assertNotIn("device_code", field_names)
        self.assertNotIn("user_code", field_names)

    @patch("console.services.mcp_device_authorization.secrets.token_urlsafe", return_value="device-secret")
    @patch("console.services.mcp_device_authorization.generate_user_code", return_value="BCDF-GHJK")
    def test_create_persists_only_hashes_and_expires_in_ten_minutes(self, _user_code, _device_code):
        result = self.create_grant()
        record = MCPDeviceAuthorization.objects.get(pk=result.record_id)

        self.assertEqual(result.device_code, "device-secret")
        self.assertEqual(result.user_code, "BCDF-GHJK")
        self.assertNotEqual(record.device_code_hash, result.device_code)
        self.assertNotEqual(record.user_code_hash, result.user_code)
        self.assertEqual(record.expires_at, self.now + datetime.timedelta(minutes=10))
        self.assertEqual(record.status, MCPDeviceAuthorization.STATUS_PENDING)

    def test_approve_then_exchange_is_atomic_and_one_time(self):
        result = self.create_grant()

        inspected = device_auth.inspect_user_code(
            result.user_code, self.user, "192.0.2.11", now=self.now + datetime.timedelta(seconds=1))
        self.assertEqual(inspected.client_name, "Rainskills")
        self.assertEqual(inspected.scope, "mcp")

        decided = device_auth.decide_user_code(
            result.user_code, self.user, "approve", "192.0.2.11", now=self.now + datetime.timedelta(seconds=2))
        self.assertEqual(decided.status, MCPDeviceAuthorization.STATUS_APPROVED)

        exchanged = device_auth.poll_device_token(
            result.device_code, "rainskills", "192.0.2.10", now=self.now + datetime.timedelta(seconds=6))
        self.assertEqual(exchanged.status, device_auth.POLL_APPROVED)
        self.assertEqual(exchanged.user_id, 17)
        self.assertEqual(exchanged.enterprise_id, "enterprise-17")

        consumed = device_auth.poll_device_token(
            result.device_code, "rainskills", "192.0.2.10", now=self.now + datetime.timedelta(seconds=12))
        self.assertEqual(consumed.status, device_auth.POLL_CONSUMED)

    def test_deny_returns_access_denied(self):
        result = self.create_grant()
        device_auth.decide_user_code(
            result.user_code, self.user, "deny", "192.0.2.12", now=self.now + datetime.timedelta(seconds=1))

        polled = device_auth.poll_device_token(
            result.device_code, "rainskills", "192.0.2.10", now=self.now + datetime.timedelta(seconds=6))

        self.assertEqual(polled.status, device_auth.POLL_DENIED)

    def test_expired_code_cannot_be_inspected_or_exchanged(self):
        result = self.create_grant()
        after_expiry = self.now + datetime.timedelta(minutes=11)

        with self.assertRaises(device_auth.DeviceAuthorizationError) as inspect_error:
            device_auth.inspect_user_code(result.user_code, self.user, "192.0.2.11", now=after_expiry)
        self.assertEqual(inspect_error.exception.error, device_auth.POLL_EXPIRED)

        polled = device_auth.poll_device_token(
            result.device_code, "rainskills", "192.0.2.10", now=after_expiry)
        self.assertEqual(polled.status, device_auth.POLL_EXPIRED)

    def test_polling_before_interval_returns_slow_down(self):
        result = self.create_grant()

        early = device_auth.poll_device_token(
            result.device_code, "rainskills", "192.0.2.10", now=self.now + datetime.timedelta(seconds=1))
        pending = device_auth.poll_device_token(
            result.device_code, "rainskills", "192.0.2.10", now=self.now + datetime.timedelta(seconds=11))

        self.assertEqual(early.status, device_auth.POLL_SLOW_DOWN)
        self.assertEqual(early.interval, 10)
        self.assertEqual(pending.status, device_auth.POLL_PENDING)

    @override_settings(RAINBOND_MCP_DEVICE_RATE_LIMIT_CREATE=2)
    def test_creation_rate_limit_is_database_backed_and_hides_raw_source(self):
        self.create_grant(source="198.51.100.22")
        self.create_grant(source="198.51.100.22")

        with self.assertRaises(device_auth.DeviceAuthorizationRateLimited):
            self.create_grant(source="198.51.100.22")

        buckets = list(MCPDeviceAuthorizationRateLimit.objects.values_list("bucket_hash", flat=True))
        self.assertTrue(buckets)
        self.assertFalse(any("198.51.100.22" in bucket for bucket in buckets))

    @override_settings(
        RAINBOND_MCP_DEVICE_RATE_LIMIT_INSPECT=5,
        RAINBOND_MCP_DEVICE_RATE_LIMIT_INSPECT_WINDOW_SECONDS=600,
    )
    def test_browser_code_attempts_are_limited_to_five_per_ten_minutes(self):
        for _attempt in range(5):
            with self.assertRaises(device_auth.DeviceAuthorizationError):
                device_auth.inspect_user_code(
                    "BCDF-GHJK", self.user, "198.51.100.23", now=self.now)

        with self.assertRaises(device_auth.DeviceAuthorizationRateLimited):
            device_auth.inspect_user_code(
                "BCDF-GHJK", self.user, "198.51.100.23", now=self.now)

        bucket = MCPDeviceAuthorizationRateLimit.objects.get()
        self.assertEqual(
            bucket.expires_at - bucket.window_started_at,
            datetime.timedelta(minutes=10),
        )

    @override_settings(RAINBOND_MCP_DEVICE_GRANT_FAILURE_LIMIT=5)
    def test_terminal_grant_has_an_independent_failure_budget(self):
        result = self.create_grant()
        device_auth.decide_user_code(
            result.user_code, self.user, "deny", "192.0.2.12", now=self.now + datetime.timedelta(seconds=1))

        for attempt in range(5):
            other_user = SimpleNamespace(
                user_id=100 + attempt,
                enterprise_id="enterprise-17",
                is_active=True,
            )
            with self.assertRaises(device_auth.DeviceAuthorizationError):
                device_auth.inspect_user_code(
                    result.user_code,
                    other_user,
                    "198.51.100.{}".format(attempt + 30),
                    now=self.now + datetime.timedelta(seconds=attempt + 2),
                )

        record = MCPDeviceAuthorization.objects.get(pk=result.record_id)
        self.assertEqual(record.failed_inspection_attempts, 5)
        with self.assertRaises(device_auth.DeviceAuthorizationRateLimited):
            device_auth.inspect_user_code(
                result.user_code,
                SimpleNamespace(user_id=999, enterprise_id="enterprise-17", is_active=True),
                "198.51.100.99",
                now=self.now + datetime.timedelta(seconds=8),
            )

    @override_settings(RAINBOND_MCP_DEVICE_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",))
    def test_forwarded_source_is_used_only_for_trusted_proxy(self):
        trusted = SimpleNamespace(META={
            "REMOTE_ADDR": "10.1.2.3",
            "HTTP_X_FORWARDED_FOR": "203.0.113.5, 10.1.2.3",
        })
        untrusted = SimpleNamespace(META={
            "REMOTE_ADDR": "192.0.2.9",
            "HTTP_X_FORWARDED_FOR": "203.0.113.5",
        })

        self.assertEqual(device_auth.get_request_source(trusted), "203.0.113.5")
        self.assertEqual(device_auth.get_request_source(untrusted), "192.0.2.9")
