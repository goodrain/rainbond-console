"""Visit actions must include every exposed port and every mapping on that port."""
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()

port_module = importlib.import_module("console.services.app_config.port_service")


class Rows(list):
    def filter(self, **criteria):
        return Rows(row for row in self if all(getattr(row, key) == value for key, value in criteria.items()))


def component_port(number, protocol, outer=True):
    return SimpleNamespace(
        service_id="component", tenant_id="tenant", container_port=number, protocol=protocol,
        is_outer_service=outer, is_inner_service=True,
        to_dict=lambda: {"container_port": number, "protocol": protocol})


def mapping(number, external_port, enabled=True):
    return SimpleNamespace(
        service_id="component", tenant_id="tenant", region_id="region", container_port=number,
        end_point="0.0.0.0:{}".format(external_port), is_outer_service=enabled)


class PortVisitAddressesTests(unittest.TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant", tenant_name="demo", enterprise_id="enterprise")
        self.service = SimpleNamespace(
            service_id="component", tenant_id="tenant", service_alias="demo", service_region="region", service_cname="Demo")
        self.region = SimpleNamespace(region_id="region", region_name="region", tcpdomain="192.0.2.10")
        self.subject = port_module.AppPortService()
        self.ports = []
        self.mappings = Rows()
        self.domains = Rows()
        self.patch(port_module.port_repo, "get_service_ports", side_effect=lambda *args: self.ports)
        self.patch(port_module.port_repo, "list_by_service_ids", side_effect=lambda *args: self.ports)
        self.patch(port_module.region_repo, "get_region_by_region_name", return_value=self.region)
        self.patch(port_module.region_repo, "get_region_info_all", return_value=Rows([self.region]))
        self.patch(port_module.domain_repo, "get_service_domain_all", side_effect=lambda: self.domains)
        self.patch(port_module.tcp_domain, "get_service_tcpdomain_all", side_effect=lambda: self.mappings)
        self.patch(port_module.tcp_domain, "get_service_tcp_domains_by_service_id_and_port",
                   side_effect=lambda sid, port: self.mappings.filter(service_id=sid, container_port=port))
        self.patch(port_module.tcp_domain, "get_service_tcpdomain", side_effect=self.first_mapping)
        self.patch(self.subject, "get_port_associated_env", return_value=[])
        self.patch(self.subject, "_AppPortService__get_port_access_url", side_effect=self.http_urls)

    def patch(self, target, name, **kwargs):
        patcher = patch.object(target, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def first_mapping(self, tenant_id, region_id, service_id, container_port):
        rows = self.mappings.filter(tenant_id=tenant_id, region_id=region_id,
                                    service_id=service_id, container_port=container_port)
        return rows[0] if rows else None

    def http_urls(self, tenant, service, port):
        return ["http://{}/".format(row.domain_name) for row in self.domains
                if row.container_port == port and row.is_outer_service]

    def assert_addresses(self, expected, access_type):
        kind, info = self.subject.get_access_info(self.tenant, self.service)
        self.assertEqual(kind, access_type)
        self.assertEqual([url for port in info for url in port["access_urls"]], expected)
        batch = self.subject.list_access_infos(self.tenant, [self.service])["component"]
        self.assertEqual(batch["access_type"], access_type)
        self.assertEqual([url for port in batch["access_info"] for url in port["access_urls"]], expected)

    def test_http_udp_and_dual_ports_all_appear(self):
        self.ports = [component_port(8080, "http"), component_port(8081, "udp"), component_port(8082, "tcp+udp")]
        self.mappings = Rows([mapping(8080, 30000), mapping(8081, 30001), mapping(8082, 30002)])
        self.assert_addresses(["192.0.2.10:30000", "192.0.2.10:30001", "192.0.2.10:30002"], "not_http_outer")

    def test_one_tcp_port_keeps_all_active_mappings(self):
        self.ports = [component_port(8080, "tcp+udp")]
        self.mappings = Rows([mapping(8080, 30000), mapping(8080, 30001), mapping(8080, 30002),
                              mapping(8080, 30003, enabled=False)])
        self.assert_addresses(["192.0.2.10:30000", "192.0.2.10:30001", "192.0.2.10:30002"], "not_http_outer")

    def test_http_domains_and_nodeports_on_same_port_are_combined(self):
        self.ports = [component_port(8080, "http")]
        self.domains = Rows([
            SimpleNamespace(service_id="component", container_port=8080, domain_name="demo.example",
                            domain_path="/", protocol="http", is_outer_service=True)])
        self.mappings = Rows([mapping(8080, 30000), mapping(8080, 30001)])
        self.assert_addresses(["http://demo.example/", "192.0.2.10:30000", "192.0.2.10:30001"], "not_http_outer")

    def test_http_only_keeps_existing_visit_type(self):
        self.ports = [component_port(8080, "http"), component_port(8081, "http")]
        self.domains = Rows([
            SimpleNamespace(service_id="component", container_port=port, domain_name=name,
                            domain_path="/", protocol="http", is_outer_service=True)
            for port, name in [(8080, "one.example"), (8081, "two.example")]])
        self.assert_addresses(["http://one.example/", "http://two.example/"], "http_port")

    def test_duplicate_mapping_address_is_listed_once(self):
        self.ports = [component_port(8080, "tcp+udp")]
        self.mappings = Rows([mapping(8080, 30000), mapping(8080, 30000)])
        self.assert_addresses(["192.0.2.10:30000"], "not_http_outer")

    def test_mixed_ports_keep_http_domains_and_all_stream_addresses(self):
        self.ports = [component_port(8080, "http"), component_port(8081, "udp"), component_port(8082, "tcp+udp"),
                      component_port(8083, "http"), component_port(8084, "http")]
        self.mappings = Rows([mapping(8080, 30000), mapping(8081, 30001), mapping(8082, 30002)])
        self.domains = Rows([
            SimpleNamespace(service_id="component", container_port=port, domain_name=name,
                            domain_path="/", protocol="http", is_outer_service=True)
            for port, name in [(8083, "one.example"), (8084, "two.example")]])
        self.assert_addresses(["192.0.2.10:30000", "http://one.example/", "http://two.example/",
                               "192.0.2.10:30001", "192.0.2.10:30002"], "not_http_outer")

    def test_internal_only_port_keeps_existing_behavior(self):
        self.ports = [component_port(8080, "http", outer=False)]
        kind, info = self.subject.get_access_info(self.tenant, self.service)
        self.assertEqual(kind, "http_inner")
        self.assertEqual(info[0]["container_port"], 8080)
        self.subject._AppPortService__get_port_access_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
