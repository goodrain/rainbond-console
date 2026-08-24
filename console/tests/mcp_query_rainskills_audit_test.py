# -*- coding: utf-8 -*-
import hashlib
import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from console.exception.main import ServiceHandleException
from console.views.mcp_query import MCPQueryHTTPView


class MCPQueryRainSkillsAuditTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(
            user_id=7,
            enterprise_id="enterprise-1",
            is_authenticated=True,
            nick_name="operator",
        )

    def _metadata(self):
        content = "# Bootstrap Skill\n"
        return {
            "com.rainbond/rainskills": {
                "schema": "rainskills.operation-meta.v1",
                "operation_id": str(uuid.uuid4()),
                "cli_version": "2.2.0",
                "confirmation_type": "rainskills_cli",
                "root_skill_id": "rainbond-app-assistant",
                "skill": {
                    "id": "rainbond-fullstack-bootstrap",
                    "profile": "cli",
                    "package_version": "1.0.0",
                    "source_revision": None,
                    "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "bundle_sha256": "b" * 64,
                    "content": content,
                },
            }
        }

    def _request(self, tool_name="rainbond_create_app", arguments=None, metadata=None):
        params = {
            "name": tool_name,
            "arguments": arguments or {"team_name": "team-a", "region_name": "region-a", "app_name": "demo"},
        }
        if metadata is not None:
            params["_meta"] = metadata
        request = self.factory.post(
            "/console/mcp/rainskills/api/query",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}),
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        return request

    def test_started_persistence_failure_blocks_tool_execution(self):
        unavailable = ServiceHandleException(
            msg="audit unavailable",
            msg_show="审计服务暂不可用",
            status_code=503,
            error_code="audit_unavailable",
        )
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="api")

        with patch("console.views.mcp_query.rainskills_audit_service.begin", side_effect=unavailable):
            with patch("console.views.mcp_query.mcp_query_service.call_tool") as tool_call:
                response = view(self._request(metadata=self._metadata()))

        tool_call.assert_not_called()
        self.assertTrue(response.data["result"]["isError"])
        self.assertEqual(response.data["result"]["structuredContent"]["error_code"], "audit_unavailable")

    def test_metadata_is_passed_to_audit_but_never_to_tool_arguments(self):
        metadata = self._metadata()
        arguments = {"team_name": "team-a", "region_name": "region-a", "app_name": "demo"}
        context = SimpleNamespace(operation=SimpleNamespace(pk=1))
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="codex")

        with patch("console.views.mcp_query.rainskills_audit_service.begin", return_value=context) as begin:
            with patch("console.views.mcp_query.rainskills_audit_service.finalize_success") as finalize:
                with patch("console.views.mcp_query.mcp_query_service.call_tool", return_value={"app_id": 7}) as call:
                    response = view(self._request(arguments=arguments, metadata=metadata))

        self.assertFalse(response.data["result"]["isError"])
        begin.assert_called_once_with(self.user, "rainbond_create_app", arguments, metadata)
        call.assert_called_once_with(self.user, "rainbond_create_app", arguments)
        self.assertNotIn("_meta", call.call_args.args[2])
        finalize.assert_called_once_with(context, {"app_id": 7})

    def test_read_tool_bypasses_audit_gate(self):
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="api")
        with patch("console.views.mcp_query.rainskills_audit_service.begin") as begin:
            with patch("console.views.mcp_query.mcp_query_service.call_tool", return_value={"user_id": 7}):
                response = view(self._request(tool_name="rainbond_get_current_user", arguments={}))

        self.assertFalse(response.data["result"]["isError"])
        begin.assert_not_called()

    def test_read_variant_of_mixed_tool_bypasses_audit_gate_before_begin(self):
        arguments = {
            "team_name": "team-a", "region_name": "region-a", "app_id": 7,
            "service_id": "service-1", "operation": "summary",
        }
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="api")
        with patch("console.views.mcp_query.rainskills_audit_service.begin") as begin:
            with patch("console.views.mcp_query.mcp_query_service.call_tool", return_value={"items": []}):
                response = view(self._request(
                    tool_name="rainbond_manage_component_envs", arguments=arguments))

        self.assertFalse(response.data["result"]["isError"])
        begin.assert_not_called()

    def test_legacy_mutable_call_is_still_audited_in_compatibility_mode(self):
        context = SimpleNamespace(operation=SimpleNamespace(pk=1))
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="api")
        with patch("console.views.mcp_query.rainskills_audit_service.begin", return_value=context) as begin:
            with patch("console.views.mcp_query.rainskills_audit_service.finalize_success"):
                with patch("console.views.mcp_query.mcp_query_service.call_tool", return_value={"app_id": 7}):
                    response = view(self._request())

        self.assertFalse(response.data["result"]["isError"])
        begin.assert_called_once()
        self.assertEqual(begin.call_args.args[3], {})

    @override_settings(RAINSKILLS_AUDIT_STRICT=True)
    def test_strict_mode_blocks_legacy_mutation_before_tool_execution(self):
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="api")
        with patch("console.views.mcp_query.mcp_query_service.call_tool") as tool_call:
            response = view(self._request())

        tool_call.assert_not_called()
        error = response.data["result"]["structuredContent"]
        self.assertEqual(error["status_code"], 428)
        self.assertEqual(error["error_code"], "operation_confirmation_required")

    def test_tool_failure_finalizes_audit_without_changing_error_contract(self):
        context = SimpleNamespace(operation=SimpleNamespace(pk=1))
        failure = ServiceHandleException(
            msg="conflict", msg_show="资源冲突", status_code=409, error_code="resource_conflict")
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="api")
        with patch("console.views.mcp_query.rainskills_audit_service.begin", return_value=context):
            with patch("console.views.mcp_query.rainskills_audit_service.finalize_failure") as finalize:
                with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=failure):
                    response = view(self._request(metadata=self._metadata()))

        finalize.assert_called_once_with(context, failure)
        self.assertEqual(response.data["result"]["structuredContent"]["status_code"], 409)
        self.assertEqual(response.data["result"]["structuredContent"]["error_code"], "resource_conflict")
