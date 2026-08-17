# -*- coding: utf-8 -*-
import os
import sys
import collections
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src",
                     "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _DummyConfiguration(object):

        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _DummyApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.repositories import service_repo as service_repo_module  # noqa: E402
from console.services import storage_service as storage_service_module  # noqa: E402
from console.services import topological_services as topological_service_module  # noqa: E402
from console.views import app_monitor as app_monitor_module  # noqa: E402


class AttrDict(dict):

    def __getattr__(self, name):
        return self[name]


class MetricResult(dict):

    def __init__(self, metric, value):
        super().__init__(metric=metric, value=value)
        self.metric_accesses = 0

    def __getitem__(self, key):
        if key == "metric":
            self.metric_accesses += 1
        return super().__getitem__(key)


class DynamicService(dict):

    def __init__(self, service_id):
        super().__init__(service_id=service_id)
        self.service_id_accesses = 0

    def __getitem__(self, key):
        if key == "service_id":
            self.service_id_accesses += 1
        return super().__getitem__(key)


class ServiceRepoPerformanceTests(TestCase):

    def test_group_components_load_service_sources_in_one_query(self):
        components = [
            AttrDict(service_id="service-a",
                     create_status="complete",
                     min_memory=128),
            AttrDict(service_id="service-b",
                     create_status="complete",
                     min_memory=256),
        ]
        source_query = mock.MagicMock()
        source_query.values_list.return_value = [("service-a", "source_code"),
                                                 ("service-b", "docker_image")]

        with mock.patch.object(
                service_repo_module.base_service,
                "get_group_services_list",
                return_value=components), mock.patch.object(
                    service_repo_module.base_service,
                    "status_multi_service",
                    return_value=[
                        {
                            "service_id": "service-a",
                            "status": "running",
                            "status_cn": "运行中"
                        },
                        {
                            "service_id": "service-b",
                            "status": "closed",
                            "status_cn": "已关闭"
                        },
                    ]), mock.patch.object(
                        service_repo_module.port_repo,
                        "list_by_service_ids",
                        return_value=[]), mock.patch.object(
                            service_repo_module.TenantServiceInfo.objects,
                            "filter",
                            return_value=source_query) as source_filter:
            result = service_repo_module.service_repo.get_group_service_by_group_id(
                "1", "rainbond", "team-id", "team-name", "enterprise-id")

        source_filter.assert_called_once_with(
            service_id__in=["service-a", "service-b"])
        source_query.values_list.assert_called_once_with(
            "service_id", "service_source")
        self.assertEqual([item["service_source"] for item in result],
                         ["source_code", "docker_image"])


