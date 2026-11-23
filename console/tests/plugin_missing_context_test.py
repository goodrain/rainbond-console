# -*- coding: utf-8 -*-
import os
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import OperationalError  # noqa: E402
from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import BusinessException  # noqa: E402
from console.repositories.plugin import plugin_repo  # noqa: E402
from console.views.base import RegionTenantHeaderView  # noqa: E402
from console.views.plugin.base import PluginBaseView  # noqa: E402
from console.views.plugin.plugin_info import AllPluginVersionInfoView  # noqa: E402
from www.models.main import Tenants  # noqa: E402
from www.models.plugin import PluginBuildVersion, TenantPlugin  # noqa: E402


# capability_id: console.plugin.missing-context-not-found
class PluginMissingContextTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.team = Tenants.objects.create(
            tenant_id="plugin-team", tenant_name="plugin-team", namespace="plugin-team",
        )
        self.plugin = TenantPlugin.objects.create(
            tenant_id=self.team.tenant_id, plugin_id="fixture-plugin", region="region-one", create_user=1,
            plugin_name="fixture", plugin_alias="fixture", category="net-plugin", build_source="image",
        )
        self.version = self.create_version(self.team.tenant_id, "version-one")

    def create_version(self, tenant_id, build_version):
        return PluginBuildVersion.objects.create(
            tenant_id=tenant_id, plugin_id=self.plugin.plugin_id, region="region-one", user_id=1,
            update_info="fixture", build_version=build_version, build_status="build_success", min_memory=64, min_cpu=100,
        )

    def authenticated_context(self):
        # The parent owns authentication/team permissions; only that established
        # context is supplied here, while plugin lookup and guards run unchanged.
        def initial(view, request, *args, **kwargs):
            view.tenant = self.team
            view.response_region = "region-one"

        return initial

    def history(self, plugin_id):
        with mock.patch.object(RegionTenantHeaderView, "initial", new=self.authenticated_context()), \
                mock.patch.object(PluginBaseView, "initial_header_info") as header, \
                mock.patch("console.views.plugin.plugin_info.threading.Thread") as thread:
            response = AllPluginVersionInfoView.as_view()(
                self.factory.get("/console/teams/plugin-team/plugins/{}/versions".format(plugin_id)),
                plugin_id=plugin_id,
            )
        return response, header, thread

    def assert_not_found(self, response, code=404, message="plugin not found"):
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], code)
        self.assertEqual(response.data["msg"], message)

    def test_missing_plugin_history_returns_404_before_header_or_background_work(self):
        response, header, thread = self.history("does-not-exist")
        self.assert_not_found(response)
        header.assert_not_called()
        thread.assert_not_called()

    def test_deleted_plugin_history_returns_404_even_when_old_build_history_remains(self):
        plugin_id = self.plugin.plugin_id
        self.plugin.delete()
        self.assertTrue(PluginBuildVersion.objects.filter(plugin_id=plugin_id).exists())
        response, header, thread = self.history(plugin_id)
        self.assert_not_found(response)
        header.assert_not_called()
        thread.assert_not_called()

    def test_foreign_team_plugin_is_not_found_by_scoped_repository(self):
        self.plugin.tenant_id = "other-team"
        self.plugin.save()
        response, header, thread = self.history(self.plugin.plugin_id)
        self.assert_not_found(response)
        header.assert_not_called()
        thread.assert_not_called()

    def test_repository_does_not_exist_remains_404(self):
        with mock.patch.object(plugin_repo, "get_by_plugin_id", side_effect=TenantPlugin.DoesNotExist):
            response, header, thread = self.history(self.plugin.plugin_id)
        self.assert_not_found(response)
        header.assert_not_called()
        thread.assert_not_called()

    def test_current_team_and_region_history_keeps_existing_payload(self):
        response, header, thread = self.history(self.plugin.plugin_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["data"]["total"], 1)
        self.assertEqual(response.data["data"]["list"][0]["build_version"], self.version.build_version)
        header.assert_called_once()
        thread.return_value.start.assert_called_once()

    def test_other_region_plugin_is_rejected_before_history_query(self):
        self.plugin.region = "region-two"
        self.plugin.save()
        response, header, thread = self.history(self.plugin.plugin_id)
        self.assert_not_found(response, code=10404, message="plugin region is not current region")
        header.assert_not_called()
        thread.assert_not_called()

    def test_defensive_team_guard_still_rejects_wrong_repository_result(self):
        Tenants.objects.create(tenant_id="other-team", tenant_name="other-team", namespace="other-team")
        self.plugin.tenant_id = "other-team"
        self.plugin.save()
        with mock.patch.object(plugin_repo, "get_by_plugin_id", return_value=self.plugin):
            response, header, thread = self.history(self.plugin.plugin_id)
        self.assert_not_found(response, code=10403, message="plugin team is not current team")
        header.assert_not_called()
        thread.assert_not_called()

    def test_defensive_team_guard_still_rejects_deleted_foreign_team(self):
        self.plugin.tenant_id = "deleted-team"
        self.plugin.save()
        with mock.patch.object(plugin_repo, "get_by_plugin_id", return_value=self.plugin):
            response, header, thread = self.history(self.plugin.plugin_id)
        self.assert_not_found(response, code=10403, message="current team is not exist")
        header.assert_not_called()
        thread.assert_not_called()

    def initialize_version(self, build_version):
        view = PluginBaseView()
        request = view.initialize_request(self.factory.get("/plugin-version"))
        with mock.patch.object(RegionTenantHeaderView, "initial", new=self.authenticated_context()):
            view.initial(request, plugin_id=self.plugin.plugin_id, build_version=build_version)
        return view

    def test_valid_build_version_still_populates_both_context_objects(self):
        view = self.initialize_version(self.version.build_version)
        self.assertEqual(view.plugin.pk, self.plugin.pk)
        self.assertEqual(view.plugin_version.pk, self.version.pk)

    def test_missing_build_version_keeps_existing_404(self):
        with self.assertRaises(BusinessException) as raised:
            self.initialize_version("missing-version")
        self.assert_not_found(
            raised.exception.get_response(), code=10403,
            message="plugin id fixture-plugin, build version missing-version is not exist",
        )

    def test_foreign_team_build_version_does_not_satisfy_current_plugin_version(self):
        self.create_version("other-team", "foreign-version")
        with self.assertRaises(BusinessException) as raised:
            self.initialize_version("foreign-version")
        self.assertEqual(raised.exception.get_response().status_code, 404)
        self.assertEqual(raised.exception.get_response().data["code"], 10403)

    def test_database_failure_is_not_disguised_as_missing_plugin(self):
        with mock.patch.object(plugin_repo, "get_by_plugin_id", side_effect=OperationalError("synthetic storage failure")):
            with self.assertRaises(OperationalError):
                self.initialize_version(self.version.build_version)
