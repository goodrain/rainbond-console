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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services import app_version_service as app_version_service_module  # noqa: E402
from console.services.app_version_service import app_version_service  # noqa: E402
from console.views.app_version import AppVersionSnapshotDetailView, AppVersionSnapshotListView  # noqa: E402


class AppVersionServiceDiffSummaryTestCase(TestCase):
    def test_summarize_diff_ignores_snapshot_form_runtime_flags(self):
        current_template = {
            "apps": [
                {
                    "service_alias": "web",
                    "service_env_map_list": [
                        {
                            "attr_name": "DEBUG",
                            "attr_value": "false",
                        }
                    ],
                }
            ]
        }
        snapshot_template = {
            "apps": [
                {
                    "service_alias": "web",
                    "service_env_map_list": [
                        {
                            "attr_name": "DEBUG",
                            "attr_value": "false",
                            "is_change": True,
                        }
                    ],
                }
            ]
        }

        diff_summary = app_version_service._summarize_diff(current_template, snapshot_template)

        self.assertFalse(diff_summary["has_changes"])
        self.assertEqual(diff_summary["updated_count"], 0)

    def test_summarize_diff_keeps_real_component_changes(self):
        current_template = {
            "apps": [
                {
                    "service_alias": "web",
                    "service_env_map_list": [
                        {
                            "attr_name": "DEBUG",
                            "attr_value": "true",
                        }
                    ],
                }
            ]
        }
        snapshot_template = {
            "apps": [
                {
                    "service_alias": "web",
                    "service_env_map_list": [
                        {
                            "attr_name": "DEBUG",
                            "attr_value": "false",
                            "is_change": True,
                        }
                    ],
                }
            ]
        }

        diff_summary = app_version_service._summarize_diff(current_template, snapshot_template)

        self.assertTrue(diff_summary["has_changes"])
        self.assertEqual(diff_summary["updated_count"], 1)


class AppVersionServiceDeleteSnapshotTestCase(TestCase):
    def setUp(self):
        self.relation = mock.Mock(app_model_id="hidden-app-id")

    def mock_snapshot_query(self, target_version, latest_version):
        root_query = mock.Mock()
        versions_query = mock.Mock()
        target_query = mock.Mock()
        ordered_query = mock.Mock()
        root_query.filter.return_value = versions_query
        versions_query.filter.return_value = target_query
        target_query.first.return_value = target_version
        versions_query.order_by.return_value = ordered_query
        ordered_query.first.return_value = latest_version
        return root_query

    def test_delete_snapshot_rejects_latest_version(self):
        latest_version = mock.Mock(ID=12)
        root_query = self.mock_snapshot_query(latest_version, latest_version)

        with mock.patch.object(
                app_version_service, "get_hidden_template", return_value=(self.relation, mock.Mock())), \
                mock.patch.object(
                    app_version_service_module.rainbond_app_repo,
                    "get_rainbond_app_versions",
                    return_value=root_query):
            with self.assertRaises(ServiceHandleException) as context:
                app_version_service.delete_snapshot(42, 12)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "当前版本不允许删除")

    def test_delete_snapshot_removes_historical_version(self):
        target_version = mock.Mock(ID=11)
        latest_version = mock.Mock(ID=12)
        root_query = self.mock_snapshot_query(target_version, latest_version)

        with mock.patch.object(
                app_version_service, "get_hidden_template", return_value=(self.relation, mock.Mock())), \
                mock.patch.object(
                    app_version_service_module.rainbond_app_repo,
                    "get_rainbond_app_versions",
                    return_value=root_query):
            result = app_version_service.delete_snapshot(42, 11)

        self.assertTrue(result)
        target_version.delete.assert_called_once_with()


class AppVersionServiceHiddenTemplateTestCase(TestCase):
    def test_get_or_create_hidden_template_creates_hidden_app(self):
        tenant = mock.Mock(
            tenant_name="demo-team",
            tenant_id="tenant-id",
            enterprise_id="enterprise-id",
        )
        user = mock.Mock(user_id="user-id")
        app = mock.Mock(ID=42, group_name="demo-app")
        relation = mock.Mock()
        hidden_app = mock.Mock(app_name="demo-app")
        expected_hidden_app_id = app_version_service._build_hidden_template_id_by_app_id(app.ID)

        with mock.patch.object(app_version_service, "get_hidden_template", return_value=(None, None)), \
                mock.patch.object(
                    app_version_service_module.rainbond_app_repo,
                    "get_rainbond_app_by_app_id",
                    return_value=None,
                ) as get_app_mock, \
                mock.patch.object(
                    app_version_service_module.rainbond_app_repo,
                    "add_basic_app_info",
                    return_value=hidden_app,
                ) as add_app_mock, \
                mock.patch.object(
                    app_version_service_module.app_version_template_relation_repo,
                    "get_or_create",
                    return_value=relation,
                ) as get_or_create_mock:
            result_relation, result_hidden_app = app_version_service.get_or_create_hidden_template(
                tenant, user, app
            )

        self.assertIs(result_relation, relation)
        self.assertIs(result_hidden_app, hidden_app)
        get_app_mock.assert_called_once_with(expected_hidden_app_id)
        add_app_mock.assert_called_once_with(
            app_id=expected_hidden_app_id,
            app_name="demo-app",
            create_user="user-id",
            create_team="demo-team",
            source=app_version_service.HIDDEN_TEMPLATE_SOURCE,
            dev_status="",
            scope=app_version_service.HIDDEN_TEMPLATE_SCOPE,
            describe="App version hidden template for app 42",
            is_ingerit=False,
            enterprise_id="enterprise-id",
            install_number=0,
            is_official=False,
            details="",
            arch="amd64",
            is_version=True,
        )
        get_or_create_mock.assert_called_once_with(
            42,
            defaults={
                "tenant_id": "tenant-id",
                "app_model_id": expected_hidden_app_id,
                "app_model_name": "demo-app",
                "template_type": "application_version",
            },
        )


class AppVersionSnapshotDetailViewDeleteTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppVersionSnapshotDetailView()
        self.view.app = mock.Mock(ID=42)

    def test_delete_returns_success_response(self):
        request = self.factory.delete("/console/teams/demo-team/groups/42/app-versions/11")

        with mock.patch.object(
            app_version_service_module.app_version_service,
            "delete_snapshot",
            return_value=True,
        ) as delete_mock:
            response = self.view.delete(request, 42, 11)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg"], "success")
        self.assertEqual(response.data["msg_show"], "删除成功")
        delete_mock.assert_called_once_with(42, 11)


class AppVersionSnapshotListViewPostTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppVersionSnapshotListView()
        self.view.tenant = mock.Mock()
        self.view.region = mock.Mock()
        self.view.user = mock.Mock()
        self.view.app = mock.Mock(ID=42)

    def make_request(self, payload):
        return self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/groups/42/app-versions",
                payload,
                format="json",
            )
        )

    def test_post_returns_no_change_message_when_snapshot_not_created(self):
        request = self.make_request(
            {
                "version": "1.0.3",
                "app_version_info": "demo",
                "share_service_list": [],
                "share_plugin_list": [],
                "share_k8s_resources": [],
            }
        )
        expected_result = {"version": "1.0.2", "created": False}

        with mock.patch.object(
            app_version_service_module.app_version_service,
            "create_snapshot",
            return_value=expected_result,
        ) as create_mock:
            response = self.view.post(request, 42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], expected_result)
        self.assertEqual(response.data["msg_show"], "当前没有新的变更，无需创建快照")
        create_mock.assert_called_once()
