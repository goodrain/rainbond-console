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
                    "cpu": 500,
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

    def test_region_core_cpu_values_are_compared_as_millicores(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 2,
            "node_ready": 2,
            "cap_cpu": 64,
            "req_cpu": 21.35,
            "cap_mem": 257095,
            "req_mem": 37253,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])
        self.service._probe_image_manifest = mock.Mock(return_value=("pass", "镜像版本存在", ""))
        template = {
            "arch": "amd64",
            "apps": [{
                "service_cname": "dify",
                "share_image": "goodrain.me/dify:1.11.1",
                "cpu": 2100,
                "memory": 5120,
            }],
        }

        result = self.service.run(self.tenant, self.region, template)

        self.assertEqual("pass", result["status"])
        resource_check = self._check(result, "resource_capacity")
        self.assertEqual("pass", resource_check["status"])
        self.assertEqual(42650, resource_check["details"]["free_cpu"])
        self.assertEqual(2100, resource_check["details"]["required_cpu"])

    def test_blocks_when_market_template_cpu_is_in_extend_method_map(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 1,
            "req_cpu": 0.8,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])
        template = {
            "arch": "amd64",
            "apps": [{
                "service_cname": "web",
                "extend_method_map": {
                    "container_cpu": 500,
                    "init_memory": 512,
                },
            }],
        }

        result = self.service.run(self.tenant, self.region, template, check_images=False)

        self.assertEqual(500, result["requirements"]["cpu"])
        self.assertEqual("block", result["status"])
        self.assertTrue(result["should_block"])
        resource_check = self._check(result, "resource_capacity")
        self.assertEqual("block", resource_check["status"])
        self.assertIn("CPU不足", resource_check["message"])
        self.assertEqual(300, resource_check["details"]["missing_cpu"])

    def test_top_level_cpu_matches_market_install_precedence(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "container_cpu": 0,
                "cpu": 500,
            }],
        })

        self.assertEqual(500, requirements["cpu"])

    def test_explicit_zero_cpu_uses_default_preflight_estimate(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "container_cpu": 750,
                "cpu": 500,
                "extend_method_map": {
                    "container_cpu": 0,
                },
            }],
        })

        self.assertEqual(250, requirements["cpu"])

    def test_market_app_with_unlimited_cpu_estimates_each_component(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "cpu": 0,
                "extend_method_map": {
                    "container_cpu": 0,
                },
            } for _ in range(9)],
        })

        self.assertEqual(2250, requirements["cpu"])

    def test_extend_method_map_cpu_precedes_top_level_cpu(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "cpu": 500,
                "extend_method_map": {
                    "container_cpu": 750,
                },
            }],
        })

        self.assertEqual(750, requirements["cpu"])

    def test_missing_cpu_defaults_to_250_millicores(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{}],
        })

        self.assertEqual(250, requirements["cpu"])

    def test_top_level_container_cpu_is_ignored(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "container_cpu": 750,
            }],
        })

        self.assertEqual(250, requirements["cpu"])

    def test_extend_method_map_init_memory_precedes_other_memory_values(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "memory": 1024,
                "extend_method_map": {
                    "init_memory": 768,
                    "min_memory": 256,
                },
            }],
        })

        self.assertEqual(768, requirements["memory"])

    def test_top_level_memory_precedes_extend_method_map_min_memory(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "memory": 1024,
                "extend_method_map": {
                    "min_memory": 256,
                },
            }],
        })

        self.assertEqual(1024, requirements["memory"])

    def test_extend_method_map_min_memory_is_used_when_other_memory_values_are_missing(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "extend_method_map": {
                    "min_memory": 256,
                },
            }],
        })

        self.assertEqual(256, requirements["memory"])

    def test_missing_memory_defaults_to_512_mebibytes(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{}],
        })

        self.assertEqual(512, requirements["memory"])

    def test_explicit_zero_memory_values_preserve_precedence(self):
        init_memory = self.service.parse_template_requirements({
            "apps": [{
                "memory": 1024,
                "extend_method_map": {
                    "init_memory": 0,
                    "min_memory": 256,
                },
            }],
        })
        top_level_memory = self.service.parse_template_requirements({
            "apps": [{
                "memory": 0,
                "extend_method_map": {
                    "min_memory": 256,
                },
            }],
        })

        self.assertEqual(0, init_memory["memory"])
        self.assertEqual(0, top_level_memory["memory"])

    def test_component_resources_are_multiplied_by_min_node(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "cpu": 500,
                "memory": 1024,
                "extend_method_map": {
                    "min_node": 3,
                },
            }],
        })

        self.assertEqual(1500, requirements["cpu"])
        self.assertEqual(3072, requirements["memory"])

    def test_missing_min_node_defaults_to_one_replica(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "cpu": 500,
                "memory": 1024,
            }],
        })

        self.assertEqual(500, requirements["cpu"])
        self.assertEqual(1024, requirements["memory"])

    def test_explicit_zero_min_node_requires_no_resources(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "cpu": 500,
                "memory": 1024,
                "extend_method_map": {
                    "min_node": 0,
                },
            }],
        })

        self.assertEqual(0, requirements["cpu"])
        self.assertEqual(0, requirements["memory"])

    def test_shortage_details_include_missing_cpu_and_memory(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 1,
            "req_cpu": 0.8,
            "cap_mem": 1024,
            "req_mem": 900,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])
        template = {
            "apps": [{
                "cpu": 500,
                "memory": 512,
            }],
        }

        result = self.service.run(self.tenant, self.region, template, check_images=False)

        details = self._check(result, "resource_capacity")["details"]
        self.assertEqual(300, details["missing_cpu"])
        self.assertEqual(388, details["missing_memory"])

    def test_missing_resource_bean_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value=None)
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_malformed_resource_bean_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value=[])
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_missing_resource_field_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_none_resource_field_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": None,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_boolean_resource_field_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": True,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_non_numeric_resource_field_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": "4",
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_negative_resource_field_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": -1,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_negative_node_field_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": -1,
            "node_ready": 0,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_ready_nodes_greater_than_all_nodes_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1.5,
            "node_ready": 2.5,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_oversized_integer_resource_field_warns_without_raising(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 10**1000,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "resource_capacity")

    def test_valid_float_resource_fields_are_preserved(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1.5,
            "node_ready": 0.5,
            "cap_cpu": 4.25,
            "req_cpu": 0.75,
            "cap_mem": 8192.5,
            "req_mem": 0.5,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        resource_check = self._check(result, "resource_capacity")
        self.assertEqual("pass", resource_check["status"])
        self.assertEqual(1.5, resource_check["details"]["all_node"])
        self.assertEqual(0.5, resource_check["details"]["node_ready"])
        self.assertEqual(8192.0, resource_check["details"]["free_memory"])

    def test_infinite_template_resource_values_do_not_raise(self):
        requirements = self.service.parse_template_requirements({
            "apps": [{
                "cpu": float("inf"),
                "memory": float("inf"),
            }],
        })

        self.assertEqual(0, requirements["cpu"])
        self.assertEqual(0, requirements["memory"])

    def test_explicit_zero_ready_nodes_blocks_when_resource_response_is_valid(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 0,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        resource_check = self._check(result, "resource_capacity")
        self.assertEqual("block", resource_check["status"])
        self.assertEqual("no_ready_nodes", resource_check["reason"])
        self.assertTrue(result["should_block"])

    def test_large_region_core_cpu_values_are_compared_as_millicores(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 6,
            "node_ready": 6,
            "cap_cpu": 1022,
            "req_cpu": 2,
            "cap_mem": 4134763,
            "req_mem": 2048,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["arm64", "amd64"])
        template = {
            "arch": "arm64",
            "apps": [{
                "service_cname": "logs",
                "cpu": 1500,
                "memory": 2048,
            }],
        }

        result = self.service.run(self.tenant, self.region, template, check_images=False)

        self.assertEqual("pass", result["status"])
        resource_check = self._check(result, "resource_capacity")
        self.assertEqual("pass", resource_check["status"])
        self.assertEqual(1022000, resource_check["details"]["total_cpu"])
        self.assertEqual(2000, resource_check["details"]["used_cpu"])
        self.assertEqual(1020000, resource_check["details"]["free_cpu"])
        self.assertEqual(1500, resource_check["details"]["required_cpu"])

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

    def test_blocks_when_template_arch_does_not_match_any_region_architecture(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["arm64", "s390x"])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        arch_check = self._check(result, "architecture")
        self.assertEqual("block", arch_check["status"])
        self.assertEqual("arch_mismatch", arch_check["reason"])

    def test_empty_cluster_architecture_list_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=[])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "architecture")

    def test_malformed_cluster_architecture_list_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value={"arch": "amd64"})

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "architecture")

    def test_cluster_architecture_list_with_malformed_item_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service._get_cluster_arches = mock.Mock(return_value=["amd64", None])

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "architecture")

    def test_string_region_architecture_payload_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        with mock.patch(
                "console.services.market_app_preflight_service.region_api.get_cluster_nodes_arch",
                return_value=(None, {"list": "amd64"})):
            result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "architecture")

    def test_dict_region_architecture_payload_warns_without_blocking(self):
        self.service._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        with mock.patch(
                "console.services.market_app_preflight_service.region_api.get_cluster_nodes_arch",
                return_value=(None, {"list": {"amd64": True}})):
            result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self._assert_region_capability_warning(result, "architecture")

    def test_valid_region_architecture_payload_is_deduplicated(self):
        with mock.patch(
                "console.services.market_app_preflight_service.region_api.get_cluster_nodes_arch",
                return_value=(None, {"list": ["amd64", "arm64", "amd64"]})):
            arches = self.service._get_cluster_arches(self.region)

        self.assertCountEqual(["amd64", "arm64"], arches)
        self.assertEqual(2, len(arches))

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

    def test_can_skip_image_manifest_check_for_trusted_templates(self):
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
            return_value=("warning", "镜像仓库检测超时，无法确认镜像版本", "registry_probe_timeout"))

        result = self.service.run(self.tenant, self.region, self.template, check_images=False)

        self.assertEqual("pass", result["status"])
        self.assertFalse(result["should_block"])
        self.service._probe_image_manifest.assert_not_called()
        self.assertNotIn("image_manifest", [item["name"] for item in result["checks"]])

    def test_registry_404_is_warning_not_block(self):
        with mock.patch("console.services.market_app_preflight_service.requests.head",
                        return_value=Obj(status_code=404)):
            status, message, reason = self.service._probe_image_manifest(
                "registry.example.com/team/web:missing", 1)

        self.assertEqual("warning", status)
        self.assertEqual("image_not_found", reason)
        self.assertIn("无法确认", message)

    def test_parse_docker_hub_short_image_name(self):
        parsed = self.service._parse_image("nginx:1.25")

        self.assertEqual(("registry-1.docker.io", "library/nginx", "1.25"), parsed)

    def test_parse_docker_hub_namespace_image_name(self):
        parsed = self.service._parse_image("goodrain/demo")

        self.assertEqual(("registry-1.docker.io", "goodrain/demo", "latest"), parsed)

    def test_parse_registry_image_name(self):
        parsed = self.service._parse_image("registry.example.com/team/web:v1")

        self.assertEqual(("registry.example.com", "team/web", "v1"), parsed)

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

    def _assert_region_capability_warning(self, result, check_name):
        check = self._check(result, check_name)
        self.assertEqual("warning", check["status"])
        self.assertEqual("region_capability_missing", check["reason"])
        self.assertFalse(result["should_block"])
