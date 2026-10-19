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
                            "ready": 2
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
                "rbd_version": "v6.9.12",
                "k8s_version": "v1.30.4",
            }
        }))

        result = self.service._fetch_cluster_resources("eid", "region-a")

        self.assertEqual({"running": 17, "total": None}, result["pods"])
        self.assertEqual(25.0, result["cpu"]["allocation_percent"])
        self.assertEqual("MiB", result["memory"]["unit"])
        self.service._region_api.get_region_resources.assert_called_once_with("eid",
                                                                              region="region-a",
                                                                              connect_timeout=2,
                                                                              timeout=3,
                                                                              retries=0)

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
        self.assertEqual({
            "connect_timeout": 2,
            "timeout": 3,
            "retries": 0
        }, self.service._region_api.get_query_range_data.call_args.kwargs)
        self.assertEqual([("platform-overview:metrics:eid:region-a:cpu:6h", 15)], self.service._cache.set_calls)

    def test_metric_query_failure_returns_unavailable(self):
        self.service._get_enterprise_region = mock.Mock(return_value=REGION)
        self.service._metric_tenant_name = mock.Mock(return_value="team-a")
        self.service._region_api.get_query_range_data = mock.Mock(return_value=({"status": 503}, None))

        result = self.service.get_metrics("eid", "region-a", "memory", "1h")

        self.assertEqual("unavailable", result["status"])
        self.assertEqual([], result["series"])
        self.assertEqual({
            "connect_timeout": 2,
            "timeout": 3,
            "retries": 0
        }, self.service._region_api.get_query_range_data.call_args.kwargs)

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

        self.assertEqual("ok", result["status"])
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


class PlatformPluginInstalledOnlyTest(TestCase):
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