class TopologicalServicePerformanceTests(TestCase):

    def _call_topology_with_dynamic_services(self, dynamic_services):
        app = SimpleNamespace(ID=1, app_id=1, app_type="rainbond", group_name="app")
        relation = SimpleNamespace(service_id="service-a", group_id=1)
        service = SimpleNamespace(
            service_id="service-a",
            service_cname="name-rbd",
            service_alias="service-a",
            service_source="source_code",
            min_memory=128,
            min_node=2,
            create_status="complete",
        )

        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(topological_service_module.ServiceGroupRelation.objects,
                                  "filter",
                                  return_value=[relation]))
            stack.enter_context(
                mock.patch.object(topological_service_module.TenantServiceRelation.objects, "filter", return_value=[]))
            stack.enter_context(
                mock.patch.object(topological_service_module.TenantServiceInfo.objects, "filter", return_value=[service]))
            stack.enter_context(
                mock.patch.object(topological_service_module.ServiceGroup.objects, "filter", return_value=[app]))
            stack.enter_context(
                mock.patch.object(topological_service_module.TenantServicesPort.objects, "filter", return_value=[]))
            stack.enter_context(
                mock.patch.object(topological_service_module.region_api, "service_status", return_value={"list": []}))
            stack.enter_context(
                mock.patch.object(topological_service_module.base_service, "_process_kubeblocks_status", return_value=[]))
            stack.enter_context(
                mock.patch.object(
                    topological_service_module.region_api,
                    "get_dynamic_services_pods",
                    return_value={"list": dynamic_services}))
            stack.enter_context(
                mock.patch.object(
                    topological_service_module.region_app_repo,
                    "get_region_app_id",
                    return_value="region-app-id"))
            stack.enter_context(
                mock.patch.object(topological_service_module.base_service, "get_watch_managed", return_value={}))
            return topological_service_module.topological_service.get_group_topological_graph(
                "1", "rainbond", "team-name", "enterprise-id")

    def test_topology_null_dynamic_service_list_falls_back_to_configured_replicas(self):
        result = self._call_topology_with_dynamic_services(None)

        self.assertEqual(result["json_data"]["service-a"]["node_num"], 2)

    def test_topology_batches_ports_and_counts_dynamic_instances_once(self):
        app = SimpleNamespace(ID=1,
                              app_id=1,
                              app_type="rainbond",
                              group_name="app")
        relations = [
            SimpleNamespace(service_id=service_id, group_id=1)
            for service_id in ("service-a", "service-b", "service-c")
        ]
        services = [
            SimpleNamespace(
                service_id=service_id,
                service_cname="name-rbd",
                service_alias=service_id,
                service_source="source_code",
                min_memory=128,
                min_node=2,
                create_status="complete",
            ) for service_id in ("service-a", "service-b", "service-c")
        ]
        dynamic_services = [
            DynamicService("service-a"),
            DynamicService("service-a"),
            DynamicService("service-b")
        ]
        ports = [
            SimpleNamespace(service_id="service-a", is_outer_service=False),
            SimpleNamespace(service_id="service-a", is_outer_service=True),
            SimpleNamespace(service_id="service-b", is_outer_service=False),
        ]

        def relation_filter(**kwargs):
            if "group_id" in kwargs:
                return relations
            return relations

        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(topological_service_module.ServiceGroupRelation.objects,
                                  "filter",
                                  side_effect=relation_filter))
            stack.enter_context(
                mock.patch.object(topological_service_module.TenantServiceRelation.objects, "filter", return_value=[]))
            stack.enter_context(
                mock.patch.object(topological_service_module.TenantServiceInfo.objects, "filter", return_value=services))
            stack.enter_context(
                mock.patch.object(topological_service_module.ServiceGroup.objects, "filter", return_value=[app]))
            port_filter = stack.enter_context(
                mock.patch.object(topological_service_module.TenantServicesPort.objects, "filter", return_value=ports))
            stack.enter_context(
                mock.patch.object(topological_service_module.region_api, "service_status", return_value={"list": []}))
            stack.enter_context(
                mock.patch.object(topological_service_module.base_service, "_process_kubeblocks_status", return_value=[]))
            stack.enter_context(
                mock.patch.object(
                    topological_service_module.region_api,
                    "get_dynamic_services_pods",
                    return_value={"list": dynamic_services}))
            stack.enter_context(
                mock.patch.object(
                    topological_service_module.region_app_repo,
                    "get_region_app_id",
                    return_value="region-app-id"))
            stack.enter_context(
                mock.patch.object(topological_service_module.base_service, "get_watch_managed", return_value={}))
            result = topological_service_module.topological_service.get_group_topological_graph(
                "1", "rainbond", "team-name", "enterprise-id")

        port_filter.assert_called_once()
        self.assertEqual(set(port_filter.call_args.kwargs["service_id__in"]),
                         {"service-a", "service-b", "service-c"})
        self.assertTrue(result["json_data"]["service-a"]["is_internet"])
        self.assertFalse(result["json_data"]["service-b"]["is_internet"])
        self.assertFalse(result["json_data"]["service-c"]["is_internet"])
        self.assertEqual(result["json_data"]["service-a"]["node_num"], 2)
        self.assertEqual(result["json_data"]["service-b"]["node_num"], 1)
        self.assertEqual(result["json_data"]["service-c"]["node_num"], 0)
        self.assertEqual(
            [item.service_id_accesses for item in dynamic_services], [1, 1, 1])

    def test_internet_topology_still_detects_outer_http_ports(self):
        relation_query = mock.MagicMock()
        relation_query.values_list.return_value = ["service-a"]
        service = SimpleNamespace(
            service_id="service-a",
            service_alias="component",
            service_cname="Component",
            service_region="rainbond",
        )
        port = SimpleNamespace(
            is_outer_service=True,
            protocol="http",
            mapping_port=80,
            container_port=8080,
            to_dict=lambda: {"container_port": 8080},
        )

        with mock.patch.object(
                topological_service_module.ServiceGroupRelation.objects,
                "filter",
                return_value=relation_query), mock.patch.object(
                    topological_service_module.TenantServiceInfo.objects,
                    "filter",
                    return_value=[service]), mock.patch.object(
                        topological_service_module.TenantServicesPort.objects,
                        "filter",
                        return_value=[port]), mock.patch.object(
                            topological_service_module.ServiceDomain.objects,
                            "filter",
                            return_value=[]), mock.patch.object(
                                topological_service_module.region_services,
                                "get_region_httpdomain",
                                return_value="example.com"):
            result = topological_service_module.topological_service.get_internet_topological_graph(
                "1", "team-name")

        self.assertEqual(len(result["result_list"]), 1)
        self.assertEqual(result["result_list"][0]["service_alias"],
                         "component")


