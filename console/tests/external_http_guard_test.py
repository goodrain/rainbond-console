# -*- coding: utf-8 -*-
# capability_id: console.tests.external-http-guard
import http.client
import os
from types import SimpleNamespace

import conftest
import pytest
import requests

from django.test import SimpleTestCase
from console.utils.offline import is_external_telemetry_disabled
from goodrain_web.sentry_config import get_frontend_posthog_config, get_sentry_config
from scripts import run_pytest


class ExternalHttpGuardTests(SimpleTestCase):

    def _assert_blocked_request_fails_test(self, request):
        blocked_request_count = conftest.blocked_external_http_request_count()

        with self.assertRaisesRegex(RuntimeError, "external HTTP requests are disabled during tests"):
            request()

        with pytest.raises(pytest.fail.Exception):
            conftest.fail_for_blocked_external_http_requests_since(blocked_request_count)

    def test_disables_external_telemetry(self):
        sentry_env = dict(os.environ, SENTRY_DSN="https://sentry.example.invalid/1")

        self.assertTrue(is_external_telemetry_disabled())
        self.assertFalse(get_sentry_config(sentry_env)["enabled"])
        self.assertFalse(get_frontend_posthog_config()["enabled"])

    def test_blocks_external_requests_before_transport(self):
        self._assert_blocked_request_fails_test(lambda: requests.get("https://example.invalid"))

    def test_blocks_external_requests_through_local_http_proxy(self):
        self._assert_blocked_request_fails_test(
            lambda: requests.get(
                "http://example.invalid",
                proxies={"http": "http://127.0.0.1:8080"},
            )
        )

    def test_blocks_http_and_https_connections_before_dns(self):
        for connection_class in (http.client.HTTPConnection, http.client.HTTPSConnection):
            with self.subTest(connection_class=connection_class.__name__):
                self._assert_blocked_request_fails_test(lambda: connection_class("example.invalid").connect())

    def test_allows_loopback_hosts(self):
        blocked_request_count = conftest.blocked_external_http_request_count()

        for host in ("localhost", "127.0.0.1", "[::1]"):
            with self.subTest(host=host):
                conftest._assert_local_test_host(SimpleNamespace(host=host))

        self.assertEqual(blocked_request_count, conftest.blocked_external_http_request_count())

    def test_runner_disables_external_reporting_before_django_setup(self):
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.delenv("RAINBOND_TELEMETRY_DISABLED", raising=False)
            monkeypatch.delenv("RAINBOND_ERROR_REPORTING_DISABLED", raising=False)

            run_pytest.configure_test_environment()

            self.assertEqual(os.environ["RAINBOND_TELEMETRY_DISABLED"], "1")
            self.assertEqual(os.environ["RAINBOND_ERROR_REPORTING_DISABLED"], "1")
