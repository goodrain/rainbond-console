# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
from datetime import datetime
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
from console.services.market_app import app_restore as app_restore_module  # noqa: E402
from console.services.market_app import new_app as new_app_module  # noqa: E402
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


class AppVersionServiceComponentDiffDetailTestCase(TestCase):
    def test_build_component_diff_details_tracks_added_removed_and_field_updates(self):
        current_template = {
            "apps": [
                {
                    "service_alias": "web",
                    "service_env_map_list": [
                        {"attr_name": "DEBUG", "attr_value": "true"},
                        {"attr_name": "LOG_LEVEL", "attr_value": "info"},
                    ],
                    "port_map_list": [
                        {"container_port": 8080, "protocol": "tcp", "port_alias": "WEB"},
                        {"container_port": 8081, "protocol": "tcp", "port_alias": "METRICS"},
                    ],
                    "service_volume_map_list": [
                        {"volume_name": "data", "volume_path": "/data", "volume_capacity": 20},
                    ],
                    "probes": [
                        {
                            "probe_id": "ready",
                            "mode": "readiness",
                            "port": 8080,
                            "path": "/healthz",
                            "failure_threshold": 5,
                        }
                    ],
                },
                {
                    "service_alias": "worker",
                    "service_env_map_list": [],
                    "port_map_list": [],
                    "service_volume_map_list": [],
                    "probes": [],
                },
            ]
        }
        previous_template = {
            "apps": [
                {
                    "service_alias": "web",
                    "service_env_map_list": [
                        {"attr_name": "DEBUG", "attr_value": "false"},
                        {"attr_name": "OLD_FLAG", "attr_value": "1"},
                    ],
                    "port_map_list": [
                        {"container_port": 8080, "protocol": "tcp", "port_alias": "WEB"},
                    ],
                    "service_volume_map_list": [
                        {"volume_name": "data", "volume_path": "/data", "volume_capacity": 10},
                        {"volume_name": "cache", "volume_path": "/cache", "volume_capacity": 5},
                    ],
                    "probes": [
                        {
                            "probe_id": "ready",
                            "mode": "readiness",
                            "port": 8080,
                            "path": "/health",
                            "failure_threshold": 3,
                        }
                    ],
                },
                {
                    "service_alias": "api",
                    "service_env_map_list": [],
                    "port_map_list": [],
                    "service_volume_map_list": [],
                    "probes": [],
                },
            ]
        }

        diff_detail = app_version_service._build_component_diff_details(current_template, previous_template)

        self.assertEqual(diff_detail["added_components"], [{"component_name": "worker"}])
        self.assertEqual(diff_detail["removed_components"], [{"component_name": "api"}])
        self.assertEqual(len(diff_detail["updated_components"]), 1)
        updated_component = diff_detail["updated_components"][0]
        self.assertEqual(updated_component["component_name"], "web")

        field_changes = {item["field_key"]: item for item in updated_component["field_changes"]}

        env_change = field_changes["service_env_map_list"]
        self.assertEqual(env_change["field_label"], "环境变量")
        self.assertEqual([item["identity"] for item in env_change["added"]], ["LOG_LEVEL"])
        self.assertEqual([item["identity"] for item in env_change["removed"]], ["OLD_FLAG"])
        self.assertEqual([item["identity"] for item in env_change["updated"]], ["DEBUG"])
        self.assertEqual(env_change["updated"][0]["before"]["attr_value"], "false")
        self.assertEqual(env_change["updated"][0]["after"]["attr_value"], "true")

        port_change = field_changes["port_map_list"]
        self.assertEqual([item["identity"] for item in port_change["added"]], ["8081/tcp/METRICS"])

        volume_change = field_changes["service_volume_map_list"]
        self.assertEqual([item["identity"] for item in volume_change["removed"]], ["cache@/cache"])
        self.assertEqual([item["identity"] for item in volume_change["updated"]], ["data@/data"])
        self.assertEqual(volume_change["updated"][0]["before"]["volume_capacity"], 10)
        self.assertEqual(volume_change["updated"][0]["after"]["volume_capacity"], 20)

        probe_change = field_changes["probes"]
        self.assertEqual([item["identity"] for item in probe_change["updated"]], ["ready"])
        self.assertEqual(probe_change["updated"][0]["before"]["path"], "/health")
        self.assertEqual(probe_change["updated"][0]["after"]["path"], "/healthz")


