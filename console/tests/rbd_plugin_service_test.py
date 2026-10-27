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

from django.db import connections  # noqa: E402
from django.db.models.signals import post_init  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from console.repositories.service_group_relation_repo import service_group_relation_repo  # noqa: E402
from console.services.platform_plugin_service import platform_plugin_service  # noqa: E402
from console.services.plugin_service import rbd_plugin_service  # noqa: E402
from www.models.main import RegionApp, ServiceDomain, ServiceGroupRelation  # noqa: E402


# capability_id: console.platform-plugin.scoped-component-domain-reads
class PluginRelationScopeTests(TestCase):
    def test_plugin_relation_query_has_all_three_scopes(self):
        with mock.patch.object(ServiceGroupRelation.objects, "filter") as query:
            service_group_relation_repo.list_by_tenant_and_app_ids(["tenant-1"], [72], "rainbond")
        query.assert_called_once_with(tenant_id__in=["tenant-1"], group_id__in=[72], region_name="rainbond")

    def test_existing_tenant_only_query_remains_unchanged(self):
        with mock.patch.object(ServiceGroupRelation.objects, "filter") as query:
            service_group_relation_repo.list_by_tenant_ids(["tenant-1"])
        query.assert_called_once_with(tenant_id__in=["tenant-1"])


