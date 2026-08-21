import json
import collections
import collections.abc
import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

from addict import Dict

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

if "openapi_client" not in sys.modules:
    openapi_client = ModuleType("openapi_client")
    configuration = ModuleType("openapi_client.configuration")
    rest = ModuleType("openapi_client.rest")
    configuration.Configuration = type("Configuration", (), {})
    rest.ApiException = type("ApiException", (Exception,), {})
    sys.modules["openapi_client"] = openapi_client
    sys.modules["openapi_client.configuration"] = configuration
    sys.modules["openapi_client.rest"] = rest

import django  # noqa: E402

django.setup()

from console.repositories.app import TenantServiceInfoRepository  # noqa: E402
from console.repositories.app_config import TenantServiceRelationRepository  # noqa: E402
from console.repositories.perm_repo import OptimizedRolePermRepo  # noqa: E402
from console.repositories.plugin.listing import list_plugins_for_service  # noqa: E402
from console.repositories.team_repo import TeamRepo  # noqa: E402
from console.repositories.user_repo import UserRepo  # noqa: E402
from console.repositories.user_role_repo import UserRoleRepo  # noqa: E402
from console.services.app_config.domain_service import DomainService  # noqa: E402
from console.services.market_app_service import MarketAppService  # noqa: E402
from console.services.service_services import BaseService  # noqa: E402

domain_service_module = importlib.import_module("console.services.app_config.domain_service")


