# -*- coding: utf-8 -*-
"""Error-contract tests for MCP tools.

These verify that MCP tool failures are always returned in a shape the
rainbond-copilot `extractMcpErrorText` can read (a non-empty human readable
reason in `content[].text` and `structuredContent`), so telemetry stops
recording null `error_message`.
"""
import json
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

django.setup()

from console.exception.main import ServiceHandleException
from console.services.mcp_query_service import mcp_query_service
from console.views.mcp_query import MCPQueryHTTPView


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MCPToolErrorDispatchTests(SimpleTestCase):
    """K1: any tool exception must reach the copilot-parseable error shape."""

    KEY_TOOLS = (
        "rainbond_delete_component",
        "rainbond_manage_component_ports",
        "rainbond_manage_component_storage",
        "rainbond_manage_component_dependency",
        "rainbond_get_component_summary",
    )

    def setUp(self):
        self.factory = APIRequestFactory()
        self.http_view = MCPQueryHTTPView.as_view()
        self.user = SimpleNamespace(user_id=1, is_authenticated=True, nick_name="tester")

    def _init_session(self):
        init_request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        force_authenticate(init_request, user=self.user)
        return self.http_view(init_request)["Mcp-Session-Id"]

    def _call_tool(self, session_id, name, arguments):
        request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
            HTTP_MCP_SESSION_ID=session_id,
        )
        with patch("console.views.mcp_query.user_services.get_user_by_user_id", return_value=self.user):
            return self.http_view(request)

    @staticmethod
    def _assert_parseable_error(test, response, expected_substring, expected_status=500):
        test.assertEqual(response.status_code, 200)
        result = response.data["result"]
        test.assertTrue(result["isError"])
        content = result["content"]
        test.assertTrue(content)
        test.assertEqual(content[0]["type"], "text")
        test.assertIn(expected_substring, content[0]["text"])
        structured = result["structuredContent"]
        test.assertTrue(structured.get("msg_show"))
        test.assertIn(expected_substring, structured["msg_show"])
        test.assertEqual(structured["status_code"], expected_status)
        test.assertEqual(structured["error_code"], expected_status)

    # capability_id: console.mcp.tool-error-fallback
    def test_generic_tool_exception_is_returned_as_parseable_error(self):
        session_id = self._init_session()
        for name in self.KEY_TOOLS:
            reason = "boom from {}".format(name)
            with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=RuntimeError(reason)):
                response = self._call_tool(session_id, name, {})
            self._assert_parseable_error(self, response, reason, expected_status=500)

    # capability_id: console.mcp.tool-error-fallback
    def test_region_style_exception_maps_status_and_extracts_message(self):
        session_id = self._init_session()

        class FakeRegionError(Exception):
            def __init__(self):
                self.status = 404
                self.message = {"httpcode": 404, "body": {"msg_show": "组件在集群中不存在"}}

            def __str__(self):
                return json.dumps(self.message, ensure_ascii=False)

        with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=FakeRegionError()):
            response = self._call_tool(session_id, "rainbond_delete_component", {"service_id": "svc-1"})

        self._assert_parseable_error(self, response, "组件在集群中不存在", expected_status=404)


class MCPComponentContextErrorTests(SimpleTestCase):
    """K2/K3: real tool code returns structured, readable failure reasons."""

    def setUp(self):
        self.user = Obj(user_id=1, pk=1, enterprise_id="eid-1", nick_name="admin", is_enterprise_admin=True)
        self.user.get_username = lambda: self.user.nick_name
        self.team = Obj(
            ID=11, tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1", creater=1,
        )
        self.app = Obj(ID=12, tenant_id="team-1", region_name="rainbond", group_name="demo-app")
        self.service = Obj(
            service_id="svc-1", tenant_id="team-1", service_region="rainbond",
            service_alias="alias-1", service_cname="component-1",
        )
        self.region = Obj(region_name="rainbond", enterprise_id="eid-1")
        self.relations = [Obj(service_id="svc-1")]

        patchers = {
            "team": patch(
                "console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name",
                return_value=self.team),
            "region": patch(
                "console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name",
                return_value=self.region),
            "app": patch(
                "console.services.mcp_query_service.group_service.get_app_by_id",
                return_value=self.app),
            "service": patch(
                "console.services.mcp_query_service.service_repo.get_service_by_service_id",
                return_value=self.service),
            "relations": patch(
                "console.services.mcp_query_service.group_service_relation_repo.get_services_by_group",
                return_value=self.relations),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)

    def _delete_args(self, **overrides):
        args = {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"}
        args.update(overrides)
        return args

    # capability_id: console.component.delete-dependency-conflict
    def test_delete_component_dependency_conflict_returns_structured_reason(self):
        conflict_msg = "组件被component-2,component-3依赖，不可删除"
        with patch(
                "console.services.mcp_query_service.app_manage_service.delete",
                return_value=(412, conflict_msg)):
            with self.assertRaises(ServiceHandleException) as ctx:
                mcp_query_service.call_tool(self.user, "rainbond_delete_component", self._delete_args())

        exc = ctx.exception
        self.assertEqual(exc.status_code, 412)
        self.assertEqual(exc.msg, "dependency_conflict")
        self.assertIn("component-2", exc.msg_show)
        self.assertIn("解除依赖", exc.msg_show)
        self.assertIsNotNone(exc.details)
        self.assertEqual(exc.details["reason"], "dependency_conflict")
        self.assertIs(exc.details["retryable"], False)
        self.assertEqual(exc.details["service_id"], "svc-1")

    # capability_id: console.component.delete-dependency-conflict
    def test_delete_component_running_conflict_is_non_retryable(self):
        running_msg = "组件可能处于运行状态,请先关闭组件"
        with patch(
                "console.services.mcp_query_service.app_manage_service.delete",
                return_value=(409, running_msg)):
            with self.assertRaises(ServiceHandleException) as ctx:
                mcp_query_service.call_tool(self.user, "rainbond_delete_component", self._delete_args())

        exc = ctx.exception
        self.assertEqual(exc.status_code, 409)
        self.assertEqual(exc.msg, "component_running")
        self.assertIn("请先关闭组件", exc.msg_show)
        self.assertIs(exc.details["retryable"], False)

    # capability_id: console.mcp.input-validation-contract
    def test_missing_service_id_returns_invalid_input(self):
        args = self._delete_args()
        args.pop("service_id")
        with self.assertRaises(ServiceHandleException) as ctx:
            mcp_query_service.call_tool(self.user, "rainbond_delete_component", args)

        exc = ctx.exception
        self.assertEqual(exc.status_code, 400)
        self.assertIn("service_id", exc.msg)
        self.assertEqual(exc.msg_show, "参数service_id无效")

    # capability_id: console.mcp.input-validation-contract
    def test_unknown_component_returns_not_found(self):
        with patch(
                "console.services.mcp_query_service.service_repo.get_service_by_service_id",
                return_value=None):
            with self.assertRaises(ServiceHandleException) as ctx:
                mcp_query_service.call_tool(
                    self.user, "rainbond_get_component_summary", self._delete_args(service_id="missing"))

        exc = ctx.exception
        self.assertEqual(exc.status_code, 404)
        self.assertEqual(exc.msg_show, "组件不存在")
