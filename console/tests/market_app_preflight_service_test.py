# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MarketInstallPreflightServiceTests(TestCase):
    def setUp(self):
        from console.services.market_app_preflight_service import MarketInstallPreflightService

        self.service = MarketInstallPreflightService()
        self.tenant = Obj(tenant_id="tenant-1", tenant_name="team-a", enterprise_id="eid-1")
        self.region = Obj(region_name="region-a")
        self.template = {
            "arch": "amd64",
            "apps": [
                {
                    "service_cname": "mysql",
                    "share_image": "goodrain.me/default-mysql:20260704195926",
                    "container_cpu": 500,
                    "memory": 1024,
                },
                {
                    "service_cname": "web",
                    "image": "goodrain.me/default-web:20260704195926",
                    "extend_method_map": {
                        "init_memory": 512,
                    },
                },
            ],
        }

    def test_blocks_when_cluster_resource_is_not_enough(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 1000,
            "req_cpu": 800,
            "cap_mem": 2048,
            "req_mem": 1600,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])
        self.service._probe_image_manifest = mock.Mock(return_value=("pass", "镜像版本存在", ""))

        result = self.service.run(self.tenant, self.region, self.template)

        self.assertEqual("block", result["status"])
        resource_check = self._check(result, "resource_capacity")
        self.assertEqual("block", resource_check["status"])
        self.assertIn("内存不足", resource_check["message"])
        self.assertTrue(result["should_block"])

    def test_blocks_when_template_arch_does_not_match_region(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4000,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["arm64"])
        self.service._probe_image_manifest = mock.Mock(return_value=("pass", "镜像版本存在", ""))

        result = self.service.run(self.tenant, self.region, self.template)

        self.assertEqual("block", result["status"])
        arch_check = self._check(result, "architecture")
        self.assertEqual("block", arch_check["status"])
        self.assertIn("架构不匹配", arch_check["message"])

    def test_warns_when_market_image_tag_cannot_be_confirmed(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4000,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])
        self.service._probe_image_manifest = mock.Mock(
            return_value=("warning", "镜像版本无法确认，可能不存在", "image_not_found"))

        result = self.service.run(self.tenant, self.region, self.template)

        self.assertEqual("warning", result["status"])
        self.assertFalse(result["should_block"])
        image_check = self._check(result, "image_manifest")
        self.assertEqual("warning", image_check["status"])
        self.assertEqual("image_not_found", image_check["reason"])

    def test_registry_404_is_warning_not_block(self):
        with mock.patch("console.services.market_app_preflight_service.requests.head",
                        return_value=Obj(status_code=404)):
            status, message, reason = self.service._probe_image_manifest(
                "registry.example.com/team/web:missing", 1)

        self.assertEqual("warning", status)
        self.assertEqual("image_not_found", reason)
        self.assertIn("无法确认", message)

    def test_warns_when_region_capability_is_missing(self):
        self.service._get_region_resources = mock.Mock(side_effect=Exception("old region api"))
        self.service._get_cluster_arches = mock.Mock(side_effect=Exception("old region api"))
        self.service._probe_image_manifest = mock.Mock(
            return_value=("warning", "镜像仓库检测超时，无法确认镜像版本", "registry_probe_timeout"))

        result = self.service.run(self.tenant, self.region, self.template)

        self.assertEqual("warning", result["status"])
        self.assertFalse(result["should_block"])
        self.assertEqual("warning", self._check(result, "resource_capacity")["status"])
        self.assertEqual("warning", self._check(result, "architecture")["status"])
        self.assertEqual("warning", self._check(result, "image_manifest")["status"])

    def test_warn_mode_does_not_block_confirmed_failures(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 1000,
            "req_cpu": 900,
            "cap_mem": 1024,
            "req_mem": 900,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])
        self.service._probe_image_manifest = mock.Mock(return_value=("pass", "镜像版本存在", ""))

        result = self.service.run(self.tenant, self.region, self.template, mode="warn")

        self.assertEqual("warning", result["status"])
        self.assertFalse(result["should_block"])
        self.assertEqual("block", self._check(result, "resource_capacity")["status"])

    @staticmethod
    def _check(result, name):
        for item in result["checks"]:
            if item["name"] == name:
                return item
        raise AssertionError("missing check {}".format(name))
