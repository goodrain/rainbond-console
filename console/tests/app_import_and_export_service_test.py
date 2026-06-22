# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
import typing
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired
    except ImportError:
        typing.NotRequired = lambda item: item

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "rest_framework_simplejwt.tokens" not in sys.modules:
    simplejwt_module = ModuleType("rest_framework_simplejwt")
    simplejwt_tokens_module = ModuleType("rest_framework_simplejwt.tokens")

    class _DummyAccessToken(dict):
        @classmethod
        def for_user(cls, user):
            return cls()

        def __str__(self):
            return ""

    simplejwt_tokens_module.AccessToken = _DummyAccessToken
    simplejwt_module.tokens = simplejwt_tokens_module
    sys.modules["rest_framework_simplejwt"] = simplejwt_module
    sys.modules["rest_framework_simplejwt.tokens"] = simplejwt_tokens_module
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
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.db import OperationalError  # noqa: E402
from django.db.models.query import QuerySet  # noqa: E402
from django.db.transaction import TransactionManagementError  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)

from console.services.app_import_and_export_service import export_service, import_service  # noqa: E402
from console.views.center_pool import app_import as app_import_view_module  # noqa: E402


# capability_id: console.app.export-metadata
class AppExportServiceMetadataTestCase(TestCase):
    def test_get_app_metadata_allows_missing_picture(self):
        app = mock.Mock(pic=None, describe="demo app")
        app_version = mock.Mock(
            app_template=json.dumps({"group_key": "demo-app", "group_version": "1.0.0"}),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        self.assertEqual(result["annotations"]["suffix"], "")
        self.assertEqual(result["annotations"]["image_base64_string"], "")
        self.assertEqual(result["annotations"]["describe"], "demo app")
        self.assertEqual(result["helm_chart"]["image_handle"], "")

    def test_get_app_metadata_falls_back_to_image(self):
        app = mock.Mock(pic=None, describe="demo app")
        component = {
            "service_alias": "web",
            "image": "registry.example.com/demo/web:1.0.0"
        }
        app_version = mock.Mock(
            app_template=json.dumps({
                "group_key": "demo-app",
                "group_version": "1.0.0",
                "apps": [component]
            }),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        self.assertEqual(result["apps"][0]["share_image"], component["image"])

    def test_get_app_metadata_keeps_existing_share_image(self):
        app = mock.Mock(pic=None, describe="demo app")
        component = {
            "service_alias": "web",
            "image": "registry.example.com/demo/web:1.0.0",
            "share_image": "registry.example.com/share/web:2.0.0"
        }
        app_version = mock.Mock(
            app_template=json.dumps({
                "group_key": "demo-app",
                "group_version": "1.0.0",
                "apps": [component]
            }),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        self.assertEqual(result["apps"][0]["share_image"], component["share_image"])

    def test_get_app_metadata_keeps_container_component_type(self):
        app = mock.Mock(pic=None, describe="demo app")
        component = {
            "service_alias": "web",
            "image": "registry.example.com/demo/web:1.0.0",
            "extend_method": "stateless_multiple",
            "service_source": "docker_image",
            "service_type": "application",
        }
        app_version = mock.Mock(
            app_template=json.dumps({
                "group_key": "demo-app",
                "group_version": "1.0.0",
                "template_version": "v2",
                "apps": [component]
            }),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        exported_component = result["apps"][0]
        self.assertEqual("application", exported_component["service_type"])
        self.assertEqual("v2", result["template_version"])
        self.assertNotIn("vm", exported_component)

    def test_get_app_metadata_normalizes_stale_vm_service_type_for_container(self):
        app = mock.Mock(pic=None, describe="demo app")
        component = {
            "service_alias": "web",
            "image": "registry.example.com/demo/web:1.0.0",
            "extend_method": "stateless_multiple",
            "service_source": "docker_image",
            "service_type": "vm",
        }
        app_version = mock.Mock(
            app_template=json.dumps({
                "group_key": "demo-app",
                "group_version": "1.0.0",
                "template_version": "v3",
                "apps": [component]
            }),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        exported_component = result["apps"][0]
        self.assertEqual("application", exported_component["service_type"])
        self.assertEqual("v2", result["template_version"])
        self.assertNotIn("vm", exported_component)

    def test_get_app_metadata_backfills_vm_root_disk_image_from_share_image(self):
        app = mock.Mock(pic=None, describe="demo app")
        component = {
            "service_alias": "vm-root",
            "extend_method": "vm",
            "service_type": "vm",
            "share_image": "registry.example.com/share/windows-root:2.0.0",
            "vm": {
                "boot_source_format": "qcow2",
                "disk_layout": [{
                    "disk_key": "disk",
                    "disk_role": "root",
                    "format": "qcow2",
                    "source_type": "registry",
                    "image": "",
                }]
            }
        }
        app_version = mock.Mock(
            app_template=json.dumps({
                "group_key": "demo-app",
                "group_version": "1.0.0",
                "template_version": "v2",
                "apps": [component]
            }),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        self.assertEqual("registry.example.com/share/windows-root:2.0.0", result["apps"][0]["vm"]["disk_layout"][0]["image"])
        self.assertEqual("v3", result["template_version"])

    def test_get_app_metadata_falls_back_to_plugin_image(self):
        app = mock.Mock(pic=None, describe="demo app")
        plugin = {
            "plugin_alias": "demo-plugin",
            "image": "registry.example.com/demo/plugin:1.0.0"
        }
        app_version = mock.Mock(
            app_template=json.dumps({
                "group_key": "demo-app",
                "group_version": "1.0.0",
                "plugins": [plugin]
            }),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        self.assertEqual(result["plugins"][0]["share_image"], plugin["image"])

    def test_get_app_metadata_copies_scaling_resources_for_package_export(self):
        app = mock.Mock(pic=None, describe="demo app")
        component = {
            "service_alias": "web",
            "image": "registry.example.com/demo/web:1.0.0",
            "extend_method_map": {
                "min_node": 2,
                "max_node": 7,
                "step_node": 2,
                "min_memory": 64,
                "init_memory": 1024,
                "max_memory": 4096,
                "step_memory": 128,
                "container_cpu": 600,
            }
        }
        app_version = mock.Mock(
            app_template=json.dumps({
                "group_key": "demo-app",
                "group_version": "1.0.0",
                "apps": [component]
            }),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        exported_component = result["apps"][0]
        self.assertEqual(exported_component["cpu"], 600)
        self.assertEqual(exported_component["memory"], 1024)
        self.assertEqual(exported_component["extend_method_map"]["init_memory"], 1024)

    # capability_id: console.app-export.query-status
    def test_get_export_status_updates_exporting_record_and_wraps_download_url(self):
        app = mock.Mock(app_id="demo-app")
        app_version = mock.Mock(
            version="1.0.0",
            app_template=json.dumps({
                "governance_mode": "KUBERNETES_NATIVE_SERVICE",
                "apps": [{"service_source": "source_code"}],
            }),
        )
        export_record = mock.Mock(
            region_name="demo-region",
            event_id="evt-1",
            status="exporting",
            format="rainbond-app",
            file_path="/v2/download/app.tgz",
        )

        with mock.patch(
            "console.services.app_import_and_export_service."
            "app_export_record_repo.get_enter_export_record_by_key_and_version",
            return_value=[export_record],
        ), mock.patch(
            "console.services.app_import_and_export_service."
            "region_services.get_enterprise_region_by_region_name",
            return_value=mock.Mock(region_name="demo-region"),
        ), mock.patch(
            "console.services.app_import_and_export_service.region_api.get_app_export_status",
            return_value=(None, {"bean": {"status": "success", "tar_file_href": "/v2/download/app.tgz"}}),
        ), mock.patch(
            "console.services.app_import_and_export_service.region_repo.get_region_by_region_name",
            return_value=mock.Mock(wsurl="http://console.example.com"),
        ):
            result = export_service.get_export_status("eid-1", app, app_version)

        self.assertTrue(result["rainbond_app"]["is_export_before"])
        self.assertEqual(result["rainbond_app"]["status"], "success")
        self.assertEqual(result["rainbond_app"]["file_path"], "/console/regions/demo-region/websocket/download/app.tgz")
        self.assertTrue(result["helm_chart"]["is_export_before"] is False)
        self.assertTrue(result["slug"]["is_export_before"] is False)
        export_record.save.assert_called_once_with()


class CenterAppImportViewWorkflowTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = app_import_view_module.CenterAppImportView()
        self.view.user = mock.Mock(enterprise_id="eid-1")
        self.view.enterprise = mock.Mock(enterprise_id="eid-1")

    def make_request(self, method, payload=None):
        payload = payload or {}
        request_factory = getattr(self.factory, method)
        request = request_factory("/console/center/app-import/evt-1", payload, format="json")
        return self.view.initialize_request(request)

    # capability_id: console.app-import.start
    def test_post_starts_app_import(self):
        request = self.make_request("post", {
            "scope": "team",
            "tenant_name": "demo-team",
            "file_name": "demo-app.rainbond"
        })

        with mock.patch.object(app_import_view_module.import_service, "start_import_apps") as start_mock, \
                mock.patch.object(app_import_view_module.operation_log_service, "create_component_library_log"):
            response = self.view.post(request, "evt-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "操作成功，正在导入")
        start_mock.assert_called_once_with("team", "evt-1", ["demo-app.rainbond"], "demo-team", "eid-1")

    # capability_id: console.app-import.query-status
    def test_get_returns_import_status(self):
        request = self.factory.get("/console/center/app-import/evt-1", {"arch": "amd64"})
        record = mock.Mock()
        record.to_dict.return_value = {"event_id": "evt-1", "status": "success"}

        with mock.patch.object(app_import_view_module.import_service, "get_and_update_import_by_event_id",
                               return_value=(record, [{"file_name": "demo-app", "status": "success"}])) as get_mock:
            response = self.view.get.__wrapped__.__wrapped__(self.view, request, "evt-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["event_id"], "evt-1")
        self.assertEqual(response.data["data"]["list"][0]["status"], "success")
        get_mock.assert_called_once_with("evt-1", "amd64")

    # capability_id: console.app-import.query-status
    def test_get_preserves_database_error_when_transaction_is_broken(self):
        request = self.factory.get("/console/center/app-import/evt-1", {"arch": "amd64"})
        database_error = OperationalError("database is locked")
        rollback_error = TransactionManagementError("An error occurred in the current transaction.")

        with mock.patch.object(app_import_view_module.transaction, "savepoint", return_value="sp-1"), \
                mock.patch.object(app_import_view_module.transaction, "savepoint_rollback",
                                  side_effect=rollback_error) as rollback_mock, \
                mock.patch.object(app_import_view_module.import_service, "get_and_update_import_by_event_id",
                                  side_effect=database_error):
            with self.assertRaises(OperationalError) as ctx:
                self.view.get.__wrapped__.__wrapped__(self.view, request, "evt-1")

        # The savepoint design attempts a rollback on error; even when that rollback
        # itself fails (broken transaction) the original database error is preserved.
        self.assertIs(ctx.exception, database_error)
        rollback_mock.assert_called_once_with("sp-1")

    # capability_id: console.app-import.abandon
    def test_delete_abandons_import(self):
        request = self.factory.delete("/console/center/app-import/evt-1")

        with mock.patch.object(app_import_view_module.import_service, "delete_import_app_dir_by_event_id") as delete_mock:
            response = self.view.delete(request, "evt-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "操作成功")
        delete_mock.assert_called_once_with("evt-1")


class AppImportStatusUpdateTestCase(TestCase):
    # capability_id: console.app-import.query-status
    def test_get_and_update_import_by_event_id_skips_unchanged_running_status_save(self):
        import_record = mock.Mock(status="importing", region="region-a", enterprise_id="eid-1")

        with mock.patch(
                "console.services.app_import_and_export_service."
                "app_import_record_repo.get_import_record_by_event_id",
                return_value=import_record,
        ), mock.patch(
                "console.services.app_import_and_export_service.region_api.get_enterprise_app_import_status",
                return_value=(None, {"bean": {"status": "importing", "apps": "demo:checking"}}),
        ):
            record, apps_status = import_service.get_and_update_import_by_event_id("evt-1", "amd64")

        self.assertIs(record, import_record)
        self.assertEqual(apps_status, [{"file_name": "demo", "status": "checking"}])
        import_record.save.assert_not_called()

    # capability_id: console.app-import.query-status
    def test_get_and_update_import_by_event_id_saves_partial_success_once(self):
        import_record = mock.Mock(status="importing", region="region-a", enterprise_id="eid-1")

        with mock.patch(
                "console.services.app_import_and_export_service."
                "app_import_record_repo.get_import_record_by_event_id",
                return_value=import_record,
        ), mock.patch(
                "console.services.app_import_and_export_service.region_api.get_enterprise_app_import_status",
                return_value=(None, {"bean": {"status": "importing", "apps": "web:success,worker:checking"}}),
        ):
            record, apps_status = import_service.get_and_update_import_by_event_id("evt-1", "amd64")

        self.assertIs(record, import_record)
        self.assertEqual(apps_status, [{"file_name": "web", "status": "success"}, {"file_name": "worker", "status": "checking"}])
        self.assertEqual(import_record.status, "partial_success")
        import_record.save.assert_called_once_with()

    # capability_id: console.app-import.openapi-query-status
    def test_openapi_deploy_app_get_import_by_event_id_skips_unchanged_status_save(self):
        import_record = mock.Mock(status="importing", region="region-a", enterprise_id="eid-1")

        with mock.patch(
                "console.services.app_import_and_export_service."
                "app_import_record_repo.get_import_record_by_event_id",
                return_value=import_record,
        ), mock.patch(
                "console.services.app_import_and_export_service.region_api.get_enterprise_app_import_status",
                return_value=(None, {"bean": {"status": "importing"}}),
        ):
            record, metadata = import_service.openapi_deploy_app_get_import_by_event_id("evt-1")

        self.assertIs(record, import_record)
        self.assertEqual(metadata, [])
        import_record.save.assert_not_called()


class AppImportServiceMetadataTestCase(TestCase):
    service_module = "console.services.app_import_and_export_service"

    class DummyRainbondCenterApp(object):
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def build_import_metadata(self):
        return [{
            "template_version": "v2",
            "group_key": "demo-app",
            "group_name": "Demo App",
            "group_version": "1.0.0",
            "apps": [{
                "service_cname": "web",
                "service_key": "svc-key",
                "version": "component-version",
                "arch": "amd64",
                "service_extend_method": {
                    "min_node": 2,
                    "max_node": 7,
                    "step_node": 2,
                    "min_memory": 512,
                    "max_memory": 4096,
                    "step_memory": 128,
                    "is_restart": False,
                    "container_cpu": 600,
                },
            }],
            "annotations": {},
        }]

    def test_save_enterprise_import_info_normalizes_extend_method_map(self):
        import_record = mock.Mock(
            enterprise_id="eid-1",
            team_name="demo-team",
            scope="enterprise",
            ID=11,
            region="demo-region",
        )
        metadata = json.dumps(self.build_import_metadata())

        with mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_by_app_id".format(self.service_module),
            return_value=None,
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_apps".format(self.service_module),
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_app_versions".format(self.service_module),
        ) as bulk_versions, mock.patch(
            "{}.app_store.is_no_multiple_region_hub".format(self.service_module),
            return_value=False,
        ):
            import_service._AppImportService__save_enterprise_import_info(import_record, metadata, "amd64")

        created_version = bulk_versions.call_args[0][0][0]
        saved_template = json.loads(created_version.app_template)
        extend_method_map = saved_template["apps"][0]["extend_method_map"]
        self.assertEqual(extend_method_map["min_node"], 2)
        self.assertEqual(extend_method_map["max_node"], 7)
        self.assertEqual(extend_method_map["step_node"], 2)
        self.assertEqual(extend_method_map["init_memory"], 512)
        self.assertEqual(extend_method_map["container_cpu"], 600)

    def test_save_team_import_info_normalizes_extend_method_map(self):
        tenant = mock.Mock(enterprise_id="eid-1", tenant_name="demo-team")
        metadata = json.dumps(self.build_import_metadata())

        with mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_by_app_id".format(self.service_module),
            return_value=None,
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_apps".format(self.service_module),
        ) as bulk_apps, mock.patch(
            "{}.RainbondCenterApp".format(self.service_module),
            self.DummyRainbondCenterApp,
        ):
            import_service._AppImportService__save_import_info(tenant, "team", metadata)

        created_app = bulk_apps.call_args[0][0][0]
        saved_template = json.loads(created_app.app_template)
        extend_method_map = saved_template["apps"][0]["extend_method_map"]
        self.assertEqual(extend_method_map["max_node"], 7)
        self.assertEqual(extend_method_map["step_node"], 2)

    def test_save_enterprise_import_info_restores_resources_from_ram_fields(self):
        import_record = mock.Mock(
            enterprise_id="eid-1",
            team_name="demo-team",
            scope="enterprise",
            ID=11,
            region="demo-region",
        )
        metadata = json.dumps([{
            "template_version": "v2",
            "group_key": "demo-app",
            "group_name": "Demo App",
            "group_version": "1.0.0",
            "apps": [{
                "service_cname": "web",
                "service_key": "svc-key",
                "version": "component-version",
                "cpu": 600,
                "memory": 1024,
                "extend_method_map": {
                    "min_node": 2,
                    "max_node": 7,
                    "step_node": 2,
                    "min_memory": 64,
                    "max_memory": 4096,
                    "step_memory": 128,
                },
            }],
            "annotations": {},
        }])

        with mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_by_app_id".format(self.service_module),
            return_value=None,
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_apps".format(self.service_module),
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_app_versions".format(self.service_module),
        ) as bulk_versions, mock.patch(
            "{}.app_store.is_no_multiple_region_hub".format(self.service_module),
            return_value=False,
        ):
            import_service._AppImportService__save_enterprise_import_info(import_record, metadata, "amd64")

        created_version = bulk_versions.call_args[0][0][0]
        saved_template = json.loads(created_version.app_template)
        extend_method_map = saved_template["apps"][0]["extend_method_map"]
        self.assertEqual(extend_method_map["container_cpu"], 600)
        self.assertEqual(extend_method_map["init_memory"], 1024)

    # capability_id: console.market-app.install-unlimited-resources
    def test_save_enterprise_import_info_preserves_explicit_unlimited_resources(self):
        import_record = mock.Mock(
            enterprise_id="eid-1",
            team_name="demo-team",
            scope="enterprise",
            ID=11,
            region="demo-region",
        )
        metadata = json.dumps([{
            "template_version": "v2",
            "group_key": "demo-app",
            "group_name": "Demo App",
            "group_version": "1.0.0",
            "apps": [{
                "service_cname": "web",
                "service_key": "svc-key",
                "version": "component-version",
                "cpu": 0,
                "memory": 1024,
                "extend_method_map": {
                    "min_node": 2,
                    "max_node": 7,
                    "step_node": 2,
                    "min_memory": 64,
                    "init_memory": 0,
                    "max_memory": 4096,
                    "step_memory": 128,
                },
            }],
            "annotations": {},
        }])

        with mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_by_app_id".format(self.service_module),
            return_value=None,
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_apps".format(self.service_module),
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_app_versions".format(self.service_module),
        ) as bulk_versions, mock.patch(
            "{}.app_store.is_no_multiple_region_hub".format(self.service_module),
            return_value=False,
        ):
            import_service._AppImportService__save_enterprise_import_info(import_record, metadata, "amd64")

        created_version = bulk_versions.call_args[0][0][0]
        saved_template = json.loads(created_version.app_template)
        extend_method_map = saved_template["apps"][0]["extend_method_map"]
        self.assertEqual(extend_method_map["container_cpu"], 0)
        self.assertEqual(extend_method_map["init_memory"], 0)

    # capability_id: console.app-import.identity-collision
    def test_save_enterprise_import_info_splits_same_key_when_name_differs(self):
        import_record = mock.Mock(
            enterprise_id="eid-1",
            team_name="demo-team",
            scope="team",
            ID=11,
            region="demo-region",
        )
        metadata = json.dumps(self.build_import_metadata())
        existing_app = mock.Mock(
            app_id="demo-app",
            app_name="Other App",
            source="import",
            arch="amd64",
        )

        def get_app(app_id):
            if app_id == "demo-app":
                return existing_app
            return None

        with mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_by_app_id".format(self.service_module),
            side_effect=get_app,
        ), mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version".format(self.service_module),
            return_value=None,
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_apps".format(self.service_module),
        ) as bulk_apps, mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_app_versions".format(self.service_module),
        ) as bulk_versions, mock.patch(
            "{}.app_store.is_no_multiple_region_hub".format(self.service_module),
            return_value=False,
        ):
            import_service._AppImportService__save_enterprise_import_info(import_record, metadata, "amd64")

        created_app = bulk_apps.call_args[0][0][0]
        created_version = bulk_versions.call_args[0][0][0]
        saved_template = json.loads(created_version.app_template)
        self.assertNotEqual(created_app.app_id, "demo-app")
        self.assertEqual(created_app.app_name, "Demo App")
        self.assertEqual(created_version.app_id, created_app.app_id)
        self.assertEqual(saved_template["group_key"], created_app.app_id)
        existing_app.save.assert_not_called()

    # capability_id: console.app-import.identity-collision
    def test_save_enterprise_import_info_keeps_same_key_and_name_as_multiple_versions(self):
        import_record = mock.Mock(
            enterprise_id="eid-1",
            team_name="demo-team",
            scope="team",
            ID=11,
            region="demo-region",
        )
        metadata = self.build_import_metadata()
        metadata[0]["group_version"] = "2.0.0"
        existing_app = mock.Mock(
            app_id="demo-app",
            app_name="Demo App",
            source="import",
            arch="amd64",
        )

        with mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_by_app_id".format(self.service_module),
            return_value=existing_app,
        ), mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version".format(self.service_module),
            return_value=None,
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_apps".format(self.service_module),
        ) as bulk_apps, mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_app_versions".format(self.service_module),
        ) as bulk_versions, mock.patch(
            "{}.app_store.is_no_multiple_region_hub".format(self.service_module),
            return_value=False,
        ):
            import_service._AppImportService__save_enterprise_import_info(
                import_record, json.dumps(metadata), "amd64"
            )

        self.assertEqual(bulk_apps.call_args[0][0], [])
        created_version = bulk_versions.call_args[0][0][0]
        saved_template = json.loads(created_version.app_template)
        self.assertEqual(created_version.app_id, "demo-app")
        self.assertEqual(saved_template["group_key"], "demo-app")
        existing_app.save.assert_called_once_with()

    # capability_id: console.app-import.identity-collision
    def test_save_enterprise_import_info_splits_same_key_name_version_when_content_differs(self):
        import_record = mock.Mock(
            enterprise_id="eid-1",
            team_name="demo-team",
            scope="team",
            ID=11,
            region="demo-region",
        )
        metadata = self.build_import_metadata()
        metadata[0]["apps"][0]["service_cname"] = "web-new"
        existing_app = mock.Mock(
            app_id="demo-app",
            app_name="Demo App",
            source="import",
            arch="amd64",
        )
        existing_version = mock.Mock(app_template=json.dumps(self.build_import_metadata()[0]))

        def get_app(app_id):
            if app_id == "demo-app":
                return existing_app
            return None

        def get_version(app_id, version):
            if app_id == "demo-app":
                return existing_version
            return None

        with mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_by_app_id".format(self.service_module),
            side_effect=get_app,
        ), mock.patch(
            "{}.rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version".format(self.service_module),
            side_effect=get_version,
        ), mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_apps".format(self.service_module),
        ) as bulk_apps, mock.patch(
            "{}.rainbond_app_repo.bulk_create_rainbond_app_versions".format(self.service_module),
        ) as bulk_versions, mock.patch(
            "{}.app_store.is_no_multiple_region_hub".format(self.service_module),
            return_value=False,
        ):
            import_service._AppImportService__save_enterprise_import_info(
                import_record, json.dumps(metadata), "amd64"
            )

        created_app = bulk_apps.call_args[0][0][0]
        created_version = bulk_versions.call_args[0][0][0]
        saved_template = json.loads(created_version.app_template)
        self.assertNotEqual(created_app.app_id, "demo-app")
        self.assertEqual(created_app.app_name, "Demo App")
        self.assertEqual(created_version.app_id, created_app.app_id)
        self.assertEqual(saved_template["group_key"], created_app.app_id)
        self.assertEqual(saved_template["apps"][0]["service_cname"], "web-new")
        existing_app.save.assert_not_called()
        existing_version.save.assert_not_called()


class AppImportPreparationWorkflowTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    # capability_id: console.app-import.init
    def test_enterprise_import_init_creates_record_when_none_exists(self):
        view = app_import_view_module.EnterpriseAppImportInitView()
        view.user = mock.Mock(nick_name="admin")
        request = self.factory.post("/console/enterprise/app-import/init")
        record = mock.Mock(region="demo-region", event_id="evt-1", source_dir="/tmp/import", status="created_dir")

        with mock.patch.object(
            app_import_view_module.import_service,
            "get_user_not_finish_import_record_in_enterprise",
            return_value=[],
        ), mock.patch.object(
            app_import_view_module.import_service,
            "create_app_import_record_2_enterprise",
            return_value=record,
        ), mock.patch.object(
            app_import_view_module.import_service,
            "get_upload_url",
            return_value="https://upload.example.com",
        ), mock.patch.object(
            app_import_view_module.region_services,
            "get_region_by_region_name",
            return_value=mock.Mock(region_alias="演示集群"),
        ):
            response = view.post(request, enterprise_id="eid-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["event_id"], "evt-1")
        self.assertEqual(response.data["data"]["bean"]["upload_url"], "https://upload.example.com")

    # capability_id: console.app-import.create-dir
    def test_tarball_dir_post_creates_import_dir(self):
        view = app_import_view_module.CenterAppTarballDirView()
        view.tenant = mock.Mock(tenant_name="demo-team")
        view.user = mock.Mock()
        view.response_region = "demo-region"
        request = self.factory.post("/console/teams/demo-team/import-dir")
        record = mock.Mock()
        record.to_dict.return_value = {"event_id": "evt-1", "source_dir": "/tmp/import"}

        with mock.patch.object(
            app_import_view_module.import_service,
            "create_import_app_dir",
            return_value=record,
        ) as create_mock:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["event_id"], "evt-1")
        create_mock.assert_called_once_with(view.tenant, view.user, "demo-region")

    # capability_id: console.app-import.list-dir
    def test_tarball_dir_get_lists_imported_packages(self):
        view = app_import_view_module.CenterAppTarballDirView()
        request = self.factory.get("/console/teams/demo-team/import-dir/evt-1")

        with mock.patch.object(
            app_import_view_module.import_service,
            "get_import_app_dir",
            return_value=["a.rainbond", "b.rainbond"],
        ) as get_mock:
            response = view.get(request, event_id="evt-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], ["a.rainbond", "b.rainbond"])
        get_mock.assert_called_once_with("evt-1")

    # capability_id: console.app-import.delete-dir
    def test_tarball_dir_delete_removes_import_dir(self):
        view = app_import_view_module.CenterAppTarballDirView()
        view.tenant = mock.Mock(tenant_name="demo-team")
        view.response_region = "demo-region"
        request = self.factory.delete("/console/teams/demo-team/import-dir?event_id=evt-1")
        record = mock.Mock()
        record.to_dict.return_value = {"event_id": "evt-1", "status": "deleted"}

        with mock.patch.object(
            app_import_view_module.import_service,
            "delete_import_app_dir",
            return_value=record,
        ) as delete_mock:
            response = view.delete(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["event_id"], "evt-1")
        delete_mock.assert_called_once_with(view.tenant, "demo-region", "evt-1")
