# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

from django.http import HttpResponse

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

openapi_client_module = ModuleType("openapi_client")
openapi_client_module.ApiClient = lambda configuration=None: SimpleNamespace(
    configuration=configuration)
openapi_client_module.MarketOpenapiApi = lambda client=None: SimpleNamespace(
    client=client)

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
sys.modules.setdefault(
    "openapi_client.configuration",
    openapi_client_configuration,
)
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

from console.views import rbd_plugin  # noqa: E402


class FakeValuesQuerySet(list):
    def values(self, *args):
        return self


class GatewayMonitoringPluginProxyTests(TestCase):
    def test_gateway_monitoring_app_top_path_detection(self):
        self.assertTrue(rbd_plugin._is_gateway_monitoring_app_top_path(
            "rainbond-gateway-monitoring",
            "api/v1/platform/apps/top-latency",
        ))
        self.assertTrue(rbd_plugin._is_gateway_monitoring_app_top_path(
            "rainbond-gateway-monitoring",
            "api/v1/teams/rbd-prd/apps/top-throughput",
        ))
        self.assertFalse(rbd_plugin._is_gateway_monitoring_app_top_path(
            "rainbond-gateway-monitoring",
            "api/v1/apps/3/components/summary",
        ))
        self.assertFalse(rbd_plugin._is_gateway_monitoring_app_top_path(
            "other-plugin",
            "api/v1/platform/apps/top-latency",
        ))

    def test_plugin_query_token_authentication_accepts_iframe_token(self):
        request = mock.Mock()
        request.META = {}
        request.COOKIES = {}
        request.GET = {"token": "iframe-token"}
        request.query_params = {}
        request.path = (
            "/console/regions/rainbond/backend/plugins/"
            "rainbond-enterprise-alarm/"
        )

        auth = rbd_plugin.PluginQueryTokenAuthentication()

        self.assertEqual(auth.get_jwt_value(request), "iframe-token")

    @mock.patch("console.views.rbd_plugin.region_api.stream_proxy")
    def test_backend_proxy_allows_same_origin_iframe(self, stream_proxy):
        request = mock.Mock()
        request.META = {}
        response = HttpResponse("ok")
        stream_proxy.return_value = response

        result = rbd_plugin.RainbondPluginBackendView().get(
            request,
            region_name="rainbond",
            plugin_name="rainbond-enterprise-alarm",
            file_path="",
        )

        self.assertEqual(result["X-Frame-Options"], "SAMEORIGIN")

    @mock.patch("console.views.rbd_plugin.Tenants.objects.filter")
    @mock.patch("console.views.rbd_plugin.ServiceGroup.objects.filter")
    @mock.patch("console.views.rbd_plugin.RegionApp.objects.filter")
    def test_enriches_app_and_team_names_from_console_models(
            self,
            region_app_filter,
            service_group_filter,
            tenant_filter,
    ):
        region_app_filter.return_value = FakeValuesQuerySet([
            {
                "region_app_id": "6cf2bf3464d74f3da0a612c5917b2957",
                "app_id": 3,
            },
        ])
        service_group_filter.return_value = FakeValuesQuerySet([
            {
                "ID": 3,
                "tenant_id": "team-id-1",
                "group_name": "订单系统",
                "region_name": "rainbond",
            },
        ])
        tenant_filter.return_value = FakeValuesQuerySet([
            {
                "tenant_id": "team-id-1",
                "tenant_name": "rbd-prd",
                "tenant_alias": "生产团队",
                "namespace": "rbd-prd",
            },
        ])

        payload = {
            "data": [
                {
                    "app_id": "3",
                    "team_id": "unknown_team",
                    "namespace": "rbd-prd",
                    "region_app_id": "6cf2bf3464d74f3da0a612c5917b2957",
                    "name": "3",
                    "request_count": 280,
                },
            ],
        }

        rbd_plugin._enrich_gateway_monitoring_app_items(payload, "rainbond")

        self.assertEqual(payload["data"][0]["app_id"], "3")
        self.assertEqual(payload["data"][0]["name"], "订单系统")
        self.assertEqual(payload["data"][0]["app_name"], "订单系统")
        self.assertEqual(payload["data"][0]["team_id"], "team-id-1")
        self.assertEqual(payload["data"][0]["team_name"], "rbd-prd")
        self.assertEqual(payload["data"][0]["team_alias"], "生产团队")
