# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import SimpleTestCase  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.ai_engine_service import AIEngineProxyService  # noqa: E402


class AIEngineSecurityAndResponseTests(SimpleTestCase):

    # capability_id: console.mcp.ai-engine-security

    def setUp(self):
        self.service = AIEngineProxyService()
        self.user = SimpleNamespace(user_id=1, enterprise_id="eid-1", is_enterprise_admin=False)
        self.team = SimpleNamespace(
            tenant_id="tenant-1",
            tenant_name="team-a",
            enterprise_id="eid-1",
            namespace="team-a-ns",
            creater=1,
        )
        self.patchers = [
            mock.patch(
                "console.services.ai_engine_service.team_services.get_enterprise_tenant_by_tenant_name",
                return_value=self.team,
            ),
            mock.patch(
                "console.services.ai_engine_service.region_services.get_enterprise_region_by_region_name",
                return_value=SimpleNamespace(region_name="rainbond", enterprise_id="eid-1"),
            ),
            mock.patch(
                "console.services.ai_engine_service.team_repo.get_team_region_by_name",
                return_value=[SimpleNamespace(is_active=True, is_init=True)],
            ),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def args(**overrides):
        values = {"team_name": "team-a", "region_name": "rainbond"}
        values.update(overrides)
        return values

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_monitoring_preserves_unavailable_null_and_real_zero_metrics(self, request):
        request.return_value = (200, {
            "code": 200,
            "data": {
                "window": "15m",
                "output_tokens_per_second": None,
                "failed_requests": 0,
                "queue": {
                    "available": False,
                    "count": None,
                    "source": "unavailable"
                },
                "memory": {
                    "used_bytes": 0,
                    "source": "real"
                },
            },
        })

        result = self.service.get_monitoring_overview(self.user, self.args())

        self.assertIsNone(result["output_tokens_per_second"])
        self.assertEqual(0, result["failed_requests"])
        self.assertIs(result["queue"]["available"], False)
        self.assertIsNone(result["queue"]["count"])
        self.assertEqual(0, result["memory"]["used_bytes"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_registry_error_prefix_is_normalized_without_inventing_codes(self, request):
        request.side_effect = [
            (400, {
                "code": 400,
                "msg": "registry_rate_limited: retry later"
            }),
            (422, {
                "code": 422,
                "msg": "some changing human message"
            }),
        ]

        with self.assertRaises(ServiceHandleException) as stable:
            self.service.get_capabilities(self.user, self.args())
        with self.assertRaises(ServiceHandleException) as fallback:
            self.service.get_capabilities(self.user, self.args())

        self.assertEqual("registry_rate_limited", stable.exception.error_code)
        self.assertEqual("ai_engine_http_422", fallback.exception.error_code)

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_error_text_redacts_sensitive_argv_values(self, request):
        request.return_value = (400, {
            "code": 400,
            "msg": "invalid --future-token secret-value and --api-key=another-secret",
            "error_code": "vllm_extra_argv_conflict",
        })

        with self.assertRaises(ServiceHandleException) as ctx:
            self.service.get_capabilities(self.user, self.args())

        self.assertNotIn("secret-value", ctx.exception.msg)
        self.assertNotIn("another-secret", ctx.exception.msg)
        self.assertIn("--future-token ***", ctx.exception.msg)
        self.assertIn("--api-key=***", ctx.exception.msg)

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_resource_capacity_does_not_expose_raw_kubernetes_node_fields(self, request):
        request.return_value = (200, {
            "code": 200,
            "data": {
                "gpu_available":
                False,
                "resource_capacity": {
                    "cpu": {
                        "available": 0,
                        "source": "team_quota"
                    }
                },
                "nodes": [{
                    "name": "node-a",
                    "architecture": "amd64",
                    "gpu_count": 0,
                    "labels": {
                        "secret-label": "value"
                    },
                    "annotations": {
                        "credential": "value"
                    },
                    "taints": [{
                        "key": "private"
                    }],
                }],
            },
        })

        result = self.service.get_resource_capacity(self.user, self.args())

        self.assertIs(result["gpu_available"], False)
        self.assertEqual(0, result["resource_capacity"]["cpu"]["available"])
        self.assertEqual({"name": "node-a", "architecture": "amd64", "gpu_count": 0}, result["nodes"][0])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_team_model_list_removes_nested_registry_readme(self, request):
        request.return_value = (200, {
            "code": 200,
            "data": {
                "models": [{
                    "model_key": "model-1",
                    "status": "ready",
                    "registry_claims": {
                        "model_id": "Qwen/Qwen3-1.7B",
                        "readme": "large internal README",
                    },
                }],
            },
        })

        result = self.service.list_team_models(self.user, self.args(page=1, page_size=20))

        self.assertNotIn("readme", result["items"][0]["registry_claims"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_update_state_checks_team_ownership_before_put(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": [{
                    "instance_id": "inst-1"
                }]
            }),
            (200, {
                "code": 200,
                "data": None
            }),
        ]

        result = self.service.update_instance_state(self.user, self.args(instance_id="inst-1", target_state="Stopped"))

        self.assertTrue(result["accepted"])
        self.assertEqual("GET", request.call_args_list[0].args[3])
        self.assertEqual("PUT", request.call_args_list[1].args[3])
        self.assertEqual({"target_state": "Stopped"}, request.call_args_list[1].kwargs["body"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_delete_team_model_checks_team_inventory_before_delete(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "model_key": "model-1",
                        "status": "ready"
                    }]
                }
            }),
            (200, {
                "code": 200,
                "data": None
            }),
        ]

        result = self.service.delete_team_model(self.user, self.args(model_key="model-1"))

        self.assertEqual({"deleted": True, "model_key": "model-1"}, result)
        self.assertEqual("GET", request.call_args_list[0].args[3])
        self.assertEqual("DELETE", request.call_args_list[1].args[3])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_download_logs_validate_job_ownership_and_enforce_output_limit(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "downloads": [{
                        "job_name": "job-1"
                    }]
                }
            }),
            (200, {
                "code": 200,
                "data": {
                    "logs": "a" * (70 * 1024) + "\npassword=secret"
                }
            }),
        ]

        result = self.service.get_model_download_logs(self.user, self.args(job_name="job-1", tail_lines=1000))

        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["logs"].encode("utf-8")), 64 * 1024)
        self.assertNotIn("secret", result["logs"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_catalog_detail_encodes_segments_and_omits_readme(self, request):
        request.return_value = (200, {
            "code": 200,
            "data": {
                "model_id": "Qwen/模型 7B",
                "readme": "very large",
                "license": "apache-2.0"
            },
        })

        result = self.service.get_model_catalog_detail(self.user, self.args(owner="Qwen", repo_name="模型 7B"))

        self.assertNotIn("readme", result)
        self.assertIn("%E6%A8%A1%E5%9E%8B%207B", request.call_args.args[4])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_model_download_requires_exactly_one_supported_source(self, request):
        invalid_arguments = (
            self.args(),
            self.args(catalog_model_id="Qwen/Qwen3", modelscope_model="Qwen/Qwen3"),
            self.args(modelscope_model="/Users/me/model"),
            self.args(modelscope_model="https://example.com/model.bin"),
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments), self.assertRaises(ServiceHandleException):
                self.service.create_model_download(self.user, arguments)
        request.assert_not_called()
