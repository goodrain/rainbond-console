from unittest import TestCase, mock

from console.exception.main import ServiceHandleException
from console.services.platform_plugin_service import platform_plugin_service


class PlatformPluginServiceTests(TestCase):

    def test_list_platform_plugins_without_valid_license_returns_all_market_plugins(self):
        market_plugins = [
            {"plugin_id": "rainbond-free", "plugin_name": "免费插件", "app_level": "free", "latest_version": "1.0.0"},
            {"plugin_id": "rainbond-enterprise", "plugin_name": "商业插件", "app_level": "enterprise", "latest_version": "1.0.0"},
        ]

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)):
            plugins = platform_plugin_service.list_platform_plugins("eid", "region")

        self.assertEqual(2, len(plugins))
        self.assertEqual({"rainbond-free", "rainbond-enterprise"}, {item["plugin_id"] for item in plugins})

    def test_list_platform_plugins_with_valid_license_filters_unauthorized_enterprise_plugins(self):
        market_plugins = [
            {"plugin_id": "rainbond-free", "plugin_name": "免费插件", "app_level": "free", "latest_version": "1.0.0"},
            {"plugin_id": "rainbond-enterprise-a", "plugin_name": "商业插件A", "app_level": "enterprise", "latest_version": "1.0.0"},
            {"plugin_id": "rainbond-enterprise-b", "plugin_name": "商业插件B", "app_level": "enterprise", "latest_version": "1.0.0"},
        ]
        license_bean = {
            "valid": True,
            "plugin_mapping": {
                "rainbond-enterprise-a": "app-key-a",
            }
        }

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)):
            plugins = platform_plugin_service.list_platform_plugins("eid", "region")

        self.assertEqual(2, len(plugins))
        self.assertEqual({"rainbond-free", "rainbond-enterprise-a"}, {item["plugin_id"] for item in plugins})

    def test_install_platform_plugin_rejects_unauthorized_enterprise_plugin(self):
        market_plugins = [
            {"plugin_id": "rainbond-enterprise-a", "plugin_name": "商业插件A", "app_level": "enterprise"}
        ]
        license_bean = {
            "valid": True,
            "plugin_mapping": {},
            "access_key": "license-ak",
        }

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)):
            with self.assertRaises(ServiceHandleException) as context:
                platform_plugin_service.install_platform_plugin("eid", "region", "rainbond-enterprise-a", mock.Mock())

        self.assertEqual("该插件未授权", context.exception.msg_show)
