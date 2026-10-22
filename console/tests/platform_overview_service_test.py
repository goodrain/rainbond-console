# -*- coding: utf-8 -*-
import base64
import collections
import datetime
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock
from urllib.parse import parse_qs

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module = ModuleType("openapi_client.configuration")
    configuration_module.Configuration = type("Configuration", (), {})
    rest_module = ModuleType("openapi_client.rest")
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.platform_overview_service import PlatformOverviewService  # noqa: E402
from console.services.platform_plugin_service import PlatformPluginService  # noqa: E402
from console.services import platform_plugin_service as platform_plugin_module  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402
from console.services import platform_overview_service as overview_module  # noqa: E402
from django.conf import settings  # noqa: E402
from django.test import override_settings  # noqa: E402

# capability_id: console.platform-overview.aggregate

REGION = SimpleNamespace(
    region_id="region-id",
    region_name="region-a",
    region_alias="Region A",
    status="1",
    provider="kubernetes",
    create_time=None,
)


class MemoryCache(object):
    def __init__(self):
        self.values = {}
        self.set_calls = []

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, timeout=None):
        self.values[key] = value
        self.set_calls.append((key, timeout))


class PlatformOverviewServiceTest(TestCase):
    def setUp(self):
        self.region_api = mock.Mock()
        self.service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=self.region_api)

    def test_runtime_uses_isolated_region_clients_under_overlap(self):
        barrier = threading.Barrier(2)
        records = []
        instances = []

        class OverlappingRegionApi(object):
            def __init__(self):
                self.default_headers = {}
                instances.append(self)

            def get_cluster_nodes(self, region_name, **kwargs):
                return {"status": 200}, {"list": []}

            def get_enterprise_running_services(self, enterprise_id, region_name, **kwargs):
                token = "token-a" if region_name == "region-a" else "token-b"
                self.default_headers["Authorization"] = token
                barrier.wait(timeout=1)
                records.append(("https://{}/running-services".format(region_name), self.default_headers["Authorization"]))
                return {"service_ids": []}

            def get_user_service_abnormal_status(self, region_name, enterprise_id, **kwargs):
                return {"service_ids": []}

        service = PlatformOverviewService(cache_backend=MemoryCache(), region_api_factory=OverlappingRegionApi)
        region_b = SimpleNamespace(**dict(REGION.__dict__, region_name="region-b", region_id="region-b-id"))

        result = service._fetch_runtime_regions("eid", [REGION, region_b])

        self.assertEqual("token-a", dict(records)["https://region-a/running-services"])
        self.assertEqual("token-b", dict(records)["https://region-b/running-services"])
        self.assertEqual(6, len(instances))
        self.assertIsNot(instances[0], instances[1])
        self.assertEqual("ok", result["region-a"]["status"])
        self.assertEqual("ok", result["region-b"]["status"])

    def test_shell_uses_database_counts_without_region_calls(self):
        counts = {"clusters": 1, "teams": 2, "users": 3, "applications": 4, "components": 5}
        with mock.patch.object(self.service, "_list_region_records", return_value=[REGION]), \
                mock.patch.object(self.service, "_database_counts", return_value=counts), \
                mock.patch.object(self.service, "_region_api") as region_api:
            result = self.service.get_shell("eid")

        self.assertEqual("ok", result["status"])
        self.assertEqual(counts, result["global"])
        self.assertEqual("region-a", result["clusters"][0]["region_name"])
        self.assertFalse(region_api.mock_calls)

    def test_runtime_degrades_failed_region_and_uses_cache(self):
        region_b = SimpleNamespace(**dict(REGION.__dict__, region_id="region-b-id", region_name="region-b"))
        self.service._list_region_records = mock.Mock(return_value=[REGION, region_b])
        self.service._database_workload_counts = mock.Mock(return_value={"applications": 4, "components": 8})
        self.service._fetch_runtime_regions = mock.Mock(
            return_value={
                "region-a": {
                    "status": "ok",
                    "data": {
                        "region_name": "region-a",
                        "nodes": {
                            "total": 2,
                            "ready": 2,
                            "certificate_status": "ok"
                        },
                        "running_service_ids": ["s1", "s2"],
                        "abnormal_service_ids": [],
                        "workloads_status": "ok",
                        "alarms_status": "ok",
                        "status": "ok",
                    },
                },
                "region-b": {
                    "status": "unavailable",
                    "data": None,
                },
            })
        self.service._database_running_workload_counts = mock.Mock(return_value={"applications": 1, "components": 2})

        first = self.service.get_runtime("eid")
        second = self.service.get_runtime("eid")

        self.assertEqual("partial", first["status"])
        self.assertEqual(1, first["global"]["clusters"]["healthy"])
        self.assertEqual(1, first["global"]["clusters"]["unavailable"])
        self.assertEqual(2, first["global"]["nodes"]["ready"])
        self.assertEqual(2, first["global"]["components"]["running"])
        self.assertEqual(first, second)
        self.service._fetch_runtime_regions.assert_called_once_with("eid", [REGION, region_b])
        self.assertEqual([("platform-overview:runtime:eid", 15)], self.service._cache.set_calls)

    def test_zero_enterprise_shell_and_runtime_do_not_call_region(self):
        counts = {"clusters": 0, "teams": 0, "users": 0, "applications": 0, "components": 0}
        self.service._list_region_records = mock.Mock(return_value=[])
        self.service._database_counts = mock.Mock(return_value=counts)
        self.service._database_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_running_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_application_alerts = mock.Mock(return_value=[])
        self.service._fetch_region_runtime = mock.Mock()

        shell = self.service.get_shell("empty")
        runtime = self.service.get_runtime("empty")

        self.assertEqual(counts, shell["global"])
        self.assertEqual([], shell["clusters"])
        self.assertEqual(0, runtime["global"]["clusters"]["total"])
        self.assertEqual("ok", runtime["status"])
        self.service._fetch_region_runtime.assert_not_called()

    def test_runtime_keeps_node_data_when_optional_alarm_call_fails(self):
        self.service._fetch_nodes = mock.Mock(return_value={"total": 2, "ready": 2})
        self.service._region_api.get_enterprise_running_services = mock.Mock(return_value={"service_ids": ["s1"]})
        self.service._region_api.get_user_service_abnormal_status = mock.Mock(side_effect=RuntimeError("not supported"))

        result = self.service._fetch_region_runtime("eid", REGION)

        self.assertEqual("partial", result["status"])
        self.assertEqual({"total": 2, "ready": 2}, result["nodes"])
        self.assertEqual("ok", result["workloads_status"])
        self.assertEqual("unavailable", result["alarms_status"])

    def test_runtime_marks_none_region_payloads_unavailable_and_uses_five_second_deadline(self):
        self.service._fetch_nodes = mock.Mock(return_value={"total": 2, "ready": 2})
        self.service._region_api.get_enterprise_running_services = mock.Mock(return_value=None)
        self.service._region_api.get_user_service_abnormal_status = mock.Mock(return_value=None)

        result = self.service._fetch_region_runtime("eid", REGION)

        self.assertEqual("partial", result["status"])
        self.assertEqual("unavailable", result["workloads_status"])
        self.assertEqual("unavailable", result["alarms_status"])
        self.service._region_api.get_enterprise_running_services.assert_called_once_with("eid",
                                                                                         "region-a",
                                                                                         test=False,
                                                                                         connect_timeout=2,
                                                                                         timeout=3,
                                                                                         retries=0)
        self.service._region_api.get_user_service_abnormal_status.assert_called_once_with("region-a",
                                                                                          "eid",
                                                                                          connect_timeout=2,
                                                                                          timeout=3,
                                                                                          retries=0)

    def test_region_runtime_calls_fan_out_concurrently(self):
        def delayed(value):
            time.sleep(0.08)
            return value

        self.service._fetch_nodes = mock.Mock(side_effect=lambda *_args, **_kwargs: delayed({"total": 1, "ready": 1}))
        self.service._region_api.get_enterprise_running_services = mock.Mock(
            side_effect=lambda *_args, **_kwargs: delayed({"service_ids": ["s1"]}))
        self.service._region_api.get_user_service_abnormal_status = mock.Mock(
            side_effect=lambda *_args, **_kwargs: delayed({"service_ids": []}))

        started = time.monotonic()
        result = self.service._fetch_region_runtime("eid", REGION)
        elapsed = time.monotonic() - started

        self.assertEqual("ok", result["status"])
        self.assertLess(elapsed, 0.18)

    def test_run_sections_returns_at_deadline_without_waiting_for_late_task(self):
        release = threading.Event()

        def late_call():
            release.wait(0.3)
            return "late"

        started = time.monotonic()
        sections = self.service._run_sections({"fast": lambda: "done", "late": late_call}, max_workers=2, timeout_seconds=0.04)
        elapsed = time.monotonic() - started
        release.set()

        self.assertLess(elapsed, 0.15)
        self.assertEqual({"status": "ok", "data": "done"}, sections["fast"])
        self.assertEqual({"status": "unavailable", "data": None}, sections["late"])

    def test_runtime_overall_deadline_returns_partial_without_waiting(self):
        release = threading.Event()
        self.service.SECTION_DEADLINE_SECONDS = 0.04
        self.service._list_region_records = mock.Mock(return_value=[REGION])
        self.service._fetch_nodes = mock.Mock(side_effect=lambda *_args: release.wait(0.3))
        self.service._fetch_running_service_ids = mock.Mock(return_value=[])
        self.service._fetch_abnormal_service_ids = mock.Mock(return_value=[])
        self.service._database_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_running_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_application_alerts = mock.Mock(return_value=[])

        started = time.monotonic()
        result = self.service.get_runtime("eid")
        elapsed = time.monotonic() - started
        release.set()

        self.assertLess(elapsed, 0.15)
        self.assertEqual("partial", result["status"])
        self.assertEqual("unavailable", result["regions"][0]["status"])

    def test_runtime_region_fanout_is_bounded_to_eight_workers(self):
        lock = threading.Lock()
        active = [0]
        peak = [0]

        def observed(value):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.03)
            with lock:
                active[0] -= 1
            return value

        regions = [SimpleNamespace(**dict(REGION.__dict__, region_name="region-{}".format(index))) for index in range(4)]
        self.service._fetch_nodes = mock.Mock(side_effect=lambda *_args: observed({"total": 1, "ready": 1}))
        self.service._fetch_running_service_ids = mock.Mock(side_effect=lambda *_args: observed([]))
        self.service._fetch_abnormal_service_ids = mock.Mock(side_effect=lambda *_args: observed([]))

        with ThreadPoolExecutor(max_workers=2) as callers:
            results = list(
                callers.map(lambda suffix: self.service._fetch_runtime_regions("eid-{}".format(suffix), regions),
                            ("one", "two")))

        self.assertEqual([4, 4], [len(result) for result in results])
        self.assertLessEqual(peak[0], 8)
        self.assertGreater(peak[0], 3)

    def test_runtime_cold_cache_is_single_flight_for_same_key(self):
        started = threading.Event()
        release = threading.Event()
        calls = [0]

        def runtime_regions(_enterprise_id, _regions):
            calls[0] += 1
            started.set()
            release.wait(1)
            return {}

        self.service._list_region_records = mock.Mock(return_value=[])
        self.service._fetch_runtime_regions = mock.Mock(side_effect=runtime_regions)
        self.service._database_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_running_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_application_alerts = mock.Mock(return_value=[])

        with ThreadPoolExecutor(max_workers=2) as callers:
            first = callers.submit(self.service.get_runtime, "eid")
            self.assertTrue(started.wait(1))
            second = callers.submit(self.service.get_runtime, "eid")
            time.sleep(0.04)
            self.assertEqual(1, calls[0])
            release.set()
            first_result = first.result(timeout=1)
            second_result = second.result(timeout=1)

        self.assertEqual(first_result, second_result)
        self.assertEqual(1, calls[0])
        self.assertEqual(1, len(self.service._cache.set_calls))

    def test_snapshot_overall_deadline_returns_partial_without_waiting(self):
        release = threading.Event()
        self.service.SECTION_DEADLINE_SECONDS = 0.04
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._fetch_cluster_resources = mock.Mock(side_effect=lambda *_args: release.wait(0.3))
        self.service._fetch_nodes = mock.Mock(return_value={})
        self.service._fetch_components = mock.Mock(return_value=[])
        self.service._fetch_plugins = mock.Mock(return_value=[])
        self.service._database_team_ranking = mock.Mock(return_value={})
        self.service._database_gateway_summary = mock.Mock(return_value=None)

        started = time.monotonic()
        result = self.service.get_cluster_overview("eid", "region-a")
        elapsed = time.monotonic() - started
        release.set()

        self.assertLess(elapsed, 0.15)
        self.assertEqual("partial", result["status"])
        self.assertEqual("unavailable", result["sections"]["resources"]["status"])
        time.sleep(0.02)
        cached = self.service._cache.get("platform-overview:snapshot:eid:region-a")
        self.assertEqual("unavailable", cached["sections"]["resources"]["status"])

    def test_cluster_snapshot_degrades_one_failed_section(self):
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._fetch_cluster_resources = mock.Mock(return_value={"cpu": {"capacity": 8, "allocated": 2}})
        self.service._fetch_nodes = mock.Mock(side_effect=RuntimeError("nodes down"))
        self.service._fetch_components = mock.Mock(return_value=[{"name": "rbd-api", "status": "Running"}])
        self.service._fetch_plugins = mock.Mock(return_value=[{"name": "monitor", "status": "RUNNING"}])
        self.service._database_team_ranking = mock.Mock(return_value=[])
        self.service._database_gateway_summary = mock.Mock(return_value=None)

        result = self.service.get_cluster_overview("eid", "region-a")

        self.assertEqual("partial", result["status"])
        self.assertEqual("unavailable", result["sections"]["nodes"]["status"])
        self.assertEqual("ok", result["sections"]["components"]["status"])
        self.assertEqual("empty", result["sections"]["gateway"]["status"])
        self.assertEqual([("platform-overview:snapshot:eid:region-a", 10)], self.service._cache.set_calls)

    def test_snapshot_degrades_plugin_section_when_region_plugin_http_status_fails(self):
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._fetch_cluster_resources = mock.Mock(return_value={})
        self.service._fetch_nodes = mock.Mock(return_value={})
        self.service._fetch_components = mock.Mock(return_value=[])
        self.service._fetch_plugins = mock.Mock(side_effect=ServiceHandleException("plugins unavailable"))
        self.service._database_team_ranking = mock.Mock(return_value={})
        self.service._database_gateway_summary = mock.Mock(return_value=None)

        result = self.service.get_cluster_overview("eid", "region-a")

        self.assertEqual("partial", result["status"])
        self.assertEqual("unavailable", result["sections"]["plugins"]["status"])

    def test_cluster_resources_do_not_invent_pod_total_from_real_region_contract(self):
        self.service._region_api.get_region_resources = mock.Mock(return_value=({
            "status": 200
        }, {
            "bean": {
                "cap_cpu": 8,
                "req_cpu": 2,
                "cap_mem": 16384,
                "req_mem": 4096,
                "run_pod_number": 17,
                "k8s_version": "v1.30.4",
            }
        }))

        result = self.service._fetch_cluster_resources("eid", "region-a")

        self.assertEqual({"running": None, "active": 17, "total": None}, result["pods"])
        self.assertEqual(25.0, result["cpu"]["allocation_percent"])
        self.assertEqual("MiB", result["memory"]["unit"])
        self.service._region_api.get_region_resources.assert_called_once_with("eid",
                                                                              region="region-a",
                                                                              connect_timeout=2,
                                                                              timeout=3,
                                                                              retries=0)

    def test_cluster_version_uses_real_show_contract_and_is_cached(self):
        self.region_api.get_enterprise_api_version_v2.return_value = ({"status": 200}, {"raw": "v6.9.12-release-real"})

        first = self.service._fetch_cluster_version("eid", "region-a")
        second = self.service._fetch_cluster_version("eid", "region-a")

        self.assertEqual("v6.9.12-release-real", first)
        self.assertEqual(first, second)
        self.region_api.get_enterprise_api_version_v2.assert_called_once_with("eid",
                                                                              region="region-a",
                                                                              connect_timeout=2,
                                                                              timeout=3,
                                                                              retries=0)

    def test_snapshot_uses_show_version_and_keeps_resources_when_version_fails(self):
        sections = {
            "resources": {
                "status": "ok",
                "data": {
                    "cpu": {
                        "capacity": 8
                    },
                    "versions": {
                        "kubernetes": "v1.30.4"
                    }
                }
            },
            "versions": {
                "status": "ok",
                "data": "v6.9.12-release-real"
            },
        }
        with mock.patch.object(self.service, "_run_sections", return_value=sections):
            result = self.service._build_cluster_overview("eid", "region-a", REGION)
        self.assertEqual("v6.9.12-release-real", result["sections"]["resources"]["data"]["versions"]["rainbond"])

        sections["versions"] = {"status": "unavailable", "data": None}
        with mock.patch.object(self.service, "_run_sections", return_value=sections):
            result = self.service._build_cluster_overview("eid", "region-a", REGION)
        self.assertEqual("ok", result["sections"]["resources"]["status"])
        self.assertIsNone(result["sections"]["resources"]["data"]["versions"]["rainbond"])

    def test_cluster_version_rejects_missing_or_failed_show_response(self):
        for response in (({"status": 200}, {}), ({"status": 503}, {"raw": "stale"})):
            self.region_api.get_enterprise_api_version_v2.return_value = response
            with self.assertRaises(RuntimeError):
                self.service._fetch_cluster_version("eid", "region-a")

    def test_cluster_version_decodes_actual_plain_text_show_bytes(self):
        self.region_api.get_enterprise_api_version_v2.return_value = ({"status": 200}, {"raw": b"v6.9.12-release-real"})

        result = self.service._fetch_cluster_version("eid", "region-a")

        self.assertEqual("v6.9.12-release-real", result)
        self.assertEqual(result, self.service._cache.get("platform-overview:version:eid:region-a"))

    def test_invalid_show_bytes_become_unavailable_without_caching(self):
        self.region_api.get_enterprise_api_version_v2.return_value = ({"status": 200}, {"raw": b"\xff\xfe"})

        sections = self.service._run_sections(
            {"versions": lambda: self.service._fetch_cluster_version("eid", "region-a")}, max_workers=1)

        self.assertEqual({"status": "unavailable", "data": None}, sections["versions"])
        self.assertIsNone(self.service._cache.get("platform-overview:version:eid:region-a"))

    def test_show_client_respects_overview_deadline_and_retry_options(self):
        client = overview_module.RegionInvokeApi()
        with mock.patch.object(client, "_RegionInvokeApi__get_region_access_info_by_enterprise_id",
                               return_value=("https://region.example", "")), \
                mock.patch.object(client, "_get", return_value=({"status": 200}, {"raw": "v6.9.12"})) as get:
            client.get_enterprise_api_version_v2("eid", "region-a", connect_timeout=2, timeout=3, retries=0)
        self.assertEqual(0, get.call_args.kwargs["retries"])
        self.assertEqual(3, get.call_args.kwargs["timeout"])

    def test_isolated_cluster_clients_send_the_owned_region_authorization(self):
        methods = [
            ("get_cluster_nodes", ("region-a",)),
            ("get_rainbond_components", ("region-a",)),
            ("list_plugins", ("eid", "region-a", False)),
            ("get_user_service_abnormal_status", ("region-a", "eid")),
        ]
        for method_name, args in methods:
            client = overview_module.RegionInvokeApi()
            region = SimpleNamespace(url="https://region.example", token="Token test-region")
            with mock.patch.object(client, "get_region_info", return_value=region), \
                    mock.patch.object(client, "get_enterprise_region_info", return_value=region), \
                    mock.patch.dict(settings.MODULES, {"RegionToken": True}), \
                    mock.patch.object(client, "_get", return_value=({"status": 200}, {})) as get:
                getattr(client, method_name)(*args)
            self.assertEqual("Token test-region", get.call_args.args[1].get("Authorization"), method_name)

    def test_overview_node_and_component_calls_use_single_five_second_attempt(self):
        self.service._region_api.get_cluster_nodes = mock.Mock(return_value=({"status": 200}, {"list": []}))

        self.service._fetch_nodes("region-a")
        with mock.patch.object(overview_module.enterprise_services, "get_rbdcomponents", return_value=[]) as components:
            self.service._fetch_components("region-a")

        self.service._region_api.get_cluster_nodes.assert_called_once_with("region-a", connect_timeout=2, timeout=3, retries=0)
        components.assert_called_once_with("region-a",
                                           connect_timeout=2,
                                           timeout=3,
                                           retries=0,
                                           region_api_client=self.region_api)

    def test_rainbond_components_handle_zero_replicas_and_pending_pod(self):
        client = mock.Mock()
        client.get_rainbond_components.return_value = ({
            "status": 200
        }, {
            "list": [{
                "name": "rbd-api",
                "run_pods": 0,
                "all_pods": 0,
                "pods": [],
            }, {
                "name": "rbd-worker",
                "run_pods": 0,
                "all_pods": 1,
                "pods": [{
                    "metadata": {
                        "name": "rbd-worker-pending"
                    },
                    "status": {
                        "phase": "Pending"
                    }
                }],
            }]
        })

        result = overview_module.enterprise_services.get_rbdcomponents("region-a", region_api_client=client)

        self.assertEqual("Abnormal", result[0]["status"])
        self.assertEqual("Abnormal", result[1]["status"])
        self.assertIsNone(result[1]["pods"][0]["create_time"])
        self.assertIsNone(result[1]["pods"][0]["pod_ip"])
        self.assertEqual(0, result[1]["pods"][0]["all_container"])

    def test_pending_rainbond_component_keeps_overview_section_available(self):
        client = mock.Mock()
        client.get_rainbond_components.return_value = ({
            "status": 200
        }, {
            "list": [{
                "name": "rbd-worker",
                "run_pods": 0,
                "all_pods": 1,
                "pods": [{
                    "metadata": {
                        "name": "pending"
                    },
                    "status": {
                        "phase": "Pending"
                    }
                }],
            }]
        })
        service = PlatformOverviewService(cache_backend=MemoryCache(), region_api_factory=lambda: client)
        service._get_enterprise_region = mock.Mock(return_value=REGION)
        service._fetch_cluster_resources = mock.Mock(return_value={})
        service._fetch_nodes = mock.Mock(return_value={})
        service._fetch_plugins = mock.Mock(return_value=[])
        service._database_team_ranking = mock.Mock(return_value={})
        service._database_gateway_summary = mock.Mock(return_value=None)

        result = service.get_cluster_overview("eid", "region-a")

        self.assertEqual("ok", result["sections"]["components"]["status"])
        self.assertEqual("Abnormal", result["sections"]["components"]["data"][0]["status"])

    def test_node_normalizer_reports_not_ready_and_disk_threshold(self):
        gib = 1024 * 1024 * 1024
        nodes = self.service._normalize_nodes({
            "list": [{
                "name": "172.16.0.4",
                "conditions": [{
                    "type": "Ready",
                    "status": "False"
                }],
                "unschedulable": False,
                "roles": ["worker"],
                "architecture": "amd64",
                "resource": {
                    "req_cpu": 2,
                    "cap_cpu": 8,
                    "req_memory": 4096,
                    "cap_memory": 16384,
                    "req_disk": 82 * gib,
                    "cap_disk": 100 * gib,
                    "req_container_disk": 60 * gib,
                    "cap_container_disk": 100 * gib,
                },
            }]
        })

        self.assertEqual(1, nodes["total"])
        self.assertEqual(0, nodes["ready"])
        self.assertEqual("node_not_ready", nodes["alerts"][0]["type"])
        disk_alert = next(item for item in nodes["alerts"] if item["type"] == "disk_usage")
        self.assertEqual(82.0, disk_alert["usage_percent"])
        self.assertEqual("root", disk_alert["filesystem"])
        self.assertIn("当前已使用 82%", disk_alert["message"])

    def test_team_ranking_is_top_five_with_stable_tie_break(self):
        items = [{
            "tenant_alias": "team-{}".format(index),
            "tenant_name": "t{}".format(index),
            "score": score
        } for index, score in enumerate([3, 9, 1, 9, 7, 6, 5])]

        result = self.service._top_five(items, "score")

        self.assertEqual(5, len(result))
        self.assertEqual(["team-1", "team-3"], [result[0]["tenant_alias"], result[1]["tenant_alias"]])
        self.assertEqual([9, 9, 7, 6, 5], [item["score"] for item in result])

    def test_team_ranking_allocation_math_and_units(self):
        teams = [{"tenant_id": "t1", "tenant_name": "team-one", "tenant_alias": "Team One"}]
        resources = [{"tenant_id": "t1", "cpu_millicores": 3500, "memory_mib": 5120}]
        applications = [{"tenant_id": "t1", "total": 4}]

        result = self.service._build_team_rankings(teams, resources, applications)

        self.assertEqual(3.5, result["cpu"][0]["cpu_cores"])
        self.assertEqual(5.0, result["memory"][0]["memory_gib"])
        self.assertEqual(4, result["applications"][0]["applications"])

    def test_gateway_summary_is_scoped_to_selected_region_and_maps_certificate_issue(self):
        service_query = mock.Mock()
        service_query.values.return_value = [{
            "service_id": "s1",
            "service_alias": "api",
            "service_cname": "API",
            "tenant_id": "t1",
        }, {
            "service_id": "s2",
            "service_alias": "worker",
            "service_cname": "Worker",
            "tenant_id": "t2",
        }]
        domain = SimpleNamespace(service_id="s1",
                                 tenant_id="t1",
                                 certificate_id=7,
                                 domain_name="api.example.com",
                                 service_alias="api",
                                 service_name="API")
        certificate = SimpleNamespace(ID=7, alias="api-cert", certificate="ignored")
        teams = [
            SimpleNamespace(tenant_id="t1", tenant_name="team-one"),
            SimpleNamespace(tenant_id="t2", tenant_name="team-two"),
        ]
        relations_data = [
            SimpleNamespace(service_id="s1", tenant_id="t1", region_name="region-a", group_id=42),
            SimpleNamespace(service_id="s2", tenant_id="t2", region_name="region-a", group_id=84),
            SimpleNamespace(service_id="s1", tenant_id="t2", region_name="region-a", group_id=84),
        ]
        group_query = mock.Mock()
        group_query.values_list.return_value = [42, 84]

        with mock.patch.object(self.service, "_tenant_ids", return_value=["t1", "t2"]), \
                mock.patch.object(overview_module.TenantServiceInfo.objects, "filter", return_value=service_query) as services, \
                mock.patch.object(overview_module.ServiceDomain.objects, "filter", return_value=[domain]), \
                mock.patch.object(overview_module.ServiceTcpDomain.objects, "filter", return_value=[]), \
                mock.patch.object(overview_module.ServiceDomainCertificate.objects, "filter", return_value=[certificate]), \
                mock.patch.object(overview_module.Tenants.objects, "filter", return_value=teams), \
                mock.patch.object(overview_module.ServiceGroup.objects, "filter", return_value=group_query), \
                mock.patch.object(
                    overview_module.ServiceGroupRelation.objects, "filter", return_value=relations_data) as relations, \
                mock.patch.object(self.service, "_certificate_status", return_value=("warning", "2026-11-01T00:00:00")):
            result = self.service._database_gateway_summary("eid", REGION)

        services.assert_called_once_with(tenant_id__in=["t1", "t2"], service_region="region-a")
        self.assertEqual(1, result["http_domains"])
        self.assertEqual("configured_routes_and_bound_certificates", result["scope"])
        self.assertFalse(result["reachability_checked"])
        self.assertEqual("api.example.com", result["issues"][0]["domain"])
        self.assertEqual(42, result["issues"][0]["application_id"])
        relations.assert_called_once_with(service_id__in=["s1", "s2"],
                                          tenant_id__in=["t1", "t2"],
                                          region_name="region-a",
                                          group_id__in=[42, 84])

    def test_application_alarm_relation_ignores_duplicate_historical_region(self):
        teams = [
            SimpleNamespace(tenant_id="t1", tenant_name="team-one", tenant_alias="Team One"),
            SimpleNamespace(tenant_id="t2", tenant_name="team-two", tenant_alias="Team Two"),
        ]
        services = [
            SimpleNamespace(tenant_id="t1",
                            service_id="s1",
                            service_alias="api",
                            service_cname="API",
                            service_region="region-a"),
            SimpleNamespace(tenant_id="t2",
                            service_id="s2",
                            service_alias="worker",
                            service_cname="Worker",
                            service_region="region-b"),
        ]
        relations_data = [
            SimpleNamespace(service_id="s1", tenant_id="t1", region_name="region-a", group_id=42),
            SimpleNamespace(service_id="s2", tenant_id="t2", region_name="region-b", group_id=84),
            SimpleNamespace(service_id="s1", tenant_id="t2", region_name="region-b", group_id=84),
        ]
        groups_data = [
            SimpleNamespace(ID=42, group_name="app-a"),
            SimpleNamespace(ID=84, group_name="app-b"),
        ]

        with mock.patch.object(self.service, "_tenant_ids", return_value=["t1", "t2"]), \
                mock.patch.object(overview_module.Tenants.objects, "filter", return_value=teams), \
                mock.patch.object(overview_module.TenantServiceInfo.objects, "filter", return_value=services), \
                mock.patch.object(
                    overview_module.ServiceGroupRelation.objects, "filter", return_value=relations_data) as relations, \
                mock.patch.object(overview_module.ServiceGroup.objects, "filter", return_value=groups_data) as groups:
            result = self.service._database_application_alerts("eid", {"s1", "s2"})

        relations.assert_called_once_with(service_id__in=["s1", "s2"],
                                          tenant_id__in=["t1", "t2"],
                                          region_name__in=["region-a", "region-b"])
        groups.assert_called_once_with(ID__in=[42, 84], tenant_id__in=["t1", "t2"], region_name__in=["region-a", "region-b"])
        by_service = {item["service_id"]: item for item in result}
        self.assertEqual(42, by_service["s1"]["application_id"])
        self.assertEqual("app-a", by_service["s1"]["application_name"])
        self.assertEqual(84, by_service["s2"]["application_id"])

    def test_metric_query_uses_server_owned_query_and_cache(self):
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._metric_tenant_name = mock.Mock(return_value="team-a")
        self.service._region_api.get_query_range_data = mock.Mock(return_value=({
            "status": 200
        }, {
            "status": "success",
            "data": {
                "result": [{
                    "metric": {},
                    "values": [[1, "12.5"]]
                }]
            },
        }))

        first = self.service.get_metrics("eid", "region-a", "cpu", "6h")
        second = self.service.get_metrics("eid", "region-a", "cpu", "6h")

        self.assertEqual("ok", first["status"])
        self.assertEqual("percent", first["unit"])
        params = self.service._region_api.get_query_range_data.call_args.args[2]
        self.assertIn("query=", params)
        self.assertNotIn("up%7B", params)
        self.assertEqual(first, second)
        self.assertEqual(1, self.service._region_api.get_query_range_data.call_count)
        options = self.service._region_api.get_query_range_data.call_args.kwargs
        self.assertLessEqual(options["connect_timeout"], 2)
        self.assertLessEqual(options["timeout"], 3)
        self.assertLessEqual(options["connect_timeout"] + options["timeout"], 5)
        self.assertEqual(0, options["retries"])
        self.assertEqual([("platform-overview:metrics-absolute-v1:eid:region-a:cpu:6h", 15)], self.service._cache.set_calls)

    def test_metric_query_failure_returns_unavailable(self):
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._metric_tenant_name = mock.Mock(return_value="team-a")
        self.service._region_api.get_query_range_data = mock.Mock(return_value=({"status": 503}, None))

        result = self.service.get_metrics("eid", "region-a", "memory", "1h")

        self.assertEqual("unavailable", result["status"])
        self.assertEqual([], result["series"])
        options = self.service._region_api.get_query_range_data.call_args.kwargs
        self.assertLessEqual(options["connect_timeout"] + options["timeout"], 5)
        self.assertEqual(0, options["retries"])

    def test_metrics_use_cluster_query_path_without_initialized_team(self):
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._metric_tenant_name = mock.Mock(return_value=None)
        self.service._region_api.get_query_range_data = mock.Mock(return_value=({
            "status": 200
        }, {
            "status": "success",
            "data": {
                "result": []
            },
        }))

        result = self.service.get_metrics("eid", "region-a", "cpu", "1h")

        self.assertEqual("empty", result["status"])
        self.assertEqual("", self.service._region_api.get_query_range_data.call_args.args[1])

    def test_tenant_ids_exclude_inactive_teams_and_stale_region_memberships(self):
        active_teams = mock.Mock()
        active_team_ids = mock.Mock(name="active_team_ids")
        active_teams.values_list.return_value = active_team_ids
        memberships = mock.Mock()
        memberships.values_list.return_value = ["active-team"]

        with mock.patch.object(overview_module.Tenants.objects, "filter", return_value=active_teams) as teams, \
                mock.patch.object(overview_module.TenantRegionInfo.objects, "filter", return_value=memberships) as regions:
            result = list(self.service._tenant_ids("eid", "region-a"))

        teams.assert_called_once_with(enterprise_id="eid", is_active=True)
        regions.assert_called_once_with(enterprise_id="eid",
                                        tenant_id__in=active_team_ids,
                                        is_active=True,
                                        is_init=True,
                                        region_name="region-a")
        self.assertEqual(["active-team"], result)

    def test_certificate_expiry_is_compared_as_utc_absolute_time(self):
        certificate = SimpleNamespace(ID=7, certificate=base64.b64encode(b"certificate").decode("ascii"))
        parsed = mock.Mock()
        parsed.get_notAfter.return_value = b"20261118120000Z"
        now = datetime.datetime(2026, 10, 19, 20, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))

        with mock.patch.object(overview_module.crypto, "load_certificate", return_value=parsed):
            status, expires_at = self.service._certificate_status(certificate, now)

        self.assertEqual("warning", status)
        self.assertEqual("2026-11-18T12:00:00+00:00", expires_at)

    def test_certificate_naive_now_is_localized_before_utc_comparison(self):
        certificate = SimpleNamespace(ID=7, certificate=base64.b64encode(b"certificate").decode("ascii"))
        parsed = mock.Mock()
        parsed.get_notAfter.return_value = b"20261118100000Z"
        naive_shanghai_now = datetime.datetime(2026, 10, 19, 15, 0)
        shanghai = datetime.timezone(datetime.timedelta(hours=8))

        with mock.patch.object(overview_module.crypto, "load_certificate", return_value=parsed), \
                mock.patch.object(overview_module.timezone, "get_current_timezone", return_value=shanghai):
            status, expires_at = self.service._certificate_status(certificate, naive_shanghai_now)

        self.assertEqual("normal", status)
        self.assertEqual("2026-11-18T10:00:00+00:00", expires_at)

    def test_metric_query_rejects_unknown_metric_and_range(self):
        with self.assertRaises(ValueError):
            self.service.get_metrics("eid", "region-a", "up{}", "6h")
        with self.assertRaises(ValueError):
            self.service.get_metrics("eid", "region-a", "cpu", "7d")

    def _remediation_runtime(self, region_sections, regions=None):
        self.service._list_region_records = mock.Mock(return_value=[REGION] if regions is None else regions)
        self.service._fetch_runtime_regions = mock.Mock(return_value=region_sections)
        self.service._database_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_running_workload_counts = mock.Mock(return_value={"applications": 0, "components": 0})
        self.service._database_application_alerts = mock.Mock(return_value=[])
        return self.service.get_runtime("eid")

    def test_remediation_all_failed_node_counts_are_null_not_zero(self):
        result = self._remediation_runtime({
            "region-a": {"status": "unavailable", "data": None},
        })

        self.assertEqual({"status": "unavailable", "total": None, "ready": None}, result["global"]["nodes"])
        self.assertEqual(1, result["global"]["clusters"]["unavailable"])

    def test_remediation_partial_node_counts_are_explicitly_partial(self):
        region_b = SimpleNamespace(**dict(REGION.__dict__, region_name="region-b"))
        result = self._remediation_runtime({
            "region-a": {
                "status": "ok",
                "data": {
                    "nodes": {"total": 2, "ready": 1},
                    "workloads_status": "ok",
                    "alarms_status": "ok",
                },
            },
            "region-b": {"status": "unavailable", "data": None},
        }, [REGION, region_b])

        self.assertEqual({"status": "partial", "total": 2, "ready": 1}, result["global"]["nodes"])

    def test_remediation_optional_workload_failure_does_not_make_nodes_partial(self):
        result = self._remediation_runtime({
            "region-a": {
                "status": "ok",
                "data": {
                    "nodes": {"total": 2, "ready": 2},
                    "workloads_status": "unavailable",
                    "alarms_status": "ok",
                    "status": "partial",
                },
            },
        })

        self.assertEqual({"status": "ok", "total": 2, "ready": 2}, result["global"]["nodes"])

    def test_remediation_zero_active_regions_have_real_zero_nodes(self):
        disabled = SimpleNamespace(**dict(REGION.__dict__, status="0"))
        for regions in ([], [disabled]):
            self.service._cache = MemoryCache()
            result = self._remediation_runtime({}, regions)
            self.assertEqual({"status": "ok", "total": 0, "ready": 0}, result["global"]["nodes"])

    def test_remediation_runtime_nodes_request_lightweight_mode(self):
        self.region_api.get_cluster_nodes.return_value = ({"status": 200}, {"list": []})
        self.region_api.get_enterprise_running_services.return_value = {"service_ids": []}
        self.region_api.get_user_service_abnormal_status.return_value = {"service_ids": []}

        self.service._fetch_runtime_regions("eid", [REGION])

        self.region_api.get_cluster_nodes.assert_called_once_with(
            "region-a", include_stats=False, connect_timeout=2, timeout=3, retries=0)

    def test_remediation_region_node_client_keeps_default_and_adds_only_explicit_lightweight_query(self):
        client = overview_module.RegionInvokeApi()
        region = SimpleNamespace(url="https://region.example", token="")
        with mock.patch.object(client, "get_region_info", return_value=region), \
                mock.patch.object(client, "_get", return_value=({"status": 200}, {"list": []})) as get:
            client.get_cluster_nodes("region-a")
            self.assertEqual("https://region.example/v2/cluster/nodes", get.call_args.args[0])
            client.get_cluster_nodes("region-a", include_stats=False, connect_timeout=2, timeout=3, retries=0)
            self.assertEqual("https://region.example/v2/cluster/nodes?include_stats=false", get.call_args.args[0])

    def test_remediation_resources_prefer_millicores_and_strict_running_pods(self):
        self.region_api.get_region_resources.return_value = ({"status": 200}, {"bean": {
            "cap_cpu": 7,
            "cap_cpu_millicores": 7900,
            "req_cpu": 2,
            "cap_mem": 16384,
            "req_mem": 4096,
            "run_pod_number": 17,
            "running_pod_number": 12,
            "resource_source": "kubernetes",
            "resource_scope": "rainbond_workloads",
        }})

        result = self.service._fetch_cluster_resources("eid", "region-a")

        self.assertEqual(7.9, result["cpu"]["capacity"])
        self.assertEqual({"running": 12, "active": 17, "total": None}, result["pods"])
        self.assertEqual("kubernetes", result["source"])
        self.assertEqual("rainbond_workloads", result["scope"])

    def test_remediation_old_resource_api_does_not_relabel_active_as_running(self):
        self.region_api.get_region_resources.return_value = ({"status": 200}, {"bean": {
            "cap_cpu": 8, "req_cpu": 2, "cap_mem": 16384, "req_mem": 4096, "run_pod_number": 17,
        }})

        result = self.service._fetch_cluster_resources("eid", "region-a")

        self.assertEqual({"running": None, "active": 17, "total": None}, result["pods"])
        self.assertEqual("unknown", result["source"])

    def test_remediation_resource_fields_reject_missing_negative_and_nonfinite_values(self):
        good = {"cap_cpu": 8, "req_cpu": 2, "cap_mem": 16384, "req_mem": 4096}
        for field in good:
            for invalid in (None, "not-a-number", "NaN", float("inf"), -1):
                with self.subTest(field=field, invalid=invalid):
                    self.region_api.get_region_resources.return_value = ({"status": 200}, {
                        "bean": dict(good, **{field: invalid})})
                    with self.assertRaises(RuntimeError):
                        self.service._fetch_cluster_resources("eid", "region-a")

    def test_remediation_legacy_missing_disk_stats_are_unknown_not_healthy(self):
        result = self.service._normalize_nodes({"list": [{
            "name": "node-a", "conditions": [{"type": "Ready", "status": "True"}], "resource": {},
        }]})

        self.assertEqual("unavailable", result["disk_stats_status"])
        self.assertEqual("unavailable", result["items"][0]["disk_stats_status"])
        self.assertEqual([], result["alerts"])

    def test_remediation_disk_availability_preserves_explicit_partial_and_not_requested(self):
        for status in ("partial", "not_requested"):
            with self.subTest(status=status):
                result = self.service._normalize_nodes({"list": [{
                    "name": "node-a", "disk_stats_status": status,
                    "conditions": [{"type": "Ready", "status": "True"}],
                    "resource": {"req_disk": 82, "cap_disk": 100},
                }]})
                self.assertEqual(status, result["disk_stats_status"])
                self.assertEqual(status, result["items"][0]["disk_stats_status"])

    def test_remediation_nodes_reject_malformed_lists_and_do_not_serialize_nan_resources(self):
        for body in ({}, {"list": None}, {"list": {}}, {"list": [None]}):
            with self.subTest(body=body), self.assertRaises(RuntimeError):
                self.service._normalize_nodes(body)
        result = self.service._normalize_nodes({"list": [{
            "name": "node-a", "conditions": [], "resource": {"cap_cpu": "NaN", "req_cpu": "Inf"},
        }]})
        self.assertIsNone(result["items"][0]["cpu"]["capacity"])
        self.assertIsNone(result["items"][0]["cpu"]["allocated"])

    def test_remediation_unavailable_disk_stats_do_not_produce_stale_disk_alerts(self):
        result = self.service._normalize_nodes({"list": [{
            "name": "node-a", "disk_stats_status": "unavailable",
            "conditions": [{"type": "Ready", "status": "True"}],
            "resource": {"req_disk": 82, "cap_disk": 100},
        }]})
        self.assertEqual([], result["items"][0]["disks"])
        self.assertEqual([], result["alerts"])

    def test_remediation_overview_hides_only_absent_operator_not_other_zero_replica_services(self):
        components = [
            {"name": "rainbond-operator", "run_pods": 0, "all_pods": 0, "pods": []},
            {"name": "rbd-api", "run_pods": 0, "all_pods": 0, "pods": []},
            {"name": "rbd-worker", "run_pods": 0, "all_pods": 1, "pods": [{"pod_name": "pending"}]},
        ]
        with mock.patch.object(overview_module.enterprise_services, "get_rbdcomponents", return_value=components):
            result = self.service._fetch_components("region-a")

        self.assertEqual(["rbd-api", "rbd-worker"], [item["name"] for item in result])
        self.assertEqual([{"pod_name": "pending"}], result[1]["pods"])
        self.assertEqual(3, len(components))

    def test_remediation_team_rankings_declare_configured_resource_scope_and_all_team_totals(self):
        teams = [{"tenant_id": str(index), "tenant_name": str(index), "tenant_alias": str(index)} for index in range(6)]
        resources = [{"tenant_id": str(index), "cpu_millicores": 1000, "memory_mib": 1024} for index in range(6)]
        applications = [{"tenant_id": str(index), "total": 1} for index in range(6)]

        result = self.service._build_team_rankings(teams, resources, applications)

        self.assertEqual("configured_resources", result["scope"])
        self.assertTrue(result["includes_inactive_components"])
        self.assertEqual({"cpu_cores": 6, "memory_gib": 6, "applications": 6}, result["totals"])
        self.assertEqual(5, len(result["cpu"]))

    def _remediation_metric_query(self, responses, metric="cpu"):
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._metric_tenant_name = mock.Mock(return_value="team-a")
        self.region_api.get_query_range_data.side_effect = responses
        return self.service.get_metrics("eid", "region-a", metric, "1h")

    @staticmethod
    def _prometheus_result(values):
        return {"status": 200}, {"status": "success", "data": {"result": values}}

    def test_remediation_metrics_filter_invalid_points_but_keep_real_zero(self):
        result = self._remediation_metric_query([self._prometheus_result([{
            "metric": {}, "values": [[1, "NaN"], [2, "+Inf"], ["bad", "1"], [3, "0"], [4, "12.5"]],
        }])])

        self.assertEqual("ok", result["status"])
        self.assertEqual([[3, "0"], [4, "12.5"]], result["series"][0]["values"])
        self.assertEqual("node_exporter", result["source"])
        self.assertEqual("host_cpu_utilization", result["semantics"])
        self.assertEqual(1, self.region_api.get_query_range_data.call_count)

    def test_remediation_metrics_empty_primary_uses_one_guarded_root_cadvisor_fallback(self):
        result = self._remediation_metric_query([
            self._prometheus_result([]),
            self._prometheus_result([{"metric": {}, "values": [[1, "34.5"]]}]),
        ], metric="memory")

        self.assertEqual("ok", result["status"])
        self.assertEqual("cadvisor_root", result["source"])
        self.assertEqual("scrape_targets", result["coverage"])
        self.assertEqual("host_memory_working_set", result["semantics"])
        self.assertEqual(2, self.region_api.get_query_range_data.call_count)
        params = self.region_api.get_query_range_data.call_args.args[2]
        query = parse_qs(params.lstrip("?"))["query"][0]
        for guard in ('job="cadvisor"', 'id="/"', 'kubernetes_io_hostname!=""', "machine_memory_bytes", "up{"):
            self.assertIn(guard, query)
        self.assertIn('namespace=""', query)
        self.assertIn('pod=""', query)
        self.assertNotIn("service_id", query)

    def test_remediation_metrics_no_host_coverage_remains_empty_not_zero(self):
        result = self._remediation_metric_query([self._prometheus_result([]), self._prometheus_result([])])

        self.assertEqual("empty", result["status"])
        self.assertEqual("host_coverage_unverified", result["reason"])
        self.assertEqual([], result["series"])
        self.assertEqual(2, self.region_api.get_query_range_data.call_count)

    def test_remediation_metrics_failed_primary_does_not_retry_or_fallback(self):
        result = self._remediation_metric_query([({"status": 503}, {"status": "success", "data": {"result": []}})])

        self.assertEqual("unavailable", result["status"])
        self.assertEqual("query_failed", result["reason"])
        self.assertEqual(1, self.region_api.get_query_range_data.call_count)

    def test_remediation_metrics_malformed_success_is_unavailable_not_empty(self):
        for body in ({"status": "success"}, {"status": "success", "data": {"result": None}},
                     {"status": "success", "data": {"result": [{"values": "bad"}]}}):
            with self.subTest(body=body):
                self.service._cache = MemoryCache()
                self.region_api.get_query_range_data.reset_mock()
                result = self._remediation_metric_query([({"status": 200}, body)])
                self.assertEqual("unavailable", result["status"])
                self.assertEqual("query_failed", result["reason"])
                self.assertEqual(1, self.region_api.get_query_range_data.call_count)

    def test_remediation_each_fallback_has_root_node_identity_and_target_coverage_guards(self):
        for metric in ("cpu", "memory", "network"):
            with self.subTest(metric=metric):
                query = self.service._cadvisor_query(metric)
                self.assertIn('id="/"', query)
                self.assertIn('namespace=""', query)
                self.assertIn('pod=""', query)
                self.assertIn('kubernetes_io_hostname!=""', query)
                self.assertIn('count(up{job="cadvisor"}) == count(up{job="cadvisor",kubernetes_io_hostname!=""})', query)
                self.assertIn("min(max by (kubernetes_io_hostname)", query)
                self.assertNotIn(" bool ", query)
                self.assertNotIn("by (instance)", query)

    def test_remediation_cadvisor_cpu_accepts_total_and_unlabelled_root_samples_only(self):
        query = self.service._cadvisor_query("cpu")

        self.assertIn('cpu=~"total|"', query)
        self.assertIn("max by (kubernetes_io_hostname)", query)
        self.assertNotIn('cpu=~".*"', query)

    def test_remediation_metrics_all_nonfinite_points_do_not_form_a_curve(self):
        result = self._remediation_metric_query([
            self._prometheus_result([{"metric": {}, "values": [[1, "NaN"], [2, "Inf"]]}]),
            self._prometheus_result([{"metric": {}, "values": [[1, "NaN"]]}]),
        ])

        self.assertEqual("empty", result["status"])
        self.assertEqual([], result["series"])

    def test_remediation_metrics_fallback_obeys_remaining_five_second_budget(self):
        clock = [100.0]

        def query(_region, _tenant, _params, **kwargs):
            self.assertLessEqual(kwargs["connect_timeout"] + kwargs["timeout"], 5 - (clock[0] - 100.0) + 0.001)
            self.assertEqual(0, kwargs["retries"])
            clock[0] += 4.0 if self.region_api.get_query_range_data.call_count == 1 else 1.0
            return self._prometheus_result([])

        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._metric_tenant_name = mock.Mock(return_value="team-a")
        self.region_api.get_query_range_data.side_effect = query
        with mock.patch("time.monotonic", side_effect=lambda: clock[0]):
            result = self.service.get_metrics("eid", "region-a", "cpu", "1h")

        self.assertEqual(2, self.region_api.get_query_range_data.call_count)
        self.assertEqual("empty", result["status"])

    def test_remediation_metrics_exhausted_budget_does_not_start_fallback(self):
        clock = [100.0]

        def query(*_args, **_kwargs):
            clock[0] = 105.1
            return self._prometheus_result([])

        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._metric_tenant_name = mock.Mock(return_value="team-a")
        self.region_api.get_query_range_data.side_effect = query
        with mock.patch("time.monotonic", side_effect=lambda: clock[0]):
            result = self.service.get_metrics("eid", "region-a", "cpu", "1h")

        self.assertEqual("unavailable", result["status"])
        self.assertEqual("deadline_exceeded", result["reason"])
        self.assertEqual(1, self.region_api.get_query_range_data.call_count)


