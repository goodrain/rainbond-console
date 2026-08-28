# -*- coding: utf-8 -*-
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    configuration_module.Configuration = _Configuration
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

from django.urls import resolve
from rest_framework.test import APIRequestFactory

from console.views.plugin import plugin_config


class PluginVolumeOptionsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = plugin_config.PluginVolumeOptionsView()
        self.view.tenant = SimpleNamespace(tenant_name="demo-team")
        self.view.response_region = "region-1"

    def test_volume_options_route_precedes_plugin_id_route(self):
        match = resolve("/console/teams/demo-team/plugins/volume-opts")

        self.assertIs(match.func.view_class, plugin_config.PluginVolumeOptionsView)

    def test_get_returns_region_volume_options(self):
        options = [
            {
                "volume_type": "local-path",
                "name_show": "Local Path",
                "access_mode": ["RWO"],
            },
            {
                "volume_type": "nfs-client",
                "name_show": "NFS",
                "access_mode": ["RWX"],
            },
        ]
        request = self.factory.get("/console/teams/demo-team/plugins/volume-opts")

        with mock.patch.object(
                plugin_config.region_api,
                "get_volume_options",
                return_value=SimpleNamespace(list=options),
        ) as get_volume_options:
            response = self.view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], options)
        get_volume_options.assert_called_once_with("region-1", "demo-team")

    def test_get_returns_empty_list_when_region_has_no_volume_options(self):
        request = self.factory.get("/console/teams/demo-team/plugins/volume-opts")

        for region_response in (SimpleNamespace(), SimpleNamespace(list=None), None):
            with self.subTest(region_response=region_response):
                with mock.patch.object(
                        plugin_config.region_api,
                        "get_volume_options",
                        return_value=region_response,
                ) as get_volume_options:
                    response = self.view.get(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["data"]["list"], [])
                get_volume_options.assert_called_once_with("region-1", "demo-team")
