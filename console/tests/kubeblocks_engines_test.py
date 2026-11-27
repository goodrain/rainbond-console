from types import SimpleNamespace
from unittest import TestCase, mock

from kubeblocks_cluster_validation_test import KubeBlocksService, kubeblocks_module


class KubeBlocksAdditionalEngineTests(TestCase):
    def setUp(self):
        self.service = KubeBlocksService()
        self.service.env_service = mock.Mock()
        self.service.env_service.add_service_env_var.return_value = (200, "", None)

    def test_kafka_without_account_injects_bootstrap_servers(self):
        self.service._add_database_env_vars(None,
                                            mock.Mock(),
                                            "region",
                                            mock.Mock(),
                                            database_type="kafka",
                                            connect_ctx={
                                                "connect_infos": [{
                                                    "auth_type": "none",
                                                    "host": "events-kafka-combine-headless.team.svc",
                                                    "ports": [{
                                                        "name": "kafka",
                                                        "port": 9092,
                                                        "protocol": "tcp"
                                                    }]
                                                }]
                                            })
        envs = {
            call.kwargs["attr_name"]: call.kwargs["attr_value"]
            for call in self.service.env_service.add_service_env_var.call_args_list
        }
        self.assertEqual(envs["KAFKA_BOOTSTRAP_SERVERS"], "events-kafka-combine-headless.team.svc:9092")
        self.assertNotIn("KAFKA_PASSWORD", envs)
        self.assertNotIn("KAFKA_USER", envs)

    def test_clickhouse_registers_both_client_ports(self):
        self.service.port_service = mock.Mock()
        self.service.port_service.get_service_ports.return_value = []
        self.service.port_service.add_service_port.return_value = (200, "", SimpleNamespace())
        self.service._enable_port_outer_service = mock.Mock()
        self.service._configure_service_ports(None,
                                              mock.Mock(),
                                              "region",
                                              mock.Mock(),
                                              database_type="clickhouse",
                                              connect_ctx={
                                                  "port":
                                                  9000,
                                                  "connect_infos": [{
                                                      "external_access":
                                                      False,
                                                      "ports": [{
                                                          "name": "clickhouse",
                                                          "port": 9000,
                                                          "protocol": "tcp"
                                                      }, {
                                                          "name": "clickhouse-http",
                                                          "port": 8123,
                                                          "protocol": "http"
                                                      }]
                                                  }]
                                              })
        calls = self.service.port_service.add_service_port.call_args_list
        self.assertEqual([call.kwargs["container_port"] for call in calls], [9000, 8123])
        self.assertTrue(all(not call.kwargs["is_outer_service"] for call in calls))
        self.service._enable_port_outer_service.assert_not_called()

    def test_topology_reaches_adapter_request(self):
        request = self.service._build_cluster_request(
            {
                "cluster_name": "events",
                "database_type": "kafka",
                "version": "3.3.2",
                "topology": "combined",
                "cpu": "1",
                "memory": "2Gi",
                "storage_size": "20Gi",
                "replicas": 3
            }, SimpleNamespace(service_id="svc", service_alias="events"), "team")
        self.assertEqual(request["topology"], "combined")

    def test_existing_engine_connection_variables_remain_compatible(self):
        for kind, port in (("mysql", 3306), ("postgresql", 6432), ("redis", 6379), ("rabbitmq", 5672)):
            with self.subTest(engine=kind):
                self.service.env_service.reset_mock()
                self.service._add_database_env_vars(
                    None, mock.Mock(), "region", mock.Mock(), database_type=kind,
                    connect_ctx={"connect_infos": [{"user": "account", "password": "$DB_PASSWORD"}]})
                envs = {call.kwargs["attr_name"] for call in self.service.env_service.add_service_env_var.call_args_list}
                self.assertEqual(envs, {f"{kind.upper()}_USER", f"{kind.upper()}_PASSWORD"})
                self.assertEqual(self.service._get_default_port_by_database_type(kind), port)

    def test_restore_refreshes_connection_instead_of_copying_old_host(self):
        old = SimpleNamespace(service_cname="analytics", service_id="old", k8s_component_name="analytics-a123-clickhouse")
        new = mock.Mock(service_id="new", service_alias="restored")
        self.service.group_service = mock.Mock()
        self.service.group_service.get_service_group_info.return_value = SimpleNamespace(ID=1)
        self.service.port_service = mock.Mock()
        self.service.port_service.get_service_ports.return_value = []
        self.service.env_service.get_env_var.return_value = []
        restore_result = (200, {"bean": {"new_service": "restored-clickhouse"}})
        with mock.patch.object(kubeblocks_module.app_service, "create_kubeblocks_component", return_value=(200, "", new)), \
                mock.patch.object(kubeblocks_module.deploy_repo, "create_deploy_relation_by_service_id"), \
                mock.patch.object(self.service, "restore_cluster_from_backup", return_value=restore_result), \
                mock.patch.object(self.service, "_add_to_application_group"), \
                mock.patch.object(self.service, "_create_region_service"), \
                mock.patch.object(self.service, "_deploy_component"), \
                mock.patch.object(self.service, "_configure_service_ports"), \
                mock.patch.object(self.service, "_fetch_connection_info", return_value={"fresh": True}) as fetch, \
                mock.patch.object(self.service, "_add_database_env_vars") as inject:
            status, _ = self.service.restore_component_from_backup(None, mock.Mock(), "region", old, "backup")
        self.assertEqual(status, 200)
        fetch.assert_called_once()
        self.assertEqual(inject.call_args.kwargs["database_type"], "clickhouse")
        self.assertEqual(inject.call_args.kwargs["connect_ctx"], {"fresh": True})
