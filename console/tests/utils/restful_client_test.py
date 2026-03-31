# coding: utf-8
from unittest import TestCase

import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django

django.setup()

from console.exception.main import ServiceHandleException
from console.exception.main import StoreNoPermissionsError
from console.utils.restful_client import apiException
from console.utils.restful_client import get_market_client
from openapi_client.rest import ApiException


class DummyResource(object):
    name = "demo-app"


class RestfulClientApiExceptionTests(TestCase):
    def _build_api_exception(self, status, body="body"):
        exc = ApiException(status=status, reason="boom")
        exc.body = body
        return exc

    # capability_id: console.market-client.auth-missing
    def test_api_exception_401(self):
        @apiException
        def fn(client, resource):
            raise self._build_api_exception(401)

        with self.assertRaises(ServiceHandleException) as ctx:
            fn(object(), DummyResource())
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.error_code, 10421)

    # capability_id: console.market-client.permission-denied
    def test_api_exception_403(self):
        @apiException
        def fn(client, resource):
            raise self._build_api_exception(403)

        with self.assertRaises(StoreNoPermissionsError) as ctx:
            fn(object(), DummyResource())
        self.assertEqual(ctx.exception.bean, {"name": "demo-app"})

    # capability_id: console.market-client.not-found
    def test_api_exception_404(self):
        @apiException
        def fn(client, resource):
            raise self._build_api_exception(404, body="missing")

        with self.assertRaises(ServiceHandleException) as ctx:
            fn(object(), DummyResource())
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.msg, "missing")

    # capability_id: console.market-client.bad-request
    def test_api_exception_generic_4xx(self):
        @apiException
        def fn(client, resource):
            raise self._build_api_exception(422, body="invalid")

        with self.assertRaises(ServiceHandleException) as ctx:
            fn(object(), DummyResource())
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.msg, "invalid")

    # capability_id: console.market-client.server-error
    def test_api_exception_generic_5xx(self):
        @apiException
        def fn(client, resource):
            raise self._build_api_exception(500, body="oops")

        with self.assertRaises(ServiceHandleException) as ctx:
            fn(object(), DummyResource())
        self.assertEqual(ctx.exception.status_code, 400)

    # capability_id: console.market-client.deserialize-error
    def test_api_exception_value_error(self):
        @apiException
        def fn(client, resource):
            raise ValueError("bad json")

        with self.assertRaises(ServiceHandleException) as ctx:
            fn(object(), DummyResource())
        self.assertEqual(ctx.exception.status_code, 400)


class RestfulClientFactoryTests(TestCase):
    # capability_id: console.market-client.host-config
    def test_get_market_client_uses_explicit_host(self):
        client = get_market_client("token-123", host="http://example.com")
        self.assertEqual(client.api_client.configuration.host, "http://example.com")
        self.assertEqual(client.api_client.configuration.api_key["Authorization"], "token-123")

    # capability_id: console.market-client.default-host
    def test_get_market_client_uses_default_host(self):
        client = get_market_client(None)
        self.assertEqual(client.api_client.configuration.host, "http://api.goodrain.com:80")
        self.assertEqual(client.api_client.configuration.api_key, {})
