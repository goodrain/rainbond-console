# -*- coding: utf-8 -*-
import json
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

django.setup()

from console.exception.main import ServiceHandleException
from console.views.mcp_query import (
    MCPQueryHTTPView,
    MCPQueryMessageView,
    MCPQuerySSEView,
    _get_mcp_sse_session,
    _load_mcp_http_session,
    _remove_mcp_sse_session,
)


def _decode_chunk(chunk):
    if isinstance(chunk, bytes):
        return chunk.decode("utf-8")
    return chunk


def _parse_sse_data(chunk):
    for line in chunk.splitlines():
        if line.startswith("data: "):
            return line[len("data: "):]
    return ""


class MCPQuerySSEViewTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.http_view = MCPQueryHTTPView.as_view()
        self.sse_view = MCPQuerySSEView.as_view()
        self.message_view = MCPQueryMessageView.as_view()

    # capability_id: console.mcp.http-initialize
    def test_http_initialize_returns_json_and_session_header(self):
        request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
            HTTP_MCP_PROTOCOL_VERSION="2025-03-26",
        )

        response = self.http_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Mcp-Session-Id"] != "", True)
        self.assertEqual(response["MCP-Protocol-Version"], "2025-03-26")
        self.assertIn("Mcp-Session-Id", response["Access-Control-Expose-Headers"])
        self.assertEqual(response.data["result"]["protocolVersion"], "2025-03-26")
        session_payload = _load_mcp_http_session(response["Mcp-Session-Id"])
        self.assertEqual(session_payload["protocol_version"], "2025-03-26")

    # capability_id: console.mcp.http-tools-list-with-auth
    def test_http_post_tools_list_allows_authenticated_request_without_session_header(self):
        user = SimpleNamespace(user_id=1, is_authenticated=True, is_enterprise_admin=False, enterprise_id="eid-1")
        request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
            HTTP_MCP_PROTOCOL_VERSION="2025-03-26",
        )
        force_authenticate(request, user=user)

        response = self.http_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["MCP-Protocol-Version"], "2025-03-26")
        self.assertEqual(response["Mcp-Session-Id"] != "", True)
        self.assertTrue(response.data["result"]["tools"])

    # capability_id: console.mcp.http-tools-sse
    def test_http_post_can_return_sse_message_response(self):
        init_request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        init_response = self.http_view(init_request)
        session_id = init_response["Mcp-Session-Id"]

        tools_request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }),
            content_type="application/json",
            HTTP_ACCEPT="text/event-stream",
            HTTP_MCP_SESSION_ID=session_id,
        )

        with patch("console.views.mcp_query.user_services.get_user_by_user_id", return_value=SimpleNamespace(user_id=1)):
            response = self.http_view(tools_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        chunk = _decode_chunk(next(iter(response.streaming_content)))
        self.assertIn("event: message", chunk)
        self.assertIn('"tools"', chunk)

    # capability_id: console.mcp.structured-tool-error
    def test_http_tool_error_includes_structured_validation_details(self):
        user = SimpleNamespace(user_id=1, is_authenticated=True, nick_name="tester")
        init_request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        force_authenticate(init_request, user=user)
        init_response = self.http_view(init_request)
        session_id = init_response["Mcp-Session-Id"]

        request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "rainbond_manage_component_ports",
                    "arguments": {
                        "team_name": "demo-team",
                        "region_name": "rainbond",
                        "app_id": 20,
                        "service_id": "svc-1",
                        "operation": "add",
                        "port": 80,
                        "port_alias": "p80"
                    }
                }
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
            HTTP_MCP_SESSION_ID=session_id,
        )

        exc = ServiceHandleException(msg="add port error", msg_show="端口别名不合法", status_code=400)
        exc.details = {
            "field": "port_alias",
            "reason": "pattern_mismatch",
            "expected_pattern": "^[A-Z][A-Z0-9_]*$",
            "retryable": False,
        }

        with patch("console.views.mcp_query.user_services.get_user_by_user_id", return_value=user):
            with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=exc):
                response = self.http_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["result"]["isError"])
        self.assertEqual(response.data["result"]["structuredContent"]["error_code"], 400)
        self.assertEqual(response.data["result"]["structuredContent"]["details"]["field"], "port_alias")
        self.assertEqual(response.data["result"]["structuredContent"]["details"]["reason"], "pattern_mismatch")
        self.assertFalse(response.data["result"]["structuredContent"]["details"]["retryable"])

    # capability_id: console.mcp.http-delete-session
    def test_http_delete_accepts_valid_session_token(self):
        init_request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        init_response = self.http_view(init_request)
        session_id = init_response["Mcp-Session-Id"]

        delete_request = self.factory.delete(
            "/console/mcp/query",
            HTTP_MCP_SESSION_ID=session_id,
        )

        delete_response = self.http_view(delete_request)

        self.assertEqual(delete_response.status_code, 204)
        self.assertIsNotNone(_load_mcp_http_session(session_id))

    # capability_id: console.mcp.legacy-sse-endpoint
    def test_get_returns_endpoint_event_for_legacy_sse_clients(self):
        request = self.factory.get(
            "/console/mcp/query/sse",
            HTTP_ACCEPT="text/event-stream",
        )

        response = self.sse_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertNotIn("Connection", response)

        stream = iter(response.streaming_content)
        first_chunk = _decode_chunk(next(stream))
        self.assertIn("event: endpoint", first_chunk)

        endpoint = _parse_sse_data(first_chunk)
        self.assertTrue(endpoint.startswith("http://testserver/console/mcp/query/message?session_id="))
        self.assertNotIn('"', endpoint)

        parsed = urlparse(endpoint)
        session_id = parse_qs(parsed.query)["session_id"][0]
        self.assertIsNotNone(_get_mcp_sse_session(session_id))

        _remove_mcp_sse_session(session_id)

    # capability_id: console.mcp.post-message
    def test_post_message_enqueues_initialize_response_on_sse_stream(self):
        sse_request = self.factory.get(
            "/console/mcp/query/sse",
            HTTP_ACCEPT="text/event-stream",
        )
        sse_response = self.sse_view(sse_request)
        stream = iter(sse_response.streaming_content)
        endpoint_chunk = _decode_chunk(next(stream))
        endpoint = _parse_sse_data(endpoint_chunk)

        parsed = urlparse(endpoint)
        session_id = parse_qs(parsed.query)["session_id"][0]

        message_request = self.factory.post(
            "{}?{}".format(parsed.path, parsed.query),
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        message_response = self.message_view(message_request)

        self.assertEqual(message_response.status_code, 202)

        message_chunk = _decode_chunk(next(stream))
        self.assertIn("event: message", message_chunk)
        self.assertIn('"protocolVersion": "2024-11-05"', message_chunk)
        self.assertIn('"name": "rainbond-console-mcp"', message_chunk)

        _remove_mcp_sse_session(session_id)
