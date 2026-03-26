# -*- coding: utf-8 -*-
import json
from urllib.parse import parse_qs, urlparse

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from console.views.mcp_query import (
    MCPQueryHTTPView,
    MCPQueryMessageView,
    MCPQuerySSEView,
    _get_mcp_sse_session,
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
        self.assertEqual(response.data["result"]["protocolVersion"], "2025-03-26")
        _remove_mcp_sse_session(response["Mcp-Session-Id"])

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

        response = self.http_view(tools_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        chunk = _decode_chunk(next(iter(response.streaming_content)))
        self.assertIn("event: message", chunk)
        self.assertIn('"tools"', chunk)
        _remove_mcp_sse_session(session_id)

    def test_http_delete_closes_session(self):
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
        self.assertIsNone(_get_mcp_sse_session(session_id))

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
