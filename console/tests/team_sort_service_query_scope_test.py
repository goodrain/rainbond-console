# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _DummyConfiguration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _DummyApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import team as team_views  # noqa: E402


class TeamSortServiceQueryScopeTest(TestCase):
    def test_get_loads_component_metadata_once_and_preserves_filter_and_sort(self):
        outer_result = [
            {"metric": {"service": "service-a"}, "value": [100, "5"]},
            {"metric": {"service": "missing-service"}, "value": [102, "20"]},
        ]
        inner_result = [
            {"metric": {"service": "service-a"}, "value": [101, "7"]},
            {"metric": {"service": "service-b"}, "value": [103, "8"]},
        ]
        region_responses = [
            (200, {"data": {"result": outer_result}}),
            (200, {"data": {"result": inner_result}}),
        ]
        services = [
            mock.Mock(service_id="service-a", service_cname="Component A", service_alias="component-a"),
            mock.Mock(service_id="service-b", service_cname="Component B", service_alias="component-b"),
        ]
        view = team_views.TeamSortServiceQueryView()
        view.tenant = mock.Mock(tenant_id="team-id")
        request = APIRequestFactory().get("/console/teams/team-a/regions/region-a/component-traffic")

        with mock.patch.object(
                team_views.region_api, "get_query_service_access", side_effect=region_responses), \
                mock.patch.object(
                    team_views.service_repo, "list_by_component_ids", return_value=services) as list_components:
            response = view.get(request, "team-a", "region-a")

        list_components.assert_called_once_with(["service-a", "missing-service", "service-b"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], [
            {
                "metric": {
                    "service": "service-a",
                    "service_cname": "Component A",
                    "service_alias": "component-a",
                },
                "value": [101, 12],
            },
            {
                "metric": {
                    "service": "service-b",
                    "service_cname": "Component B",
                    "service_alias": "component-b",
                },
                "value": [103, 8],
            },
        ])

    def test_get_skips_component_query_when_prometheus_returns_no_services(self):
        view = team_views.TeamSortServiceQueryView()
        view.tenant = mock.Mock(tenant_id="team-id")
        request = APIRequestFactory().get("/console/teams/team-a/regions/region-a/component-traffic")
        empty_response = (200, {"data": {"result": []}})

        with mock.patch.object(
                team_views.region_api,
                "get_query_service_access",
                side_effect=[empty_response, empty_response]), \
                mock.patch.object(team_views.service_repo, "list_by_component_ids") as list_components:
            response = view.get(request, "team-a", "region-a")

        list_components.assert_not_called()
        self.assertEqual(response.data["data"]["list"], [])