# capability_id: console.platform-plugin.scoped-component-domain-reads
class PluginScopedReadIntegrationTests(TestCase):
    def setUp(self):
        self.alias = "plugin_scoped_read_test"
        connections.databases[self.alias] = {
            "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
            "ATOMIC_REQUESTS": False, "AUTOCOMMIT": True, "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False, "OPTIONS": {}, "TIME_ZONE": None,
            "USER": "", "PASSWORD": "", "HOST": "", "PORT": "", "TEST": {},
        }
        self.database = connections[self.alias]
        self.addCleanup(self.close_database)
        models = (ServiceGroupRelation, RegionApp, ServiceDomain)
        with self.database.schema_editor() as schema:
            for model in models:
                schema.create_model(model)
        for model in models:
            patcher = mock.patch.object(model, "objects", model.objects.db_manager(self.alias))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.teams = [SimpleNamespace(tenant_id="tenant-1", tenant_name="plugins-a"),
                      SimpleNamespace(tenant_id="tenant-2", tenant_name="plugins-b")]
        RegionApp.objects.bulk_create([
            RegionApp(region_name="rainbond", region_app_id="region-app-a", app_id=72),
            RegionApp(region_name="rainbond", region_app_id="region-app-b", app_id=73),
            RegionApp(region_name="another-region", region_app_id="region-app-a", app_id=74),
        ])
        relations = [
            ServiceGroupRelation(tenant_id="tenant-1", group_id=72, region_name="rainbond", service_id="valid-a"),
            ServiceGroupRelation(tenant_id="tenant-1", group_id=72, region_name="rainbond", service_id="internal-a"),
            ServiceGroupRelation(tenant_id="tenant-2", group_id=73, region_name="rainbond", service_id="valid-b"),
            ServiceGroupRelation(tenant_id="tenant-1", group_id=72, region_name="another-region", service_id="other-region"),
            ServiceGroupRelation(tenant_id="tenant-3", group_id=72, region_name="rainbond", service_id="other-tenant"),
        ]
        relations.extend([
            ServiceGroupRelation(tenant_id="tenant-1", group_id=1000 + i, region_name="rainbond",
                                 service_id="unrelated-{}".format(i))
            for i in range(500)
        ])
        ServiceGroupRelation.objects.bulk_create(relations)
        domains = [self.domain(relation.service_id) for relation in relations]
        domains.append(self.domain("valid-a", suffix="-secure", protocol="https"))
        ServiceDomain.objects.bulk_create(domains)

    def close_database(self):
        self.database.close()
        del connections[self.alias]
        connections.databases.pop(self.alias, None)

    @staticmethod
    def domain(service_id, suffix="", protocol="http"):
        return ServiceDomain(
            http_rule_id=service_id + suffix, region_id="fixture-region", tenant_id="fixture-tenant",
            service_id=service_id, service_name=service_id, domain_name=service_id + suffix + ".example.invalid",
            protocol=protocol, is_outer_service=service_id != "internal-a")

    def list_plugins(self, plugins, official=False):
        with mock.patch("console.services.plugin_service.region_api.list_plugins",
                        return_value=(None, {"list": plugins})) as upstream, \
                mock.patch("console.services.plugin_service.team_services.list_by_team_names", return_value=self.teams), \
                mock.patch("console.services.plugin_service.is_cloud_market_disabled", return_value=True):
            result = rbd_plugin_service.list_plugins("fixture-enterprise", "rainbond", official=official)
        upstream.assert_called_once_with("fixture-enterprise", "rainbond", official)
        return result

    @staticmethod
    def plugin(name="sample-a", region_app_id="region-app-a", team_name="plugins-a", access_urls=None):
        return {"name": name, "region_app_id": region_app_id, "team_name": team_name, "alias": name,
                "backend_service": "plugin-backend:8080/", "access_urls": access_urls or []}

    def test_real_query_excludes_other_apps_tenants_and_regions(self):
        with CaptureQueriesContext(self.database) as queries:
            rows = list(service_group_relation_repo.list_by_tenant_and_app_ids(
                ["tenant-1", "tenant-2"], [72, 73], "rainbond"))
        self.assertEqual({row.service_id for row in rows}, {"valid-a", "internal-a", "valid-b"})
        self.assertEqual(len(queries), 1)
        self.assertEqual(ServiceGroupRelation.objects.count(), 505)

    def test_empty_scope_never_reads_relations(self):
        for team_ids, app_ids in (([], [72]), (["tenant-1"], []), ([], [])):
            with self.subTest(teams=team_ids, apps=app_ids), CaptureQueriesContext(self.database) as queries:
                self.assertEqual([], list(service_group_relation_repo.list_by_tenant_and_app_ids(
                    team_ids, app_ids, "rainbond")))
                self.assertEqual(len(queries), 0)

    def test_service_materializes_only_plugin_relations_and_domains_for_large_team(self):
        loaded_relations, loaded_domains = [], []

        def relation_loaded(sender, instance, **kwargs):
            loaded_relations.append(instance.service_id)

        def domain_loaded(sender, instance, **kwargs):
            loaded_domains.append(instance.service_id)

        post_init.connect(relation_loaded, sender=ServiceGroupRelation)
        post_init.connect(domain_loaded, sender=ServiceDomain)
        try:
            with CaptureQueriesContext(self.database) as queries:
                plugins, need_authz = self.list_plugins([
                    self.plugin(), self.plugin("sample-b", "region-app-b", "plugins-b")])
        finally:
            post_init.disconnect(relation_loaded, sender=ServiceGroupRelation)
            post_init.disconnect(domain_loaded, sender=ServiceDomain)

        self.assertFalse(need_authz)
        self.assertEqual(sorted(loaded_relations), ["internal-a", "valid-a", "valid-b"])
        self.assertEqual(sorted(loaded_domains), ["internal-a", "valid-a", "valid-a", "valid-b"])
        self.assertEqual(len(queries), 3, "region mapping, scoped relations and scoped domains stay batched")
        self.assertEqual(plugins[0]["app_id"], 72)
        self.assertEqual(plugins[1]["app_id"], 73)
        self.assertEqual(set(plugins[0]["urls"]), {
            "http://valid-a.example.invalid", "https://valid-a-secure.example.invalid"})
        self.assertEqual(plugins[1]["urls"], ["http://valid-b.example.invalid"])
        self.assertEqual(plugins[0]["backend"], "http://plugin-backend:8080")
        self.assertEqual(plugins[0]["display_name"], "sample-a")

    def test_official_access_urls_and_ordinary_domain_fallback_keep_their_priority(self):
        for official in (False, True):
            with self.subTest(official=official):
                plugins, _ = self.list_plugins([
                    self.plugin(access_urls=["https://reported.example.invalid/"]),
                    self.plugin("sample-b", "region-app-b", "plugins-b"),
                ], official=official)
                expected = {"https://reported.example.invalid"} if official else {
                    "http://valid-a.example.invalid", "https://valid-a-secure.example.invalid"}
                self.assertEqual(set(plugins[0]["urls"]), expected)
                self.assertEqual(plugins[1]["urls"], ["http://valid-b.example.invalid"])

    def test_vm_nodeport_failure_retains_reported_url_then_domain_fallback(self):
        for access_urls in (["https://reported.example.invalid/"], []):
            with self.subTest(access_urls=access_urls), \
                    mock.patch("console.services.plugin_service.region_api.get_tenant_ns_resource",
                               side_effect=RuntimeError("controlled resource failure")):
                plugins, _ = self.list_plugins([
                    self.plugin(name="rainbond-vm", access_urls=access_urls)], official=True)
                expected = {"https://reported.example.invalid"} if access_urls else {
                    "http://valid-a.example.invalid", "https://valid-a-secure.example.invalid"}
                self.assertEqual(set(plugins[0]["urls"]), expected)

    def test_unmapped_plugin_never_loads_other_app_relations_or_domains(self):
        with CaptureQueriesContext(self.database) as queries:
            plugins, need_authz = self.list_plugins([self.plugin(region_app_id="unmapped-app")])
        self.assertFalse(need_authz)
        self.assertEqual(plugins[0]["app_id"], -1)
        self.assertEqual(plugins[0]["urls"], [])
        self.assertEqual(len(queries), 1, "empty mapped app IDs must short-circuit relation and domain SQL")

    def test_missing_plugin_team_does_not_read_other_teams_relations(self):
        self.teams = []
        with CaptureQueriesContext(self.database) as queries:
            plugins, _ = self.list_plugins([self.plugin()])
        self.assertEqual(plugins[0]["urls"], [])
        self.assertEqual(len(queries), 1)

    def test_empty_plugin_list_does_not_read_any_plugin_mapping_tables(self):
        with CaptureQueriesContext(self.database) as queries:
            self.assertEqual(self.list_plugins([]), ([], False))
        self.assertEqual(len(queries), 0)


