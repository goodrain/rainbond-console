# -*- coding: utf-8 -*-
import collections
import importlib
import os
import sys
import typing
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    typing.NotRequired = typing.Optional

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration(object):
        def __init__(self):
            self.host = ""
            self.api_key = {}

    configuration_module.Configuration = _Configuration
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
if "rest_framework_simplejwt.tokens" not in sys.modules:
    simplejwt_module = ModuleType("rest_framework_simplejwt")
    tokens_module = ModuleType("rest_framework_simplejwt.tokens")
    tokens_module.AccessToken = object
    simplejwt_module.tokens = tokens_module
    sys.modules["rest_framework_simplejwt"] = simplejwt_module
    sys.modules["rest_framework_simplejwt.tokens"] = tokens_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import RequestFactory  # noqa: E402
from django.db import connections  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.views.app_overview import AppGroupVisitView  # noqa: E402
from console.models.main import RegionConfig  # noqa: E402
from www.models.main import ServiceTcpDomain, TenantServiceEnvVar, TenantServiceInfo, TenantServicesPort  # noqa: E402

visit_module = importlib.import_module("console.views.app_overview")
port_module = importlib.import_module("console.services.app_config.port_service")


# capability_id: console.app-overview.group-visit-resilience
class AppGroupVisitViewTestCase(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.view = AppGroupVisitView()
        self.view.region_name = "demo-region"
        self.team = mock.Mock(tenant_name="demo", tenant_id="demo-id")

    def test_get_skips_components_deleted_after_topology_load(self):
        request = self.request_factory.get("/console/teams/demo/group/service/visit", {"service_alias": "missing-active"})
        active_service = mock.Mock(service_id="service-active", service_alias="active")

        def get_access_info(team, service, **kwargs):
            if service is None:
                raise AttributeError("'NoneType' object has no attribute 'service_id'")
            return "http", [{"url": "https://example.com"}]

        with mock.patch("console.views.app_overview.team_services.get_tenant_by_tenant_name",
                        return_value=self.team), \
                mock.patch("console.views.app_overview.service_repo.list_by_tenant_region_and_aliases",
                           return_value=[active_service]), \
                mock.patch("console.views.app_overview.port_repo.list_by_service_ids", return_value=[]), \
                mock.patch("console.views.app_overview.port_service.get_access_info",
                           side_effect=get_access_info) as access_info:
            response = self.view.get(request, "demo")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]["list"]), 1)
        access_info.assert_called_once_with(self.team, active_service, service_ports=[], context={})

    def test_get_preserves_service_handle_exception(self):
        request = self.request_factory.get("/console/teams/demo/group/service/visit", {"service_alias": "active"})
        service = mock.Mock(service_id="service-active", service_alias="active")
        error = ServiceHandleException(msg="region unavailable", msg_show="数据中心不可用", status_code=503)

        with mock.patch("console.views.app_overview.team_services.get_tenant_by_tenant_name",
                        return_value=self.team), \
                mock.patch("console.views.app_overview.service_repo.list_by_tenant_region_and_aliases",
                           return_value=[service]), \
                mock.patch("console.views.app_overview.port_repo.list_by_service_ids", return_value=[]), \
                mock.patch("console.views.app_overview.port_service.get_access_info", side_effect=error):
            with self.assertRaises(ServiceHandleException) as raised:
                self.view.get(request, "demo")

        self.assertIs(raised.exception, error)

    def test_get_reports_regular_exception_without_python2_message_attribute(self):
        request = self.request_factory.get("/console/teams/demo/group/service/visit", {"service_alias": "active"})
        service = mock.Mock(service_id="service-active", service_alias="active")

        with mock.patch("console.views.app_overview.team_services.get_tenant_by_tenant_name",
                        return_value=self.team), \
                mock.patch("console.views.app_overview.service_repo.list_by_tenant_region_and_aliases",
                           return_value=[service]), \
                mock.patch("console.views.app_overview.port_repo.list_by_service_ids", return_value=[]), \
                mock.patch("console.views.app_overview.port_service.get_access_info",
                           side_effect=ValueError("invalid access data")):
            response = self.view.get(request, "demo")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg"], "invalid access data")


