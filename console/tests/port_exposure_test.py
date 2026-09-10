import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from console.utils.port_exposure import get_bindings, supports


class PortExposureTests(unittest.TestCase):
    def test_http_component_includes_all_l4_mappings_without_writing_port(self):
        api = MagicMock()
        api.api_gateway_get_proxy.side_effect = [
            {"list": []},
            {"list": [
                {"service_name": "svc-30010", "nodePort": 30010, "protocols": ["TCP"]},
                {"service_name": "svc-30020", "nodePort": 30020, "protocols": ["UDP"]},
                {"service_name": "svc-30030", "nodePort": 30030, "protocols": ["TCP", "UDP"]},
            ]},
        ]
        port = SimpleNamespace(container_port=8080, protocol="http", save=MagicMock())
        tenant = SimpleNamespace(tenant_name="team", tenant_id="tenant")
        service = SimpleNamespace(service_alias="svc", service_id="component")
        result = get_bindings(api, "region", tenant, service, port)
        self.assertTrue(result["is_outer_service"])
        self.assertEqual(result["bind_domains"], [])
        self.assertEqual([p["protocol"] for p in result["bind_tcp_domains"]], ["tcp", "udp", "tcp+udp"])
        self.assertEqual(result["bind_tcp_domains"][2]["service_name"], "svc-30030")
        port.save.assert_not_called()

    def test_failed_query_is_not_an_empty_binding_list(self):
        api = MagicMock()
        api.api_gateway_get_proxy.return_value = None
        with self.assertRaises(ValueError):
            get_bindings(api, "region", SimpleNamespace(tenant_name="team", tenant_id="tenant"),
                         SimpleNamespace(service_alias="svc", service_id="id"), SimpleNamespace(container_port=53))

    def test_protocol_compatibility(self):
        self.assertTrue(supports("http", "tcp"))
        self.assertFalse(supports("http", "udp"))
        self.assertTrue(supports("tcp+udp", "udp"))
        self.assertFalse(supports("tcp", "tcp+udp"))


if __name__ == "__main__":
    unittest.main()
