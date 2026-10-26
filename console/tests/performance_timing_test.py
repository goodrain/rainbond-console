# -*- coding: utf-8 -*-
import json
import os
from types import SimpleNamespace
from unittest import TestCase, mock

from goodrain_web.performance import (PerformanceTimingMiddleware, get_performance_context, record_region_call)


class FakeResponse(dict):
    def __init__(self, status_code=200):
        super(FakeResponse, self).__init__()
        self.status_code = status_code


# capability_id: console.performance.response-timing
class PerformanceTimingMiddlewareTestCase(TestCase):
    def test_timing_header_aggregates_region_calls_with_logging_disabled(self):
        original_response = FakeResponse(status_code=201)
        original_response.content = b"unchanged response"

        def get_response(_request):
            record_region_call("GET", "https://region.example/private-component?credential=$TEST_SECRET", 200, 225.5)
            record_region_call("POST", "https://region.example/another-component", 200, 25.25)
            return original_response

        request = SimpleNamespace(
            method="GET", path="/console/teams/private-team", body=b"private body",
            META={"QUERY_STRING": "credential=$TEST_SECRET", "HTTP_AUTHORIZATION": "$TEST_AUTH"})
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 11.25]) as clock, \
                mock.patch("goodrain_web.performance.logger.info") as log_info:
            response = PerformanceTimingMiddleware(get_response)(request)

        self.assertIs(response, original_response)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content, b"unchanged response")
        self.assertEqual(response["Server-Timing"], "console_handler;dur=1250.000, region_http;dur=250.750")
        self.assertEqual(clock.call_count, 2)
        log_info.assert_not_called()
        self.assertIsNone(get_performance_context())

    def test_zero_region_timing_and_consecutive_requests_do_not_share_context(self):
        calls = []

        def get_response(_request):
            if not calls:
                record_region_call("GET", "https://region.example/first", 200, 10)
            calls.append(True)
            return FakeResponse()

        request = SimpleNamespace(method="GET", path="/api/teams", META={})
        middleware = PerformanceTimingMiddleware(get_response)
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[1.0, 1.125, 2.0, 2.25]):
            first = middleware(request)
            record_region_call("GET", "https://region.example/outside", 200, 1000)
            second = middleware(request)

        self.assertEqual(first["Server-Timing"], "console_handler;dur=125.000, region_http;dur=10.000")
        self.assertEqual(second["Server-Timing"], "console_handler;dur=250.000, region_http;dur=0.000")
        self.assertNotEqual(first["X-Request-ID"], second["X-Request-ID"])
        self.assertIsNone(get_performance_context())

    def test_non_api_response_is_not_instrumented(self):
        request = SimpleNamespace(method="GET", path="/", META={})
        original = FakeResponse()
        with mock.patch("goodrain_web.performance.time.monotonic") as clock:
            response = PerformanceTimingMiddleware(lambda _request: original)(request)
        self.assertIs(response, original)
        self.assertNotIn("Server-Timing", response)
        self.assertNotIn("X-Request-ID", response)
        clock.assert_not_called()
        self.assertIsNone(get_performance_context())

    def test_timing_does_not_iterate_streaming_body(self):
        chunks = []

        def content():
            chunks.append(True)
            yield b"stream chunk"

        original = FakeResponse()
        original.streaming_content = content()
        request = SimpleNamespace(method="GET", path="/console/logs", META={})
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[1.0, 1.125]):
            response = PerformanceTimingMiddleware(lambda _request: original)(request)
        self.assertEqual(response["Server-Timing"], "console_handler;dur=125.000, region_http;dur=0.000")
        self.assertEqual(chunks, [])
        self.assertIs(response.streaming_content, original.streaming_content)

    def test_timing_header_failure_does_not_break_business_response_or_context_reset(self):
        class UnavailableTimingHeaderResponse(FakeResponse):
            def __setitem__(self, key, value):
                if key == "Server-Timing":
                    raise RuntimeError("timing header unavailable")
                super().__setitem__(key, value)

        original = UnavailableTimingHeaderResponse()
        request = SimpleNamespace(method="GET", path="/console/teams", META={})
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[1.0, 1.125]):
            response = PerformanceTimingMiddleware(lambda _request: original)(request)
        self.assertIs(response, original)
        self.assertIsNone(get_performance_context())

    def test_slow_request_logs_sanitized_region_breakdown(self):
        def get_response(_request):
            record_region_call(
                "GET",
                "https://rbd-api-api:8443/v2/cluster/nodes?token=secret#fragment",
                200,
                225.5,
            )
            return FakeResponse()

        request = SimpleNamespace(
            method="GET",
            path="/console/enterprise/demo/regions",
            META={"QUERY_STRING": "check_status=yes&token=secret"},
        )

        with mock.patch.dict(os.environ, {
                "CONSOLE_PERFORMANCE_LOG_ENABLED": "true",
                "CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "500",
        }), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 11.25]), \
                mock.patch("goodrain_web.performance.logger.info") as log_info:
            response = PerformanceTimingMiddleware(get_response)(request)

        payload = json.loads(log_info.call_args.args[1])
        self.assertEqual(payload["event"], "console_request_timing")
        self.assertEqual(payload["path"], "/console/enterprise/demo/regions")
        self.assertNotIn("token", json.dumps(payload))
        self.assertEqual(payload["total_ms"], 1250.0)
        self.assertEqual(payload["region_call_count"], 1)
        self.assertEqual(payload["region_total_ms"], 225.5)
        self.assertEqual(payload["region_max_ms"], 225.5)
        self.assertEqual(payload["non_region_ms"], 1024.5)
        self.assertEqual(payload["region_calls"][0]["path"], "/v2/cluster/nodes")
        self.assertEqual(response["X-Request-ID"], payload["request_id"])
        self.assertIsNone(get_performance_context())

    def test_fast_request_does_not_write_performance_log(self):
        request = SimpleNamespace(method="GET", path="/console/teams", META={})

        with mock.patch.dict(os.environ, {
                "CONSOLE_PERFORMANCE_LOG_ENABLED": "true",
                "CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "500",
        }), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 10.1]), \
                mock.patch("goodrain_web.performance.logger.info") as log_info:
            response = PerformanceTimingMiddleware(lambda _request: FakeResponse())(request)

        log_info.assert_not_called()
        self.assertIn("X-Request-ID", response)
        self.assertIsNone(get_performance_context())

    def test_failed_request_is_logged_and_context_is_reset(self):
        def fail(_request):
            raise RuntimeError("boom")

        request = SimpleNamespace(method="GET", path="/console/teams", META={})

        with mock.patch.dict(os.environ, {
                "CONSOLE_PERFORMANCE_LOG_ENABLED": "true",
                "CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "500",
        }), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 10.1]), \
                mock.patch("goodrain_web.performance.logger.info") as log_info, \
                self.assertRaises(RuntimeError):
            PerformanceTimingMiddleware(fail)(request)

        payload = json.loads(log_info.call_args.args[1])
        self.assertEqual(payload["status"], 500)
        self.assertIsNone(get_performance_context())

    def test_logging_failure_does_not_break_request(self):
        request = SimpleNamespace(method="GET", path="/console/teams", META={})

        with mock.patch.dict(os.environ, {
                "CONSOLE_PERFORMANCE_LOG_ENABLED": "true",
                "CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "0",
        }), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 10.1]), \
                mock.patch("goodrain_web.performance.logger.info", side_effect=RuntimeError("log unavailable")):
            response = PerformanceTimingMiddleware(lambda _request: FakeResponse())(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(get_performance_context())

    def test_performance_log_is_disabled_by_default(self):
        request = SimpleNamespace(method="GET", path="/console/teams", META={})

        with mock.patch.dict(os.environ, {"CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "0"}, clear=True), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 10.1]), \
                mock.patch("goodrain_web.performance.logger.info") as log_info:
            response = PerformanceTimingMiddleware(lambda _request: FakeResponse())(request)

        log_info.assert_not_called()
        self.assertIn("X-Request-ID", response)
        self.assertIsNone(get_performance_context())
