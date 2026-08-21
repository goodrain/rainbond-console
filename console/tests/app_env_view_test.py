# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client = ModuleType("openapi_client")
    configuration = ModuleType("openapi_client.configuration")
    rest = ModuleType("openapi_client.rest")

    class StubConfiguration(object):
        def __init__(self):
            self.api_key = {}
            self.client_side_validation = False
            self.host = ""

    openapi_client.ApiClient = object
    openapi_client.MarketOpenapiApi = object
    configuration.Configuration = StubConfiguration
    rest.ApiException = type("ApiException", (Exception,), {})
    sys.modules["openapi_client"] = openapi_client
    sys.modules["openapi_client.configuration"] = configuration
    sys.modules["openapi_client.rest"] = rest
if "rest_framework_simplejwt.tokens" not in sys.modules:
    simplejwt = ModuleType("rest_framework_simplejwt")
    tokens = ModuleType("rest_framework_simplejwt.tokens")

    class StubAccessToken(dict):
        @classmethod
        def for_user(cls, user):
            return cls()

        def __str__(self):
            return ""

    tokens.AccessToken = StubAccessToken
    simplejwt.tokens = tokens
    sys.modules["rest_framework_simplejwt"] = simplejwt
    sys.modules["rest_framework_simplejwt.tokens"] = tokens

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.app_config.app_env import AppEnvView  # noqa: E402


class AppEnvViewPaginationTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppEnvView()
        self.view.service = mock.Mock(tenant_id="tenant-id", service_id="service-id")

    # capability_id: console.database.orm-pagination
    def test_get_returns_empty_list_when_requested_page_exceeds_inner_env_total(self):
        request = self.factory.get("/console/teams/demo-team/apps/demo-service/envs",
                                   {"env_type": "inner", "page": 2, "page_size": 10})
        queryset = mock.MagicMock()
        queryset.order_by.return_value = queryset
        queryset.count.return_value = 8

        with mock.patch("console.views.app_config.app_env.TenantServiceEnvVar.objects.filter", return_value=queryset):
            response = self.view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["total"], 8)
        self.assertEqual(response.data["data"]["list"], [])
        queryset.__getitem__.assert_not_called()
