# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType
from types import SimpleNamespace
from unittest import mock
import unittest

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired
    except ImportError:
        typing.NotRequired = lambda item: item

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

from django.db.models.query import QuerySet  # noqa: E402

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)

from console.services import kubeblocks_service as kubeblocks_module  # noqa: E402
from console.services.kubeblocks_service import KubeBlocksService  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402


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

    # capability_id: console.kubeblocks.app-resource-statistics
    def test_build_cluster_request_prefers_region_app_id_for_resource_statistics(self):
        new_service = SimpleNamespace(
            service_id="service-1",
            service_alias="gr000001",
        )

        cluster_request = self.service._build_cluster_request(
            {
                "cluster_name": "mysql-demo",
                "database_type": "mysql",
                "version": "8.0.30",
                "cpu": "500m",
                "memory": "512Mi",
                "storage_size": "10Gi",
                "replicas": 1,
                "storage_class": "standard",
                "group_id": 2,
                "region_app_id": "region-app-2",
            },
            new_service,
            "team-a-ns",
        )

        self.assertEqual(cluster_request["rbdService"]["service_id"], "service-1")
        self.assertEqual(cluster_request["rbdService"]["app_id"], "region-app-2")

    # capability_id: console.kubeblocks.app-resource-statistics
    def test_create_cluster_resolves_region_app_id_for_resource_statistics(self):
        tenant = SimpleNamespace(tenant_id="tenant-1", namespace="team-a-ns")
        user = SimpleNamespace(nick_name="alice")
        service = SimpleNamespace(
            service_id="service-1",
            service_alias="gr000001",
            k8s_component_name="mysql-demo",
        )
        params = {
            "cluster_name": "mysql-demo",
            "database_type": "mysql",
            "version": "8.0.30",
            "cpu": "500m",
            "memory": "512Mi",
            "storage_size": "10Gi",
            "replicas": 1,
            "storage_class": "standard",
            "group_id": 2,
        }

        with mock.patch.object(kubeblocks_module.region_app_repo, "get_region_app_id",
                               return_value="region-app-2") as get_region_app_id, \
                mock.patch.object(kubeblocks_module.region_api, "create_kubeblocks_cluster",
                                  return_value=({"status": 200}, {"bean": {}})) as create_cluster:
            success, body = self.service._create_cluster(
                tenant=tenant,
                user=user,
                region_name="region-a",
                params=params,
                kubeblocks_service=service,
            )

        self.assertTrue(success)
        self.assertEqual(body, {"bean": {}})
        get_region_app_id.assert_called_once_with("region-a", 2)
        sent_body = create_cluster.call_args[0][1]
        self.assertEqual(sent_body["rbdService"]["app_id"], "region-app-2")

    # capability_id: console.kubeblocks.create-credential-sync
    def test_create_complete_syncs_database_credentials(self):
        tenant = SimpleNamespace(tenant_id="tenant-1", namespace="team-a-ns")
        user = SimpleNamespace(nick_name="alice", get_username=lambda: "alice")
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
        connect_ctx = {"connect_infos": [{"user": "stub-user", "password": "stub-password"}]}

        with mock.patch.object(self.service, "_create_component_metadata", return_value=new_service), \
                mock.patch.object(self.service, "_create_cluster", return_value=(True, cluster_result)), \
                mock.patch.object(self.service, "_update_component_name"), \
                mock.patch.object(self.service, "_add_to_application_group"), \
                mock.patch.object(self.service, "_create_region_service"), \
                mock.patch.object(self.service, "_fetch_connection_info", return_value=connect_ctx) as fetch_info, \
                mock.patch.object(self.service, "_add_database_env_vars") as add_database_env_vars, \
                mock.patch.object(self.service, "_configure_service_ports") as configure_ports, \
                mock.patch.object(self.service, "_deploy_component", return_value={"status": "ok"}), \
                mock.patch.object(self.service, "_build_success_response", return_value={"service_id": "service-1"}), \
                mock.patch.object(self.service, "_cleanup_on_failure"), \
                mock.patch.object(kubeblocks_module.deploy_repo, "create_deploy_relation_by_service_id"):
            create_complete = self.service.create_complete_kubeblocks_component.__wrapped__
            success, result_data, error_msg = create_complete(
                self.service,
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
        fetch_info.assert_called_once_with(region_name="region-a", service_id="service-1", msg_show="获取数据库连接信息失败")
        add_database_env_vars.assert_called_once()
        self.assertEqual(add_database_env_vars.call_args[1]["connect_ctx"], fetch_info.return_value)
        self.assertEqual(add_database_env_vars.call_args[1]["database_type"], "mysql")
        configure_ports.assert_called_once()
        self.assertEqual(configure_ports.call_args[1]["connect_ctx"], fetch_info.return_value)
        self.assertEqual(configure_ports.call_args[1]["database_type"], "mysql")

    # capability_id: console.kubeblocks.create-credential-sync
    def test_add_database_env_vars_uses_database_user_and_password_names(self):
        tenant = SimpleNamespace(tenant_id="tenant-1", enterprise_id="enterprise-1", tenant_name="team-a")
        user = SimpleNamespace(nick_name="alice", get_username=lambda: "alice")
        service = SimpleNamespace(
            tenant_id="tenant-1",
            service_id="service-1",
            service_alias="gr000001",
            service_region="region-a",
            create_status="creating",
        )

        self.service.env_service = mock.Mock()
        self.service.env_service.add_service_env_var.return_value = (200, "success", SimpleNamespace())

        self.service._add_database_env_vars(
            tenant=tenant,
            user=user,
            region_name="region-a",
            service=service,
            connect_ctx={"connect_infos": [{"user": "stub-user", "password": "stub-password"}]},
            database_type="mysql",
        )

        attr_names = [call_args[1]["attr_name"] for call_args in self.service.env_service.add_service_env_var.call_args_list]
        self.assertEqual(attr_names, ["MYSQL_USER", "MYSQL_PASSWORD"])

    # capability_id: console.kubeblocks.create-credential-sync
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

    # capability_id: console.kubeblocks.backup-repo.ready-guard
    def test_create_cluster_returns_backup_repo_not_ready_message(self):
        tenant = SimpleNamespace(tenant_id="tenant-1", namespace="team-a-ns")
        user = SimpleNamespace(nick_name="alice")
        service = SimpleNamespace(
            service_id="service-1",
            service_alias="gr000001",
            k8s_component_name="mysql-demo",
        )
        params = {
            "cluster_name": "mysql-demo",
            "database_type": "mysql",
            "version": "8.0.30",
            "cpu": "500m",
            "memory": "512Mi",
            "storage_size": "10Gi",
            "backup_repo": "team-a-ns-prod",
        }

        with mock.patch.object(self.service, "ensure_backup_repo_ready_for_use",
                               side_effect=ServiceHandleException(
                                   msg="backup repo is not ready",
                                   msg_show="备份仓库正在检测中，请检测通过后再使用",
                               )), \
                mock.patch.object(kubeblocks_module.region_api, "create_kubeblocks_cluster") as create_cluster:
            success, message = self.service._create_cluster(
                tenant=tenant,
                user=user,
                region_name="region-a",
                params=params,
                kubeblocks_service=service,
            )

        self.assertFalse(success)
        self.assertEqual(message, "备份仓库正在检测中，请检测通过后再使用")
        create_cluster.assert_not_called()
