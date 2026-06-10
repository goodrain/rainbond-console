# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from types import SimpleNamespace
from unittest import mock
import unittest

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
openapi_client = ModuleType("openapi_client")
openapi_client.ApiClient = mock.Mock()
openapi_client.MarketOpenapiApi = mock.Mock()
configuration_module = ModuleType("openapi_client.configuration")
configuration_module.Configuration = mock.Mock
rest_module = ModuleType("openapi_client.rest")
rest_module.ApiException = Exception
sys.modules.setdefault("openapi_client", openapi_client)
sys.modules.setdefault("openapi_client.configuration", configuration_module)
sys.modules.setdefault("openapi_client.rest", rest_module)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import kubeblocks_service as kubeblocks_module  # noqa: E402
from console.services.kubeblocks_service import KubeBlocksService  # noqa: E402


class KubeBlocksClusterValidationTests(unittest.TestCase):

    def setUp(self):
        self.service = KubeBlocksService()

    def _valid_params(self):
        return {
            "cluster_name": "mysql-demo",
            "database_type": "mysql",
            "version": "8.0.30",
            "cpu": "500m",
            "memory": "512Mi",
            "storage_size": "10Gi",
            "replicas": 1,
        }

    # capability_id: console.kubeblocks.cluster-resource-validation
    def test_validate_cluster_params_rejects_zero_cpu(self):
        params = self._valid_params()
        params["cpu"] = "0m"

        valid, message = self.service.validate_cluster_params(params)

        self.assertFalse(valid)
        self.assertEqual(message, "CPU 配置必须大于0")

    # capability_id: console.kubeblocks.cluster-resource-validation
    def test_validate_cluster_params_rejects_zero_memory(self):
        params = self._valid_params()
        params["memory"] = "0Mi"

        valid, message = self.service.validate_cluster_params(params)

        self.assertFalse(valid)
        self.assertEqual(message, "内存配置必须大于0")

    # capability_id: console.kubeblocks.cluster-resource-validation
    def test_validate_cluster_params_accepts_positive_decimal_cpu_and_memory(self):
        params = self._valid_params()
        params["cpu"] = "0.5"
        params["memory"] = "0.5Gi"

        valid, message = self.service.validate_cluster_params(params)

        self.assertTrue(valid)
        self.assertEqual(message, "")


class KubeBlocksCreateFlowTests(unittest.TestCase):

    def setUp(self):
        self.service = KubeBlocksService()

    # capability_id: console.kubeblocks.create-no-credential-wait
    def test_create_complete_does_not_wait_for_connection_info(self):
        tenant = SimpleNamespace(tenant_id="tenant-1", namespace="team-a-ns")
        user = SimpleNamespace(nick_name="alice")
        new_service = SimpleNamespace(
            service_id="service-1",
            service_alias="gr000001",
            tenant_id="tenant-1",
        )
        cluster_result = {
            "bean": {
                "metadata": {
                    "name": "test"
                },
                "spec": {
                    "componentSpecs": [{
                        "name": "mysql",
                        "serviceVersion": "8.0.30",
                    }]
                }
            }
        }

        with mock.patch.object(self.service, "_create_component_metadata", return_value=new_service), \
                mock.patch.object(self.service, "_create_cluster", return_value=(True, cluster_result)), \
                mock.patch.object(self.service, "_update_component_name"), \
                mock.patch.object(self.service, "_add_to_application_group"), \
                mock.patch.object(self.service, "_create_region_service"), \
                mock.patch.object(self.service, "_configure_service_ports") as configure_ports, \
                mock.patch.object(self.service, "_deploy_component", return_value={"status": "ok"}), \
                mock.patch.object(self.service, "_build_success_response", return_value={"service_id": "service-1"}), \
                mock.patch.object(self.service, "_cleanup_on_failure"), \
                mock.patch.object(kubeblocks_module.deploy_repo, "create_deploy_relation_by_service_id"), \
                mock.patch.object(kubeblocks_module.region_api, "get_kubeblocks_connect_info",
                                  side_effect=AssertionError("must not wait for connection info during create")) as fetch_info:
            success, result_data, error_msg = self.service.create_complete_kubeblocks_component(
                tenant=tenant,
                user=user,
                region_name="region-a",
                creation_params={
                    "group_id": 2,
                    "database_type": "mysql",
                },
            )

        self.assertTrue(success)
        self.assertEqual(result_data, {"service_id": "service-1"})
        self.assertIsNone(error_msg)
        fetch_info.assert_not_called()
        configure_ports.assert_called_once()
        self.assertEqual(configure_ports.call_args[1]["database_type"], "mysql")

    # capability_id: console.kubeblocks.create-no-credential-wait
    def test_configure_service_ports_uses_database_type_default_port(self):
        tenant = SimpleNamespace(tenant_id="tenant-1")
        user = SimpleNamespace(nick_name="alice")
        service = SimpleNamespace(
            tenant_id="tenant-1",
            service_id="service-1",
            service_alias="gr000001",
        )
        port_data = SimpleNamespace(container_port=3306, protocol="tcp", port_alias="MYSQL")

        self.service.port_service = mock.Mock()
        self.service.port_service.get_service_ports.return_value = []
        self.service.port_service.add_service_port.return_value = (200, "ok", port_data)

        fetch_error = AssertionError("must not fetch connection info for known database port")
        with mock.patch.object(self.service, "_enable_port_outer_service"), \
                mock.patch.object(kubeblocks_module.region_api, "get_kubeblocks_connect_info",
                                  side_effect=fetch_error) as fetch_info:
            self.service._configure_service_ports(
                tenant=tenant,
                user=user,
                region_name="region-a",
                service=service,
                database_type="mysql",
            )

        fetch_info.assert_not_called()
        self.service.port_service.add_service_port.assert_called_once()
        self.assertEqual(self.service.port_service.add_service_port.call_args[1]["container_port"], 3306)
        self.assertEqual(self.service.port_service.add_service_port.call_args[1]["port_alias"], "MYSQL")
