from unittest import TestCase, mock

from console.services.platform_plugin_service import platform_plugin_service
from console.services.plugin_service import rbd_plugin_service


class RainbondPluginServiceTests(TestCase):

    def setUp(self):
        platform_plugin_service.clear_market_plugin_cache()

    def tearDown(self):
        platform_plugin_service.clear_market_plugin_cache()

    def test_official_plugin_without_market_metadata_does_not_require_auth(self):
        region_plugins = {
            "list": [
                {
                    "name": "rainbond-vm",
                    "region_app_id": "region-app-2",
                    "team_name": "rbd-plugins",
                    "alias": "虚拟机管理",
                    "backend": "",
                    "access_urls": [],
                }
            ]
        }

        with mock.patch("console.services.plugin_service.region_api.list_plugins", return_value=(None, region_plugins)), \
                mock.patch("console.services.plugin_service.team_services.list_by_team_names", return_value=[]), \
                mock.patch("console.services.plugin_service.region_app_repo.list_by_region_app_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.domain_repo.list_by_component_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.platform_plugin_service._get_market_platform_plugins",
                           return_value=(mock.Mock(), [])), \
                mock.patch("console.services.plugin_service.platform_plugin_service._select_market_plugin",
                           return_value=None):
            plugins, need_authz = rbd_plugin_service.list_plugins("eid", "rainbond", official=True)

        self.assertFalse(need_authz)
        self.assertNotIn("app_level", plugins[0])

    def test_official_free_plugins_do_not_require_auth(self):
        region_plugins = {
            "list": [
                {
                    "name": "rainbond-enterprise-base",
                    "region_app_id": "region-app-1",
                    "team_name": "rbd-plugins",
                    "alias": "企业基础功能",
                    "backend": "",
                    "access_urls": [],
                }
            ]
        }
        market_plugins = [
            {
                "plugin_id": "rainbond-enterprise-base",
                "app_key": "free-app-key",
                "app_level": "free",
                "plugin_name": "企业基础功能",
            }
        ]

        with mock.patch("console.services.plugin_service.region_api.list_plugins", return_value=(None, region_plugins)), \
                mock.patch("console.services.plugin_service.team_services.list_by_team_names", return_value=[]), \
                mock.patch("console.services.plugin_service.region_app_repo.list_by_region_app_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.domain_repo.list_by_component_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.platform_plugin_service._get_market_platform_plugins",
                           return_value=(mock.Mock(), market_plugins)), \
                mock.patch("console.services.plugin_service.platform_plugin_service._select_market_plugin",
                           return_value=market_plugins[0]):
            plugins, need_authz = rbd_plugin_service.list_plugins("eid", "rainbond", official=True)

        self.assertFalse(need_authz)
        self.assertEqual("free", plugins[0].get("app_level"))
