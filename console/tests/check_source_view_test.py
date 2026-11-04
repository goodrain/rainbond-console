# -*- coding: utf-8 -*-
import os
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402
from django.test import RequestFactory, SimpleTestCase, override_settings  # noqa: E402

django.setup()

from console.views.user import CheckSourceView  # noqa: E402


# capability_id: console.login.source-url
@override_settings(MODULES={"SSO_LOGIN": False}, ALLOWED_HOSTS=["14.103.239.147", "console.example.test"])
class CheckSourceViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_response(self, **kwargs):
        request = self.factory.get("/console/checksource", **kwargs)
        response = CheckSourceView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        return response.data["data"]["bean"]

    def test_private_login_url_matches_request_origin_and_route_mode(self):
        cases = (
            ("hash", False, "14.103.239.147:7070", "http://14.103.239.147:7070/#/user/login"),
            ("hash", True, "console.example.test", "https://console.example.test/#/user/login"),
            ("history", False, "console.example.test:7070", "http://console.example.test:7070/user/login"),
            ("history", True, "console.example.test", "https://console.example.test/user/login"),
        )
        for route_mode, secure, host, expected in cases:
            with self.subTest(route_mode=route_mode, secure=secure, host=host), \
                    mock.patch.dict(os.environ, {"ROUTE_MODE": route_mode}):
                bean = self.get_response(secure=secure, HTTP_HOST=host)
                self.assertEqual(bean["url"], expected)
                self.assertIs(bean["is_public"], False)
                self.assertEqual(bean["redirect"], "redirect to the private rainbond login page!")

    def test_private_login_url_defaults_to_hash_routing(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("ROUTE_MODE", None)
            bean = self.get_response(HTTP_HOST="console.example.test:7070")
        self.assertEqual(bean["url"], "http://console.example.test:7070/#/user/login")

    @override_settings(SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_private_login_url_respects_trusted_proxy_scheme(self):
        with mock.patch.dict(os.environ, {"ROUTE_MODE": "hash"}):
            bean = self.get_response(HTTP_HOST="console.example.test", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(bean["url"], "https://console.example.test/#/user/login")

    @override_settings(SECURE_PROXY_SSL_HEADER=None, USE_X_FORWARDED_HOST=False)
    def test_private_login_url_does_not_trust_unconfigured_proxy_headers(self):
        with mock.patch.dict(os.environ, {"ROUTE_MODE": "hash"}):
            bean = self.get_response(
                HTTP_HOST="console.example.test:7070",
                HTTP_X_FORWARDED_PROTO="https",
                HTTP_X_FORWARDED_HOST="other.example.test",
            )
        self.assertEqual(bean["url"], "http://console.example.test:7070/#/user/login")

    @override_settings(MODULES={"SSO_LOGIN": True})
    def test_public_cloud_retains_sso_login_url(self):
        for route_mode in ("hash", "history"):
            with self.subTest(route_mode=route_mode), mock.patch.dict(os.environ, {"ROUTE_MODE": route_mode}):
                bean = self.get_response(HTTP_HOST="console.example.test:7070")
                self.assertEqual(bean["url"], "https://sso.goodrain.com/#/login/")
                self.assertIs(bean["is_public"], True)
                self.assertEqual(bean["redirect"], "redirect to the sso login page!")
