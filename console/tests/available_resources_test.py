# -*- coding: utf-8 -*-
import collections
import importlib
import os
import sys
import typing
from pathlib import Path
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired
    except ImportError:
        typing.NotRequired = lambda item: item

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client = ModuleType("openapi_client")
openapi_client.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
openapi_client.ApiClient = type("ApiClient", (), {"__init__": lambda self, configuration=None: None})
sys.modules.setdefault("openapi_client", openapi_client)
openapi_client_configuration = ModuleType("openapi_client.configuration")


class StubConfiguration(object):
    def __init__(self):
        self.api_key = {}
        self.client_side_validation = False
        self.host = ""


openapi_client_configuration.Configuration = StubConfiguration
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
openapi_client_rest = ModuleType("openapi_client.rest")
openapi_client_rest.ApiException = type("ApiException", (Exception,), {})
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
market_openapi_api = ModuleType("openapi_client.api.market_openapi_api")
market_openapi_api.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
sys.modules.setdefault("openapi_client.api.market_openapi_api", market_openapi_api)
sys.modules.setdefault("rest_framework_simplejwt", ModuleType("rest_framework_simplejwt"))
simplejwt_tokens = ModuleType("rest_framework_simplejwt.tokens")
simplejwt_tokens.AccessToken = type("AccessToken", (), {})
sys.modules.setdefault("rest_framework_simplejwt.tokens", simplejwt_tokens)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.app-create.available-resources


class AvailableResourcesServiceTests(TestCase):
    def setUp(self):
        try:
            service_module = importlib.import_module("console.services.available_resources_service")
        except ImportError:
            self.fail("available resources service is not implemented")
        self.service = service_module.AvailableResourcesService()
        self.tenant = Obj(enterprise_id="eid-1")
        self.region = Obj(region_name="region-a")

    @mock.patch("console.services.available_resources_service.region_api.get_region_resources")
    def test_converts_region_capacity_to_free_resources(self, get_region_resources):
        get_region_resources.return_value = self._region_response(
            cap_cpu=4,
            req_cpu=1.1,
            cap_mem=8192,
            req_mem=3197,
        )

        result = self.service.get_available_resources(self.tenant, self.region)

        self.assertEqual({"free_cpu": 2900, "free_memory": 4995}, result)
        get_region_resources.assert_called_once_with("eid-1", region="region-a")

    @mock.patch("console.services.available_resources_service.region_api.get_region_resources")
    def test_clamps_equal_and_overcommitted_resources_to_zero(self, get_region_resources):
        cases = (
            ({"cap_cpu": 1.5, "req_cpu": 1.5, "cap_mem": 512, "req_mem": 512}, {
                "free_cpu": 0,
                "free_memory": 0,
            }),
            ({"cap_cpu": 1.5, "req_cpu": 2, "cap_mem": 512, "req_mem": 768}, {
                "free_cpu": 0,
                "free_memory": 0,
            }),
        )
        for resources, expected in cases:
            with self.subTest(resources=resources):
                get_region_resources.return_value = self._region_response(**resources)

                self.assertEqual(expected, self.service.get_available_resources(self.tenant, self.region))

    @mock.patch("console.services.available_resources_service.region_api.get_region_resources")
    def test_rounds_fractional_cpu_values_independently_before_subtracting(self, get_region_resources):
        get_region_resources.return_value = self._region_response(
            cap_cpu=3.3336,
            req_cpu=1.1114,
            cap_mem=1024,
            req_mem=256,
        )

        result = self.service.get_available_resources(self.tenant, self.region)

        self.assertEqual(2223, result["free_cpu"])
        self.assertIsInstance(result["free_cpu"], int)
        self.assertIsInstance(result["free_memory"], int)

    @mock.patch("console.services.available_resources_service.region_api.get_region_resources")
    def test_region_error_returns_failure_instead_of_zero_resources(self, get_region_resources):
        from console.exception.main import ServiceHandleException

        get_region_resources.side_effect = RuntimeError("region unavailable")

        with self.assertRaises(ServiceHandleException) as context:
            self.service.get_available_resources(self.tenant, self.region)

        self.assertEqual(502, context.exception.status_code)
        self.assertEqual("资源检测失败，请稍后重试", context.exception.msg_show)
        self.assertIsNone(context.exception.bean)

    @mock.patch("console.services.available_resources_service.region_api.get_region_resources")
    def test_invalid_region_data_returns_failure_instead_of_zero_resources(self, get_region_resources):
        from console.exception.main import ServiceHandleException

        invalid_beans = (
            None,
            {"all_node": 1, "node_ready": 1, "cap_cpu": 4, "req_cpu": 1, "cap_mem": 1024},
            self._bean(cap_cpu=float("nan")),
            self._bean(req_cpu=float("inf")),
            self._bean(cap_mem=-1),
            self._bean(node_ready=0),
            self._bean(all_node=1, node_ready=2),
        )
        for bean in invalid_beans:
            with self.subTest(bean=bean):
                get_region_resources.return_value = ({"status": 200}, {"bean": bean})

                with self.assertRaises(ServiceHandleException) as context:
                    self.service.get_available_resources(self.tenant, self.region)

                self.assertEqual(502, context.exception.status_code)
                self.assertIsNone(context.exception.bean)

    @staticmethod
    def _bean(**overrides):
        bean = {
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 1,
            "cap_mem": 1024,
            "req_mem": 256,
        }
        bean.update(overrides)
        return bean

    @classmethod
    def _region_response(cls, **overrides):
        return {"status": 200}, {"bean": cls._bean(**overrides)}


class AvailableResourcesViewTests(TestCase):
    def _view_class(self):
        try:
            view_module = importlib.import_module("console.views.app_create.available_resources")
        except ImportError:
            self.fail("available resources view is not implemented")
        return view_module.AvailableResourcesView

    def test_get_returns_only_available_resource_fields(self):
        view_class = self._view_class()
        view = view_class()
        view.tenant = Obj(enterprise_id="eid-1")
        view.region = Obj(region_name="region-a")
        resources = {"free_cpu": 2900, "free_memory": 4995}

        with mock.patch(
                "console.views.app_create.available_resources.available_resources_service.get_available_resources",
                return_value=resources) as get_available_resources:
            response = view.get(Obj())

        get_available_resources.assert_called_once_with(view.tenant, view.region)
        self.assertEqual(200, response.status_code)
        self.assertEqual(resources, response.data["data"]["bean"])
        self.assertEqual({"bean", "list"}, set(response.data["data"]))

    def test_route_uses_team_create_permission_scope(self):
        url_source = Path(__file__).parents[1].joinpath("urls", "__init__.py").read_text(encoding="utf-8")

        self.assertIn("apps/available_resources", url_source)
        self.assertIn("AvailableResourcesView.as_view(),\n        perms.APP_CREATE_PERMS)", url_source)
