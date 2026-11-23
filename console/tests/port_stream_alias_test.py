"""Legacy stream input must reach storage and region as the TCP transport."""
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()

from www.models.main import TenantServicesPort  # noqa: E402

port_module = importlib.import_module("console.services.app_config.port_service")


class StreamPortAliasTests(unittest.TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant", tenant_name="team", enterprise_id="enterprise")
        self.service = SimpleNamespace(tenant_id="tenant", service_id="component", service_alias="mysql",
                                       service_region="region", create_status="complete", service_source="docker_image")
        self.app = SimpleNamespace(governance_mode="KUBERNETES_NATIVE_SERVICE")
        self.port = TenantServicesPort(ID=1, tenant_id="tenant", service_id="component", container_port=3306,
                                       protocol="stream", port_alias="MYSQL", k8s_service_name="mysql",
                                       is_inner_service=True, is_outer_service=False)
        self.port.save = MagicMock()
        self.api = self.mock(port_module, "region_api")
        self.repo = self.mock(port_module, "port_repo")
        self.repo.get_service_ports.return_value = []
        self.repo.get_service_port_by_port.return_value = None
        self.repo.add_service_port.side_effect = lambda **data: TenantServicesPort(**data)
        self.mock(port_module.AppPortService, "check_k8s_service_name")
        self.mock(port_module.AppPortService, "check_port")

    def mock(self, target, name, *args, **kwargs):
        patcher = patch.object(target, name, *args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_single_add_sends_and_saves_tcp(self):
        code, _, row = port_module.AppPortService().add_service_port(
            self.tenant, self.service, 3306, protocol="stream", port_alias="MYSQL", app=self.app)

        self.assertEqual(code, 200)
        self.assertEqual(row.protocol, "tcp")
        sent = self.api.add_service_port.call_args.args[3]["port"][0]
        self.assertEqual(sent["protocol"], "tcp")
        self.assertEqual(self.repo.add_service_port.call_args.kwargs["protocol"], "tcp")

    def test_batch_add_preserves_other_transports_and_does_not_mutate_input(self):
        data = [{"port": 3306, "protocol": "stream"}, {"port": 8080, "protocol": "http"},
                {"port": 53, "protocol": "udp"}, {"port": 5353, "protocol": "tcp+udp"}]
        rows = port_module.AppPortService.batch_add_service_ports.__wrapped__(
            port_module.AppPortService(), self.tenant, self.service, data, app=self.app)

        self.assertEqual([row.protocol for row in rows], ["tcp", "http", "udp", "tcp+udp"])
        sent = self.api.add_service_port.call_args.args[3]["port"]
        self.assertEqual([row["protocol"] for row in sent], ["tcp", "http", "udp", "tcp+udp"])
        self.assertEqual(data[0]["protocol"], "stream")

    def test_change_reconciles_an_existing_stream_row_instead_of_returning_unchanged(self):
        self.repo.get_service_port_by_port.return_value = self.port
        self.mock(port_module.region_repo, "get_region_by_region_name", return_value=SimpleNamespace())

        code, _, _ = port_module.AppPortService.manage_port.__wrapped__(
            port_module.AppPortService(), self.tenant, self.service, "region", 3306, "change_protocol", "stream", None)

        self.assertEqual(code, 200)
        self.assertEqual(self.port.protocol, "tcp")
        self.port.save.assert_called_once()
        sent = self.api.update_service_port.call_args.args[3]["port"][0]
        self.assertEqual(sent["protocol"], "tcp")

    def test_direct_update_normalizes_outgoing_copy(self):
        data = [{"container_port": 3306, "protocol": "stream"},
                {"container_port": 8080, "protocol": "http"}, {"container_port": 9000}]
        port_module.AppPortService.update_service_port(self.tenant, "region", "mysql", data, "operator")

        sent = self.api.update_service_port.call_args.args[3]
        self.assertEqual(sent["port"][0]["protocol"], "tcp")
        self.assertEqual(sent["port"][1]["protocol"], "http")
        self.assertNotIn("protocol", sent["port"][2])
        self.assertEqual(sent["operator"], "operator")
        self.assertEqual(data[0]["protocol"], "stream")


if __name__ == "__main__":
    unittest.main()
