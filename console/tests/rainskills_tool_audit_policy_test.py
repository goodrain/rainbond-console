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
            classify_tool("rainbond_get_current_user"),
            ToolAuditSpec("read", "none", "enterprise"),
        )

    def test_known_mutation_uses_server_owned_risk_and_scope(self):
        self.assertEqual(
            classify_tool("rainbond_delete_app"),
            ToolAuditSpec("write", "high", "app"),
        )

    def test_unknown_tool_fails_safe_as_an_enterprise_write(self):
        self.assertEqual(
            classify_tool("rainbond_future_tool"),
            ToolAuditSpec("write", "medium", "enterprise"),
        )
