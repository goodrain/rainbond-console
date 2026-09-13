# -*- coding: utf-8 -*-
import json
import os
import sys
from types import ModuleType
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import SimpleTestCase  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


class AIEngineRegionClientTests(SimpleTestCase):

    # capability_id: console.mcp.ai-engine-region-client

    def setUp(self):
        self.client = RegionInvokeApi()
        self.access = mock.patch.object(
            self.client,
            "_RegionInvokeApi__get_region_access_info_by_enterprise_id",
            return_value=("https://region.example", "region-token"),
        )
        self.access_mock = self.access.start()
        self.addCleanup(self.access.stop)

    def test_request_plugin_backend_encodes_query_and_json_body(self):
        with mock.patch.object(
                self.client,
                "_request",
                return_value=(202, json.dumps({
                    "code": 202,
                    "data": {
                        "ok": True
                    }
                }).encode("utf-8")),
        ) as request:
            status, body = self.client.request_plugin_backend(
                "eid-1",
                "rainbond",
                "rainbond-ai-engine",
                "POST",
                "/api/v1/ai-engine/team/models/downloads",
                query={
                    "keyword": "Qwen/模型 & 7B",
                    "tag": ["a", "b"]
                },
                body={"source_uri": "Qwen/Qwen3-8B"},
                headers={
                    "X-AI-Team-Name": "team-a",
                    "X-AI-Region-Name": "rainbond",
                    "X-AI-Team-Namespace": "team-a-ns",
                },
                timeout=15,
            )

        self.assertEqual(202, status)
        self.assertEqual({"code": 202, "data": {"ok": True}}, body)
        kwargs = request.call_args.kwargs
        self.assertIn("keyword=Qwen%2F%E6%A8%A1%E5%9E%8B+%26+7B", request.call_args.args[0])
        self.assertIn("tag=a&tag=b", request.call_args.args[0])
        self.assertEqual("POST", request.call_args.args[1])
        self.assertEqual({"source_uri": "Qwen/Qwen3-8B"}, json.loads(kwargs["body"]))
        self.assertEqual(15, kwargs["timeout"])
        self.assertEqual(5, kwargs["connect_timeout"])
        self.assertEqual("team-a", kwargs["headers"]["X-AI-Team-Name"])

    def test_request_plugin_backend_preserves_error_status_and_body(self):
        upstream = {
            "code": 400,
            "msg": "reserved argument",
            "error_code": "vllm_extra_argv_reserved",
            "details": {
                "argument": "--model"
            },
        }
        with mock.patch.object(self.client, "_request", return_value=(400, json.dumps(upstream).encode("utf-8"))):
            status, body = self.client.request_plugin_backend("eid-1", "rainbond", "rainbond-ai-engine", "GET",
                                                              "/api/v1/ai-engine/instances")

        self.assertEqual(400, status)
        self.assertEqual(upstream, body)

    def test_request_plugin_backend_rejects_unsafe_methods_before_transport(self):
        with mock.patch.object(self.client, "_request") as request:
            with self.assertRaises(ServiceHandleException):
                self.client.request_plugin_backend("eid-1", "rainbond", "rainbond-ai-engine", "PATCH",
                                                   "/api/v1/ai-engine/instances")
        request.assert_not_called()

    def test_request_plugin_backend_rejects_absolute_and_traversal_paths(self):
        paths = (
            "https://attacker.example/steal",
            "//attacker.example/steal",
            "/api/v1/ai-engine/../secrets",
            "/api/v1/ai-engine/instances?token=leak",
            "/api/v1/ai-engine/instances#fragment",
        )
        for path in paths:
            with self.subTest(path=path), self.assertRaises(ServiceHandleException):
                self.client.request_plugin_backend("eid-1", "rainbond", "rainbond-ai-engine", "GET", path)

    def test_request_plugin_backend_rejects_unapproved_headers(self):
        with self.assertRaises(ServiceHandleException):
            self.client.request_plugin_backend(
                "eid-1",
                "rainbond",
                "rainbond-ai-engine",
                "GET",
                "/api/v1/ai-engine/instances",
                headers={"Authorization": "attacker-controlled"},
            )
