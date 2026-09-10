# -*- coding: utf-8 -*-
import os
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module = ModuleType("openapi_client.configuration")
    configuration_module.Configuration = type("Configuration", (), {})
    rest_module = ModuleType("openapi_client.rest")
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import SimpleTestCase  # noqa: E402

from console.services.deployment_invocation import deployment_invocation_context  # noqa: E402
from console.services.ai_engine_service import ai_engine_service  # noqa: E402
from console.services.mcp_ai_engine_tools import mcp_ai_engine_tools  # noqa: E402
from console.services.mcp_query_service import mcp_query_service  # noqa: E402
from console.services.rainskills_tool_audit_policy import classify_tool  # noqa: E402

P0_AI_ENGINE_TOOL_NAMES = {
    "rainbond_get_ai_engine_capabilities",
    "rainbond_get_ai_engine_resource_capacity",
    "rainbond_search_ai_engine_model_catalog",
    "rainbond_get_ai_engine_model_catalog_detail",
    "rainbond_list_ai_engine_model_recommendations",
    "rainbond_list_ai_engine_team_models",
    "rainbond_get_ai_engine_team_model",
    "rainbond_get_ai_engine_model_download",
    "rainbond_get_ai_engine_model_download_logs",
    "rainbond_create_ai_engine_model_download",
    "rainbond_delete_ai_engine_team_model",
    "rainbond_list_ai_engine_instances",
    "rainbond_get_ai_engine_instance",
    "rainbond_get_ai_engine_instance_logs",
    "rainbond_create_ai_engine_instance",
    "rainbond_update_ai_engine_instance_state",
    "rainbond_delete_ai_engine_instance",
    "rainbond_get_ai_engine_monitoring_overview",
}

PREREQUISITE_AI_ENGINE_TOOL_NAMES = {
    "rainbond_get_ai_engine_instance_deployment",
    "rainbond_list_ai_engine_instance_events",
    "rainbond_list_ai_engine_gpu_devices",
    "rainbond_get_ai_engine_gpu_device_timeseries",
    "rainbond_list_ai_engine_gpu_instance_bindings",
    "rainbond_list_ai_engine_gpu_instance_usage",
}

ALL_AI_ENGINE_TOOL_NAMES = P0_AI_ENGINE_TOOL_NAMES | PREREQUISITE_AI_ENGINE_TOOL_NAMES


