# -*- coding: utf-8 -*-
from types import SimpleNamespace

from django.test import SimpleTestCase

from console.services.deployment_invocation import deployment_invocation_context
from console.services.mcp_query_service import mcp_query_service
from console.services.rainskills_tool_audit_policy import (
    MUTABLE_TOOL_POLICY,
    READ_ONLY_TOOL_NAMES,
    ToolAuditSpec,
    classify_tool,
)


class RainSkillsToolAuditPolicyTests(SimpleTestCase):

    def test_every_visible_tool_has_exactly_one_explicit_classification(self):
        admin = SimpleNamespace(is_enterprise_admin=True)
        with deployment_invocation_context("rainskills", "api"):
            names = {item["name"] for item in mcp_query_service.list_tools(admin)}

        self.assertEqual(names, READ_ONLY_TOOL_NAMES | set(MUTABLE_TOOL_POLICY))
        self.assertFalse(READ_ONLY_TOOL_NAMES & set(MUTABLE_TOOL_POLICY))

    def test_read_tools_do_not_enter_the_write_gate(self):
        self.assertEqual(
            classify_tool("rainbond_get_current_user", {}),
            ToolAuditSpec("read", "none", "enterprise"),
        )

    def test_known_mutation_uses_server_owned_risk_and_scope(self):
        self.assertEqual(
            classify_tool("rainbond_delete_app", {}),
            ToolAuditSpec("write", "high", "app"),
        )

    def test_unknown_tool_fails_safe_as_an_enterprise_write(self):
        self.assertEqual(
            classify_tool("rainbond_future_tool", {}),
            ToolAuditSpec("write", "medium", "enterprise"),
        )

    def test_mixed_component_tools_classify_read_aliases_from_arguments(self):
        cases = (
            ("rainbond_manage_component_envs", "summary"),
            ("rainbond_manage_component_connection_envs", "list"),
            ("rainbond_manage_component_ports", "view"),
            ("rainbond_manage_component_storage", "list_unmounted"),
            ("rainbond_manage_component_autoscaler", "records"),
            ("rainbond_manage_component_probe", "get"),
            ("rainbond_manage_component_dependency", "summary"),
        )
        for tool_name, operation in cases:
            with self.subTest(tool_name=tool_name, operation=operation):
                policy = classify_tool(tool_name, {"operation": operation})
                self.assertEqual(policy.operation_class, "read")
                self.assertEqual(policy.risk, "none")
                self.assertEqual(policy.scope, "component")

    def test_mixed_component_tools_keep_mutations_in_the_write_gate(self):
        policy = classify_tool(
            "rainbond_manage_component_envs", {"operation": "delete"})

        self.assertEqual(policy.operation_class, "write")
        self.assertEqual(policy.risk, "medium")
        self.assertEqual(policy.scope, "component")
        self.assertEqual(policy.resource_type, "component_env")
        self.assertEqual(policy.action, "delete")

    def test_actual_side_effects_override_query_like_tool_names(self):
        cases = (
            ("rainbond_exec", "high", "component", "component_exec"),
            ("rainbond_get_component_check_result", "low", "component", "component_source"),
            ("rainbond_get_yaml_app_check_result", "low", "app", "app_components"),
        )
        for tool_name, risk, scope, resource_type in cases:
            with self.subTest(tool_name=tool_name):
                policy = classify_tool(tool_name, {})
                self.assertEqual(policy.operation_class, "write")
                self.assertEqual(policy.risk, risk)
                self.assertEqual(policy.scope, scope)
                self.assertEqual(policy.resource_type, resource_type)

    def test_operate_app_scope_and_target_mode_follow_service_ids(self):
        cases = (
            (["service-1"], "component", "single"),
            (["service-1", "service-2"], "app", "multiple"),
            ([], "app", "all"),
            (None, "app", "all"),
        )
        for service_ids, scope, target_mode in cases:
            arguments = {"action": "restart"}
            if service_ids is not None:
                arguments["service_ids"] = service_ids
            with self.subTest(service_ids=service_ids):
                policy = classify_tool("rainbond_operate_app", arguments)
                self.assertEqual(policy.scope, scope)
                self.assertEqual(policy.target_mode, target_mode)
                self.assertEqual(policy.action, "restart")
                self.assertEqual(policy.resource_type, "component_runtime")
