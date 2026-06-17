# -*- coding: utf-8 -*-
# capability_id: console.app-migrate.port-bind-failure-visible
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.groupapp_recovery import groupapps_migrate as migrate_module  # noqa: E402
from console.services.groupapp_recovery.groupapps_migrate import GroupappsMigrateService  # noqa: E402


def _make_port(container_port, is_outer, protocol):
    """Build a fake TenantServicesPort-like object for the port_list loop."""
    port = mock.Mock()
    port.is_outer_service = is_outer
    port.protocol = protocol
    port.container_port = container_port
    return port


class SavePortHttpFailureVisibleTest(TestCase):
    """When an outer HTTP port fails to bind on the data center, the failure
    must be recorded and returned, and subsequent ports must still be processed.
    """

    def setUp(self):
        self.service = mock.Mock()
        self.service.service_id = "svc-1"
        self.service.service_alias = "gr-svc"
        self.service.service_cname = "my-service"
        self.service.service_region = "rg-1"

        self.tenant = mock.Mock()
        self.tenant.tenant_id = "tid-1"
        self.tenant.tenant_name = "team-1"

        # Two outer HTTP ports; first bind fails, second succeeds.
        self.port_a = _make_port(8080, True, "http")
        self.port_b = _make_port(8081, True, "http")

        # __save_port builds TenantServicesPort(**port) then bulk_create then
        # iterates port_list. We replace the constructed list with our fakes.
        self._patchers = []

        def _patch(target, **kwargs):
            p = mock.patch.object(migrate_module, target, **kwargs)
            self._patchers.append(p)
            return p.start()

        self.mock_port_cls = _patch("TenantServicesPort")
        # bulk_create is a no-op; the loop iterates port_list built earlier in
        # the method from real construction. To control the loop, we patch the
        # construction so port_list contains our fakes.
        self.mock_port_cls.side_effect = [self.port_a, self.port_b]
        self.mock_port_cls.objects.bulk_create = mock.Mock()

        self.mock_region_repo = _patch("region_repo")
        region = mock.Mock()
        region.httpdomain = "example.com"
        region.region_id = "rid-1"
        region.region_name = "rg-1"
        self.mock_region_repo.get_region_by_region_name.return_value = region

        self.mock_domain_repo = _patch("domain_repo")
        # No existing domains -> goes into the create + bind branch.
        self.mock_domain_repo.get_service_domain_by_container_port.return_value = []

        self.mock_tcp_domain = _patch("tcp_domain")

        self.mock_region_api = _patch("region_api")
        # First bind raises, second succeeds.
        self.mock_region_api.bind_http_domain.side_effect = [Exception("boom"), None]

    def tearDown(self):
        for p in self._patchers:
            p.stop()

    def _call_save_port(self, ports):
        save_port = getattr(self.service_inst, "_GroupappsMigrateService__save_port")
        return save_port(
            "rg-1",
            self.tenant,
            self.service,
            ports,
            "KUBERNETES_NATIVE_SERVICE",
            [],
            False,
        )

    def setUpInstance(self):
        self.service_inst = GroupappsMigrateService()

    def test_first_port_failure_does_not_skip_second_and_is_reported(self):
        self.setUpInstance()
        ports = [
            {"ID": 1, "container_port": 8080, "protocol": "http", "is_outer_service": True},
            {"ID": 2, "container_port": 8081, "protocol": "http", "is_outer_service": True},
        ]

        # (a) must not raise
        failed = self._call_save_port(ports)

        # (b) the failure list contains the first port
        self.assertTrue(failed, "expected a non-empty failed-port list")
        failed_ports = [f.get("port") for f in failed]
        self.assertIn(8080, failed_ports)
        self.assertNotIn(8081, failed_ports)

        # (c) the second port's region bind was still attempted (no early return)
        self.assertEqual(self.mock_region_api.bind_http_domain.call_count, 2)
        # rollback of the failed local domain record happened
        self.mock_domain_repo.delete_http_domains.assert_called_once()


if __name__ == "__main__":
    import unittest
    unittest.main()