class MCPAIEngineToolContractTests(SimpleTestCase):

    # capability_id: console.mcp.ai-engine-tool-catalog

    def setUp(self):
        self.admin = SimpleNamespace(
            user_id=1,
            enterprise_id="eid-1",
            is_enterprise_admin=True,
        )
        with deployment_invocation_context("rainskills", "api"):
            self.tools = {tool["name"]: tool for tool in mcp_query_service.list_tools(self.admin)}

    def test_catalog_contains_every_p0_ai_engine_tool(self):
        self.assertTrue(ALL_AI_ENGINE_TOOL_NAMES.issubset(set(self.tools)))

    def test_every_ai_engine_schema_rejects_unknown_top_level_fields(self):
        for name in ALL_AI_ENGINE_TOOL_NAMES:
            with self.subTest(tool=name):
                schema = self.tools[name]["inputSchema"]
                self.assertEqual("object", schema["type"])
                self.assertIs(schema["additionalProperties"], False)
                self.assertNotIn("namespace", schema["properties"])
                self.assertNotIn("backend_service", schema["properties"])
                self.assertNotIn("headers", schema["properties"])

    def test_list_and_search_tools_cap_page_size_at_fifty(self):
        names = (
            "rainbond_search_ai_engine_model_catalog",
            "rainbond_list_ai_engine_team_models",
            "rainbond_list_ai_engine_instances",
        )
        for name in names:
            with self.subTest(tool=name):
                page_size = self.tools[name]["inputSchema"]["properties"]["page_size"]
                self.assertEqual(50, page_size["maximum"])
                self.assertEqual(1, page_size["minimum"])

    def test_log_tools_cap_tail_lines_at_one_thousand(self):
        names = (
            "rainbond_get_ai_engine_model_download_logs",
            "rainbond_get_ai_engine_instance_logs",
        )
        for name in names:
            with self.subTest(tool=name):
                tail_lines = self.tools[name]["inputSchema"]["properties"]["tail_lines"]
                self.assertEqual(1000, tail_lines["maximum"])
                self.assertEqual(1, tail_lines["minimum"])

    def test_instance_log_schema_supports_previous_and_bounded_since(self):
        properties = self.tools["rainbond_get_ai_engine_instance_logs"]["inputSchema"]["properties"]
        self.assertEqual("boolean", properties["previous"]["type"])
        self.assertEqual(1, properties["since_seconds"]["minimum"])
        self.assertEqual(86400, properties["since_seconds"]["maximum"])

    def test_instance_event_schema_has_no_free_kubernetes_selectors(self):
        properties = self.tools["rainbond_list_ai_engine_instance_events"]["inputSchema"]["properties"]
        self.assertEqual(100, properties["limit"]["maximum"])
        self.assertEqual(86400, properties["since_seconds"]["maximum"])
        for forbidden in ("namespace", "pod_name", "selector", "field_selector", "label_selector"):
            self.assertNotIn(forbidden, properties)

    def test_gpu_timeseries_window_and_point_bounds_are_closed(self):
        properties = self.tools["rainbond_get_ai_engine_gpu_device_timeseries"]["inputSchema"]["properties"]
        self.assertEqual(["1h", "24h"], properties["window"]["enum"])
        self.assertEqual(720, properties["max_points"]["maximum"])

    def test_instance_state_is_a_closed_enum(self):
        target_state = self.tools["rainbond_update_ai_engine_instance_state"]["inputSchema"]["properties"]["target_state"]
        self.assertEqual(["Running", "Stopped"], target_state["enum"])

    def test_instance_create_schema_closes_nested_objects_and_argv(self):
        schema = self.tools["rainbond_create_ai_engine_instance"]["inputSchema"]
        resources = schema["properties"]["resources"]
        dynamic_params = schema["properties"]["dynamic_params"]
        extra_argv = schema["properties"]["extra_argv"]

        self.assertIs(resources["additionalProperties"], False)
        self.assertIs(dynamic_params["additionalProperties"], False)
        self.assertEqual(256, extra_argv["maxItems"])
        self.assertEqual(4096, extra_argv["items"]["maxLength"])
        for forbidden in ("gpu_allocation", "node_count"):
            self.assertNotIn(forbidden, resources["properties"])
        for forbidden in ("quantization", "extra_args", "env_vars", "resolved_argv"):
            self.assertNotIn(forbidden, dynamic_params["properties"])

    def test_ai_engine_tools_have_explicit_audit_scope_and_risk(self):
        read_names = ALL_AI_ENGINE_TOOL_NAMES - {
            "rainbond_create_ai_engine_model_download",
            "rainbond_delete_ai_engine_team_model",
            "rainbond_create_ai_engine_instance",
            "rainbond_update_ai_engine_instance_state",
            "rainbond_delete_ai_engine_instance",
        }
        for name in read_names:
            with self.subTest(tool=name):
                policy = classify_tool(name, {})
                self.assertEqual("read", policy.operation_class)
                self.assertEqual("none", policy.risk)
                self.assertIn(policy.scope, ("team", "enterprise"))
                self.assertTrue(policy.resource_type)

        expected_writes = {
            "rainbond_create_ai_engine_model_download": ("medium", "ai_engine_model"),
            "rainbond_delete_ai_engine_team_model": ("high", "ai_engine_model"),
            "rainbond_create_ai_engine_instance": ("medium", "ai_engine_instance"),
            "rainbond_update_ai_engine_instance_state": ("medium", "ai_engine_instance_runtime"),
            "rainbond_delete_ai_engine_instance": ("high", "ai_engine_instance"),
        }
        for name, expected in expected_writes.items():
            with self.subTest(tool=name):
                policy = classify_tool(name, {})
                self.assertEqual("write", policy.operation_class)
                self.assertEqual(expected[0], policy.risk)
                self.assertEqual("team", policy.scope)
                self.assertEqual(expected[1], policy.resource_type)

    def test_unplanned_ai_engine_endpoints_are_not_exposed(self):
        forbidden = {
            "rainbond_create_ai_engine_catalog_model",
            "rainbond_sync_ai_engine_model_catalog",
            "rainbond_create_ai_engine_upload",
            "rainbond_create_ai_engine_api_key",
            "rainbond_chat_ai_engine_instance",
        }
        self.assertFalse(forbidden & set(self.tools))

    def test_every_p0_tool_dispatches_to_the_domain_service(self):
        for tool_name, method_name in mcp_ai_engine_tools.TOOL_METHODS.items():
            with self.subTest(tool=tool_name), mock.patch.object(ai_engine_service,
                                                                 method_name,
                                                                 return_value={"tool": tool_name}) as handler:
                result = mcp_query_service.call_tool(self.admin, tool_name, {})

            self.assertEqual({"tool": tool_name}, result)
            handler.assert_called_once_with(self.admin, {})

    def test_console_catalog_matches_ai_engine_prerequisite_contract(self):
        ai_engine_root = os.environ.get("RAINBOND_AI_ENGINE_ROOT")
        if ai_engine_root:
            contract_path = Path(ai_engine_root) / "contracts/skills-prerequisites-v1.json"
        else:
            contract_path = Path(__file__).resolve().parent / "fixtures/ai_engine/skills-prerequisites-v1.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))

        self.assertEqual(contract["schema"], ai_engine_service.UPSTREAM_CONTRACT_SCHEMA)
        self.assertTrue(set(contract["mcp_tools"].values()).issubset(self.tools))
        log_properties = self.tools[contract["mcp_tools"]["logs"]]["inputSchema"]["properties"]
        self.assertTrue(set(contract["logs"]["request_fields"]).issubset(log_properties))
        event_properties = self.tools[contract["mcp_tools"]["events"]]["inputSchema"]["properties"]
        self.assertTrue(set(contract["events"]["request_fields"]).issubset(event_properties))
        self.assertFalse(set(contract["events"]["forbidden_inputs"]) & set(event_properties))
        self.assertIn("available", contract["deployment"]["response_fields"])
        self.assertIn("deployment_history_unavailable", contract["deployment"]["unavailable_reasons"])
        self.assertIn("used_memory_bytes", contract["gpu"]["response_fields"])
        self.assertEqual(["real", "unavailable"], contract["gpu"]["usage_sources"])
        self.assertIn("gpu_usage_unavailable", contract["gpu"]["usage_unavailable_reasons"])