class StorageServicePerformanceTests(TestCase):

    def test_prometheus_queries_use_configured_timeout(self):
        response = mock.MagicMock()
        response.json.return_value = {
            "status": "success",
            "data": {
                "result": []
            }
        }

        with mock.patch.dict(os.environ, {"PROMETHEUS_REQUEST_TIMEOUT": "1.5"}), mock.patch.object(
                storage_service_module.requests, "get",
                return_value=response) as request_get, mock.patch.object(
                    storage_service_module.region_app_repo,
                    "get_region_app_id",
                    return_value="region-app-id"):
            service = storage_service_module.StorageService()
            service.get_storage_usage_by_service_id("service-id")
            service.get_tenant_storage_usage("tenant-id")
            service.get_app_storage_usage("rainbond", "1")

        self.assertEqual(request_get.call_count, 3)
        for request_call in request_get.call_args_list:
            self.assertEqual(request_call.kwargs["timeout"], 1.5)

    def test_prometheus_query_timeout_defaults_to_three_seconds_and_degrades(
            self):
        with mock.patch.dict(os.environ, {},
                             clear=True), mock.patch.object(
                                 storage_service_module.requests,
                                 "get",
                                 side_effect=TimeoutError) as request_get:
            result = storage_service_module.StorageService(
            ).get_storage_usage_by_service_id("service-id")

        self.assertEqual(result, 0.0)
        self.assertEqual(request_get.call_args.kwargs["timeout"], 3.0)


class BatchAppMonitorPerformanceTests(TestCase):

    def test_batch_monitor_indexes_throughput_results_without_changing_response(
            self):
        services = [
            SimpleNamespace(service_id="service-a", service_cname="source"),
            SimpleNamespace(service_id="service-b", service_cname="target"),
        ]
        response_results = [
            MetricResult({
                "client": "1111",
                "service_id": "service-b"
            }, [0, "0.5"]),
            MetricResult({
                "client": "public",
                "service_id": "service-a"
            }, [0, "0.8"]),
        ]
        throughput_results = [
            MetricResult({
                "client": "public",
                "service_id": "service-a"
            }, [0, "3"]),
            MetricResult({
                "client": "1111",
                "service_id": "service-b"
            }, [0, "7"]),
        ]
        query_responses = [
            (200, {
                "data": {
                    "result": response_results
                }
            }),
            (200, {
                "data": {
                    "result": throughput_results
                }
            }),
        ]
        view = app_monitor_module.BatchAppMonitorQueryView()
        view.response_region = "rainbond"
        view.tenant = SimpleNamespace(tenant_name="team-name",
                                      enterprise_id="enterprise-id")

        with mock.patch.object(app_monitor_module.group_service,
                               "get_group_services",
                               return_value=services), mock.patch.object(
                                   app_monitor_module.region_api,
                                   "get_services_pods",
                                   return_value={
                                       "list": [{
                                           "pod_ip": "1.1.1.1",
                                           "service_id": "service-a"
                                       }]
                                   }), mock.patch.object(
                                       app_monitor_module.region_api,
                                       "get_query_data",
                                       side_effect=query_responses):
            response = view.get(SimpleNamespace(), group_id="1")

        self.assertEqual(
            response.data["data"]["list"],
            [
                {
                    "is_web": False,
                    "target": "service-b",
                    "source": "service-a",
                    "data": {
                        "response_time": 0.5,
                        "throughput_rate": 7.0
                    },
                },
                {
                    "is_web": True,
                    "target": "service-a",
                    "source": None,
                    "data": {
                        "response_time": 0.8,
                        "throughput_rate": 3.0
                    },
                },
            ],
        )
        self.assertEqual([item.metric_accesses for item in throughput_results],
                         [1, 1])
