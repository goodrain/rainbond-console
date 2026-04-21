# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
sys.modules.setdefault("openapi_client", ModuleType("openapi_client"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.app_overview import AppVMExportView  # noqa: E402


class AppVMExportViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppVMExportView()
        self.view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team")
        self.view.service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            service_cname="Windows 测试机",
            extend_method="vm",
            image="demo/image"
        )
        self.view.response_region = "demo-region"
        self.view.app = SimpleNamespace(ID=1)

    def test_post_requests_confirmation_when_existing_export_found(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-export", {}, format="json")
        )

        with mock.patch("console.views.app_overview.vms.list_vm_export_assets_for_service", return_value=[
            SimpleNamespace(
                ID=12,
                name="service-a",
                status="ready",
                source_type="vm_export",
                extra_json='{"display_name":"Windows 测试机"}'
            )
        ]), mock.patch("console.views.app_overview.vms.build_vm_export_confirmation_payload", return_value={
            "id": 12,
            "display_name": "Windows 测试机",
            "status": "ready",
        }):
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["bean"]["requires_confirmation"])
        self.assertEqual("Windows 测试机", response.data["data"]["bean"]["existing_asset"]["display_name"])

    def test_post_rejects_export_when_vm_running(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-export", {}, format="json")
        )

        with mock.patch("console.views.app_overview.vms.list_vm_export_assets_for_service", return_value=[]), \
                mock.patch("console.views.app_overview.app_service.get_service_status", return_value={"status": "running"}), \
                mock.patch("console.views.app_overview.vms.start_vm_export", side_effect=ValueError("vm export requires closed status")):
            response = self.view.post(request)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["msg"], "vm export forbidden")

    def test_post_starts_export_when_vm_closed(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-export", {}, format="json")
        )

        with mock.patch("console.views.app_overview.vms.list_vm_export_assets_for_service", return_value=[]), \
                mock.patch("console.views.app_overview.app_service.get_service_status", return_value={"status": "closed"}), \
                mock.patch("console.views.app_overview.vms.start_vm_export", return_value={"id": 12, "status": "exporting"}) as start_mock:
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["id"], 12)
        start_mock.assert_called_once()

    def test_post_replaces_existing_export_when_confirmed(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-export", {"force_replace": True}, format="json")
        )

        with mock.patch("console.views.app_overview.vms.list_vm_export_assets_for_service", return_value=[
            SimpleNamespace(ID=12)
        ]), \
                mock.patch("console.views.app_overview.vms.replace_vm_export_assets_for_service") as replace_mock, \
                mock.patch("console.views.app_overview.app_service.get_service_status", return_value={"status": "closed"}), \
                mock.patch("console.views.app_overview.vms.start_vm_export", return_value={"id": 12, "status": "exporting"}) as start_mock:
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        replace_mock.assert_called_once_with(self.view.service, "demo-region", "demo-team")
        start_mock.assert_called_once()

    def test_get_returns_latest_export_status(self):
        request = self.view.initialize_request(
            self.factory.get("/console/teams/demo-team/apps/demo-vm/vm-export")
        )
        asset = SimpleNamespace(build_event_id="evt-1", extra_json="{}", status="exporting")

        with mock.patch("console.views.app_overview.vms.get_latest_vm_export_asset", return_value=asset) as latest_mock, \
                mock.patch("console.views.app_overview.vms.sync_vm_export_status", return_value={"id": 11, "status": "ready"}) as sync_mock:
            response = self.view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["status"], "ready")
        latest_mock.assert_called_once_with("tenant-a", "service-a")
        sync_mock.assert_called_once()
