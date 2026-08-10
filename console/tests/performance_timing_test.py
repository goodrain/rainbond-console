# -*- coding: utf-8 -*-
import json
import os
from types import SimpleNamespace
from unittest import TestCase, mock

from goodrain_web.performance import (PerformanceTimingMiddleware, get_performance_context,
                                      record_region_call)


class FakeResponse(dict):
    def __init__(self, status_code=200):
        super(FakeResponse, self).__init__()
        self.status_code = status_code


class PerformanceTimingMiddlewareTestCase(TestCase):
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

        with mock.patch.dict(os.environ, {"CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "500"}), \
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

        with mock.patch.dict(os.environ, {"CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "500"}), \
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

        with mock.patch.dict(os.environ, {"CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "500"}), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 10.1]), \
                mock.patch("goodrain_web.performance.logger.info") as log_info, \
                self.assertRaises(RuntimeError):
            PerformanceTimingMiddleware(fail)(request)

        payload = json.loads(log_info.call_args.args[1])
        self.assertEqual(payload["status"], 500)
        self.assertIsNone(get_performance_context())

    def test_logging_failure_does_not_break_request(self):
        request = SimpleNamespace(method="GET", path="/console/teams", META={})

        with mock.patch.dict(os.environ, {"CONSOLE_SLOW_REQUEST_THRESHOLD_MS": "0"}), \
                mock.patch("goodrain_web.performance.time.monotonic", side_effect=[10.0, 10.1]), \
                mock.patch("goodrain_web.performance.logger.info", side_effect=RuntimeError("log unavailable")):
            response = PerformanceTimingMiddleware(lambda _request: FakeResponse())(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(get_performance_context())
