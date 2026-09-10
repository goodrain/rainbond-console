"""Regression for HTTP component ports exposed through a four-layer gateway rule."""
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()

from django.test import RequestFactory  # noqa: E402
from console.views.app_config.app_port import AppPortView  # noqa: E402

port_module = importlib.import_module("console.services.app_config.port_service")


class PortViewExposureTests(unittest.TestCase):
    def test_http_port_reports_tcp_mapping_without_saving_flags(self):
        port = SimpleNamespace(
            container_port=8080, protocol="http", is_inner_service=False, is_outer_service=False,
            save=MagicMock(), to_dict=lambda: {"container_port": 8080, "protocol": "http", "is_outer_service": False})
        view = AppPortView()
        view.tenant = SimpleNamespace(tenant_id="tenant", tenant_name="team")
        view.service = SimpleNamespace(service_id="component", service_alias="svc")
        view.region = "region"
        with patch.object(port_module.AppPortService, "get_service_ports", return_value=[port]), \
                patch.object(port_module.AppPortService, "get_port_variables", return_value={"environment": []}), \
                patch.object(port_module.region_api, "api_gateway_get_proxy", side_effect=[
                    {"list": []}, {"list": [{"service_name": "svc-30010", "nodePort": 30010, "protocols": ["TCP"]}]}]):
            response = view.get(RequestFactory().get("/ports"))
        result = response.data["data"]["list"][0]
        self.assertTrue(result["is_outer_service"])
        self.assertEqual(result["protocol"], "http")
        self.assertEqual(result["bind_tcp_domains"][0]["protocol"], "tcp")
        self.assertFalse(port.is_outer_service)
        port.save.assert_not_called()

    def test_gateway_sync_keeps_existing_rule_identity_and_settings(self):
        from www.models.main import ServiceTcpDomain
        port = MagicMock(pk=1, container_port=53)
        mapping = SimpleNamespace(tcp_rule_id="existing-rule", rule_extensions="existing-settings", save=MagicMock())
        bindings = {"is_outer_service": True, "bind_domains": [], "bind_tcp_domains": [
            {"end_point": "0.0.0.0:30030", "protocol": "tcp+udp"}]}
        service = SimpleNamespace(service_id="component", service_alias="dns", service_cname="DNS")
        tenant = SimpleNamespace(tenant_id="tenant")
        region = SimpleNamespace(region_id="region")
        with patch.object(port_module.TenantServicesPort.objects, "select_for_update") as locked, \
                patch.object(port_module.AppPortService, "get_external_bindings", return_value=bindings), \
                patch.object(ServiceTcpDomain.objects, "get_or_create", return_value=(mapping, False)), \
                patch.object(ServiceTcpDomain.objects, "filter"):
            locked.return_value.get.return_value = port
            port_module.AppPortService.sync_external_bindings.__wrapped__(
                port_module.AppPortService(), tenant, service, region, port)
        self.assertEqual(mapping.tcp_rule_id, "existing-rule")
        self.assertEqual(mapping.rule_extensions, "existing-settings")
        self.assertEqual(mapping.protocol, "tcp+udp")
        self.assertTrue(port.is_outer_service)


if __name__ == "__main__":
    unittest.main()