class RainbondPluginServiceTests(TestCase):
    # capability_id: console.platform-plugin.vm-access-url-fallback

    def setUp(self):
        platform_plugin_service.clear_market_plugin_cache()

    def tearDown(self):
        platform_plugin_service.clear_market_plugin_cache()

    def test_official_enterprise_authz_and_scoped_mapping_are_preserved(self):
        plugin = PluginScopedReadIntegrationTests.plugin()
        team = SimpleNamespace(tenant_id="tenant-1", tenant_name="plugins-a")
        mapping = SimpleNamespace(app_id=72, region_app_id="region-app-a")
        market_plugin = {"plugin_id": "sample-a", "app_level": "enterprise"}
        with mock.patch("console.services.plugin_service.region_api.list_plugins",
                        return_value=(None, {"list": [plugin]})), \
                mock.patch("console.services.plugin_service.team_services.list_by_team_names", return_value=[team]), \
                mock.patch("console.services.plugin_service.region_app_repo.list_by_region_app_ids", return_value=[mapping]), \
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_and_app_ids",
                           return_value=[]) as relations, \
                mock.patch("console.services.plugin_service.domain_repo.list_by_component_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.is_cloud_market_disabled", return_value=False), \
                mock.patch("console.services.plugin_service.platform_plugin_service._get_market_platform_plugins_cached",
                           return_value=(None, [market_plugin])), \
                mock.patch("console.services.plugin_service.platform_plugin_service._select_market_plugin",
                           return_value=market_plugin):
            plugins, need_authz = rbd_plugin_service.list_plugins("fixture-enterprise", "rainbond", official=True)
        self.assertTrue(need_authz)
        self.assertEqual(plugins[0]["app_level"], "enterprise")
        self.assertEqual(plugins[0]["app_id"], 72)
        relations.assert_called_once_with(["tenant-1"], [72], "rainbond")

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
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_and_app_ids",
                           return_value=[]), \
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
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_and_app_ids",
                           return_value=[]), \
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
                mock.patch("console.services.plugin_service.region_app_repo.list_by_region_app_ids",
                           return_value=[region_app]), \
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_and_app_ids",
                           return_value=[relation]), \
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
                mock.patch("console.services.plugin_service.region_app_repo.list_by_region_app_ids",
                           return_value=[region_app]), \
                mock.patch("console.services.plugin_service.service_group_relation_repo.list_by_tenant_and_app_ids",
                           return_value=[relation]), \
                mock.patch("console.services.plugin_service.domain_repo.list_by_component_ids", return_value=[]), \
                mock.patch("console.services.plugin_service.region_api.get_tenant_ns_resource",
                           side_effect=service_lookup), \
                mock.patch("console.services.plugin_service.platform_plugin_service._get_market_platform_plugins",
                           return_value=(mock.Mock(), [])), \
                mock.patch("console.services.plugin_service.platform_plugin_service._select_market_plugin",
                           return_value=None):
            plugins, _ = rbd_plugin_service.list_plugins("eid", "rainbond", official=True, request=request)

        self.assertEqual(["http://172.16.20.221:31002"], plugins[0]["urls"])
