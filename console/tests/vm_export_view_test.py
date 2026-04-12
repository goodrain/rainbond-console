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
            extend_method="vm",
            image="demo/image"
        )
        self.view.response_region = "demo-region"
        self.view.app = SimpleNamespace(ID=1)

    def test_post_rejects_duplicate_export_name(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-export", {"name": "snapshot-1"}, format="json")
        )

        with mock.patch("console.views.app_overview.vm_repo.get_vm_image_by_tenant_id_and_name") as query_mock:
            query_mock.return_value.exists.return_value = True
            response = self.view.post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "虚拟机镜像名称已存在")

    def test_post_starts_export_when_vm_closed(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-export", {"name": "snapshot-1"}, format="json")
        )

        with mock.patch("console.views.app_overview.vm_repo.get_vm_image_by_tenant_id_and_name") as query_mock, \
                mock.patch("console.views.app_overview.app_service.get_service_status", return_value={"status": "closed"}), \
                mock.patch("console.views.app_overview.vms.start_vm_export", return_value={"id": 11, "status": "exporting"}) as start_mock:
            query_mock.return_value.exists.return_value = False
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["id"], 11)
        start_mock.assert_called_once()

    def test_post_starts_export_when_vm_running(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-export", {"name": "snapshot-1"}, format="json")
        )

        with mock.patch("console.views.app_overview.vm_repo.get_vm_image_by_tenant_id_and_name") as query_mock, \
                mock.patch("console.views.app_overview.app_service.get_service_status", return_value={"status": "running"}), \
                mock.patch("console.views.app_overview.vms.start_vm_export", return_value={"id": 12, "status": "exporting"}) as start_mock:
            query_mock.return_value.exists.return_value = False
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["id"], 12)
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
