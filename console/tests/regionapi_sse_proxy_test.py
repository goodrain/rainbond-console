# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from www.apiclient.regionapi import RegionInvokeApi
import urllib3


class RegionApiSSEProxyTests(SimpleTestCase):

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    # capability_id: console.resource-center.pod-logs
    def test_sse_proxy_passes_region_auth_headers(self, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        region = Mock(url="http://region.example.com", token="region-token")
        mock_get_region_info.return_value = region
        client = Mock()
        response = Mock()
        response.stream.return_value = iter([b"chunk-1"])
        client.request.return_value = response
        mock_get_client.return_value = client

        http_response = api.sse_proxy("rainbond", "/v2/tenants/default/services/svc/logs")

        self.assertEqual(http_response["Content-Type"], "text/event-stream")
        _, kwargs = client.request.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "region-token")
        self.assertEqual(kwargs["url"], "http://region.example.com/v2/tenants/default/services/svc/logs")

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    # capability_id: console.region.sse-utf8-streaming
    def test_sse_proxy_decodes_utf8_characters_split_across_chunks(self, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        mock_get_region_info.return_value = Mock(url="http://region.example.com", token="region-token")
        character = "中".encode("utf-8")
        response = Mock()
        response.stream.return_value = iter([b"x" * 4094 + character[:2], character[2:] + b"\n"])
        client = Mock()
        client.request.return_value = response
        mock_get_client.return_value = client

        http_response = api.sse_proxy("rainbond", "/v2/logs")

        content = b"".join(http_response.streaming_content).decode("utf-8")
        self.assertEqual(content, "x" * 4094 + "中\n")

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    # capability_id: console.region.sse-utf8-streaming
    def test_sse_proxy_replaces_invalid_trailing_utf8_without_stopping_stream(
            self, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        mock_get_region_info.return_value = Mock(url="http://region.example.com", token="region-token")
        response = Mock()
        response.stream.return_value = iter([b"complete line\n", b"incomplete \xe4\xb8"])
        client = Mock()
        client.request.return_value = response
        mock_get_client.return_value = client

        http_response = api.sse_proxy("rainbond", "/v2/logs")

        content = b"".join(http_response.streaming_content).decode("utf-8")
        self.assertEqual(content, "complete line\nincomplete \ufffd")

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    # capability_id: console.region.sse-protocol-disconnect
    def test_sse_proxy_ends_cleanly_when_upstream_disconnects(self, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        mock_get_region_info.return_value = Mock(url="http://region.example.com", token="region-token")
        response = Mock()

        def interrupted_stream(_chunk_size):
            yield b"complete line\n"
            raise urllib3.exceptions.ProtocolError("Connection broken", "IncompleteRead")

        response.stream.side_effect = interrupted_stream
        client = Mock()
        client.request.return_value = response
        mock_get_client.return_value = client

        http_response = api.sse_proxy("rainbond", "/v2/logs")

        content = b"".join(http_response.streaming_content).decode("utf-8")
        self.assertEqual(content, "complete line\n")
        response.close.assert_called_once_with()

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    # capability_id: console.region.sse-read-timeout
    def test_sse_proxy_ends_cleanly_after_idle_read_timeout(self, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        mock_get_region_info.return_value = Mock(url="http://region.example.com", token="region-token")
        response = Mock()

        def timed_out_stream(_chunk_size):
            yield b"complete line\n"
            raise urllib3.exceptions.ReadTimeoutError(None, "/v2/logs", "Read timed out")

        response.stream.side_effect = timed_out_stream
        client = Mock()
        client.request.return_value = response
        mock_get_client.return_value = client

        http_response = api.sse_proxy("rainbond", "/v2/logs")

        content = b"".join(http_response.streaming_content).decode("utf-8")
        self.assertEqual(content, "complete line\n")
        response.close.assert_called_once_with()

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    @patch.object(RegionInvokeApi, "_RegionInvokeApi__get_tenant_region_info")
    # capability_id: console.resource-center.pod-logs
    def test_sse_proxy_rewrites_console_tenant_name_to_region_tenant_name(
            self, mock_get_tenant_region, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        region = Mock(url="http://region.example.com", token="region-token")
        tenant_region = Mock(region_tenant_name="region-default")
        mock_get_region_info.return_value = region
        mock_get_tenant_region.return_value = tenant_region
        client = Mock()
        response = Mock()
        response.stream.return_value = iter([b"chunk-1"])
        client.request.return_value = response
        mock_get_client.return_value = client

        api.sse_proxy("rainbond", "/v2/tenants/default/services/svc/pods/pod-1/logs?lines=100")

        _, kwargs = client.request.call_args
        self.assertEqual(
            kwargs["url"],
            "http://region.example.com/v2/tenants/region-default/services/svc/pods/pod-1/logs?lines=100",
        )

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    @patch.object(RegionInvokeApi, "_RegionInvokeApi__get_tenant_region_info")
    @patch.object(RegionInvokeApi, "_RegionInvokeApi__get_region_access_info")
    # capability_id: console.resource-center.pod-logs
    def test_get_component_pod_log_uses_bounded_read_timeout(
            self, mock_access_info, mock_get_tenant_region, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        region = Mock(url="http://region.example.com", token="region-token")
        tenant_region = Mock(region_tenant_name="region-default")
        mock_access_info.return_value = ("http://region.example.com", "region-token")
        mock_get_region_info.return_value = region
        mock_get_tenant_region.return_value = tenant_region
        client = Mock()
        response = Mock()
        client.request.return_value = response
        mock_get_client.return_value = client

        result = api.get_component_pod_log("default", "rainbond", "svc", "pod-1", lines=100, read_timeout=3)

        self.assertIs(result, response)
        _, kwargs = client.request.call_args
        self.assertEqual(
            kwargs["url"],
            "http://region.example.com/v2/tenants/region-default/services/svc/pods/pod-1/logs?lines=100",
        )
        self.assertEqual(kwargs["headers"]["Authorization"], "region-token")
        self.assertIsInstance(kwargs["timeout"], urllib3.Timeout)
        self.assertEqual(kwargs["timeout"].read_timeout, 3)

    @patch.object(RegionInvokeApi, "get_client")
    @patch.object(RegionInvokeApi, "get_region_info")
    @patch.object(RegionInvokeApi, "_RegionInvokeApi__get_tenant_region_info")
    @patch.object(RegionInvokeApi, "_RegionInvokeApi__get_region_access_info")
    # capability_id: console.resource-center.pod-logs
    def test_get_component_pod_log_supports_follow_query(
            self, mock_access_info, mock_get_tenant_region, mock_get_region_info, mock_get_client):
        api = RegionInvokeApi()
        region = Mock(url="http://region.example.com", token="region-token")
        tenant_region = Mock(region_tenant_name="region-default")
        mock_access_info.return_value = ("http://region.example.com", "region-token")
        mock_get_region_info.return_value = region
        mock_get_tenant_region.return_value = tenant_region
        client = Mock()
        response = Mock()
        client.request.return_value = response
        mock_get_client.return_value = client

        api.get_component_pod_log("default", "rainbond", "svc", "pod-1", lines=100, container_name="main", follow=False)

        _, kwargs = client.request.call_args
        self.assertEqual(
            kwargs["url"],
            "http://region.example.com/v2/tenants/region-default/services/svc/pods/pod-1/logs"
            "?lines=100&container=main&follow=false",
        )