class AppVersionServiceSnapshotDetailTestCase(TestCase):
    def test_get_snapshot_detail_includes_previous_version_and_field_diff(self):
        relation = mock.Mock(app_model_id="hidden-app-id")
        current_template = {
            "apps": [{
                "service_alias": "web",
                "service_env_map_list": [{"attr_name": "DEBUG", "attr_value": "true"}],
                "port_map_list": [],
                "service_volume_map_list": [],
                "probes": [],
            }]
        }
        previous_template = {
            "apps": [{
                "service_alias": "web",
                "service_env_map_list": [{"attr_name": "DEBUG", "attr_value": "false"}],
                "port_map_list": [],
                "service_volume_map_list": [],
                "probes": [],
            }]
        }
        current_version = mock.Mock(
            ID=12,
            version="1.0.3",
            version_alias="stable",
            app_version_info="snapshot current",
            create_time=datetime(2026, 3, 24, 10, 0, 0),
            app_template=json.dumps(current_template),
        )
        previous_version = mock.Mock(
            ID=11,
            version="1.0.2",
            version_alias="prev",
            app_version_info="snapshot previous",
            create_time=datetime(2026, 3, 24, 9, 0, 0),
            app_template=json.dumps(previous_template),
        )
        query = mock.Mock()
        query.first.return_value = current_version
        query.order_by.return_value = [current_version, previous_version]

        with mock.patch.object(
                app_version_service, "get_hidden_template", return_value=(relation, mock.Mock())), \
                mock.patch.object(
                    app_version_service_module.RainbondCenterAppVersion.objects,
                    "filter",
                    return_value=query):
            detail = app_version_service.get_snapshot_detail(42, 12)

        self.assertEqual(detail["previous_version"], "1.0.2")
        self.assertTrue(detail["has_previous_version"])
        self.assertTrue(detail["diff_summary"]["has_changes"])
        self.assertEqual(detail["diff_summary"]["updated_components"], ["web"])
        updated_components = detail["component_diff_details"]["updated_components"]
        self.assertEqual(len(updated_components), 1)
        self.assertEqual(updated_components[0]["component_name"], "web")
        self.assertEqual(updated_components[0]["field_changes"][0]["field_key"], "service_env_map_list")


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


class AppRestoreSnapshotCompatibilityTestCase(TestCase):
    def test_create_component_allows_snapshot_without_service_source(self):
        restore = app_restore_module.AppRestore.__new__(app_restore_module.AppRestore)
        restore.support_labels = []
        snap = {
            "service_base": {"service_id": "service-id"},
            "service_source": None,
            "service_env_vars": [],
            "service_ports": [],
            "service_volumes": [],
            "service_config_file": [],
            "service_probes": [],
            "service_monitors": [],
            "component_graphs": [],
            "service_labels": [],
            "component_k8s_attributes": [],
            "action_type": "nothing",
        }

        with mock.patch.object(
            app_restore_module,
            "TenantServiceInfo",
            return_value=mock.Mock(service_id="service-id"),
        ):
            component = restore._create_component(snap, {})

        self.assertIsNone(component.component_source)
        self.assertEqual(component.action_type, "nothing")


class AppVersionRollbackRestoreActionTypeTestCase(TestCase):
    def test_create_component_forces_update_action_for_legacy_snapshot(self):
        restore = app_version_service_module.AppVersionRollbackRestore.__new__(
            app_version_service_module.AppVersionRollbackRestore
        )
        restore.support_labels = []
        snap = {
            "service_base": {"service_id": "service-id"},
            "service_source": None,
            "service_env_vars": [],
            "service_ports": [],
            "service_volumes": [],
            "service_config_file": [],
            "service_probes": [],
            "service_monitors": [],
            "component_graphs": [],
            "service_labels": [],
            "component_k8s_attributes": [],
            "action_type": "nothing",
        }

        with mock.patch.object(
            app_restore_module,
            "TenantServiceInfo",
            return_value=mock.Mock(service_id="service-id"),
        ):
            component = restore._create_component(snap, {})

        self.assertEqual(component.action_type, app_restore_module.ActionType.UPDATE.value)


class NewAppUpdateComponentsTestCase(TestCase):
    def test_update_components_overwrites_service_sources_when_snapshot_missing_source(self):
        new_app = new_app_module.NewApp.__new__(new_app_module.NewApp)
        component = mock.Mock(component_id="service-id")
        new_app.update_components = [
            mock.Mock(
                component=component,
                component_source=None,
                envs=[],
                ports=[],
                volumes=[],
                config_files=[],
                probes=[],
                extend_info=None,
                monitors=[],
                graphs=[],
                labels=[],
                k8s_attributes=[],
            )
        ]

        with mock.patch.object(new_app_module.service_repo, "bulk_update"), \
                mock.patch.object(new_app_module.service_source_repo, "bulk_update") as bulk_update_mock, \
                mock.patch.object(
                    new_app_module.service_source_repo,
                    "overwrite_by_component_ids",
                    create=True,
                ) as overwrite_mock, \
                mock.patch.object(new_app_module.extend_repo, "bulk_create_or_update"), \
                mock.patch.object(new_app_module.env_var_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.port_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.volume_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.config_file_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.probe_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.service_monitor_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.component_graph_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.service_label_repo, "overwrite_by_component_ids"), \
                mock.patch.object(new_app_module.k8s_attribute_repo, "overwrite_by_component_ids"):
            new_app._update_components()

        bulk_update_mock.assert_not_called()
        overwrite_mock.assert_called_once_with(["service-id"], [])
