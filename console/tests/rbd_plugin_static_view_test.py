# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

import urllib3
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

openapi_client_module = ModuleType("openapi_client")
openapi_client_module.ApiClient = lambda configuration=None: SimpleNamespace(configuration=configuration)
openapi_client_module.MarketOpenapiApi = lambda client=None: SimpleNamespace(client=client)

openapi_client_configuration = ModuleType("openapi_client.configuration")


class _OpenAPIConfiguration(object):
    def __init__(self):
        self.client_side_validation = False
        self.host = ""
        self.api_key = {}


openapi_client_configuration.Configuration = _OpenAPIConfiguration

openapi_client_rest = ModuleType("openapi_client.rest")


class _ApiException(Exception):
    def __init__(self, status=400, body=""):
        super().__init__(body)
        self.status = status
        self.body = body


openapi_client_rest.ApiException = _ApiException

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
sys.modules.setdefault("openapi_client", openapi_client_module)
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

from console.views.rbd_plugin import RainbondPluginStaticView  # noqa: E402


class RainbondPluginStaticViewTests(SimpleTestCase):
    STATIC_HEADER_ALLOWLIST = frozenset([
        "accept",
        "cache-control",
        "if-match",
        "if-modified-since",
        "if-none-match",
        "if-range",
        "if-unmodified-since",
        "range",
    ])

    def setUp(self):
        self.factory = RequestFactory()

    def _assert_forwarded(self, upstream_response):
        request = self.factory.get(
            "/console/regions/rainbond/static/plugins/rainbond-agent",
            HTTP_ACCEPT="application/javascript",
        )
        with mock.patch(
                "console.views.rbd_plugin.region_api.proxy",
                return_value=upstream_response,
        ) as proxy, mock.patch(
                "console.views.rbd_plugin.region_api.get_proxy",
                return_value=b"legacy response",
        ) as get_proxy:
            response = RainbondPluginStaticView().get(
                request,
                region_name="rainbond",
                plugin_name="rainbond-agent",
            )

        proxy.assert_called_once()
        args, kwargs = proxy.call_args
        self.assertEqual(args, (
            request,
            "/v2/platform/static/plugins/rainbond-agent",
            "rainbond",
        ))
        timeout = kwargs["timeout"]
        self.assertIsInstance(timeout, urllib3.Timeout)
        self.assertEqual(timeout.connect_timeout, 5.0)
        self.assertEqual(timeout.read_timeout, 30.0)
        self.assertEqual(kwargs["header_allowlist"], self.STATIC_HEADER_ALLOWLIST)
        get_proxy.assert_not_called()
        self.assertIs(response, upstream_response)
        return response

    def test_preserves_successful_javascript_response(self):
        upstream_response = HttpResponse(
            b"System.register([], function () {});",
            status=200,
            content_type="application/javascript",
        )

        response = self._assert_forwarded(upstream_response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"System.register([], function () {});")
        self.assertEqual(response["Content-Type"], "application/javascript")

    def test_preserves_region_not_found_response(self):
        upstream_response = HttpResponse(
            b"plugin not found",
            status=404,
            content_type="text/plain",
        )

        response = self._assert_forwarded(upstream_response)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b"plugin not found")
        self.assertEqual(response["Content-Type"], "text/plain")

    def test_preserves_region_bad_gateway_response(self):
        upstream_response = HttpResponse(
            b"plugin frontend unavailable",
            status=502,
            content_type="application/problem+json",
        )

        response = self._assert_forwarded(upstream_response)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.content, b"plugin frontend unavailable")
        self.assertEqual(response["Content-Type"], "application/problem+json")
