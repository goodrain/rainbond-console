# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module = ModuleType("openapi_client.configuration")
    configuration_module.Configuration = type("Configuration", (), {})
    rest_module = ModuleType("openapi_client.rest")
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import SimpleTestCase  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.mcp_query_service import mcp_query_service  # noqa: E402
from console.services.platform_plugin_service import platform_plugin_service  # noqa: E402


class MCPPlatformPluginToolContractTests(SimpleTestCase):

    # capability_id: console.mcp.platform-plugin-tools

    def test_list_is_visible_to_authenticated_user_but_install_is_admin_only(self):
        user = SimpleNamespace(user_id=2, enterprise_id="eid-1", is_enterprise_admin=False)
        admin = SimpleNamespace(user_id=1, enterprise_id="eid-1", is_enterprise_admin=True)

        user_names = {tool["name"] for tool in mcp_query_service.list_tools(user)}
        admin_names = {tool["name"] for tool in mcp_query_service.list_tools(admin)}

        self.assertIn("rainbond_list_platform_plugins", user_names)
        self.assertNotIn("rainbond_install_platform_plugin", user_names)
        self.assertIn("rainbond_install_platform_plugin", admin_names)

    def test_schemas_do_not_accept_enterprise_or_install_target_overrides(self):
        admin = SimpleNamespace(user_id=1, enterprise_id="eid-1", is_enterprise_admin=True)
        tools = {tool["name"]: tool for tool in mcp_query_service.list_tools(admin)}
        for name in ("rainbond_list_platform_plugins", "rainbond_install_platform_plugin"):
            with self.subTest(tool=name):
                schema = tools[name]["inputSchema"]
                self.assertIs(schema["additionalProperties"], False)
                for forbidden in ("enterprise_id", "team_name", "namespace", "app_id", "market_url", "version"):
                    self.assertNotIn(forbidden, schema["properties"])

    def test_install_requires_enterprise_admin_even_if_called_directly(self):
        user = SimpleNamespace(user_id=2, enterprise_id="eid-1", is_enterprise_admin=False)
        with self.assertRaises(ServiceHandleException) as ctx:
            mcp_query_service.call_tool(
                user,
                "rainbond_install_platform_plugin",
                {
                    "region_name": "rainbond",
                    "plugin_id": "rainbond-ai-engine"
                },
            )
        self.assertEqual(403, ctx.exception.status_code)

    @mock.patch("console.services.mcp_platform_plugin_tools.platform_plugin_service")
    def test_list_uses_platform_plugin_service_strict_path(self, plugin_service):
        plugin_service.list_platform_plugins_strict.return_value = [{"plugin_id": "rainbond-ai-engine"}]
        user = SimpleNamespace(user_id=2, enterprise_id="eid-1", is_enterprise_admin=False)

        result = mcp_query_service.call_tool(user, "rainbond_list_platform_plugins", {"region_name": "rainbond"})

        self.assertEqual([{"plugin_id": "rainbond-ai-engine"}], result["items"])
        plugin_service.list_platform_plugins_strict.assert_called_once_with("eid-1", "rainbond")

    @mock.patch("console.services.mcp_platform_plugin_tools.platform_plugin_service")
    def test_install_is_idempotent_when_plugin_is_already_installed(self, plugin_service):
        installed = {
            "plugin_id": "rainbond-ai-engine",
            "installed": True,
            "status": "RUNNING",
            "team_name": "rbd-plugins",
            "app_id": 7,
        }
        plugin_service.list_platform_plugins_strict.return_value = [installed]
        admin = SimpleNamespace(user_id=1, enterprise_id="eid-1", is_enterprise_admin=True)

        result = mcp_query_service.call_tool(
            admin,
            "rainbond_install_platform_plugin",
            {
                "region_name": "rainbond",
                "plugin_id": "rainbond-ai-engine"
            },
        )

        self.assertTrue(result["already_installed"])
        self.assertEqual("rbd-plugins", result["team_name"])
        plugin_service.install_platform_plugin.assert_not_called()

    @mock.patch("console.services.platform_plugin_service.region_api.list_plugins")
    def test_strict_list_fails_closed_when_region_inventory_is_unavailable(self, list_plugins):
        list_plugins.side_effect = RuntimeError("region unavailable")

        with self.assertRaises(ServiceHandleException) as ctx:
            platform_plugin_service.list_platform_plugins_strict("eid-1", "rainbond")

        self.assertEqual(503, ctx.exception.status_code)
        self.assertEqual("platform_plugin_state_unavailable", ctx.exception.error_code)

    def test_strict_list_fails_closed_when_installed_app_mapping_is_unavailable(self):
        installed = {
            "rainbond-ai-engine": {
                "name": "rainbond-ai-engine",
                "region_app_id": "region-app-1",
                "status": "RUNNING",
            },
        }
        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins_strict", return_value=installed), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={}):
            with self.assertRaises(ServiceHandleException) as ctx:
                platform_plugin_service.list_platform_plugins_strict("eid-1", "rainbond")

        self.assertEqual(503, ctx.exception.status_code)
        self.assertEqual("platform_plugin_state_unavailable", ctx.exception.error_code)

    @mock.patch("console.services.mcp_platform_plugin_tools.platform_plugin_service")
    def test_install_delegates_once_when_plugin_is_not_installed(self, plugin_service):
        plugin_service.list_platform_plugins_strict.return_value = []
        plugin_service.install_platform_plugin.return_value = {
            "plugin_id": "rainbond-ai-engine",
            "team_name": "rbd-plugins",
            "app_id": 7,
        }
        admin = SimpleNamespace(user_id=1, enterprise_id="eid-1", is_enterprise_admin=True)

        result = mcp_query_service.call_tool(
            admin,
            "rainbond_install_platform_plugin",
            {
                "region_name": "rainbond",
                "plugin_id": "rainbond-ai-engine"
            },
        )

        self.assertIs(result["already_installed"], False)
        self.assertEqual("", result["status"])
        plugin_service.install_platform_plugin.assert_called_once_with("eid-1", "rainbond", "rainbond-ai-engine", admin)

    def test_platform_tool_requires_server_enterprise_context(self):
        user = SimpleNamespace(user_id=2, enterprise_id="", is_enterprise_admin=False)

        with self.assertRaises(ServiceHandleException) as ctx:
            mcp_query_service.call_tool(user, "rainbond_list_platform_plugins", {"region_name": "rainbond"})

        self.assertEqual(403, ctx.exception.status_code)

    def test_strict_list_keeps_installed_plugin_when_market_catalog_omits_it(self):
        installed = {
            "rainbond-ai-engine": {
                "name": "rainbond-ai-engine",
                "region_app_id": "region-app-1",
                "status": "RUNNING",
                "team_name": "rbd-plugins",
                "plugin_type": "both",
            },
        }
        with mock.patch("console.services.platform_plugin_service.is_cloud_market_disabled", return_value=False), \
                mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins_strict", return_value=installed), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={"region-app-1": 7}), \
                mock.patch.object(platform_plugin_service, "_get_region_arches", return_value={"amd64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins_cached",
                                  return_value=(mock.Mock(), [])):
            result = platform_plugin_service.list_platform_plugins_strict("eid-1", "rainbond")

        self.assertEqual(1, len(result))
        self.assertEqual("rainbond-ai-engine", result[0]["plugin_id"])
        self.assertTrue(result[0]["installed"])
        self.assertEqual("RUNNING", result[0]["status"])
        self.assertEqual(7, result[0]["app_id"])
