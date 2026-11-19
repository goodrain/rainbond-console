"""Transport protocol support must survive validation and port conversion."""
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()

from openapi.serializer.app_serializer import ComponentPortReqSerializers, ComponentUpdatePortReqSerializers  # noqa: E402

new_components_module = importlib.import_module("console.services.market_app.new_components")


class PortProtocolCompatibilityTests(unittest.TestCase):
    def test_create_and_update_accept_transport_protocols(self):
        for protocol in ("tcp", "udp", "tcp+udp"):
            for serializer in (
                ComponentPortReqSerializers(data={"port": 8082, "protocol": protocol, "is_inner_service": True}),
                ComponentUpdatePortReqSerializers(data={"action": "change_protocol", "protocol": protocol}),
            ):
                with self.subTest(protocol=protocol, serializer=type(serializer).__name__):
                    self.assertTrue(serializer.is_valid(), serializer.errors)
                    self.assertEqual(serializer.validated_data["protocol"], protocol)

    def test_port_conversion_preserves_transport_protocols(self):
        builder = new_components_module.NewComponents.__new__(new_components_module.NewComponents)
        component = SimpleNamespace(tenant_id="tenant", service_id="component", service_alias="demo")
        with patch.object(new_components_module.port_service, "check_k8s_service_name"):
            for protocol in ("tcp", "udp", "tcp+udp"):
                with self.subTest(protocol=protocol):
                    ports = builder._template_to_ports(component, [{"container_port": 8082, "protocol": protocol}])
                    self.assertEqual(ports[0].protocol, protocol)

    def test_port_conversion_respects_explicit_inner_service_and_keeps_legacy_default(self):
        builder = new_components_module.NewComponents.__new__(new_components_module.NewComponents)
        component = SimpleNamespace(tenant_id="tenant", service_id="component", service_alias="demo")

        with patch.object(new_components_module.port_service, "check_k8s_service_name"):
            ports = builder._template_to_ports(
                component,
                [
                    {"container_port": 8080, "is_inner_service": False},
                    {"container_port": 8081},
                ],
            )

        self.assertFalse(ports[0].is_inner_service)
        self.assertTrue(ports[1].is_inner_service)

    def test_port_conversion_keeps_outer_service_ports_inner(self):
        builder = new_components_module.NewComponents.__new__(new_components_module.NewComponents)
        component = SimpleNamespace(tenant_id="tenant", service_id="component", service_alias="demo")

        with patch.object(new_components_module.port_service, "check_k8s_service_name"):
            ports = builder._template_to_ports(
                component,
                [
                    {"container_port": 8080, "is_inner_service": False, "is_outer_service": True},
                    {"container_port": 8081, "is_inner_service": False, "is_outer_service": False},
                ],
            )

        self.assertTrue(ports[0].is_inner_service)
        self.assertTrue(ports[0].is_outer_service)
        self.assertFalse(ports[1].is_inner_service)
        self.assertFalse(ports[1].is_outer_service)

    def test_port_conversion_normalizes_template_service_flags(self):
        builder = new_components_module.NewComponents.__new__(new_components_module.NewComponents)
        component = SimpleNamespace(tenant_id="tenant", service_id="component", service_alias="demo")
        values = [(None, True), ("false", False), ("true", True), (0, False), (1, True)]

        with patch.object(new_components_module.port_service, "check_k8s_service_name"):
            for index, (value, expected) in enumerate(values):
                with self.subTest(value=value):
                    port = builder._template_to_ports(
                        component,
                        [{"container_port": 8100 + index, "is_inner_service": value}],
                    )[0]

                    self.assertIs(port.is_inner_service, expected)
                    self.assertIs(type(port.is_inner_service), bool)

            outer_port = builder._template_to_ports(
                component,
                [{"container_port": 8200, "is_inner_service": "false", "is_outer_service": "true"}],
            )[0]

        self.assertIs(outer_port.is_inner_service, True)
        self.assertIs(outer_port.is_outer_service, True)

    def test_existing_default_and_invalid_protocol_validation_are_unchanged(self):
        default = ComponentPortReqSerializers(data={"port": 8080, "is_inner_service": True})
        self.assertTrue(default.is_valid(), default.errors)
        self.assertEqual(default.validated_data["protocol"], "http")
        invalid = ComponentPortReqSerializers(data={"port": 8080, "protocol": "invalid", "is_inner_service": True})
        self.assertFalse(invalid.is_valid())
        self.assertIn("protocol", invalid.errors)


if __name__ == "__main__":
    unittest.main()
