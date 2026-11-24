# -*- coding: utf-8 -*-
import os
from types import SimpleNamespace
from unittest import mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
django.setup()

from django.db import connection, transaction  # noqa: E402
from django.test import TestCase  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.mcp_query_service import mcp_query_service  # noqa: E402
from www.models.main import TenantServiceConfigurationFile, TenantServiceVolume  # noqa: E402


# capability_id: console.mcp.config-file-update-content
class MCPConfigFileUpdateTests(TestCase):
    def setUp(self):
        self.team = SimpleNamespace(tenant_name="team-1", tenant_id="tenant-1")
        self.app = SimpleNamespace(ID=100)
        self.service = SimpleNamespace(
            service_id="service-1", service_alias="component-1",
            service_region="region-1", create_status="complete",
        )
        self.user = SimpleNamespace(nick_name="test-operator")
        self.volume = TenantServiceVolume.objects.create(
            service_id="service-1", category="", host_path="",
            volume_type="config-file", volume_path="/etc/app.conf",
            volume_name="app-conf", volume_capacity=0, mode=644,
        )
        self.config = TenantServiceConfigurationFile.objects.create(
            service_id="service-1", volume_id=self.volume.ID,
            volume_name="app-conf", file_content="original content\n",
        )
        self.context_patch = mock.patch.object(
            mcp_query_service, "_get_team_app_service_context",
            return_value=(self.team, self.app, self.service),
        )
        self.context_patch.start()
        self.addCleanup(self.context_patch.stop)
        self.region_patch = mock.patch(
            "console.services.mcp_query_service.region_api.upgrade_service_volumes",
            return_value=(SimpleNamespace(status=200), {}),
        )
        self.region_call = self.region_patch.start()
        self.addCleanup(self.region_patch.stop)

    def update(self, extra=None):
        arguments = {
            "team_name": "team-1", "region_name": "region-1",
            "app_id": 100, "service_id": "service-1",
            "operation": "update_volume", "volume_id": self.volume.ID,
            "new_volume_path": "/etc/updated.conf", "mode": 600,
        }
        arguments.update(extra or {})
        return mcp_query_service.manage_component_storage(self.user, arguments)

    def assert_saved(self, content):
        self.volume.refresh_from_db()
        self.config.refresh_from_db()
        self.assertEqual(self.volume.volume_path, "/etc/updated.conf")
        self.assertEqual(self.volume.mode, 600)
        self.assertEqual(self.config.file_content, content)

    def test_omitted_content_preserves_file_in_region_and_database(self):
        result = self.update()

        self.assertTrue(result["updated"])
        self.assert_saved("original content\n")
        self.assertEqual(self.region_call.call_args.args[3]["file_content"], "original content\n")
        self.assertEqual(self.region_call.call_args.args[:3], ("region-1", "team-1", "component-1"))

    def test_omitted_content_preserves_file_without_region_for_incomplete_service(self):
        self.service.create_status = "creating"

        result = self.update()

        self.assertTrue(result["updated"])
        self.assert_saved("original content\n")
        self.region_call.assert_not_called()

    def test_omitted_content_preserves_existing_empty_file(self):
        self.config.file_content = ""
        self.config.save()

        self.update()

        self.assert_saved("")
        self.assertEqual(self.region_call.call_args.args[3]["file_content"], "")

    def test_permission_only_update_preserves_content_and_path(self):
        result = self.update({"new_volume_path": None})

        self.assertTrue(result["updated"])
        self.volume.refresh_from_db()
        self.config.refresh_from_db()
        self.assertEqual(self.volume.volume_path, "/etc/app.conf")
        self.assertEqual(self.volume.mode, 600)
        self.assertEqual(self.config.file_content, "original content\n")
        self.assertEqual(self.region_call.call_args.args[3]["file_content"], "original content\n")

    def test_explicit_new_content_reaches_region_and_database(self):
        self.update({"new_file_content": "updated configuration\n"})

        self.assert_saved("updated configuration\n")
        self.assertEqual(self.region_call.call_args.args[3]["file_content"], "updated configuration\n")

    def test_explicit_empty_string_clears_file(self):
        self.update({"new_file_content": ""})

        self.assert_saved("")
        self.assertEqual(self.region_call.call_args.args[3]["file_content"], "")

    def test_invalid_content_is_rejected_before_region_or_database_writes(self):
        for content in (None, {}, [], True, 123, 1.25):
            with self.subTest(content=content):
                with self.assertRaises(ServiceHandleException) as error:
                    with transaction.atomic(), CaptureQueriesContext(connection) as queries:
                        self.update({"new_file_content": content})

                self.assertEqual(error.exception.status_code, 400)
                self.region_call.assert_not_called()
                writes = [query["sql"] for query in queries if query["sql"].lstrip().upper().startswith(
                    ("INSERT", "UPDATE", "DELETE"))]
                self.assertEqual(writes, [])
                self.volume.refresh_from_db()
                self.config.refresh_from_db()
                self.assertEqual(self.volume.volume_path, "/etc/app.conf")
                self.assertEqual(self.volume.mode, 644)
                self.assertEqual(self.config.file_content, "original content\n")

    def test_incomplete_config_file_also_rejects_explicit_null_before_writes(self):
        self.service.create_status = "creating"

        with self.assertRaises(ServiceHandleException) as error:
            with transaction.atomic(), CaptureQueriesContext(connection) as queries:
                self.update({"new_file_content": None})

        self.assertEqual(error.exception.status_code, 400)
        self.region_call.assert_not_called()
        self.assertFalse(any(query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for query in queries))
        self.volume.refresh_from_db()
        self.config.refresh_from_db()
        self.assertEqual(self.volume.volume_path, "/etc/app.conf")
        self.assertEqual(self.config.file_content, "original content\n")

    def test_missing_config_record_retains_existing_error_without_side_effects(self):
        self.config.delete()

        with self.assertRaises(ServiceHandleException) as error:
            self.update()

        self.assertEqual(error.exception.status_code, 400)
        self.region_call.assert_not_called()
        self.volume.refresh_from_db()
        self.assertEqual(self.volume.volume_path, "/etc/app.conf")

    def test_persistent_volume_capacity_update_keeps_existing_contract(self):
        self.config.delete()
        self.volume.volume_type = "nas"
        self.volume.volume_path = "/data"
        self.volume.volume_capacity = 10
        self.volume.save()

        result = self.update({"new_volume_path": "/data", "volume_capacity": 20})

        self.assertTrue(result["updated"])
        self.volume.refresh_from_db()
        self.assertEqual(self.volume.volume_capacity, 20)
        self.assertEqual(self.region_call.call_args.args[3]["volume_capacity"], 20)
        self.assertIsNone(self.region_call.call_args.args[3]["file_content"])

    def test_region_failure_does_not_save_either_model(self):
        self.region_call.return_value = (SimpleNamespace(status=500), {})

        with self.assertRaises(ServiceHandleException) as error:
            self.update({"new_file_content": "updated configuration"})

        self.assertEqual(error.exception.status_code, 405)
        self.volume.refresh_from_db()
        self.config.refresh_from_db()
        self.assertEqual(self.volume.volume_path, "/etc/app.conf")
        self.assertEqual(self.volume.mode, 644)
        self.assertEqual(self.config.file_content, "original content\n")
