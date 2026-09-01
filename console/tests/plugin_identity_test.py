from unittest import TestCase

from console.utils.plugin_identity import is_gateway_monitoring_plugin


class GatewayMonitoringPluginIdentityTests(TestCase):
    def test_recognizes_supported_base_ids_and_architecture_suffixes(self):
        supported = (
            "rainbond-observability",
            "rainbond-observability-AMD64",
            "rainbond-observability-ARM64",
            "rainbond-gateway-monitoring",
            "rainbond-gateway-monitoring-AMD64",
            "rainbond-gateway-monitoring-ARM64",
        )

        for plugin_name in supported:
            with self.subTest(plugin_name=plugin_name):
                self.assertTrue(is_gateway_monitoring_plugin(plugin_name))

    def test_rejects_unrelated_or_empty_plugin_ids(self):
        for plugin_name in ("", "rainbond-agent", "observability-demo"):
            with self.subTest(plugin_name=plugin_name):
                self.assertFalse(is_gateway_monitoring_plugin(plugin_name))