class DatabaseAggregationPortabilityTest(TestCase):
    # capability_id: console.database.application-side-aggregation
    def test_enterprise_group_services_are_aggregated_in_python(self):
        with mock.patch("console.services.service_services.Tenants.objects.filter") as tenant_filter, \
                mock.patch("console.services.service_services.ServiceGroup.objects.filter") as group_filter, \
                mock.patch("console.services.service_services.ServiceGroupRelation.objects.filter") as relation_filter:
            tenant_filter.return_value.values_list.return_value = ["tenant-1"]
            group_filter.return_value.values_list.return_value = [10]
            relation_filter.return_value.order_by.return_value.values_list.return_value = [
                (10, "service-1"), (10, "service-2")
            ]

            result = BaseService().get_enterprise_group_services("enterprise-1")

        self.assertEqual(result, [{"group_id": 10, "service_ids": '["service-1", "service-2"]'}])

    def test_application_service_list_is_aggregated_without_database_json_functions(self):
        group = SimpleNamespace(ID=10, group_name="App", tenant_id="tenant-1")
        relation = SimpleNamespace(ID=1, group_id=10, service_id="service-1")
        service = SimpleNamespace(
            service_id="service-1", service_cname="Component", service_key="key", service_alias="alias")
        relation_query = mock.Mock()
        relation_query.order_by.return_value = [relation]

        with mock.patch("console.repositories.app.ServiceGroupRelation.objects.filter", return_value=relation_query), \
                mock.patch("console.repositories.app.TenantServiceInfo.objects.filter", return_value=[service]):
            result = TenantServiceInfoRepository._serialize_app_groups([group])

        self.assertEqual(result[0].ID, 10)
        self.assertEqual(json.loads(result[0].service_list), [{
            "service_cname": "Component",
            "service_id": "service-1",
            "service_key": "key",
            "service_alias": "alias"
        }])

    def test_role_names_are_joined_in_python(self):
        tenant = SimpleNamespace(ID=3)
        with mock.patch("console.repositories.user_role_repo.Tenants.objects.filter") as tenant_filter, \
                mock.patch("console.repositories.user_role_repo.PermRelTenant.objects.filter") as permission_filter, \
                mock.patch("console.repositories.user_role_repo.TenantUserRole.objects.filter") as role_filter:
            tenant_filter.return_value.only.return_value.first.return_value = tenant
            permission_filter.return_value.values_list.return_value = [7, 8]
            role_filter.return_value.order_by.return_value.values_list.return_value = ["developer", "viewer"]

            result = UserRoleRepo().get_role_names("user-1", "tenant-1")

        self.assertEqual(result, "developer,viewer")

    def test_domain_list_uses_orm_and_preserves_response_columns(self):
        expected = [("example.com", 1, False, 0, "alias", "http", "service", 80, "rule", "service-id", "/", "",
                     "", 100, True, False, "[]")]
        resources = mock.MagicMock()
        resources.count.return_value = 1
        resources.order_by.return_value.values_list.return_value = expected

        with mock.patch.object(domain_service_module.ServiceGroupRelation.objects, "filter") as relations, \
                mock.patch.object(domain_service_module.ServiceDomain.objects, "filter", return_value=resources) as domains:
            relations.return_value.values_list.return_value = ["service-id"]
            result, total = DomainService().get_app_service_domain_list(
                SimpleNamespace(region_id="region-id"), SimpleNamespace(tenant_id="tenant-id"), "10", None, 1, 10)

        self.assertEqual(result, expected)
        self.assertEqual(total, 1)
        domains.assert_called_once_with(
            tenant_id="tenant-id", region_id="region-id", service_id__in=["service-id"])

    def test_role_permissions_convert_string_ids_before_orm_filtering(self):
        user_roles = mock.MagicMock()
        user_roles.values_list.return_value = ["12", "invalid"]
        role_infos = mock.MagicMock()
        role_infos.values_list.return_value = [12]
        permissions = mock.MagicMock()
        permissions.values_list.return_value.distinct.return_value = [1001]

        with mock.patch("console.repositories.perm_repo.UserRole.objects.filter", return_value=user_roles), \
                mock.patch("console.repositories.perm_repo.RoleInfo.objects.filter", return_value=role_infos) as roles, \
                mock.patch("console.repositories.perm_repo.RolePerms.objects.filter", return_value=permissions):
            result = OptimizedRolePermRepo().get_user_team_perm_codes("7", "tenant", app_id=-1)

        self.assertEqual(result, [1001])
        roles.assert_called_once_with(ID__in=[12], kind="team", kind_id="tenant")

    def test_plugin_listing_is_composed_from_orm_rows(self):
        plugin_a = SimpleNamespace(
            plugin_id="plugin-a", desc="A", plugin_alias="Plugin A", category="general-plugin",
            origin_share_id="origin-a")
        plugin_b = SimpleNamespace(
            plugin_id="plugin-b", desc="B", plugin_alias="Plugin B", category="general-plugin",
            origin_share_id="origin-b")
        relation = SimpleNamespace(
            plugin_id="plugin-a", build_version="v1", plugin_status=True, min_memory=128, min_cpu=100)
        version_a = SimpleNamespace(plugin_id="plugin-a", build_version="v1")
        version_b = SimpleNamespace(plugin_id="plugin-b", build_version="v2")
        version_query = mock.MagicMock()
        version_query.order_by.return_value = [version_a, version_b]

        with mock.patch("console.repositories.plugin.listing.TenantPlugin.objects.filter",
                        return_value=[plugin_a, plugin_b]), \
                mock.patch("console.repositories.plugin.listing.TenantServicePluginRelation.objects.filter",
                           return_value=[relation]), \
                mock.patch("console.repositories.plugin.listing.PluginBuildVersion.objects.filter",
                           side_effect=[version_query, [version_b]]):
            installed, installable = list_plugins_for_service(
                "region", "tenant", "service", "", include_runtime_resources=True)

        self.assertEqual(installed[0].plugin_id, "plugin-a")
        self.assertEqual(installed[0].min_memory, 128)
        self.assertEqual(installable[0].plugin_id, "plugin-b")

    def test_team_user_rows_are_composed_without_raw_join_sql(self):
        tenant = SimpleNamespace(ID=3)
        permissions = mock.MagicMock()
        permissions.values_list.return_value = [(7, "developer")]
        user = SimpleNamespace(
            user_id=7, email="user@example.com", nick_name="User", phone="", is_active=True,
            enterprise_id="enterprise")

        with mock.patch("console.repositories.user_repo.Tenants.objects.filter") as tenant_filter, \
                mock.patch("console.repositories.user_repo.PermRelTenant.objects.filter", return_value=permissions), \
                mock.patch("console.repositories.user_repo.Users.objects.filter", return_value=[user]):
            tenant_filter.return_value.only.return_value.first.return_value = tenant
            rows = UserRepo._tenant_user_rows("tenant")

        self.assertEqual(rows[0].user_id, 7)
        self.assertEqual(rows[0].identity, "developer")

    def test_team_count_keeps_legacy_alias_only_search_semantics(self):
        permissions = mock.MagicMock()
        permissions.values_list.return_value = [3]
        tenants = mock.MagicMock()
        filtered_tenants = mock.MagicMock()
        filtered_tenants.values.return_value.distinct.return_value.count.return_value = 2
        tenants.filter.return_value = filtered_tenants

        with mock.patch("console.repositories.team_repo.PermRelTenant.objects.filter", return_value=permissions), \
                mock.patch("console.repositories.team_repo.Tenants.objects.filter", return_value=tenants):
            total = TeamRepo().count_by_user_id("enterprise", "7", "matching-user-name")

        tenants.filter.assert_called_once_with(tenant_alias__icontains="matching-user-name")
        self.assertEqual(total, 2)

    def test_team_list_keeps_case_insensitive_user_name_search(self):
        permissions = mock.MagicMock()
        permissions.values_list.return_value = [3]
        tenants = mock.MagicMock()
        tenants.distinct.return_value = []
        users = mock.MagicMock()
        users.first.return_value = SimpleNamespace(nick_name="Admin")

        with mock.patch("console.repositories.team_repo.PermRelTenant.objects.filter", return_value=permissions), \
                mock.patch("console.repositories.team_repo.Tenants.objects.filter", return_value=tenants), \
                mock.patch("console.repositories.team_repo.Users.objects.filter", return_value=users):
            result = TeamRepo().list_by_user_id("enterprise", "7", "admin")

        self.assertEqual(result, [])
        tenants.filter.assert_not_called()

    def test_market_app_tags_do_not_cross_enterprise_boundaries(self):
        connection = mock.MagicMock()
        connection.query.side_effect = [
            [
                Dict(group_key="shared-key", enterprise_id="public"),
                Dict(group_key="shared-key", enterprise_id="enterprise"),
            ],
            [
                Dict(group_key="shared-key", enterprise_id="public", tag_id=1, tag_name="Public"),
                Dict(group_key="shared-key", enterprise_id="enterprise", tag_id=2, tag_name="Private"),
            ],
        ]

        with mock.patch("console.services.market_app_service.BaseConnection", return_value=connection):
            apps = MarketAppService().get_visiable_apps_v2(
                SimpleNamespace(enterprise_id="enterprise", tenant_name="team"), "", "", "", 1, 10)

        self.assertEqual(json.loads(apps[0].tags), [{"tag_id": "1", "name": "Public"}])
        self.assertEqual(json.loads(apps[1].tags), [{"tag_id": "2", "name": "Private"}])

    def test_database_dependency_detection_keeps_case_insensitive_image_matching(self):
        tenant_ids = mock.MagicMock()
        services = mock.MagicMock()
        services.filter.return_value.values_list.return_value = ["database-service"]
        service_rows = [
            SimpleNamespace(
                service_id="database-service", image="MySQL:8", service_source="market"),
            SimpleNamespace(
                service_id="application-service", image="example/app", service_source="source_code"),
        ]
        services.__iter__.return_value = iter(service_rows)
        relations = [SimpleNamespace(service_id="application-service", dep_service_id="database-service")]

        with mock.patch("console.repositories.app_config.Tenants.objects.filter") as tenant_filter, \
                mock.patch("console.repositories.app_config.TenantServiceInfo.objects.filter", return_value=services), \
                mock.patch("console.repositories.app_config.TenantServiceRelation.objects.filter",
                           return_value=relations), \
                mock.patch("console.repositories.app_config.ServiceSourceInfo.objects.filter") as source_filter:
            tenant_filter.return_value.values_list.return_value = tenant_ids
            source_filter.return_value.values_list.return_value = []
            result = TenantServiceRelationRepository().check_db_dep_by_eid("enterprise")

        self.assertTrue(result)
        services.filter.assert_called_once()