class PlatformPluginInstalledOnlyTest(TestCase):
    def test_remediation_null_plugin_list_is_a_legacy_empty_list(self):
        service = PlatformPluginService()
        client = mock.Mock()
        client.list_plugins.return_value = ({"status": 200}, {"list": None})

        self.assertEqual([], service.list_installed_platform_plugins("eid", "region-a", region_api_client=client))

    def test_remediation_malformed_plugin_lists_remain_unavailable(self):
        for body in ({}, {"list": {}}, {"list": "invalid"}):
            service = PlatformPluginService()
            client = mock.Mock()
            client.list_plugins.return_value = ({"status": 200}, body)
            with self.subTest(body=body), self.assertRaises(ServiceHandleException):
                service.list_installed_platform_plugins("eid", "region-a", region_api_client=client)

    def test_overview_lists_only_enabled_plugins_preserving_legacy_default(self):
        service = PlatformPluginService()
        plugins = [
            {
                "name": "enabled",
                "enable_status": "true",
                "status": "RUNNING"
            },
            {
                "name": "disabled",
                "enable_status": "false",
                "status": "RUNNING"
            },
            {
                "name": "disabled-bool",
                "enable_status": False,
                "status": "RUNNING"
            },
            {
                "name": "legacy",
                "status": "RUNNING"
            },
            {
                "name": "abnormal",
                "enable_status": "true",
                "status": "ABNORMAL"
            },
        ]
        service._get_installed_plugins_strict = mock.Mock(return_value={plugin["name"]: plugin for plugin in plugins})

        result = service.list_installed_platform_plugins("eid", "region-a")

        self.assertEqual(["abnormal", "enabled", "legacy"], [plugin["name"] for plugin in result])

    def test_installed_plugins_do_not_call_market(self):
        service = PlatformPluginService()
        service._get_installed_plugins_strict = mock.Mock(return_value={
            "z-plugin": {
                "name": "z-plugin",
                "status": "RUNNING"
            },
            "a-plugin": {
                "name": "a-plugin",
                "status": "FAILED"
            },
        })

        with mock.patch.object(service, "_get_market_platform_plugins_cached") as market:
            result = service.list_installed_platform_plugins("eid", "region-a")

        market.assert_not_called()
        self.assertEqual(["a-plugin", "z-plugin"], [item["name"] for item in result])

    def test_installed_plugins_can_use_isolated_region_client(self):
        service = PlatformPluginService()
        isolated_client = mock.Mock()
        isolated_client.list_plugins.return_value = ({"status": 200}, {"list": [{"name": "monitor", "status": "RUNNING"}]})

        with mock.patch.object(platform_plugin_module.region_api, "list_plugins") as shared_list:
            result = service.list_installed_platform_plugins("eid", "region-a", region_api_client=isolated_client)

        shared_list.assert_not_called()
        isolated_client.list_plugins.assert_called_once_with("eid", "region-a", False, connect_timeout=2, timeout=3, retries=0)
        self.assertEqual("monitor", result[0]["name"])

    def test_installed_plugins_reject_non_200_region_response_even_with_list(self):
        service = PlatformPluginService()
        with mock.patch.object(platform_plugin_module.region_api,
                               "list_plugins",
                               return_value=({
                                   "status": 503
                               }, {
                                   "list": [{
                                       "name": "stale",
                                       "status": "RUNNING"
                                   }]
                               })) as list_plugins:
            with self.assertRaises(ServiceHandleException):
                service.list_installed_platform_plugins("eid", "region-a")

        list_plugins.assert_called_once_with("eid", "region-a", False, connect_timeout=2, timeout=3, retries=0)


