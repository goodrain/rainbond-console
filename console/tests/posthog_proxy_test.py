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

from console.views.posthog_proxy import PostHogProxyView  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class PostHogProxyViewTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.view = PostHogProxyView.as_view()

    def test_post_proxies_to_configured_posthog_host_without_rainbond_credentials(self):
        request = self.factory.post(
            "/console/posthog/e/?ip=0&_=1781193125735&ver=1.386.1",
            data=b'{"event":"rainbond_ui_click"}',
            content_type="application/json",
            HTTP_AUTHORIZATION="JWT rainbond-token",
            HTTP_COOKIE="token=rainbond-cookie",
            HTTP_X_CSRFTOKEN="csrf-token",
            HTTP_USER_AGENT="RainbondUITest",
        )
        upstream_response = Obj(status_code=200, content=b"ok", headers={"Content-Type": "text/plain"})

        with mock.patch.dict(os.environ, {"RAINBOND_POSTHOG_PROXY_TARGET": "https://posthog.goodrain.com"}), mock.patch(
            "console.views.posthog_proxy._send_upstream_request",
            return_value=upstream_response,
        ) as request_mock:
            response = self.view(request, path="e/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        request_mock.assert_called_once()
        _, kwargs = request_mock.call_args
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["url"], "https://posthog.goodrain.com/e/?ip=0&_=1781193125735&ver=1.386.1")
        self.assertEqual(kwargs["data"], b'{"event":"rainbond_ui_click"}')
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["headers"]["User-Agent"], "RainbondUITest")
        self.assertNotIn("Authorization", kwargs["headers"])
        self.assertNotIn("Cookie", kwargs["headers"])
        self.assertNotIn("X-Csrftoken", kwargs["headers"])

    def test_options_returns_cors_preflight_without_upstream_call(self):
        request = self.factory.options(
            "/console/posthog/e/",
            HTTP_ORIGIN="https://rainbond.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        with mock.patch("console.views.posthog_proxy._send_upstream_request") as request_mock:
            response = self.view(request, path="e/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://rainbond.example.com")
        self.assertIn("POST", response["Access-Control-Allow-Methods"])
        self.assertEqual(response["Access-Control-Allow-Headers"], "content-type")
        request_mock.assert_not_called()