# capability_id: console.app-overview.group-visit-batched-access
class AppGroupVisitBatchAccessTestCase(TestCase):
    """Exercise the real repositories against an isolated in-memory SQLite DB."""

    def setUp(self):
        self.alias = "group_visit_access"
        connections.databases[self.alias] = {
            "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
            "ATOMIC_REQUESTS": False, "AUTOCOMMIT": True, "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False, "OPTIONS": {}, "TIME_ZONE": None,
            "USER": "", "PASSWORD": "", "HOST": "", "PORT": "", "TEST": {},
        }
        self.db = connections[self.alias]
        self.models = (TenantServiceInfo, TenantServicesPort, TenantServiceEnvVar, RegionConfig, ServiceTcpDomain)
        with self.db.schema_editor() as schema:
            for model in self.models:
                schema.create_model(model)
        self.addCleanup(self._close_database)
        for model in self.models:
            patcher = mock.patch.object(model, "objects", model.objects.db_manager(self.alias))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.team = SimpleNamespace(tenant_id="team-a", tenant_name="team-a", enterprise_id="ent-a")
        self.view = AppGroupVisitView()
        self.view.region_name = "region-a"
        self.request_factory = RequestFactory()
        self.region = RegionConfig.objects.create(
            region_id="region-id-a", region_name="region-a", enterprise_id="ent-a", tcpdomain="tcp.example")

    def _close_database(self):
        self.db.close()
        del connections[self.alias]
        connections.databases.pop(self.alias, None)

    def component(self, alias="active", tenant_id="team-a", region_name="region-a"):
        return TenantServiceInfo.objects.create(
            service_id="{}-{}".format(tenant_id, alias), tenant_id=tenant_id,
            service_alias=alias, service_region=region_name, service_cname=alias.title(),
            k8s_component_name=alias, service_key="key", category="application",
            version="v1", image="example/image:v1")

    def port(self, service, port=8080, protocol="http", outer=False, inner=False):
        return TenantServicesPort.objects.create(
            tenant_id=service.tenant_id, service_id=service.service_id, container_port=port,
            protocol=protocol, is_outer_service=outer, is_inner_service=inner)

    def call(self, aliases):
        request = self.request_factory.get("/console/teams/team-a/group/service/visit", {"service_alias": aliases})
        with mock.patch.object(visit_module.team_services, "get_tenant_by_tenant_name", return_value=self.team):
            return self.view.get(request, self.team.tenant_name)

    def test_base_sql_stays_two_for_one_five_and_fifty_components(self):
        for with_ports in (False, True):
            for count in (1, 5, 50):
                with self.subTest(components=count, with_ports=with_ports):
                    TenantServicesPort.objects.all()._raw_delete(self.alias)
                    TenantServiceInfo.objects.all()._raw_delete(self.alias)
                    aliases = ["svc{}".format(i) for i in range(count)]
                    for alias in aliases:
                        service = self.component(alias)
                        if with_ports:
                            self.port(service)
                    with CaptureQueriesContext(self.db) as queries:
                        response = self.call("-".join(aliases))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(len(response.data["data"]["list"]), count)
                    self.assertEqual(len(queries), 2)

    def test_scoped_aliases_preserve_order_duplicates_and_skip_missing(self):
        self.component("same", tenant_id="team-b")
        same = self.component("same")
        last = self.component("last")
        self.component("otherregion", region_name="region-b")
        self.port(same, port=8081, protocol="tcp", inner=True)
        self.port(last, port=9090, protocol="tcp", inner=True)
        response = self.call("last-missing-same-otherregion-same")
        self.assertEqual(response.status_code, 200)
        accesses = response.data["data"]["list"]
        self.assertEqual([item["access_info"][0]["service_cname"] for item in accesses], ["Last", "Same", "Same"])
        self.assertEqual([item["access_info"][0]["container_port"] for item in accesses], [9090, 8081, 8081])

    def test_http_keeps_live_urls_and_reuses_region_only_within_one_request(self):
        first = self.component("first")
        second = self.component("second")
        self.port(first, port=8080, outer=True)
        self.port(first, port=8081, outer=True)
        self.port(second, port=8080, outer=True)
        with mock.patch.object(port_module.region_services, "get_enterprise_region_by_region_name",
                               wraps=port_module.region_services.get_enterprise_region_by_region_name) as region_lookup, \
                mock.patch.object(port_module.region_api, "api_gateway_get_proxy",
                                  return_value={"list": ["a.example", "b.example"]}) as gateway:
            with CaptureQueriesContext(self.db) as queries:
                response = self.call("first-second")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(queries), 3)
            self.assertEqual(region_lookup.call_count, 1)
            self.assertEqual(gateway.call_count, 3)
            for item in response.data["data"]["list"]:
                for port in item["access_info"]:
                    self.assertEqual(port["access_urls"], ["http://b.example/", "http://a.example/"])
            self.call("first-second")
            self.assertEqual(region_lookup.call_count, 2)
            self.assertEqual(gateway.call_count, 6)

    def test_duplicate_aliases_still_resolve_live_gateway_each_time(self):
        service = self.component()
        self.port(service, outer=True)
        with mock.patch.object(port_module.region_api, "api_gateway_get_proxy", side_effect=[
                {"list": ["first.example"]}, {"list": ["second.example"]}]):
            response = self.call("active-active")
        accesses = response.data["data"]["list"]
        self.assertEqual([item["access_info"][0]["access_urls"] for item in accesses], [
            ["http://first.example/"], ["http://second.example/"]])

    def test_tcp_region_lookup_is_reused_but_domain_results_are_not(self):
        service = self.component()
        self.port(service, port=8080, protocol="tcp", outer=True)
        self.port(service, port=9090, protocol="tcp", outer=True)
        with mock.patch.object(port_module.region_repo, "get_region_by_region_name",
                               wraps=port_module.region_repo.get_region_by_region_name) as region_lookup, \
                mock.patch.object(port_module.tcp_domain, "get_service_tcpdomain", side_effect=[
                    SimpleNamespace(end_point="0.0.0.0:30000"), SimpleNamespace(end_point="1.2.3.4:30001")]) as domains:
            response = self.call("active")
        self.assertEqual(region_lookup.call_count, 1)
        self.assertEqual(domains.call_count, 2)
        self.assertEqual([port["access_urls"] for port in response.data["data"]["list"][0]["access_info"]], [
            ["tcp.example:30000"], ["1.2.3.4:30001"]])

    def test_all_access_branches_match_existing_single_component_results(self):
        services = []
        for alias, protocol, outer, inner in (
                ("noports", "http", False, False), ("unopened", "http", False, False),
                ("httpouter", "http", True, True), ("httpfallback", "http", True, False),
                ("httpempty", "http", True, False), ("tcpouter", "tcp", True, True),
                ("tcpempty", "tcp", True, False), ("tcpinner", "tcp", False, True),
                ("httpinner", "http", False, True)):
            service = self.component(alias)
            services.append(service)
            if alias != "noports":
                self.port(service, protocol=protocol, outer=outer, inner=inner)
            if alias in ("httpfallback", "tcpouter"):
                ServiceTcpDomain.objects.create(
                    tcp_rule_id=alias, tenant_id=self.team.tenant_id, region_id=self.region.region_id,
                    service_id=service.service_id, container_port=8080, end_point="0.0.0.0:30000")
            if inner:
                TenantServiceEnvVar.objects.create(
                    tenant_id=self.team.tenant_id, service_id=service.service_id,
                    container_port=8080, name="port host", attr_name="HOST", attr_value="backend", scope="outer")
                TenantServiceEnvVar.objects.create(
                    tenant_id=self.team.tenant_id, service_id=service.service_id,
                    container_port=0, name="shared", attr_name="SHARED", attr_value="visible", scope="both")
                TenantServiceEnvVar.objects.create(
                    tenant_id=self.team.tenant_id, service_id=service.service_id,
                    container_port=0, name="duplicate", attr_name="HOST", attr_value="excluded", scope="outer")

        def gateway_response(region, tenant_id, path, app_id):
            if "service_alias=httpouter&" in path:
                return {"list": ["a.example", "b.example"]}
            return {"list": []}

        with mock.patch.object(port_module.region_api, "api_gateway_get_proxy", side_effect=gateway_response):
            expected = []
            for service in services:
                access_type, data = visit_module.port_service.get_access_info(self.team, service)
                expected.append({"access_type": access_type, "access_info": data})
            response = self.call("-".join(service.service_alias for service in services))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], expected)
        self.assertEqual(expected[3]["access_info"][0]["access_urls"], ["tcp.example:30000"])
        self.assertEqual(expected[7]["access_info"][0]["connect_info"], [
            {"name": "port host", "attr_name": "HOST", "attr_value": "backend"},
            {"name": "shared", "attr_name": "SHARED", "attr_value": "visible"},
        ])

    def test_preloaded_empty_ports_do_not_fall_back_to_per_service_query(self):
        service = self.component()
        self.port(service, outer=True)
        with mock.patch.object(port_module.port_repo, "get_service_ports") as get_ports:
            access_type, data = visit_module.port_service.get_access_info(self.team, service, service_ports=[])
        self.assertEqual(data, [])
        get_ports.assert_not_called()

    def test_single_component_call_still_reads_its_own_ports(self):
        service = self.component()
        with mock.patch.object(port_module.port_repo, "get_service_ports", return_value=[]) as get_ports:
            visit_module.port_service.get_access_info(self.team, service)
        get_ports.assert_called_once_with(self.team.tenant_id, service.service_id)

    def test_missing_components_do_not_resolve_ports_or_region(self):
        with mock.patch.object(port_module.port_repo, "list_by_service_ids", wraps=port_module.port_repo.list_by_service_ids), \
                mock.patch.object(port_module.region_api, "api_gateway_get_proxy") as gateway:
            response = self.call("missing")
        self.assertEqual(response.data["data"]["list"], [])
        gateway.assert_not_called()

    def test_empty_aliases_and_missing_team_keep_existing_responses(self):
        with mock.patch.object(visit_module.service_repo, "list_by_tenant_region_and_aliases") as services:
            response = self.call("")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], {"is_null": True})
        services.assert_not_called()
        request = self.request_factory.get("/visit", {"service_alias": "active"})
        with mock.patch.object(visit_module.team_services, "get_tenant_by_tenant_name", return_value=None):
            response = self.view.get(request, "missing")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 400)

    def test_context_configuration_keys_keep_enterprises_and_regions_separate(self):
        service = self.component()
        port = self.port(service, outer=True)
        other_team = SimpleNamespace(tenant_id="team-b", tenant_name="team-b", enterprise_id="ent-b")
        other_region_service = SimpleNamespace(
            service_id="other", service_alias="other", service_region="region-b", service_cname="Other")
        context = {}
        with mock.patch.object(port_module.region_services, "get_enterprise_region_by_region_name",
                               return_value=self.region) as regions, \
                mock.patch.object(port_module.region_api, "api_gateway_get_proxy", return_value={"list": ["a.example"]}):
            for team, component in ((self.team, service), (other_team, service), (self.team, other_region_service)):
                visit_module.port_service.get_access_info(team, component, service_ports=[port], context=context)
        self.assertEqual(regions.call_args_list, [
            mock.call("ent-a", "region-a"), mock.call("ent-b", "region-a"), mock.call("ent-a", "region-b")])
