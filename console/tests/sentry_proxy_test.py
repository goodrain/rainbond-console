# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import RequestFactory, SimpleTestCase  # noqa: E402

django.setup()

from console.views.sentry_proxy import SentryProxyView, _build_target_url  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class SentryProxyViewTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.view = SentryProxyView.as_view()

    def test_default_proxy_target_uses_goodrain_sentry_host(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            target_url = _build_target_url("api/2/envelope/", "sentry_version=7")

        self.assertEqual(target_url, "https://sentry.goodrain.com/api/2/envelope/?sentry_version=7")

    def test_proxy_target_can_include_base_path(self):
        with mock.patch.dict(os.environ, {"RAINBOND_SENTRY_PROXY_TARGET": "https://sentry.example.com/base"}, clear=True):
            target_url = _build_target_url("prefix/api/2/envelope/", "sentry_key=public")

        self.assertEqual(target_url, "https://sentry.example.com/base/prefix/api/2/envelope/?sentry_key=public")

    def test_proxy_target_can_reuse_absolute_frontend_tunnel(self):
        with mock.patch.dict(os.environ, {"RAINBOND_ERROR_REPORTING_FRONTEND_TUNNEL": "https://sentry.example.com"}, clear=True):
            target_url = _build_target_url("api/2/envelope/", "sentry_key=public")

        self.assertEqual(target_url, "https://sentry.example.com/api/2/envelope/?sentry_key=public")

    def test_proxy_target_falls_back_to_dsn_origin_when_tunnel_is_same_origin(self):
        with mock.patch.dict(os.environ, {
            "RAINBOND_ERROR_REPORTING_FRONTEND_TUNNEL": "/console/sentry",
            "RAINBOND_ERROR_REPORTING_DSN": "https://public@sentry.example.com/2",
        }, clear=True):
            target_url = _build_target_url("api/2/envelope/", "sentry_key=public")

        self.assertEqual(target_url, "https://sentry.example.com/api/2/envelope/?sentry_key=public")

    def test_proxy_target_derives_base_path_from_dsn(self):
        with mock.patch.dict(os.environ, {
            "RAINBOND_ERROR_REPORTING_DSN": "https://public@sentry.example.com/prefix/2",
        }, clear=True):
            target_url = _build_target_url("api/2/envelope/", "sentry_key=public")

        self.assertEqual(target_url, "https://sentry.example.com/prefix/api/2/envelope/?sentry_key=public")

    def test_rejects_non_envelope_paths(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                _build_target_url("api/2/store/", "")

    def test_post_proxies_envelope_without_rainbond_credentials(self):
        request = self.factory.post(
            "/console/sentry/api/2/envelope/?sentry_version=7&sentry_key=public",
            data=b'{"event_id":"abc"}\n{"type":"event"}\n{}',
            content_type="application/x-sentry-envelope",
            HTTP_AUTHORIZATION="JWT rainbond-token",
            HTTP_COOKIE="token=rainbond-cookie",
            HTTP_X_CSRFTOKEN="csrf-token",
            HTTP_USER_AGENT="RainbondUITest",
        )
        upstream_response = Obj(status_code=200, content=b"", headers={"Content-Type": "text/plain"})

        with mock.patch.dict(os.environ, {"RAINBOND_SENTRY_PROXY_TARGET": "https://sentry.goodrain.com"}), mock.patch(
            "console.views.sentry_proxy._send_upstream_request",
            return_value=upstream_response,
        ) as request_mock:
            response = self.view(request, path="api/2/envelope/")

        self.assertEqual(response.status_code, 200)
        request_mock.assert_called_once()
        _, kwargs = request_mock.call_args
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(
            kwargs["url"],
            "https://sentry.goodrain.com/api/2/envelope/?sentry_version=7&sentry_key=public",
        )
        self.assertEqual(kwargs["data"], b'{"event_id":"abc"}\n{"type":"event"}\n{}')
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/x-sentry-envelope")
        self.assertEqual(kwargs["headers"]["User-Agent"], "RainbondUITest")
        self.assertEqual(kwargs["headers"]["X-Forwarded-For"], "127.0.0.1")
        self.assertNotIn("Authorization", kwargs["headers"])
        self.assertNotIn("Cookie", kwargs["headers"])
        self.assertNotIn("X-Csrftoken", kwargs["headers"])

    def test_options_returns_cors_preflight_without_upstream_call(self):
        request = self.factory.options(
            "/console/sentry/api/2/envelope/",
            HTTP_ORIGIN="https://rainbond.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        with mock.patch("console.views.sentry_proxy._send_upstream_request") as request_mock:
            response = self.view(request, path="api/2/envelope/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://rainbond.example.com")
        self.assertIn("POST", response["Access-Control-Allow-Methods"])
        self.assertEqual(response["Access-Control-Allow-Headers"], "content-type")
        request_mock.assert_not_called()
