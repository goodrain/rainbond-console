# -*- coding: utf-8 -*-
import collections
import os
import sys
from contextlib import ExitStack
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.repositories import team_repo as team_repo_module  # noqa: E402
from console.repositories import region_repo as region_repo_module  # noqa: E402
from console.services import team_services as team_module  # noqa: E402


class Obj(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def get_name(self):
        return getattr(self, "real_name", None) or getattr(self, "nick_name", None)


def chained_values_result(rows):
    queryset = mock.MagicMock()
    values = mock.MagicMock()
    values.annotate.return_value = rows
    queryset.values.return_value = values
    return queryset, values


class TeamRepositoryBatchTest(TestCase):

    def test_batch_region_lookup_has_stable_database_order(self):
        queryset = mock.MagicMock()
        ordered_queryset = mock.MagicMock()
        queryset.order_by.return_value = ordered_queryset
        region_manager = mock.MagicMock()
        region_manager.filter.return_value = queryset

        with mock.patch.object(region_repo_module.RegionConfig, "objects", region_manager):
            result = region_repo_module.RegionRepo().get_region_by_region_names(["region-b", "region-a"])

        self.assertIs(result, ordered_queryset)
        region_manager.filter.assert_called_once_with(region_name__in=["region-b", "region-a"])
        queryset.order_by.assert_called_once_with("ID")

    def test_joined_teams_use_one_query_and_preserve_latest_permission_order(self):
        enterprise = Obj(ID=7)
        team_older = Obj(ID=11, tenant_alias="Older")
        team_latest = Obj(ID=12, tenant_alias="Latest")

        enterprise_queryset = mock.MagicMock()
        enterprise_queryset.first.return_value = enterprise
        enterprise_manager = mock.MagicMock()
        enterprise_manager.filter.return_value = enterprise_queryset

        permission_values = mock.MagicMock()
        permission_values.order_by.return_value = [12, 11, 12]
        permission_queryset = mock.MagicMock()
        permission_queryset.values_list.return_value = permission_values
        permission_manager = mock.MagicMock()
        permission_manager.filter.return_value = permission_queryset

        tenant_manager = mock.MagicMock()
        tenant_manager.filter.return_value = [team_older, team_latest]

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(team_repo_module.TenantEnterprise, "objects", enterprise_manager))
            stack.enter_context(mock.patch.object(team_repo_module.PermRelTenant, "objects", permission_manager))
            stack.enter_context(mock.patch.object(team_repo_module.Tenants, "objects", tenant_manager))
            result = team_repo_module.TeamRepo().get_tenants_by_user_id_and_eid("enterprise-1", "user-1", "te")

        self.assertEqual(result, [team_latest, team_older])
        tenant_manager.filter.assert_called_once_with(ID__in=[12, 11], tenant_alias__contains="te")

    def test_not_joined_teams_are_scoped_to_requested_enterprise(self):
        enterprise_queryset = mock.MagicMock()
        enterprise_queryset.first.return_value = Obj(ID=7)
        enterprise_manager = mock.MagicMock()
        enterprise_manager.filter.return_value = enterprise_queryset

        permission_values = mock.MagicMock()
        permission_values.order_by.return_value = [11]
        permission_queryset = mock.MagicMock()
        permission_queryset.values_list.return_value = permission_values
        permission_manager = mock.MagicMock()
        permission_manager.filter.return_value = permission_queryset

        tenant_manager = mock.MagicMock()
        tenant_manager.filter.return_value = [Obj(ID=12)]

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(team_repo_module.TenantEnterprise, "objects", enterprise_manager))
            stack.enter_context(mock.patch.object(team_repo_module.PermRelTenant, "objects", permission_manager))
            stack.enter_context(mock.patch.object(team_repo_module.Tenants, "objects", tenant_manager))
            result = team_repo_module.TeamRepo.get_user_notjoin_teams("enterprise-1", "user-1", "target")

        self.assertEqual(len(result), 1)
        args, kwargs = tenant_manager.filter.call_args
        self.assertEqual(kwargs, {"enterprise_id": "enterprise-1"})
        self.assertIn("tenant_alias", str(args[0]))


