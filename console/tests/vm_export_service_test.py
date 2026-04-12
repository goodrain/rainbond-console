import collections
import json
import os
from types import ModuleType, SimpleNamespace
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

import django

django.setup()

from django.test import TestCase

from console.services.virtual_machine import vms
from www.models.main import VirtualMachineImage


class VMExportServiceTests(TestCase):

    def test_start_vm_export_creates_snapshot_when_vm_running(self):
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image="demo/image"
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.create_vm_snapshot",
            return_value=(None, {"bean": {"snapshot_name": "snap-1"}})
        ) as snapshot_mock, mock.patch("console.services.virtual_machine.region_api.start_vm_export", return_value=(None, {
            "bean": {
                "export_id": "evt-1",
                "status": "exporting",
                "disks": [
                    {
                        "disk_key": "rootdisk",
                        "disk_name": "rootdisk",
                        "disk_role": "root",
                        "pvc_name": "rootdisk-pvc",
                        "pvc_namespace": "demo-ns",
                        "export_name": "evt-1-rootdisk",
                        "status": "exporting",
                    }
                ]
            }
        })) as export_mock:
            asset = vms.start_vm_export(
                service,
                region_name="demo-region",
                tenant_name="demo-team",
                export_name="snapshot-1",
                vm_status="running",
                description="demo export"
            )

        snapshot_mock.assert_called_once()
        export_request = export_mock.call_args[0][3]
        self.assertEqual("snapshot", export_request["source_kind"])
        self.assertEqual("snap-1", export_request["snapshot_name"])
        self.assertEqual("running", asset["extra"]["export_request"]["vm_status"])

    def test_start_vm_export_rejects_invalid_vm_status(self):
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image="demo/image"
        )

        with self.assertRaises(ValueError):
            vms.start_vm_export(
                service,
                region_name="demo-region",
                tenant_name="demo-team",
                export_name="snapshot-1",
                vm_status="undeploy"
            )

    def test_start_vm_export_creates_machine_asset_and_disk_records(self):
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image="demo/image"
        )

        with mock.patch("console.services.virtual_machine.region_api.start_vm_export", return_value=(None, {
            "bean": {
                "export_id": "evt-1",
                "status": "exporting",
                "disks": [
                    {
                        "disk_key": "rootdisk",
                        "disk_name": "rootdisk",
                        "disk_role": "root",
                        "pvc_name": "rootdisk-pvc",
                        "pvc_namespace": "demo-ns",
                        "export_name": "evt-1-rootdisk",
                        "status": "exporting",
                    },
                    {
                        "disk_key": "data-1",
                        "disk_name": "data-1",
                        "disk_role": "data",
                        "pvc_name": "data-pvc",
                        "pvc_namespace": "demo-ns",
                        "export_name": "evt-1-data-1",
                        "status": "exporting",
                    }
                ]
            }
        })):
            asset = vms.start_vm_export(
                service,
                region_name="demo-region",
                tenant_name="demo-team",
                export_name="snapshot-1",
                vm_status="closed"
            )

        self.assertEqual("machine", asset["asset_kind"])
        self.assertEqual("vm_export", asset["source_type"])
        self.assertEqual("exporting", asset["status"])
        self.assertEqual(2, asset["disk_count"])
        self.assertEqual("evt-1", asset["build_event_id"])
        self.assertEqual("service-a", asset["source_service_id"])
        self.assertEqual("closed", asset["extra"]["export_request"]["vm_status"])
        self.assertEqual(2, len(asset["disks"]))

    def test_sync_vm_export_status_updates_parent_and_disks(self):
        parent = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="snapshot-1",
            image_url="",
            source_type="vm_export",
            source_uri="service://service-a",
            status="exporting",
            build_event_id="evt-1",
            extra_json=json.dumps({
                "asset_kind": "machine",
                "disk_count": 2,
                "source_service_id": "service-a",
                "disks": [
                    {"disk_key": "rootdisk", "disk_role": "root"},
                    {"disk_key": "data-1", "disk_role": "data"},
                ]
            })
        )

        with mock.patch("console.services.virtual_machine.region_api.get_vm_export_status", return_value=(None, {
            "bean": {
                "export_id": "evt-1",
                "status": "ready",
                "disks": [
                    {
                        "disk_key": "rootdisk",
                        "disk_name": "rootdisk",
                        "disk_role": "root",
                        "pvc_name": "rootdisk-pvc",
                        "pvc_namespace": "demo-ns",
                        "export_name": "evt-1-rootdisk",
                        "status": "ready",
                        "download_url": "https://download/rootdisk"
                    },
                    {
                        "disk_key": "data-1",
                        "disk_name": "data-1",
                        "disk_role": "data",
                        "pvc_name": "data-pvc",
                        "pvc_namespace": "demo-ns",
                        "export_name": "evt-1-data-1",
                        "status": "ready",
                        "download_url": "https://download/data"
                    }
                ]
            }
        })):
            asset = vms.sync_vm_export_status(parent, region_name="demo-region", tenant_name="demo-team")

        self.assertEqual("ready", asset["status"])
        self.assertEqual(2, len(asset["disks"]))
        self.assertEqual("https://download/rootdisk", asset["disks"][0]["download_url"])
