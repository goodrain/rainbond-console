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

from console.views import public_areas  # noqa: E402


class Obj(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TeamOverviewQueryScopeTest(TestCase):

    def test_empty_application_set_skips_region_status_request(self):
        view = public_areas.TeamOverView()
        view.team = Obj(tenant_id="team-id", enterprise_id="enterprise-id")
        view.tenant = Obj(tenant_alias="Team Alias")
        view.tenant_name = "team-name"
        view.response_region = "region-a"
        view.region = Obj(region_id="region-id")
        components = mock.Mock()
        components.values_list.return_value = []
        request = APIRequestFactory().get("/console/teams/team-name/overview")

        with mock.patch.object(public_areas.team_services, "get_team_users", return_value=[Obj()]), \
                mock.patch.object(public_areas.service_repo, "get_team_service_num_by_team_id", return_value=0), \
                mock.patch.object(public_areas.common_services, "get_current_region_used_resource", return_value={}), \
                mock.patch.object(
                    public_areas.team_services,
                    "get_team_by_team_id_and_eid",
                    return_value=Obj(logo="logo")), \
                mock.patch.object(
                    public_areas.region_repo,
                    "get_region_by_region_name",
                    return_value=Obj(region_name="region-a")), \
                mock.patch.object(public_areas.group_repo, "get_tenant_region_groups", return_value=[]), \
                mock.patch.object(public_areas.service_repo, "list_svc_by_tenant", return_value=components), \
                mock.patch.object(public_areas.volume_repo, "get_services_volumes", return_value=[]), \
                mock.patch.object(public_areas.region_api, "list_app_statuses_by_app_ids") as list_statuses:
            response = view.get(request)

        list_statuses.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["running_app_num"], 0)

    def test_nonempty_application_set_still_counts_running_apps(self):
        view = public_areas.TeamOverView()
        view.team = Obj(tenant_id="team-id", enterprise_id="enterprise-id")
        view.tenant = Obj(tenant_alias="Team Alias")
        view.tenant_name = "team-name"
        view.response_region = "region-a"
        view.region = Obj(region_id="region-id")
        group = Obj(ID=11, group_name="App", k8s_app="")
        region_app = Obj(app_id=11, region_app_id="region-app-id")
        components = mock.Mock()
        components.values_list.return_value = []
        request = APIRequestFactory().get("/console/teams/team-name/overview")

        with mock.patch.object(public_areas.team_services, "get_team_users", return_value=[Obj()]), \
                mock.patch.object(public_areas.service_repo, "get_team_service_num_by_team_id", return_value=0), \
                mock.patch.object(public_areas.common_services, "get_current_region_used_resource", return_value={}), \
                mock.patch.object(
                    public_areas.team_services,
                    "get_team_by_team_id_and_eid",
                    return_value=Obj(logo="logo")), \
                mock.patch.object(
                    public_areas.region_repo,
                    "get_region_by_region_name",
                    return_value=Obj(region_name="region-a")), \
                mock.patch.object(public_areas.group_repo, "get_tenant_region_groups", return_value=[group]), \
                mock.patch.object(public_areas.region_app_repo, "list_by_app_ids", return_value=[region_app]), \
                mock.patch.object(public_areas.service_repo, "list_svc_by_tenant", return_value=components), \
                mock.patch.object(public_areas.volume_repo, "get_services_volumes", return_value=[]), \
                mock.patch.object(
                    public_areas.region_api,
                    "list_app_statuses_by_app_ids",
                    return_value={"list": [{"status": "RUNNING"}]}) as list_statuses:
            response = view.get(request)

        list_statuses.assert_called_once_with("team-name", "region-a", {"app_ids": ["region-app-id"]})
        self.assertEqual(response.data["data"]["bean"]["running_app_num"], 1)

    def test_group_service_ids_are_loaded_with_two_bounded_queries(self):
        component_queryset = mock.MagicMock()
        component_queryset.values_list.return_value = ["service-a", "service-b"]
        component_manager = mock.MagicMock()
        component_manager.filter.return_value = component_queryset

        relation_queryset = mock.MagicMock()
        relation_queryset.values.return_value = [
            {"group_id": 11, "service_id": "service-a"},
            {"group_id": 12, "service_id": "service-b"},
        ]
        relation_manager = mock.MagicMock()
        relation_manager.filter.return_value = relation_queryset

        with mock.patch.object(public_areas.TenantServiceInfo, "objects", component_manager), \
                mock.patch.object(public_areas.ServiceGroupRelation, "objects", relation_manager):
            result = public_areas._get_group_service_ids("team-1", "region-a", [11, 12])

        component_manager.filter.assert_called_once_with(tenant_id="team-1", service_region="region-a")
        component_queryset.values_list.assert_called_once_with("service_id", flat=True)
        relation_manager.filter.assert_called_once_with(
            tenant_id="team-1",
            region_name="region-a",
            group_id__in=[11, 12],
            service_id__in=["service-a", "service-b"],
        )
        relation_queryset.values.assert_called_once_with("group_id", "service_id")
        self.assertEqual(result, {11: ["service-a"], 12: ["service-b"]})

    def test_group_service_ids_skip_database_for_empty_groups(self):
        with mock.patch.object(public_areas.TenantServiceInfo.objects, "filter") as component_filter, \
                mock.patch.object(public_areas.ServiceGroupRelation.objects, "filter") as relation_filter:
            result = public_areas._get_group_service_ids("team-1", "region-a", [])

        self.assertEqual(result, {})
        component_filter.assert_not_called()
        relation_filter.assert_not_called()
