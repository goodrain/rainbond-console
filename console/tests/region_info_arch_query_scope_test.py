# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services import region_services as region_services_module  # noqa: E402
from console.services.region_services import RegionService  # noqa: E402


class RegionInfoArchQueryScopeTest(TestCase):
    def setUp(self):
        self.service = RegionService()
        self.region = SimpleNamespace(
            region_id="region-id",
            region_alias="Region A",
            region_name="region-a",
            status="1",
            region_type='["private"]',
            enterprise_id="enterprise-id",
            url="https://region-a.example.com",
            scope="private",
            provider="custom",
            provider_cluster_id="cluster-id",
            wsurl="ws://region-a.example.com",
            httpdomain="apps.example.com",
            tcpdomain="192.0.2.10",
            ssl_ca_cert="ca",
            cert_file="cert",
            key_file="key",
            desc="test region",
            create_time="2026-08-08T00:00:00Z",
        )
        self.resource_body = {
            "bean": {
                "cap_mem": 1024,
                "req_mem": 256,
                "cap_cpu": 64,
                "req_cpu": 16,
                "cap_disk": 4 * 1024 * 1024 * 1024,
                "req_disk": 1 * 1024 * 1024 * 1024,
                "resource_proxy_status": True,
                "k8s_version": "v1.30.0",
                "all_node": 7,
                "run_pod_number": 80,
                "pods": 100,
                "node_ready": 7,
            }
        }

    def _convert(self, arch_result=(200, {"list": ["arm64", "amd64", "arm64"]})):
        old_nodes = {"list": [{"architecture": "arm64"}, {"architecture": "amd64"}, {"architecture": "arm64"}]}
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  return_value=({"status": 200}, self.resource_body)), \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes",
                                  return_value=(200, old_nodes)) as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch",
                                  return_value=arch_result) as get_cluster_nodes_arch:
            result = self.service.conver_region_info(self.region, "yes")

        return result, get_cluster_nodes, get_cluster_nodes_arch

    def test_status_check_uses_lightweight_arch_endpoint_and_preserves_resource_fields(self):
        result, get_cluster_nodes, get_cluster_nodes_arch = self._convert()

        get_cluster_nodes.assert_not_called()
        get_cluster_nodes_arch.assert_called_once_with("region-a")
        self.assertEqual(["arm64", "amd64"], list(result["arch"]))
        self.assertEqual(1024, result["total_memory"])
        self.assertEqual(256, result["used_memory"])
        self.assertEqual(64, result["total_cpu"])
        self.assertEqual(16, result["used_cpu"])
        self.assertEqual(4, result["total_disk"])
        self.assertEqual(1, result["used_disk"])
        self.assertEqual("6.1.0", result["rbd_version"])
        self.assertTrue(result["resource_proxy_status"])
        self.assertEqual("v1.30.0", result["k8s_version"])
        self.assertEqual(7, result["all_nodes"])
        self.assertEqual({"running": 80}, result["services_status"])
        self.assertEqual(100, result["pods"])
        self.assertEqual(80, result["run_pod_number"])
        self.assertEqual(7, result["node_ready"])
        self.assertEqual("ok", result["health_status"])

    def test_lightweight_arch_endpoint_exception_keeps_existing_failure_fallback(self):
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  return_value=({"status": 200}, self.resource_body)), \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes",
                                  return_value=(200, {"list": [{"architecture": "amd64"}]})) as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch",
                                  side_effect=ServiceHandleException("region unavailable")) as get_cluster_nodes_arch:
            result = self.service.conver_region_info(self.region, "yes")

        get_cluster_nodes.assert_not_called()
        get_cluster_nodes_arch.assert_called_once_with("region-a")
        self.assertEqual("failure", result["health_status"])
        self.assertEqual("", result["rbd_version"])
        self.assertEqual(1024, result["total_memory"])
        self.assertEqual(64, result["total_cpu"])

    def test_lightweight_arch_endpoint_404_falls_back_to_legacy_nodes(self):
        not_found = region_services_module.region_api.CallApiError(
            "region", "/v2/cluster/nodes/arch", "GET", SimpleNamespace(status=404), {"msg": "not found"})
        legacy_nodes = {
            "list": [
                {
                    "architecture": "arm64"
                },
                {
                    "architecture": "amd64"
                },
                {
                    "architecture": "arm64"
                },
            ]
        }
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  return_value=({"status": 200}, self.resource_body)), \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes",
                                  return_value=(200, legacy_nodes)) as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch",
                                  side_effect=not_found) as get_cluster_nodes_arch:
            result = self.service.conver_region_info(self.region, "yes")

        get_cluster_nodes_arch.assert_called_once_with("region-a")
        get_cluster_nodes.assert_called_once_with("region-a")
        self.assertEqual(["arm64", "amd64"], list(result["arch"]))
        self.assertEqual("ok", result["health_status"])
        self.assertEqual("6.1.0", result["rbd_version"])
        self.assertEqual(1024, result["total_memory"])
        self.assertEqual(256, result["used_memory"])
        self.assertEqual(64, result["total_cpu"])
        self.assertEqual(16, result["used_cpu"])

    def test_lightweight_arch_endpoint_service_404_falls_back_to_legacy_nodes(self):
        not_found = ServiceHandleException("not found", status_code=404)
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  return_value=({"status": 200}, self.resource_body)), \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes",
                                  return_value=(200, {"list": [{"architecture": "amd64"}]})) as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch",
                                  side_effect=not_found):
            result = self.service.conver_region_info(self.region, "yes")

        get_cluster_nodes.assert_called_once_with("region-a")
        self.assertEqual(["amd64"], list(result["arch"]))
        self.assertEqual("ok", result["health_status"])
        self.assertEqual("6.1.0", result["rbd_version"])

    def test_lightweight_arch_endpoint_5xx_does_not_fall_back(self):
        server_error = region_services_module.region_api.CallApiError(
            "region", "/v2/cluster/nodes/arch", "GET", SimpleNamespace(status=503), {"msg": "unavailable"})
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  return_value=({"status": 200}, self.resource_body)), \
                mock.patch.object(region_services_module.region_api, "get_cluster_nodes") as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch",
                                  side_effect=server_error):
            result = self.service.conver_region_info(self.region, "yes")

        get_cluster_nodes.assert_not_called()
        self.assertEqual("failure", result["health_status"])
        self.assertEqual("", result["rbd_version"])

    def test_lightweight_arch_endpoint_timeout_does_not_fall_back(self):
        timeout_error = region_services_module.region_api.CallApiError(
            "region", "/v2/cluster/nodes/arch", "GET", SimpleNamespace(status=101), {"msg": "timeout"})
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  return_value=({"status": 200}, self.resource_body)), \
                mock.patch.object(region_services_module.region_api, "get_cluster_nodes") as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch",
                                  side_effect=timeout_error):
            result = self.service.conver_region_info(self.region, "yes")

        get_cluster_nodes.assert_not_called()
        self.assertEqual("failure", result["health_status"])
        self.assertEqual("", result["rbd_version"])

    def test_non_200_resource_response_does_not_request_architecture(self):
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  return_value=({"status": 503}, {"msg": "unavailable"})), \
                mock.patch.object(region_services_module.region_api, "get_cluster_nodes") as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch") as get_cluster_nodes_arch:
            result = self.service.conver_region_info(self.region, "yes")

        get_cluster_nodes.assert_not_called()
        get_cluster_nodes_arch.assert_not_called()
        self.assertEqual("ok", result["health_status"])
        self.assertEqual("unknown", result["rbd_version"])

    def test_resource_exception_does_not_request_architecture(self):
        with mock.patch.object(region_services_module.enterprise_services,
                               "get_enterprise_by_enterprise_id",
                               return_value=None), \
                mock.patch.object(region_services_module.region_api,
                                  "get_enterprise_api_version_v2",
                                  return_value=(200, {"raw": "6.1.0"})), \
                mock.patch.object(region_services_module.region_api,
                                  "get_region_resources",
                                  side_effect=ServiceHandleException("region unavailable")), \
                mock.patch.object(region_services_module.region_api, "get_cluster_nodes") as get_cluster_nodes, \
                mock.patch.object(region_services_module.region_api,
                                  "get_cluster_nodes_arch") as get_cluster_nodes_arch:
            result = self.service.conver_region_info(self.region, "yes")

        get_cluster_nodes.assert_not_called()
        get_cluster_nodes_arch.assert_not_called()
        self.assertEqual("failure", result["health_status"])
        self.assertEqual("", result["rbd_version"])
