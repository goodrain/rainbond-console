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


class AIEngineProxyServiceTests(SimpleTestCase):

    # capability_id: console.mcp.ai-engine-service

    def setUp(self):
        self.service = AIEngineProxyService()
        self.user = SimpleNamespace(user_id=1, enterprise_id="eid-1", is_enterprise_admin=False)
        self.team = SimpleNamespace(
            ID=11,
            tenant_id="tenant-id-1",
            tenant_name="team-a",
            enterprise_id="eid-1",
            namespace="trusted-namespace",
            creater=1,
        )
        self.region = SimpleNamespace(region_name="rainbond", enterprise_id="eid-1")
        patchers = (
            mock.patch(
                "console.services.ai_engine_service.team_services.get_enterprise_tenant_by_tenant_name",
                return_value=self.team,
            ),
            mock.patch(
                "console.services.ai_engine_service.region_services.get_enterprise_region_by_region_name",
                return_value=self.region,
            ),
            mock.patch(
                "console.services.ai_engine_service.team_repo.get_team_region_by_name",
                return_value=[SimpleNamespace(is_active=True, is_init=True)],
            ),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def args(self, **overrides):
        result = {"team_name": "team-a", "region_name": "rainbond"}
        result.update(overrides)
        return result

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_context_headers_and_plugin_name_are_server_owned(self, request):
        request.return_value = (200, {"code": 200, "msg": "success", "data": {"storage_mode": "pvc"}})

        result = self.service.get_capabilities(self.user, self.args())

        self.assertEqual("pvc", result["storage_mode"])
        call = request.call_args
        self.assertEqual("rainbond-ai-engine", call.args[2])
        self.assertEqual("/api/v1/ai-engine/deployment-capabilities", call.args[4])
        self.assertEqual(
            {
                "X-AI-Team-Name": "team-a",
                "X-AI-Region-Name": "rainbond",
                "X-AI-Team-Namespace": "trusted-namespace",
            }, call.kwargs["headers"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_cross_enterprise_team_is_rejected_before_region_call(self, request):
        with mock.patch("console.services.ai_engine_service.team_services.get_enterprise_tenant_by_tenant_name",
                        return_value=None):
            with self.assertRaises(ServiceHandleException) as ctx:
                self.service.get_capabilities(self.user, self.args(team_name="other-team"))

        self.assertEqual(404, ctx.exception.status_code)
        request.assert_not_called()

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_team_without_region_binding_is_rejected_before_region_call(self, request):
        with mock.patch("console.services.ai_engine_service.team_repo.get_team_region_by_name", return_value=[]):
            with self.assertRaises(ServiceHandleException) as ctx:
                self.service.get_capabilities(self.user, self.args())

        self.assertEqual(403, ctx.exception.status_code)
        request.assert_not_called()

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_inactive_team_region_binding_is_rejected_before_region_call(self, request):
        with mock.patch("console.services.ai_engine_service.team_repo.get_team_region_by_name",
                        return_value=[SimpleNamespace(is_active=False, is_init=False)]):
            with self.assertRaises(ServiceHandleException) as ctx:
                self.service.get_capabilities(self.user, self.args())

        self.assertEqual(403, ctx.exception.status_code)
        request.assert_not_called()

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_ai_engine_error_preserves_stable_code_and_safe_details(self, request):
        request.return_value = (400, {
            "code": 400,
            "msg": "reserved vLLM argument",
            "error_code": "vllm_extra_argv_reserved",
            "details": {
                "argument": "--model",
                "index": 3,
                "secret_value": "must-not-leak",
            },
        })

        with self.assertRaises(ServiceHandleException) as ctx:
            self.service.create_instance(
                self.user,
                self.args(
                    instance_name="demo",
                    model_key="model-key",
                    compute_mode="cpu",
                ),
            )

        self.assertEqual(400, ctx.exception.status_code)
        self.assertEqual("vllm_extra_argv_reserved", ctx.exception.error_code)
        self.assertEqual({"argument": "--model", "index": 3}, ctx.exception.details)

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_team_model_list_is_paginated_and_removes_internal_paths(self, request):
        request.return_value = (200, {
            "code": 200,
            "data": {
                "team_name":
                "team-a",
                "namespace":
                "trusted-namespace",
                "models": [
                    {
                        "model_key": "b",
                        "status": "ready",
                        "local_path": "/models/b"
                    },
                    {
                        "model_key": "a",
                        "status": "failed",
                        "local_path": "/models/a"
                    },
                    {
                        "model_key": "c",
                        "status": "ready",
                        "local_path": "/models/c"
                    },
                ],
            },
        })

        result = self.service.list_team_models(self.user, self.args(page=1, page_size=1, status="ready"))

        self.assertEqual(["b"], [item["model_key"] for item in result["items"]])
        self.assertEqual(2, result["total"])
        self.assertTrue(result["has_more"])
        self.assertNotIn("local_path", result["items"][0])
        self.assertNotIn("namespace", result)

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_instance_details_redact_sensitive_argv_and_internal_runtime_fields(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": [{
                    "instance_id": "inst-1",
                    "status": "Running"
                }]
            }),
            (200, {
                "code": 200,
                "data": {
                    "instance_id": "inst-1",
                    "namespace": "trusted-namespace",
                    "pod_name": "pod-secret-name",
                    "config": {
                        "runtime_image": "private.registry/runtime",
                        "env_vars": {
                            "TOKEN": "secret"
                        },
                        "dynamic_params": {
                            "extra_argv": ["--future-token", "top-secret", "--port=8000"],
                        },
                        "resolved_argv": ["vllm", "--api-key=abc", "--model", "/models/internal"],
                    },
                },
            }),
        ]

        result = self.service.get_instance(self.user, self.args(instance_id="inst-1"))

        self.assertNotIn("namespace", result)
        self.assertNotIn("pod_name", result)
        self.assertNotIn("runtime_image", result["config"])
        self.assertNotIn("env_vars", result["config"])
        self.assertEqual(
            ["--future-token", "***", "--port=8000"],
            result["config"]["dynamic_params"]["extra_argv"],
        )
        self.assertEqual(
            ["vllm", "--api-key=***", "--model", "***"],
            result["config"]["resolved_argv"],
        )

    def test_resolved_argv_redacts_positional_absolute_model_path(self):
        self.assertEqual(
            ["vllm", "serve", "***", "--served-model-name", "model-id"],
            self.service._redact_argv([
                "vllm",
                "serve",
                "/data/models/modelscope/private-model-path",
                "--served-model-name",
                "model-id",
            ]),
        )

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_instance_log_is_owned_before_fetch_and_redacted(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": [{
                    "instance_id": "inst-1"
                }]
            }),
            (200, {
                "code": 200,
                "data": {
                    "logs": "token=abc\nAuthorization: Bearer xyz\nready"
                }
            }),
        ]

        result = self.service.get_instance_logs(self.user, self.args(instance_id="inst-1", tail_lines=200))

        self.assertNotIn("abc", result["logs"])
        self.assertNotIn("xyz", result["logs"])
        self.assertIn("***", result["logs"])
        self.assertEqual("/api/v1/ai-engine/instances", request.call_args_list[0].args[4])
        self.assertEqual("/api/v1/ai-engine/instances/inst-1/logs", request.call_args_list[1].args[4])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_missing_instance_is_rejected_before_subresource_call(self, request):
        request.return_value = (200, {"code": 200, "data": [{"instance_id": "another"}]})

        with self.assertRaises(ServiceHandleException) as ctx:
            self.service.delete_instance(self.user, self.args(instance_id="inst-1"))

        self.assertEqual(404, ctx.exception.status_code)
        self.assertEqual(1, request.call_count)

    def test_modelscope_identity_normalization_rejects_unsupported_sources(self):
        accepted = {
            "Qwen/Qwen3-8B": "Qwen/Qwen3-8B",
            "https://modelscope.cn/models/Qwen/Qwen3-8B": "Qwen/Qwen3-8B",
            "https://www.modelscope.cn/models/Qwen/Qwen3-8B/": "Qwen/Qwen3-8B",
        }
        for value, expected in accepted.items():
            with self.subTest(value=value):
                self.assertEqual(expected, self.service.normalize_modelscope_model(value))

        rejected = (
            "/tmp/model",
            "file:///tmp/model",
            "https://huggingface.co/Qwen/Qwen3-8B",
            "https://github.com/Qwen/Qwen3-8B.git",
            "https://user:pass@modelscope.cn/models/Qwen/Qwen3-8B",
            "http://modelscope.cn/models/Qwen/Qwen3-8B",
            "https://modelscope.cn:444/models/Qwen/Qwen3-8B",
            "https://modelscope.cn/models/Qwen/Qwen3-8B?revision=main",
            "Qwen/Qwen3-8B/extra",
            "Qwen/Qwen3-8B.git",
        )
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(ServiceHandleException):
                self.service.normalize_modelscope_model(value)

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_create_model_download_normalizes_modelscope_and_returns_poll_contract(self, request):
        request.return_value = (200, {
            "code": 200,
            "data": {
                "job_name": "download-1",
                "model_key": "model-1",
                "status": "downloading"
            },
        })

        result = self.service.create_model_download(
            self.user,
            self.args(modelscope_model="https://modelscope.cn/models/Qwen/Qwen3-8B"),
        )

        body = request.call_args.kwargs["body"]
        self.assertEqual("modelscope", body["source_type"])
        self.assertEqual("Qwen/Qwen3-8B", body["source_uri"])
        self.assertNotIn("local_path", body)
        self.assertTrue(result["accepted"])
        self.assertEqual("rainbond_get_ai_engine_model_download", result["poll_tool"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_create_instance_uses_ready_verified_team_model_and_bounded_argv(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "model_key": "model-key",
                        "model_id": "model-id",
                        "status": "ready",
                        "source_type": "modelscope",
                        "engine_type": "vLLM",
                        "registry_check_status": "verified",
                        "metadata_consistency_status": "verified",
                    }],
                },
            }),
            (200, {
                "code": 200,
                "data": {
                    "instance_id": "inst-1",
                    "status": "Creating"
                }
            }),
        ]

        result = self.service.create_instance(
            self.user,
            self.args(
                instance_name="demo",
                model_key="model-key",
                compute_mode="gpu",
                gpu_count=2,
                dynamic_params={"tensor_parallel_size": 2},
                extra_argv=["--enable-future-feature"],
            ),
        )

        body = request.call_args_list[1].kwargs["body"]
        self.assertEqual("model-id", body["model_id"])
        self.assertEqual(2, body["resources"]["gpu_count"])
        self.assertEqual(["--enable-future-feature"], body["dynamic_params"]["extra_argv"])
        self.assertNotIn("runtime_image", body)
        self.assertNotIn("gpu_allocation", body["resources"])
        self.assertTrue(result["accepted"])

    def test_create_instance_rejects_extra_argv_over_sixteen_kib(self):
        with self.assertRaises(ServiceHandleException) as ctx:
            self.service.create_instance(
                self.user,
                self.args(
                    instance_name="demo",
                    model_key="model-key",
                    compute_mode="cpu",
                    extra_argv=["x" * 4096] * 5,
                ),
            )
        self.assertEqual("ai_engine_extra_argv_too_large", ctx.exception.error_code)

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_catalog_search_and_recommendations_keep_stable_collection_shapes(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "model_id": "Qwen/A"
                    }, {
                        "model_id": "Qwen/B"
                    }],
                    "total": 3,
                    "page": 1,
                    "page_size": 2,
                    "resource_meta": {
                        "source": "team_quota"
                    },
                },
            }),
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "model_id": "Qwen/A"
                    }, {
                        "model_id": "Qwen/B"
                    }],
                    "resource_meta": {
                        "source": "cluster_capacity"
                    },
                },
            }),
        ]

        catalog = self.service.search_model_catalog(self.user, self.args(keyword="Qwen", page=1, page_size=2))
        recommendations = self.service.list_model_recommendations(self.user, self.args(limit=1))

        self.assertEqual(3, catalog["total"])
        self.assertTrue(catalog["has_more"])
        self.assertEqual(["Qwen/A"], [item["model_id"] for item in recommendations["items"]])
        self.assertEqual("cluster_capacity", recommendations["resource_meta"]["source"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_get_model_and_download_filter_team_scoped_inventories(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "model_key": "model-1",
                        "status": "ready",
                        "local_path": "/internal"
                    }]
                },
            }),
            (200, {
                "code": 200,
                "data": {
                    "downloads": [{
                        "job_name": "job-1",
                        "model_key": "model-1",
                        "progress": 50
                    }]
                },
            }),
        ]

        model = self.service.get_team_model(self.user, self.args(model_key="model-1"))
        download = self.service.get_model_download(self.user, self.args(job_name="job-1"))

        self.assertEqual("model-1", model["model_key"])
        self.assertNotIn("local_path", model)
        self.assertEqual(50, download["progress"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_completed_download_falls_back_to_ready_team_model_record(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "downloads": []
                }
            }),
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "job_name": "job-complete",
                        "model_key": "modelscope:Qwen/Qwen3-0.6B",
                        "status": "ready",
                        "progress": 100,
                    }],
                },
            }),
        ]

        result = self.service.get_model_download(self.user, self.args(job_name="job-complete"))

        self.assertEqual("ready", result["status"])
        self.assertEqual(100, result["progress"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_completed_download_logs_use_team_model_for_ownership_fallback(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "downloads": []
                }
            }),
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "job_name": "job-complete",
                        "model_key": "model-1",
                        "status": "ready"
                    }]
                },
            }),
            (200, {
                "code": 200,
                "data": {
                    "logs": "download complete"
                }
            }),
        ]

        result = self.service.get_model_download_logs(self.user, self.args(job_name="job-complete", tail_lines=50))

        self.assertEqual("download complete", result["logs"])
        self.assertEqual(
            "/api/v1/ai-engine/team/downloads/job-complete/logs",
            request.call_args_list[2].args[4],
        )

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_create_model_download_resolves_builtin_catalog_metadata(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": {
                    "models": [{
                        "model_id": "Qwen/Qwen3-8B",
                        "source_uri": "Qwen/Qwen3-8B",
                        "display_name": "Qwen3 8B",
                        "default_engine": "vLLM",
                        "parameter_label": "8B",
                    }],
                    "total":
                    1,
                },
            }),
            (200, {
                "code": 200,
                "data": {
                    "job_name": "job-1",
                    "model_key": "model-1",
                    "status": "downloading"
                },
            }),
        ]

        result = self.service.create_model_download(self.user,
                                                    self.args(catalog_model_id="Qwen/Qwen3-8B", requested_revision="master"))

        body = request.call_args_list[1].kwargs["body"]
        self.assertEqual("Qwen/Qwen3-8B", body["model_id"])
        self.assertEqual("vLLM", body["engine_type"])
        self.assertEqual("8B", body["parameters"])
        self.assertEqual("master", body["requested_revision"])
        self.assertTrue(result["accepted"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_instance_list_filters_and_successful_delete_rechecks_ownership(self, request):
        inventory = (200, {
            "code":
            200,
            "data": [
                {
                    "instance_id": "inst-b",
                    "model_id": "m1",
                    "status": "Running"
                },
                {
                    "instance_id": "inst-a",
                    "model_id": "m1",
                    "status": "Stopped"
                },
                {
                    "instance_id": "inst-c",
                    "model_id": "m2",
                    "status": "Running"
                },
            ],
        })
        request.side_effect = [inventory, inventory, (200, {"code": 200, "data": None})]

        result = self.service.list_instances(self.user, self.args(page=1, page_size=1, status="Running", model_id="m1"))
        deleted = self.service.delete_instance(self.user, self.args(instance_id="inst-b"))

        self.assertEqual(["inst-b"], [item["instance_id"] for item in result["items"]])
        self.assertEqual(1, result["total"])
        self.assertTrue(deleted["deleted"])
        self.assertIs(deleted["cleanup_verified"], False)
        self.assertEqual("DELETE", request.call_args_list[2].args[3])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_invalid_upstream_envelopes_fail_closed(self, request):
        request.side_effect = [
            (200, "not-an-object"),
            (200, {
                "code": 200,
                "msg": "success"
            }),
        ]
        for expected_code in ("ai_engine_invalid_response", "ai_engine_invalid_response"):
            with self.assertRaises(ServiceHandleException) as ctx:
                self.service.get_capabilities(self.user, self.args())
            self.assertEqual(expected_code, ctx.exception.error_code)

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_instance_logs_forward_previous_since_and_preserve_unavailable(self, request):
        request.side_effect = [
            (200, {
                "code": 200,
                "data": [{
                    "instance_id": "inst-1"
                }]
            }),
            (200, {
                "code": 200,
                "data": {
                    "available": False,
                    "reason": "previous_log_unavailable",
                    "log_source": "previous",
                    "logs": "",
                    "tail_lines": 250,
                    "truncated": False,
                },
            }),
        ]

        result = self.service.get_instance_logs(
            self.user,
            self.args(instance_id="inst-1", tail_lines=250, previous=True, since_seconds=600),
        )

        self.assertEqual(
            {
                "available": False,
                "reason": "previous_log_unavailable",
                "log_source": "previous",
                "logs": "",
                "tail_lines": 250,
                "truncated": False,
            }, result)
        self.assertEqual({
            "tail_lines": 250,
            "previous": "true",
            "since_seconds": 600
        }, request.call_args_list[1].kwargs["query"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_deployment_and_events_keep_upstream_contract_but_remove_sensitive_fields(self, request):
        inventory = (200, {"code": 200, "data": [{"instance_id": "inst-1"}]})
        request.side_effect = [
            inventory,
            (200, {
                "code": 200,
                "data": {
                    "instance_id":
                    "inst-1",
                    "available":
                    True,
                    "status":
                    "Creating",
                    "current_stage":
                    "runtime_initialization",
                    "terminal":
                    False,
                    "stages": [{
                        "name": "runtime_initialization",
                        "status": "running",
                        "source": "runtime",
                        "safe_details": {
                            "reason": "loading"
                        },
                        "namespace": "must-not-leak",
                    }],
                    "failure":
                    None,
                    "poll_after_seconds":
                    5,
                },
            }),
            inventory,
            (200, {
                "code": 200,
                "data": {
                    "instance_id":
                    "inst-1",
                    "items": [{
                        "resource_type": "Pod",
                        "reason": "FailedMount",
                        "safe_message": "token=secret /var/lib/kubelet https://user:pass@example.com/x",
                        "severity": "warning",
                        "count": 1,
                        "first_seen": "2026-09-03T00:00:00Z",
                        "last_seen": "2026-09-03T00:01:00Z",
                        "source": "kubernetes",
                        "uid": "must-not-leak",
                    }],
                    "limit":
                    50,
                    "truncated":
                    False,
                    "namespace":
                    "must-not-leak",
                },
            }),
        ]

        deployment = self.service.get_instance_deployment(self.user, self.args(instance_id="inst-1"))
        events = self.service.list_instance_events(
            self.user,
            self.args(instance_id="inst-1", limit=50, since_seconds=1800),
        )

        self.assertEqual("runtime_initialization", deployment["current_stage"])
        self.assertTrue(deployment["available"])
        self.assertEqual(["name", "safe_details", "source", "status"], sorted(deployment["stages"][0]))
        encoded = str(events)
        for value in ("must-not-leak", "secret", "/var/lib/kubelet", "user:pass"):
            self.assertNotIn(value, encoded)
        self.assertEqual("FailedMount", events["items"][0]["reason"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_gpu_devices_and_timeseries_are_bounded_and_drop_raw_identifiers(self, request):
        devices = (200, {
            "code":
            200,
            "data": [{
                "device_id": "GPU-0",
                "uuid": "raw-uuid",
                "node_name": "gpu-node",
                "product_name": "RTX 3090",
                "memory_total_bytes": 24576,
                "memory_used_bytes": None,
                "utilization_rate": 0,
                "pod_name": "raw-pod",
            }],
        })
        points = [{"timestamp": index, "value": 0} for index in range(10)]
        request.side_effect = [
            devices,
            devices,
            (200, {
                "code": 200,
                "data": {
                    "device_id": "GPU-0",
                    "one_hour": {
                        "utilization_rate": points
                    }
                }
            }),
        ]

        listed = self.service.list_gpu_devices(self.user, self.args(page=1, page_size=20))
        series = self.service.get_gpu_device_timeseries(
            self.user,
            self.args(device_id="GPU-0", window="1h", max_points=3),
        )

        self.assertEqual(0, listed["items"][0]["utilization_rate"])
        self.assertIsNone(listed["items"][0]["memory_used_bytes"])
        self.assertNotIn("uuid", listed["items"][0])
        self.assertNotIn("pod_name", listed["items"][0])
        self.assertEqual(3, len(series["series"]["utilization_rate"]))
        self.assertTrue(series["truncated"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_gpu_bindings_and_usage_keep_provider_semantics_and_filter_foreign_instances(self, request):
        inventory = (200, {"code": 200, "data": [{"instance_id": "inst-1"}]})
        request.side_effect = [
            inventory,
            (200, {
                "code":
                200,
                "data": [{
                    "instance_id": "inst-1",
                    "provider": "hami",
                    "allocation_mode": "hami_shared_auto",
                    "request_unit": "hami_vgpu",
                    "memory_mib_per_gpu": 8192,
                    "physical_memory_mib_per_gpu": 24576,
                    "available_memory_mib_per_gpu": 16384,
                    "share_available": True,
                    "source": "real",
                }, {
                    "instance_id": "foreign",
                    "provider": "standard_nvidia",
                    "request_unit": "physical_gpu",
                }],
            }),
            inventory,
            (200, {
                "code":
                200,
                "data": [{
                    "instance_id": "inst-1",
                    "provider": "hami",
                    "allocation_mode": "hami_shared_auto",
                    "request_unit": "hami_vgpu",
                    "used_memory_bytes": 0,
                    "source": "real",
                }],
            }),
        ]

        bindings = self.service.list_gpu_instance_bindings(self.user, self.args(page=1, page_size=20))
        usage = self.service.list_gpu_instance_usage(self.user, self.args(page=1, page_size=20))

        self.assertEqual(["inst-1"], [item["instance_id"] for item in bindings["items"]])
        self.assertEqual("hami_vgpu", bindings["items"][0]["request_unit"])
        self.assertEqual(16384, bindings["items"][0]["available_memory_mib_per_gpu"])
        self.assertEqual(0, usage["items"][0]["used_memory_bytes"])
        self.assertEqual("real", usage["items"][0]["source"])

    @mock.patch("console.services.ai_engine_service.region_api.request_plugin_backend")
    def test_gpu_usage_preserves_explicit_unavailable_instead_of_zero(self, request):
        inventory = (200, {"code": 200, "data": [{"instance_id": "inst-1"}]})
        request.side_effect = [
            inventory,
            (200, {
                "code": 200,
                "data": [{
                    "instance_id": "inst-1",
                    "provider": "hami",
                    "allocation_mode": "hami_shared_auto",
                    "request_unit": "hami_vgpu",
                    "used_memory_bytes": None,
                    "available": False,
                    "unavailable_reason": "gpu_usage_unavailable",
                    "source": "unavailable",
                }],
            }),
        ]

        usage = self.service.list_gpu_instance_usage(self.user, self.args(page=1, page_size=20))

        self.assertIsNone(usage["items"][0]["used_memory_bytes"])
        self.assertFalse(usage["items"][0]["available"])
        self.assertEqual("gpu_usage_unavailable", usage["items"][0]["unavailable_reason"])
        self.assertEqual("unavailable", usage["items"][0]["source"])