class TeamCollectionBatchTest(TestCase):

    def setUp(self):
        self.service = team_module.TeamService()
        self.request_user = Obj(user_id=100, nick_name="request-user")
        self.team_one = Obj(
            tenant_name="one", tenant_alias="One", tenant_id="team-1", create_time="2026-08-08",
            enterprise_id="enterprise-1", creater=100, logo="one.png")
        self.team_two = Obj(
            tenant_name="two", tenant_alias="Two", tenant_id="team-2", create_time="2026-08-07",
            enterprise_id="enterprise-1", creater=200, logo="two.png")

    def test_batch_assembly_keeps_order_fields_and_uses_constant_queries(self):
        service_queryset, service_values = chained_values_result([
            {"tenant_id": "team-1", "total": 3},
        ])
        service_manager = mock.MagicMock()
        service_manager.filter.return_value = service_queryset

        group_queryset, group_values = chained_values_result([
            {"tenant_id": "team-1", "total": 2},
            {"tenant_id": "team-2", "total": 1},
        ])
        group_manager = mock.MagicMock()
        group_manager.filter.return_value = group_queryset

        region_queryset = mock.MagicMock()
        region_queryset.values.return_value = [{"tenant_id": "team-1", "region_name": "region-a"}]
        tenant_region_manager = mock.MagicMock()
        tenant_region_manager.filter.return_value = region_queryset

        role_one = Obj(ID=501, kind_id="team-1", name="developer")
        role_two = Obj(ID=502, kind_id="team-2", name="viewer")
        role_manager = mock.MagicMock()
        role_manager.filter.return_value = [role_one, role_two]
        user_role_queryset = mock.MagicMock()
        user_role_queryset.order_by.return_value = [Obj(role_id="502"), Obj(role_id="501")]
        user_role_manager = mock.MagicMock()
        user_role_manager.filter.return_value = user_role_queryset

        region = Obj(region_name="region-a", region_alias="Region A")
        owner = Obj(user_id=100, real_name="Owner One", nick_name="owner-one")

        with ExitStack() as stack:
            owners_mock = stack.enter_context(
                mock.patch.object(team_module.user_repo, "get_by_user_ids", return_value=[owner]))
            stack.enter_context(mock.patch.object(team_module.TenantRegionInfo, "objects", tenant_region_manager))
            region_mock = stack.enter_context(
                mock.patch.object(team_module.region_repo, "get_region_by_region_names", return_value=[region]))
            stack.enter_context(mock.patch.object(team_module.RoleInfo, "objects", role_manager))
            stack.enter_context(mock.patch.object(team_module.UserRole, "objects", user_role_manager))
            stack.enter_context(mock.patch.object(team_module.TenantServiceInfo, "objects", service_manager))
            stack.enter_context(mock.patch.object(team_module.ServiceGroup, "objects", group_manager))

            result = self.service.teams_with_region_info(
                [self.team_two, self.team_one], self.request_user, get_region=True)

        self.assertEqual([team["team_id"] for team in result], ["team-2", "team-1"])
        self.assertIsNone(result[0]["owner_name"])
        self.assertEqual(result[0]["roles"], ["viewer"])
        self.assertEqual(result[0]["region"], "")
        self.assertEqual(result[0]["region_list"], [])
        self.assertEqual(result[0]["service_count"], 0)
        self.assertEqual(result[0]["app_count"], 1)
        self.assertEqual(result[1]["owner_name"], "Owner One")
        self.assertEqual(result[1]["roles"], ["developer", "owner"])
        self.assertEqual(result[1]["region_list"], [{"region_name": "region-a", "region_alias": "Region A"}])
        self.assertEqual(result[1]["service_count"], 3)
        self.assertEqual(result[1]["app_count"], 2)

        owners_mock.assert_called_once_with([200, 100])
        tenant_region_manager.filter.assert_called_once_with(tenant_id__in=["team-2", "team-1"])
        region_mock.assert_called_once_with(["region-a"])
        role_manager.filter.assert_called_once_with(kind="team", kind_id__in=["team-2", "team-1"])
        user_role_manager.filter.assert_called_once_with(role_id__in=[501, 502], user_id=100)
        user_role_queryset.order_by.assert_called_once_with("ID")
        service_manager.filter.assert_called_once_with(tenant_id__in=["team-2", "team-1"])
        service_values.annotate.assert_called_once()
        group_manager.filter.assert_called_once_with(tenant_id__in=["team-2", "team-1"])
        group_values.annotate.assert_called_once()

    def test_batch_without_regions_keeps_legacy_shape(self):
        service_queryset, _ = chained_values_result([])
        group_queryset, _ = chained_values_result([])
        service_manager = mock.MagicMock()
        service_manager.filter.return_value = service_queryset
        group_manager = mock.MagicMock()
        group_manager.filter.return_value = group_queryset

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(team_module.user_repo, "get_by_user_ids", return_value=[]))
            region_mock = stack.enter_context(mock.patch.object(team_module.TenantRegionInfo.objects, "filter"))
            stack.enter_context(mock.patch.object(team_module.TenantServiceInfo, "objects", service_manager))
            stack.enter_context(mock.patch.object(team_module.ServiceGroup, "objects", group_manager))
            result = self.service.teams_with_region_info([self.team_two], get_region=False)

        self.assertNotIn("region", result[0])
        self.assertNotIn("region_list", result[0])
        self.assertNotIn("roles", result[0])
        region_mock.assert_not_called()

    def test_batch_roles_follow_user_role_order_and_append_owner_last(self):
        service_queryset, _ = chained_values_result([])
        group_queryset, _ = chained_values_result([])
        service_manager = mock.MagicMock()
        service_manager.filter.return_value = service_queryset
        group_manager = mock.MagicMock()
        group_manager.filter.return_value = group_queryset

        role_one = Obj(ID=501, kind_id="team-1", name="developer")
        role_two = Obj(ID=502, kind_id="team-1", name="viewer")
        role_manager = mock.MagicMock()
        role_manager.filter.return_value = [role_one, role_two]

        user_role_queryset = mock.MagicMock()
        user_role_queryset.__iter__.return_value = iter([
            Obj(ID=2, role_id="501"),
            Obj(ID=1, role_id="502"),
        ])
        user_role_queryset.order_by.return_value = [
            Obj(ID=1, role_id="502"),
            Obj(ID=2, role_id="501"),
        ]
        user_role_manager = mock.MagicMock()
        user_role_manager.filter.return_value = user_role_queryset

        owner = Obj(user_id=100, real_name="Owner One", nick_name="owner-one")
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(team_module.user_repo, "get_by_user_ids", return_value=[owner]))
            stack.enter_context(mock.patch.object(team_module.RoleInfo, "objects", role_manager))
            stack.enter_context(mock.patch.object(team_module.UserRole, "objects", user_role_manager))
            stack.enter_context(mock.patch.object(team_module.TenantServiceInfo, "objects", service_manager))
            stack.enter_context(mock.patch.object(team_module.ServiceGroup, "objects", group_manager))

            result = self.service.teams_with_region_info(
                [self.team_one], self.request_user, get_region=False)

        self.assertEqual(result[0]["roles"], ["viewer", "developer", "owner"])
        user_role_queryset.order_by.assert_called_once_with("ID")

    def test_batch_query_calls_do_not_grow_with_team_count(self):
        service_queryset, _ = chained_values_result([])
        group_queryset, _ = chained_values_result([])
        service_manager = mock.MagicMock()
        service_manager.filter.return_value = service_queryset
        group_manager = mock.MagicMock()
        group_manager.filter.return_value = group_queryset

        def make_teams(count):
            return [
                Obj(
                    tenant_name="team-{}".format(index), tenant_alias="Team {}".format(index),
                    tenant_id="team-{}".format(index), create_time="2026-08-08", enterprise_id="enterprise-1",
                    creater=index, logo=None)
                for index in range(count)
            ]

        with ExitStack() as stack:
            owners_mock = stack.enter_context(
                mock.patch.object(team_module.user_repo, "get_by_user_ids", return_value=[]))
            stack.enter_context(mock.patch.object(team_module.TenantServiceInfo, "objects", service_manager))
            stack.enter_context(mock.patch.object(team_module.ServiceGroup, "objects", group_manager))

            self.service.teams_with_region_info(make_teams(1), get_region=False)
            one_team_calls = (
                owners_mock.call_count,
                service_manager.filter.call_count,
                group_manager.filter.call_count,
            )

            owners_mock.reset_mock()
            service_manager.filter.reset_mock()
            group_manager.filter.reset_mock()
            self.service.teams_with_region_info(make_teams(20), get_region=False)
            many_team_calls = (
                owners_mock.call_count,
                service_manager.filter.call_count,
                group_manager.filter.call_count,
            )

        self.assertEqual(one_team_calls, (1, 1, 1))
        self.assertEqual(many_team_calls, one_team_calls)

    def test_collection_entrypoints_call_batch_assembly(self):
        joined = [self.team_one, self.team_two]
        assembled = [
            {"team_id": "team-1", "region_list": []},
            {"team_id": "team-2", "region_list": [{"region_name": "region-a"}]},
        ]

        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(team_module.enterprise_repo, "get_enterprise_user_teams", return_value=joined))
            batch_mock = stack.enter_context(
                mock.patch.object(self.service, "teams_with_region_info", return_value=assembled))
            result = self.service.get_teams_region_by_user_id("enterprise-1", self.request_user)

        self.assertEqual(result, [assembled[0], assembled[1]])
        batch_mock.assert_called_once_with(joined, self.request_user, get_region=True)

    def test_enterprise_team_list_uses_batch_assembly(self):
        raw_tenants = mock.MagicMock()
        raw_tenants.count.return_value = 2
        raw_tenants.__iter__.return_value = iter([self.team_two, self.team_one])
        assembled = [{"team_id": "team-2"}, {"team_id": "team-1"}]

        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(team_module.team_repo, "get_teams_by_enterprise_id", return_value=raw_tenants))
            batch_mock = stack.enter_context(
                mock.patch.object(self.service, "teams_with_region_info", return_value=assembled))
            result, total = self.service.get_enterprise_teams("enterprise-1", user=self.request_user)

        self.assertEqual(total, 2)
        self.assertEqual(result, assembled)
        batch_mock.assert_called_once_with([self.team_two, self.team_one], self.request_user)

    def test_user_team_list_batches_not_joined_teams_without_regions_or_roles(self):
        nojoin = [self.team_two]
        joined_result = [{"team_id": "team-1", "roles": ["owner"]}]
        nojoin_result = [{"team_id": "team-2"}]

        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(self.service, "get_teams_region_by_user_id", return_value=joined_result))
            nojoin_mock = stack.enter_context(
                mock.patch.object(team_module.team_repo, "get_user_notjoin_teams", return_value=nojoin))
            batch_mock = stack.enter_context(
                mock.patch.object(self.service, "teams_with_region_info", return_value=nojoin_result))
            result = self.service.list_user_teams("enterprise-1", self.request_user, "target")

        self.assertEqual(result, [{"team_id": "team-1", "roles": ["owner"]}, {"team_id": "team-2"}])
        nojoin_mock.assert_called_once_with("enterprise-1", 100, "target")
        batch_mock.assert_called_once_with(nojoin, get_region=False)
