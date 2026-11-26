# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest import mock

from django.http import HttpResponse, StreamingHttpResponse
from django.test import SimpleTestCase
from django.urls import resolve
from rest_framework.test import APIRequestFactory

from console.exception.main import ServiceHandleException
from openapi.services.ai_engine_proxy_service import AIEngineProxyService
from openapi.views.ai_engine_proxy import AIEnginePublicProxyView, build_openai_error_response


class AIEngineProxyContractTests(SimpleTestCase):
    # capability_id: console.ai-engine.public-scope-protocol
    def setUp(self):
        self.service = AIEngineProxyService()
        self.team = SimpleNamespace(tenant_name="team-a", namespace="trusted-ns", enterprise_id="eid", tenant_id="tid")
        for method, value in (("_get_team", self.team), ("_get_candidate_regions", ["region-a"]), ("_region_has_ai_engine",
                                                                                                   True)):
            patcher = mock.patch.object(self.service, method, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.factory = APIRequestFactory()

    def test_credentials_accept_bearer_and_anthropic_but_reject_conflicts(self):
        for authorization, api_key, expected in (("Bearer key-a", None, "key-a"), (None, "key-b", "key-b"), ("Bearer key-a",
                                                                                                             "key-a", "key-a")):
            self.assertEqual(self.service.extract_api_key(authorization, api_key), expected)
        for authorization, api_key, status in ((None, None, 401), ("Basic a", None, 401), ("Bearer key-a", "key-b", 400),
                                               (None, "key\r\nb", 401)):
            with self.subTest(authorization=authorization), self.assertRaises(ServiceHandleException) as caught:
                self.service.extract_api_key(authorization, api_key)
            self.assertEqual(caught.exception.status_code, status)

    def test_messages_allowed_and_arbitrary_paths_rejected(self):
        self.assertEqual(self.service.validate_proxy_target("POST", "v1/messages"), "v1/messages")
        self.assertEqual(self.service.validate_proxy_target("POST", "v1/responses"), "v1/responses")
        for method, path in (("GET", "v1/messages"), ("POST", "api/v1/ai-engine/api-keys"), ("POST", "v1/../v1/messages")):
            with self.assertRaises(ServiceHandleException):
                self.service.validate_proxy_target(method, path)

    @mock.patch("www.apiclient.regionapi.RegionInvokeApi")
    def test_responses_selector_is_forwarded_as_untrusted_selection_not_scope(self, client):
        request = self.factory.post("/", {"model": "supplier-model"},
                                    format="json",
                                    HTTP_AUTHORIZATION="Bearer real-key",
                                    HTTP_X_AI_MODEL_API="api-explicit",
                                    HTTP_X_AI_TEAM_NAME="forged-team",
                                    HTTP_X_AI_REGION_NAME="forged-region")
        client.return_value.stream_proxy.return_value = HttpResponse(b"{}", content_type="application/json")
        self.service.proxy_request(request, "region-a", "v1/responses", team_name="team-a")
        args, kwargs = client.return_value.stream_proxy.call_args
        self.assertEqual(args[1], "/v2/platform/backend/plugins/rainbond-ai-engine/v1/responses")
        headers = kwargs["requests_args"]["headers"]
        self.assertEqual(headers["X-AI-Model-API"], "api-explicit")
        self.assertEqual(headers["X-AI-Team-Name"], "team-a")
        self.assertEqual(headers["X-AI-Region-Name"], "region-a")
        for selector in ("api-a,api-b", "api\r\nInjected:yes", "x" * 65, ""):
            request.META["HTTP_X_AI_MODEL_API"] = selector
            with self.assertRaises(ServiceHandleException):
                self.service.proxy_request(request, "region-a", "v1/responses", team_name="team-a")

    def test_explicit_region_requires_active_binding_and_plugin(self):
        self.assertEqual(self.service.resolve_region("team-a", "region-a"), "region-a")
        with self.assertRaises(ServiceHandleException) as caught:
            self.service.resolve_region("team-a", "region-other")
        self.assertEqual(caught.exception.status_code, 403)
        self.service._region_has_ai_engine.return_value = False
        with self.assertRaises(ServiceHandleException) as caught:
            self.service.resolve_region("team-a", "region-a")
        self.assertEqual(caught.exception.status_code, 404)

    def test_legacy_region_is_unique_and_does_not_keep_revoked_binding(self):
        self.assertEqual(self.service.resolve_unique_region("team-a"), "region-a")
        self.service._get_candidate_regions.return_value = ["region-a", "region-b"]
        with self.assertRaises(ServiceHandleException) as caught:
            self.service.resolve_unique_region("team-a")
        self.assertEqual(caught.exception.status_code, 409)
        self.service._get_candidate_regions.return_value = []
        with self.assertRaises(ServiceHandleException):
            self.service.resolve_unique_region("team-a")

    def test_legacy_region_does_not_assume_uniqueness_when_another_probe_fails(self):
        self.service._get_candidate_regions.return_value = ["region-a", "region-b"]
        self.service._region_has_ai_engine.side_effect = [True, RuntimeError("region unavailable")]
        with self.assertRaises(ServiceHandleException) as caught:
            self.service.resolve_unique_region("team-a")
        self.assertEqual(caught.exception.status_code, 502)

    @mock.patch("www.apiclient.regionapi.RegionInvokeApi")
    def test_proxy_streams_with_trusted_scope_original_credential_and_no_replay(self, client):
        request = self.factory.post("/", {"stream": True},
                                    format="json",
                                    HTTP_X_API_KEY="real-key",
                                    HTTP_X_ORIGINAL_AUTHORIZATION="forged",
                                    HTTP_X_AI_TEAM_NAME="foreign",
                                    HTTP_X_AI_ACTOR_ID="admin",
                                    HTTP_X_HIGRESS_CONSUMER="forged")
        expected = StreamingHttpResponse(iter([b"data: x\n\n"]), content_type="text/event-stream")
        client.return_value.stream_proxy.return_value = expected
        result = self.service.proxy_request(request, "region-a", "v1/messages", "trace=1", team_name="team-a")
        self.assertIs(result, expected)
        args, kwargs = client.return_value.stream_proxy.call_args
        self.assertEqual(args[1:], ("/v2/platform/backend/plugins/rainbond-ai-engine/v1/messages?trace=1", "region-a"))
        self.assertEqual(
            kwargs["requests_args"]["headers"], {
                "X-AI-Team-Name": "team-a",
                "X-AI-Region-Name": "region-a",
                "X-AI-Team-Namespace": "trusted-ns",
                "X-Original-Authorization": "Bearer real-key",
                "x-api-key": "real-key",
            })
        self.assertIs(kwargs["requests_args"]["retries"], False)
        self.assertIsNone(kwargs["timeout"].read_timeout)
        expected.close()

    @mock.patch("www.apiclient.regionapi.RegionInvokeApi")
    def test_streaming_region_transport_error_gets_protocol_error_without_masking_origin_errors(self, client):
        request = self.factory.post("/", HTTP_AUTHORIZATION="Bearer real-key")
        region_error = StreamingHttpResponse(
            iter([b'{"code":502,"msg":"plugin backend unavailable: EOF","plugin":"rainbond-ai-engine"}']),
            status=502, content_type="application/json")
        client.return_value.stream_proxy.return_value = region_error
        with self.assertRaises(ServiceHandleException) as caught:
            self.service.proxy_request(request, "region-a", "v1/messages", team_name="team-a")
        self.assertEqual(caught.exception.status_code, 502)
        self.assertTrue(region_error.closed)
        origin = StreamingHttpResponse(iter([b'{"error":', b'{"message":"overloaded"}}']),
                                       status=502, content_type="application/json")
        client.return_value.stream_proxy.return_value = origin
        result = self.service.proxy_request(request, "region-a", "v1/messages", team_name="team-a")
        self.assertEqual(b"".join(result.streaming_content), b'{"error":{"message":"overloaded"}}')
        result.close()

    @mock.patch("www.apiclient.regionapi.RegionInvokeApi")
    def test_real_status_and_protocol_response_are_preserved(self, client):
        for status in (401, 403, 409, 429, 502, 503, 504):
            expected = HttpResponse(b'{"error":{"message":"upstream"}}', status=status, content_type="application/json")
            client.return_value.stream_proxy.return_value = expected
            request = self.factory.post("/", HTTP_AUTHORIZATION="Bearer real-key")
            self.assertIs(self.service.proxy_request(request, "region-a", "v1/messages", team_name="team-a"), expected)

    @mock.patch("www.apiclient.regionapi.RegionInvokeApi")
    def test_error_inspection_is_bounded_and_never_consumes_sse(self, client):
        request = self.factory.post("/", HTTP_AUTHORIZATION="Bearer real-key")
        for payload, content_type in ((b"x" * (70 * 1024), "application/json"), (b"data: error\n\n", "text/event-stream")):
            reads = []

            def body():
                reads.append(True)
                yield payload

            upstream = StreamingHttpResponse(body(), status=502, content_type=content_type)
            client.return_value.stream_proxy.return_value = upstream
            result = self.service.proxy_request(request, "region-a", "v1/messages", team_name="team-a")
            if content_type == "text/event-stream":
                self.assertFalse(reads)
            self.assertEqual(b"".join(result.streaming_content), payload)
            result.close()

    def test_url_resolves_explicit_region_before_legacy_wildcard(self):
        match = resolve("/openapi/v1/ai-engine/team-a/regions/region-b/v1/messages")
        self.assertEqual(match.kwargs, {"team_name": "team-a", "region_name": "region-b", "proxy_path": "v1/messages"})
        legacy = resolve("/openapi/v1/ai-engine/team-a/v1/chat/completions")
        self.assertNotIn("region_name", legacy.kwargs)

    def test_view_accepts_anthropic_and_explicit_region(self):
        request = self.factory.post("/", {}, format="json", HTTP_X_API_KEY="real-key")
        response = HttpResponse("ok")
        with mock.patch("openapi.views.ai_engine_proxy.ai_engine_proxy_service", self.service), \
                mock.patch.object(self.service, "proxy_request", return_value=response) as proxy:
            result = AIEnginePublicProxyView.as_view()(request,
                                                       team_name="team-a",
                                                       region_name="region-a",
                                                       proxy_path="v1/messages")
        self.assertIs(result, response)
        self.assertEqual(proxy.call_args.kwargs["team_name"], "team-a")

    def test_messages_local_errors_use_anthropic_shape(self):
        response = AIEnginePublicProxyView.as_view()(self.factory.post("/"), team_name="team-a", proxy_path="v1/messages")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["type"], "error")
        self.assertEqual(response.data["error"]["type"], "authentication_error")
        self.assertEqual(build_openai_error_response("unavailable", 502).data["error"]["type"], "server_error")
