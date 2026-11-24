# -*- coding: utf-8 -*-
import json
import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import connections  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from console.models.main import RegionConfig  # noqa: E402
from console.services.region_services import RegionService  # noqa: E402
from console.views import user_operation as view_module  # noqa: E402
from www.models.main import Tenants, TenantRegionInfo  # noqa: E402


REGION_FIELDS = {
    "service_status", "is_active", "region_status", "team_region_alias", "region_tenant_id",
    "team_region_name", "region_scope", "region_create_time", "websocket_uri", "tcpdomain", "region_id",
}


# capability_id: console.user-details.batch-team-region-reads
class UserDetailsRegionBatchIntegrationTests(TestCase):
    def setUp(self):
        self.alias = "user_details_region_batch_test"
        connections.databases[self.alias] = {
            "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
            "ATOMIC_REQUESTS": False, "AUTOCOMMIT": True, "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False, "OPTIONS": {}, "TIME_ZONE": None,
            "USER": "", "PASSWORD": "", "HOST": "", "PORT": "", "TEST": {},
        }
        self.database = connections[self.alias]
        self.addCleanup(self.close_database)
        models = (Tenants, TenantRegionInfo, RegionConfig)
        with self.database.schema_editor() as schema:
            for model in models:
                schema.create_model(model)
        for model in models:
            patcher = mock.patch.object(model, "objects", model.objects.db_manager(self.alias))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.service = RegionService()

    def close_database(self):
        self.database.close()
        del connections[self.alias]
        connections.databases.pop(self.alias, None)

    @staticmethod
    def team(index, owner=7):
        return Tenants.objects.create(
            tenant_id="fixture-team-{}".format(index), tenant_name="fixture-{}".format(index),
            tenant_alias="Fixture {}".format(index), namespace="fixture-ns-{}".format(index),
            enterprise_id="fixture-enterprise", creater=owner, limit_memory=2048)

    @staticmethod
    def config(name, status="1"):
        return RegionConfig.objects.create(
            region_id="fixture-id-" + name, region_name=name, region_alias="Alias " + name,
            url="https://{}.example.invalid".format(name), wsurl="wss://{}.example.invalid/socket".format(name),
            httpdomain="{}.example.invalid".format(name), tcpdomain="tcp.{}.example.invalid".format(name),
            status=status, scope="private", enterprise_id="fixture-enterprise")

    @staticmethod
    def membership(team, name, active=True, initialized=True, status=1):
        return TenantRegionInfo.objects.create(
            tenant_id=team.tenant_id, region_name=name, is_active=active, is_init=initialized,
            service_status=status, region_tenant_id="regional-{}-{}".format(team.ID, name),
            region_tenant_name=team.tenant_name, region_scope="public")

    def old_lists(self, teams):
        return {team.tenant_name: self.service.get_region_list_by_team_name(team.tenant_name) for team in teams}

    def populated_teams(self):
        self.config("shared")
        teams = [self.team(index) for index in range(100)]
        for team in teams:
            self.membership(team, "shared")
        return teams

    def test_original_region_subgraph_baseline_grows_with_team_count(self):
        teams = self.populated_teams()
        measurements = []
        for count in (1, 10, 100):
            with self.subTest(team_count=count), CaptureQueriesContext(self.database) as queries:
                result = self.old_lists(teams[:count])
            self.assertEqual(len(result), count)
            self.assertEqual(len(queries), count * 3)
            measurements.append({"teams": count, "old_region_queries": len(queries)})
        print("PERF_REGION_BASELINE " + json.dumps(measurements, sort_keys=True))

    def test_one_ten_and_hundred_teams_keep_exact_values_with_two_queries(self):
        teams = self.populated_teams()
        measurements = []
        for count in (1, 10, 100):
            with self.subTest(team_count=count):
                selected = teams[:count]
                with CaptureQueriesContext(self.database) as old_queries:
                    expected = self.old_lists(selected)
                with CaptureQueriesContext(self.database) as batch_queries:
                    actual = self.service.get_region_lists_by_tenants(selected)
                self.assertEqual(expected, actual)
                self.assertEqual(len(batch_queries), 2)
                self.assertGreater(len(old_queries), len(batch_queries))
                for regions in actual.values():
                    self.assertEqual(set(regions[0]), REGION_FIELDS)
                measurements.append({"teams": count, "old_region_queries": len(old_queries),
                                     "batch_region_queries": len(batch_queries)})
        print("PERF_REGION_BATCH " + json.dumps(measurements, sort_keys=True))

    def test_empty_authorized_team_list_uses_no_queries(self):
        self.populated_teams()
        with CaptureQueriesContext(self.database) as queries:
            self.assertEqual(self.service.get_region_lists_by_tenants([]), {})
        self.assertEqual(len(queries), 0)

    def test_no_active_initialized_regions_uses_one_query(self):
        team = self.team("empty")
        self.config("inactive")
        self.config("uninitialized")
        self.membership(team, "inactive", active=False)
        self.membership(team, "uninitialized", initialized=False)
        with CaptureQueriesContext(self.database) as queries:
            result = self.service.get_region_lists_by_tenants([team])
        self.assertEqual(result, {team.tenant_name: []})
        self.assertEqual(len(queries), 1)

    def test_status_filter_missing_config_scope_and_order_match_old_helper(self):
        owner, member, outsider = self.team("owner"), self.team("member"), self.team("outside")
        self.config("z-active", "1")
        self.config("a-maintenance", "3")
        self.config("disabled", "2")
        self.config("inactive", "1")
        self.config("not-initialized", "1")
        self.config("foreign-only", "1")
        self.membership(owner, "z-active", status=2)
        self.membership(owner, "a-maintenance", status=0)
        self.membership(owner, "disabled")
        self.membership(owner, "missing-config")
        self.membership(owner, "inactive", active=False)
        self.membership(owner, "not-initialized", initialized=False)
        self.membership(member, "a-maintenance")
        self.membership(outsider, "foreign-only")
        selected = [member, owner]
        expected = self.old_lists(selected)
        with CaptureQueriesContext(self.database) as queries:
            actual = self.service.get_region_lists_by_tenants(selected)
        self.assertEqual(actual, expected)
        self.assertEqual(list(actual), [member.tenant_name, owner.tenant_name])
        self.assertEqual(len(queries), 2)
        self.assertNotIn(outsider.tenant_name, actual)
        self.assertEqual({region["team_region_name"] for region in actual[owner.tenant_name]},
                         {"a-maintenance", "z-active"})
        for regions in actual.values():
            for region in regions:
                self.assertEqual(set(region), REGION_FIELDS)
                self.assertNotEqual(region["team_region_name"], "foreign-only")


