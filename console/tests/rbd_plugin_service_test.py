import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

openapi_client_module = ModuleType("openapi_client")
openapi_client_module.ApiClient = lambda configuration=None: SimpleNamespace(configuration=configuration)
openapi_client_module.MarketOpenapiApi = lambda client=None: SimpleNamespace(client=client)

openapi_client_configuration = ModuleType("openapi_client.configuration")


class _OpenAPIConfiguration(object):
    def __init__(self):
        self.client_side_validation = False
        self.host = ""
        self.api_key = {}


openapi_client_configuration.Configuration = _OpenAPIConfiguration

openapi_client_rest = ModuleType("openapi_client.rest")


class _ApiException(Exception):
    def __init__(self, status=400, body=""):
        super().__init__(body)
        self.status = status
        self.body = body


openapi_client_rest.ApiException = _ApiException

sys.modules.setdefault("openapi_client", openapi_client_module)
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import plugin_service  # noqa: E402
from console.services.plugin_service import rbd_plugin_service


class RainbondPluginServiceTests(TestCase):
    # capability_id: console.platform-plugin.vm-access-url-fallback

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

    # capability_id: console.platform-plugin.vm-access-url-fallback
    def test_official_vm_plugin_uses_fixed_virtvnc_nodeport_when_region_urls_missing(self):
        request = mock.Mock()
        request.scheme = "https"
        request.get_host.return_value = "console.example.com:7070"
        region_plugins = {
            "list": [
                {
                    "name": "rainbond-vm",
                    "region_app_id": "region-app-2",
                    "team_name": "rbd-plugins",
                    "alias": "虚拟机管理",
                    "backend": "",
                    "access_urls": [],
                    "frontend_component": "vm-ui",
                    "frontend_service": "gr785cf6.rbd-plugins.svc.cluster.local:8001/static/main.js",
                }
            ]
        }
        team = mock.Mock()
        team.tenant_id = "tenant-1"
        team.tenant_name = "rbd-plugins"
        region_app = mock.Mock()
        region_app.region_app_id = "region-app-2"
        region_app.app_id = 72
        relation = mock.Mock()
        relation.group_id = 72
        relation.service_id = "svc-frontend"
        service_bodies = {
            "virtvnc": {
                "bean": {
                    "spec": {
                        "ports": [
                            {"port": 8001, "nodePort": 31002},
                        ]
                    }
                }
            }
        }

        def service_lookup(region_name, team_name, service_name, params=None):
            return None, service_bodies.get(service_name, {"bean": {"spec": {"ports": []}}})

        with mock.patch("console.services.plugin_service.region_api.list_plugins", return_value=(None, region_plugins)), \
                mock.patch("console.services.plugin_service.team_services.list_by_team_names", return_value=[team]), \
                mock.patch("console.services.plugin_service.region_app_repo.list_by_region_app_ids", return_value=[region_app]), \
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_ids", return_value=[relation]), \
                mock.patch("console.services.plugin_service.domain_repo.list_by_component_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.region_api.get_tenant_ns_resource",
                           side_effect=service_lookup) as service_query_mock, \
                mock.patch("console.services.plugin_service.platform_plugin_service._get_market_platform_plugins",
                           return_value=(mock.Mock(), [])), \
                mock.patch("console.services.plugin_service.platform_plugin_service._select_market_plugin",
                           return_value=None):
            plugins, _ = rbd_plugin_service.list_plugins("eid", "rainbond", official=True, request=request)

        self.assertEqual(["https://console.example.com:31002"], plugins[0]["urls"])
        service_query_mock.assert_called_once_with(
            "rainbond",
            "rbd-plugins",
            "virtvnc",
            params={"group": "", "version": "v1", "resource": "services"}
        )

    def test_official_vm_plugin_prefers_fixed_virtvnc_nodeport_over_reported_access_urls(self):
        request = mock.Mock()
        request.scheme = "http"
        request.get_host.return_value = "172.16.20.221:7070"
        region_plugins = {
            "list": [
                {
                    "name": "rainbond-vm",
                    "region_app_id": "region-app-2",
                    "team_name": "rbd-plugins",
                    "alias": "虚拟机管理",
                    "backend": "",
                    "access_urls": [
                        "http://grc5c12c-8080-yds31grp.172.16.20.221.nip.io"
                    ],
                    "frontend_component": "vm-ui",
                    "frontend_service": "gr785cf6.rbd-plugins.svc.cluster.local:8001/static/main.js",
                }
            ]
        }
        team = mock.Mock()
        team.tenant_id = "tenant-1"
        team.tenant_name = "rbd-plugins"
        region_app = mock.Mock()
        region_app.region_app_id = "region-app-2"
        region_app.app_id = 72
        relation = mock.Mock()
        relation.group_id = 72
        relation.service_id = "svc-frontend"
        service_bodies = {
            "virtvnc": {
                "bean": {
                    "spec": {
                        "ports": [
                            {"port": 8001, "nodePort": 31002},
                        ]
                    }
                }
            }
        }

        def service_lookup(region_name, team_name, service_name, params=None):
            return None, service_bodies.get(service_name, {"bean": {"spec": {"ports": []}}})

        with mock.patch("console.services.plugin_service.region_api.list_plugins", return_value=(None, region_plugins)), \
                mock.patch("console.services.plugin_service.team_services.list_by_team_names", return_value=[team]), \
                mock.patch("console.services.plugin_service.region_app_repo.list_by_region_app_ids", return_value=[region_app]), \
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_ids", return_value=[relation]), \
                mock.patch("console.services.plugin_service.domain_repo.list_by_component_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.region_api.get_tenant_ns_resource",
                           side_effect=service_lookup), \
                mock.patch("console.services.plugin_service.platform_plugin_service._get_market_platform_plugins",
                           return_value=(mock.Mock(), [])), \
                mock.patch("console.services.plugin_service.platform_plugin_service._select_market_plugin",
                           return_value=None):
            plugins, _ = rbd_plugin_service.list_plugins("eid", "rainbond", official=True, request=request)

        self.assertEqual(["http://172.16.20.221:31002"], plugins[0]["urls"])