# capability_id: console.platform-overview.node-certificates
class NodeCertificateAlertsTest(TestCase):
    def setUp(self):
        self.service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=mock.Mock())
        self.now = datetime.datetime(2026, 10, 20, tzinfo=datetime.timezone.utc)

    def node(self, seconds=86400, status="partial"):
        return {"name": "worker", "conditions": [{"type": "Ready", "status": "True"}],
                "certificate_status": status, "certificates": [{
                    "name": "agent/client-kubelet.crt",
                    "expires_at": (self.now + datetime.timedelta(seconds=seconds)).isoformat()}]}

    def normalize(self, nodes):
        with mock.patch.object(overview_module.timezone, "now", return_value=self.now):
            return self.service._normalize_nodes({"list": nodes})

    def test_certificate_deadline_boundaries_and_renewal(self):
        for seconds, kind, days in [(2591999, "certificate_expiring", 30), (2592000, "certificate_expiring", 30),
                                    (0, "certificate_expired", 0), (-1, "certificate_expired", 0),
                                    (-86401, "certificate_expired", -1)]:
            with self.subTest(seconds=seconds):
                result = self.normalize([self.node(seconds)])
                alert = result["alerts"][0]
                self.assertEqual(kind, alert["type"])
                self.assertEqual("critical", alert["severity"])
                self.assertEqual("worker", alert["node_name"])
                self.assertEqual("agent/client-kubelet.crt", alert["certificate_name"])
                self.assertEqual(days, alert["remaining_days"])
                self.assertIsInstance(alert["expires_at"], str)
        self.assertEqual([], self.normalize([self.node(2592001)])["alerts"])
        self.assertEqual([], self.normalize([self.node(31536000)])["alerts"])

    def native_node(self, seconds=86400, status="ok"):
        node = self.node(seconds, status)
        node.update(certificate_source="rke2_events", certificate_observed_at=self.now.isoformat())
        return node

    def unobserved_node(self):
        return {"name": "worker", "conditions": [{"type": "Ready", "status": "True"}],
                "certificate_status": "not_observed", "certificate_source": "rke2_events",
                "certificate_checked_at": self.now.isoformat(), "certificates": []}

    def test_successful_event_query_without_observation_preserves_coverage(self):
        result = self.normalize([self.unobserved_node()])
        self.assertEqual("not_observed", result["certificate_status"])
        self.assertEqual([], result["alerts"])
        item = result["items"][0]
        self.assertEqual("not_observed", item["certificate_status"])
        self.assertEqual("rke2_events", item["certificate_source"])
        self.assertEqual(self.now.isoformat(), item["certificate_checked_at"])
        self.assertNotIn("certificate_observed_at", item)
        self.assertEqual([], item["certificates"])

    def test_native_warnings_preserve_unparsed_and_ca_risks_without_fake_expiration(self):
        for reason in ("CertificateExpirationWarning", "CACertificateExpirationWarning"):
            with self.subTest(reason=reason):
                node = self.native_node(status="unavailable")
                node["certificates"] = []
                node["certificate_warnings"] = [{"reason": reason, "observed_at": self.now.isoformat()}]
                result = self.normalize([node])
                self.assertEqual("unavailable", result["certificate_status"])
                self.assertEqual([{"type": "certificate_warning", "severity": "critical", "node_name": "worker",
                                   "reason": reason, "observed_at": "2026-10-20T00:00:00Z"}], result["alerts"])

    def test_native_warning_validation_and_independent_observation_times(self):
        warning = {"reason": "CACertificateExpirationWarning", "observed_at": self.now.isoformat()}
        invalid_warnings = [None, "", {}, [None], [dict(warning, reason="Other")]]
        invalid_warnings.extend([dict(warning, observed_at=stamp)] for stamp in (
            None, "invalid", "2026-10-20T00:00:00", [], {},
            (self.now - datetime.timedelta(minutes=65, seconds=1)).isoformat(),
            (self.now + datetime.timedelta(minutes=1, seconds=1)).isoformat()))
        for warnings in invalid_warnings:
            with self.subTest(warnings=warnings):
                node = self.native_node()
                node["certificates"] = []
                node["certificate_warnings"] = warnings
                result = self.normalize([node])
                self.assertEqual([], result["alerts"])
                self.assertEqual("unavailable", result["certificate_status"])
        node = self.native_node(status="unavailable")
        node["certificate_observed_at"] = "invalid"
        node["certificates"] = []
        node["certificate_warnings"] = [warning, dict(warning)]
        result = self.normalize([node])
        self.assertEqual(1, len(result["alerts"]))
        self.assertEqual("certificate_warning", result["alerts"][0]["type"])
        node["certificate_source"] = "other"
        self.assertEqual([], self.normalize([node])["alerts"])

    def test_native_warnings_cannot_be_cleared_by_coverage_status_or_leaf_ok(self):
        for status in ("ok", "not_observed", "partial", "unavailable"):
            with self.subTest(status=status):
                node = self.unobserved_node()
                node["certificate_status"] = status
                node["certificate_observed_at"] = self.now.isoformat()
                observed = (self.now - datetime.timedelta(minutes=1)).isoformat()
                node["certificate_warnings"] = [{"reason": "CACertificateExpirationWarning", "observed_at": observed}]
                result = self.normalize([node])
                self.assertEqual("unavailable", result["certificate_status"])
                self.assertEqual(1, len(result["alerts"]))
                self.assertEqual("2026-10-19T23:59:00Z", result["alerts"][0]["observed_at"])
        node = self.native_node(status="partial")
        node["certificate_warnings"] = [{"reason": "CertificateExpirationWarning", "observed_at": self.now.isoformat()}]
        result = self.normalize([node])
        self.assertEqual({"certificate_expiring", "certificate_warning"}, {alert["type"] for alert in result["alerts"]})

    def test_native_warning_freshness_boundaries_and_malformed_siblings_preserve_risk(self):
        node = self.native_node(status="unavailable")
        node["certificates"] = []
        for stamp in ((self.now - datetime.timedelta(minutes=65)).isoformat(),
                      (self.now + datetime.timedelta(minutes=1)).isoformat(), "2026-10-20T08:00:00+08:00"):
            with self.subTest(stamp=stamp):
                node["certificate_warnings"] = [None, {"reason": "CACertificateExpirationWarning", "observed_at": stamp}]
                self.assertEqual(1, len(self.normalize([node])["alerts"]))

    def test_ca_age_at_transport_boundary_cannot_discard_fresh_leaf_expiration(self):
        node = self.native_node(status="partial")
        node["certificate_checked_at"] = self.now.isoformat()
        node["certificate_warnings"] = [{"reason": "CACertificateExpirationWarning",
                                         "observed_at": (self.now - datetime.timedelta(minutes=65)).isoformat()}]
        with mock.patch.object(overview_module.timezone, "now", return_value=self.now + datetime.timedelta(seconds=2)):
            result = self.service._normalize_nodes({"list": [node]})
        self.assertEqual("partial", result["certificate_status"])
        self.assertEqual(1, len(result["items"][0]["certificates"]))
        self.assertEqual(["certificate_expiring"], [alert["type"] for alert in result["alerts"]])

    def test_unobserved_requires_fresh_native_query_and_explicit_empty_list(self):
        node = self.unobserved_node()
        variants = [dict(node, certificate_source=source) for source in (None, "", "other", [], {})]
        variants.extend(dict(node, certificate_checked_at=stamp) for stamp in (
            None, "invalid", "2026-10-20T00:00:00", [], {},
            (self.now - datetime.timedelta(minutes=65, seconds=1)).isoformat(),
            (self.now + datetime.timedelta(minutes=1, seconds=1)).isoformat()))
        variants.extend(dict(node, certificates=entries) for entries in (None, "", {}, [None]))
        for field in ("certificate_source", "certificate_checked_at", "certificates"):
            missing = dict(node)
            del missing[field]
            variants.append(missing)
        for variant in variants:
            with self.subTest(variant=variant):
                result = self.normalize([variant])
                self.assertEqual("unavailable", result["certificate_status"])
                self.assertEqual([], result["alerts"])

    def test_unobserved_query_freshness_boundaries_and_offsets(self):
        for stamp in ((self.now - datetime.timedelta(minutes=65)).isoformat(),
                      (self.now + datetime.timedelta(minutes=1)).isoformat(), "2026-10-20T08:00:00+08:00"):
            with self.subTest(stamp=stamp):
                node = self.unobserved_node()
                node["certificate_checked_at"] = stamp
                self.assertEqual("not_observed", self.normalize([node])["certificate_status"])

    def test_unobserved_cannot_replace_a_real_certificate_risk(self):
        node = self.native_node(status="not_observed")
        node["certificate_checked_at"] = self.now.isoformat()
        result = self.normalize([node])
        self.assertEqual("partial", result["certificate_status"])
        self.assertEqual("certificate_expiring", result["alerts"][0]["type"])
        self.assertEqual(self.now.isoformat(), result["items"][0]["certificate_observed_at"])
        self.assertEqual(self.now.isoformat(), result["items"][0]["certificate_checked_at"])

    def test_unobserved_aggregation_never_hides_missing_or_partial_coverage(self):
        observed = self.native_node()
        observed["certificates"] = []
        not_applicable = {"name": "other", "certificate_status": "not_applicable"}
        unavailable = {"name": "legacy"}
        partial = self.native_node(status="partial")
        scenarios = [
            ([self.unobserved_node(), observed, not_applicable], "not_observed"),
            ([not_applicable, self.unobserved_node()], "not_observed"),
            ([self.unobserved_node(), unavailable], "partial"),
            ([self.unobserved_node(), partial], "partial"),
            ([unavailable, dict(unavailable, name="legacy-2")], "unavailable"),
        ]
        for nodes, expected in scenarios:
            with self.subTest(expected=expected, nodes=nodes):
                self.assertEqual(expected, self.normalize(nodes)["certificate_status"])

    def test_runtime_accepts_normalized_unobserved_nodes_without_inventing_expiration(self):
        nodes = self.normalize([self.unobserved_node()])
        data = {"nodes": nodes, "workloads_status": "ok", "alarms_status": "ok"}
        with mock.patch.object(self.service, "_list_region_records", return_value=[REGION]), \
                mock.patch.object(self.service, "_fetch_runtime_regions",
                                  return_value={"region-a": {"status": "ok", "data": data}}), \
                mock.patch.object(self.service, "_database_workload_counts",
                                  return_value={"applications": 0, "components": 0}), \
                mock.patch.object(self.service, "_database_running_workload_counts",
                                  return_value={"applications": 0, "components": 0}), \
                mock.patch.object(self.service, "_database_application_alerts", return_value=[]):
            result = self.service._build_runtime("eid")
        self.assertEqual("ok", result["status"])
        self.assertEqual("healthy", result["regions"][0]["status"])
        self.assertEqual(1, result["global"]["clusters"]["healthy"])
        self.assertEqual(0, result["global"]["clusters"]["unavailable"])
        self.assertEqual([], nodes["items"][0]["certificates"])

    def test_fresh_native_ok_and_sparse_warning(self):
        node = self.native_node()
        node["certificates"] = []
        result = self.normalize([node])
        self.assertEqual("ok", result["certificate_status"])
        self.assertEqual([], result["alerts"])
        result = self.normalize([self.native_node(30 * 86400)])
        self.assertEqual("ok", result["certificate_status"])
        self.assertEqual("critical", result["alerts"][0]["severity"])
        self.assertEqual("certificate_expiring", result["alerts"][0]["type"])

    def test_native_invalid_observation_drops_stale_risks(self):
        for observed in [None, "invalid", "2026-10-20T00:00:00",
                         (self.now - datetime.timedelta(minutes=65, seconds=1)).isoformat(),
                         (self.now + datetime.timedelta(minutes=1, seconds=1)).isoformat()]:
            with self.subTest(observed=observed):
                node = self.native_node()
                node["certificate_observed_at"] = observed
                result = self.normalize([node])
                self.assertEqual("unavailable", result["certificate_status"])
                self.assertEqual([], result["alerts"])
                self.assertEqual([], result["items"][0]["certificates"])

        node = self.native_node()
        del node["certificate_observed_at"]
        self.assertEqual("unavailable", self.normalize([node])["certificate_status"])
        self.assertEqual([], self.normalize([node])["alerts"])

    def test_native_observation_boundaries_and_partial_risks(self):
        for seconds in [-3900, 60]:
            node = self.native_node()
            node["certificate_observed_at"] = (self.now + datetime.timedelta(seconds=seconds)).isoformat()
            self.assertEqual("ok", self.normalize([node])["certificate_status"])
        node = self.native_node(status="partial")
        node["certificates"].append({"name": "unknown", "expires_at": self.now.isoformat()})
        result = self.normalize([node])
        self.assertEqual("partial", result["certificate_status"])
        self.assertEqual(1, len(result["alerts"]))
        for status in ["partial", "unavailable"]:
            node = self.native_node(status=status)
            node["certificates"] = []
            self.assertEqual("unavailable", self.normalize([node])["certificate_status"])
        for entries in [None, "invalid"]:
            node = self.native_node()
            node["certificates"] = entries
            self.assertEqual("unavailable", self.normalize([node])["certificate_status"])
        node = self.native_node()
        del node["certificates"]
        self.assertEqual("unavailable", self.normalize([node])["certificate_status"])
        node = self.native_node()
        node["certificates"].append(None)
        result = self.normalize([node])
        self.assertEqual("partial", result["certificate_status"])
        self.assertEqual(1, len(result["alerts"]))

    @override_settings(USE_TZ=False)
    def test_certificate_alerts_with_production_naive_clock(self):
        self.assertTrue(overview_module.timezone.is_naive(overview_module.timezone.now()))
        expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10)).isoformat()
        names = ("agent/client-kubelet.crt", "agent/serving-kubelet.crt",
                 "agent/client-kube-proxy.crt", "agent/client-rke2-controller.crt")
        node = self.node(status="ok")
        node["certificates"] = [{"name": name, "expires_at": expiry} for name in names]
        result = self.service._normalize_nodes({"list": [node]})
        self.assertEqual("ok", result["certificate_status"])
        self.assertEqual(4, len(result["alerts"]))
        self.assertTrue(all(alert["remaining_days"] == 10 for alert in result["alerts"]))

    def test_incomplete_or_unknown_certificates_cannot_report_ok(self):
        self.assertEqual("partial", self.normalize([self.node(31536000, status="ok")])["certificate_status"])
        node = self.node(31536000, status="ok")
        node["certificates"][0]["name"] = "unknown.crt"
        self.assertEqual("unavailable", self.normalize([node])["certificate_status"])
        node = self.node(31536000, status="ok")
        for name in ("agent/serving-kubelet.crt", "agent/client-kube-proxy.crt", "agent/client-rke2-controller.crt"):
            node["certificates"].append(dict(node["certificates"][0], name=name))
        self.assertEqual("ok", self.normalize([node])["certificate_status"])
        node["certificates"].append({"name": "unknown.crt", "expires_at": "2026-10-20T00:00:00Z"})
        self.assertEqual("partial", self.normalize([node])["certificate_status"])

    def test_certificate_offset_is_compared_as_absolute_time(self):
        node = self.node()
        node["certificates"][0]["expires_at"] = "2026-11-19T08:00:00+08:00"
        alert = self.normalize([node])["alerts"][0]
        self.assertEqual(30, alert["remaining_days"])
        self.assertEqual("2026-11-19T00:00:00Z", alert["expires_at"])

    def test_invalid_and_naive_metadata_keeps_valid_risk(self):
        node = self.node(status="ok")
        node["certificates"].extend([None, {"name": "bad", "expires_at": "invalid"},
                                     {"name": "naive", "expires_at": "2026-10-20T00:00:00"}])
        result = self.normalize([node])
        self.assertEqual("partial", result["certificate_status"])
        self.assertEqual(1, len(result["items"][0]["certificates"]))
        self.assertEqual(1, len(result["alerts"]))
        for source in [{"name": "legacy"}, dict(node, certificates=None), dict(node, certificates=[])]:
            self.assertEqual("unavailable", self.normalize([source])["certificate_status"])

    def test_applicability_aggregation_and_existing_alerts(self):
        other = {"name": "other", "certificate_status": "not_applicable"}
        self.assertEqual("not_applicable", self.normalize([other])["certificate_status"])
        self.assertEqual("partial", self.normalize([other, self.node()])["certificate_status"])
        node = self.node()
        node["conditions"] = []
        node["resource"] = {"req_disk": 90, "cap_disk": 100}
        self.assertEqual({"certificate_expiring", "node_not_ready", "disk_usage"},
                         {alert["type"] for alert in self.normalize([node])["alerts"]})

    def test_runtime_health_and_counts_include_certificate_coverage(self):
        for status, alerts, ready, expected in [
                ("ok", [], 1, "healthy"), ("not_applicable", [], 1, "healthy"),
                ("partial", [], 1, "healthy"), ("unavailable", [], 1, "healthy"),
                (None, [], 1, "healthy"), ("partial", [{"type": "certificate_expiring"}], 1, "warning"),
                ("unavailable", [{"type": "certificate_warning"}], 1, "warning"),
                ("unavailable", [{"type": "node_not_ready"}], 0, "warning")]:
            with self.subTest(status=status, expected=expected):
                nodes = {"total": 1, "ready": ready, "certificate_status": status, "alerts": alerts}
                data = {"nodes": nodes, "workloads_status": "ok", "alarms_status": "ok"}
                with mock.patch.object(self.service, "_list_region_records", return_value=[REGION]), \
                        mock.patch.object(self.service, "_fetch_runtime_regions",
                                          return_value={"region-a": {"status": "ok", "data": data}}), \
                        mock.patch.object(self.service, "_database_workload_counts",
                                          return_value={"applications": 0, "components": 0}), \
                        mock.patch.object(self.service, "_database_running_workload_counts",
                                          return_value={"applications": 0, "components": 0}), \
                        mock.patch.object(self.service, "_database_application_alerts", return_value=[]):
                    result = self.service._build_runtime("eid")
                self.assertEqual(expected, result["regions"][0]["status"])
                self.assertEqual(1, result["global"]["nodes"]["total"])
                self.assertEqual(ready, result["global"]["nodes"]["ready"])
                self.assertEqual("ok", result["status"])

    def test_multiple_ready_clusters_do_not_confuse_warning_with_missing_coverage(self):
        region_b = SimpleNamespace(**dict(REGION.__dict__, region_name="region-b", region_id="region-b-id"))
        normal = {"total": 1, "ready": 1, "certificate_status": "not_observed", "alerts": []}
        warning = {"total": 1, "ready": 1, "certificate_status": "unavailable",
                   "alerts": [{"type": "certificate_warning", "severity": "critical", "node_name": "worker"}]}
        data = {"workloads_status": "ok", "alarms_status": "ok", "status": "ok"}
        sections = {"region-a": {"status": "ok", "data": dict(data, nodes=normal)},
                    "region-b": {"status": "ok", "data": dict(data, nodes=warning)}}
        with mock.patch.object(self.service, "_list_region_records", return_value=[REGION, region_b]), \
                mock.patch.object(self.service, "_fetch_runtime_regions", return_value=sections), \
                mock.patch.object(self.service, "_database_workload_counts",
                                  return_value={"applications": 0, "components": 0}), \
                mock.patch.object(self.service, "_database_running_workload_counts",
                                  return_value={"applications": 0, "components": 0}), \
                mock.patch.object(self.service, "_database_application_alerts", return_value=[]):
            result = self.service._build_runtime("eid")
        self.assertEqual("ok", result["status"])
        self.assertEqual({"total": 2, "healthy": 1, "warning": 1, "unavailable": 0, "disabled": 0},
                         result["global"]["clusters"])
        self.assertEqual({"status": "ok", "total": 2, "ready": 2}, result["global"]["nodes"])