# capability_id: console.user-details.batch-team-region-reads
class UserDetailsRegionBatchViewTests(TestCase):
    @staticmethod
    def team(index, creator):
        return SimpleNamespace(
            ID=index, tenant_id="team-{}".format(index), tenant_name="team-name-{}".format(index),
            tenant_alias="Team {}".format(index), limit_memory=2048, creater=creator,
            create_time="fixture-created", namespace="namespace-{}".format(index))

    def test_actual_view_batches_only_authorized_teams_and_keeps_user_team_permissions(self):
        user = SimpleNamespace(
            user_id=7, nick_name="fixture-user", real_name="Fixture", logo="fixture-logo", email="",
            enterprise_id="fixture-enterprise", phone="", is_sys_admin=False)
        owner, member, no_region = self.team(1, user.user_id), self.team(2, 99), self.team(3, user.user_id)
        authorized = [member, no_region, owner]
        region_map = {
            member.tenant_name: [{"region_id": "member-region"}],
            owner.tenant_name: [{"region_id": "owner-region"}],
            no_region.tenant_name: [],
        }
        request = SimpleNamespace(GET={"team_name": "selected-filter"}, user=user)
        view = view_module.UserDetailsView()
        view.user = user
        view.is_enterprise_admin = False
        with ExitStack() as stack:
            selected = stack.enter_context(mock.patch.object(
                view_module.team_services, "get_current_user_tenants", return_value=iter(authorized)))
            batch = stack.enter_context(mock.patch.object(
                view_module.region_services, "get_region_lists_by_tenants", return_value=region_map, create=True))
            old = stack.enter_context(mock.patch.object(
                view_module.region_services, "get_region_list_by_team_name",
                side_effect=AssertionError("per-team lookup must not run in the view")))
            stack.enter_context(mock.patch.object(
                view_module.enterprise_services, "get_enterprise_by_enterprise_id",
                return_value=SimpleNamespace(is_active=True)))
            stack.enter_context(mock.patch.object(
                view_module.agent_access_service, "ensure_initial_enterprise_admin_marker", return_value=None))
            stack.enter_context(mock.patch.object(view_module.user_services, "list_roles", return_value=["enterprise-role"]))
            stack.enter_context(mock.patch.object(
                view_module, "list_enterprise_perms_by_roles", return_value=["enterprise-read"]))
            roles = stack.enter_context(mock.patch.object(
                view_module.user_kind_role_service, "get_user_roles", return_value={"roles": ["team-role"]}))
            perms = stack.enter_context(mock.patch.object(
                view_module.user_kind_perm_service, "get_user_perms", return_value={"permissions": ["team-read"]}))
            stack.enter_context(mock.patch.object(
                view_module.oauth_user_repo, "get_user_oauth_services_info", return_value=[]))
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"code", "msg", "msg_show", "data"})
        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["msg"], "Obtain my details to be successful.")
        self.assertEqual(response.data["msg_show"], "获取我的详情成功")
        self.assertEqual(set(response.data["data"]), {"bean", "list"})
        self.assertEqual(response.data["data"]["list"], [])
        selected.assert_called_once_with(user_id=user.user_id, team_name="selected-filter")
        batch.assert_called_once_with(authorized)
        old.assert_not_called()
        details = response.data["data"]["bean"]
        self.assertEqual(details["user_id"], user.user_id)
        self.assertEqual(details["user_name"], user.nick_name)
        self.assertEqual(details["real_name"], user.real_name)
        self.assertEqual(details["logo"], user.logo)
        self.assertEqual(details["email"], "")
        self.assertEqual(details["enterprise_id"], user.enterprise_id)
        self.assertEqual(details["phone"], "")
        self.assertFalse(details["is_sys_admin"])
        self.assertTrue(details["is_enterprise_active"])
        self.assertFalse(details["is_enterprise_admin"])
        self.assertFalse(details["is_initial_enterprise_admin"])
        self.assertEqual(details["roles"], ["enterprise-role"])
        self.assertEqual(details["permissions"], ["enterprise-read"])
        self.assertEqual(details["oauth_services"], [])
        self.assertEqual([team["team_id"] for team in details["teams"]], [owner.ID, member.ID])
        for source, actual in zip((owner, member), details["teams"]):
            self.assertEqual(actual, {
                "team_id": source.ID, "team_name": source.tenant_name, "team_alias": source.tenant_alias,
                "limit_memory": source.limit_memory, "region": region_map[source.tenant_name],
                "creater": source.creater, "create_time": source.create_time, "namespace": source.namespace,
                "role_name_list": ["team-role"], "tenant_actions": ["team-read"],
                "is_team_owner": source.creater == user.user_id,
            })
        self.assertEqual(roles.call_args_list, [
            mock.call(kind="team", kind_id=member.tenant_id, user=user),
            mock.call(kind="team", kind_id=owner.tenant_id, user=user),
        ])
        self.assertEqual(perms.call_args_list, [
            mock.call(kind="team", kind_id=member.tenant_id, user=user, is_owner=False, is_ent_admin=False),
            mock.call(kind="team", kind_id=owner.tenant_id, user=user, is_owner=True, is_ent_admin=False),
        ])
