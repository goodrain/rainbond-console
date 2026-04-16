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

from console.exception.main import ServiceHandleException
from console.services.virtual_machine import vms
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.models.main import VirtualMachineImage


class VMExportServiceTests(TestCase):

    def test_start_vm_export_uses_direct_export_when_vm_closed(self):
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image="demo/image"
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.create_vm_snapshot"
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
                vm_status="closed",
                description="demo export"
            )

        snapshot_mock.assert_not_called()
        export_request = export_mock.call_args[0][3]
        self.assertEqual("vm", export_request["source_kind"])
        self.assertNotIn("snapshot_name", export_request)
        self.assertEqual("closed", asset["extra"]["export_request"]["vm_status"])

    def test_start_vm_export_rejects_running_status(self):
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
                vm_status="running"
            )

    def test_start_vm_export_creates_machine_asset_and_disk_records(self):
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image="demo/image"
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.create_vm_snapshot"
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

        snapshot_mock.assert_not_called()
        self.assertEqual("machine", asset["asset_kind"])
        self.assertEqual("vm_export", asset["source_type"])
        self.assertEqual("exporting", asset["status"])
        self.assertEqual(2, asset["disk_count"])
        self.assertEqual("evt-1", asset["build_event_id"])
        self.assertEqual("service-a", asset["source_service_id"])
        self.assertEqual("closed", asset["extra"]["export_request"]["vm_status"])
        self.assertEqual("vm", asset["extra"]["export_request"]["source_kind"])
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
        })), mock.patch("console.services.virtual_machine.region_api.persist_vm_export", return_value=(None, {
            "bean": {
                "status": "ready",
                "root_object_uri": "s3://vm-assets/rootdisk.qcow2",
                "machine_manifest": {
                    "version": "v1",
                    "root_disk_key": "rootdisk",
                    "disks": [
                        {"disk_key": "rootdisk", "disk_role": "root"},
                        {"disk_key": "data-1", "disk_role": "data"}
                    ]
                }
            }
        })):
            asset = vms.sync_vm_export_status(parent, region_name="demo-region", tenant_name="demo-team")

        self.assertEqual("ready", asset["status"])
        self.assertEqual(2, len(asset["disks"]))
        self.assertEqual("https://download/rootdisk", asset["disks"][0]["download_url"])

    def test_sync_vm_export_status_persists_machine_manifest_before_marking_ready(self):
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
                "source_service_alias": "demo-vm",
                "runtime_snapshot": {"boot_mode": "uefi"},
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
                        "download_url": "https://download/data-1"
                    }
                ]
            }
        })), mock.patch("console.services.virtual_machine.region_api.persist_vm_export", return_value=(None, {
            "bean": {
                "status": "ready",
                "storage_backend": "s3",
                "storage_bucket": "vm-assets",
                "storage_prefix": "vm-export/tenant-a/asset-101/",
                "root_object_uri": "s3://vm-assets/vm-export/tenant-a/asset-101/rootdisk.qcow2",
                "machine_manifest": {
                    "version": "v1",
                    "arch": "amd64",
                    "boot_mode": "uefi",
                    "root_disk_key": "rootdisk",
                    "disks": [
                        {
                            "disk_key": "rootdisk",
                            "disk_name": "rootdisk",
                            "disk_role": "root",
                            "boot_order": 1,
                            "object_key": "vm-export/tenant-a/asset-101/rootdisk.qcow2",
                            "object_uri": "s3://vm-assets/vm-export/tenant-a/asset-101/rootdisk.qcow2",
                            "format": "qcow2",
                            "size_bytes": 42949672960
                        },
                        {
                            "disk_key": "data-1",
                            "disk_name": "data-1",
                            "disk_role": "data",
                            "boot_order": 2,
                            "object_key": "vm-export/tenant-a/asset-101/data-1.qcow2",
                            "object_uri": "s3://vm-assets/vm-export/tenant-a/asset-101/data-1.qcow2",
                            "format": "qcow2",
                            "size_bytes": 214748364800
                        }
                    ]
                }
            }
        })) as persist_mock:
            asset = vms.sync_vm_export_status(parent, region_name="demo-region", tenant_name="demo-team")

        self.assertEqual("ready", asset["status"])
        self.assertEqual("s3://vm-assets/vm-export/tenant-a/asset-101/rootdisk.qcow2", asset["image_url"])
        persist_mock.assert_called_once()
        parent.refresh_from_db()
        extra = json.loads(parent.extra_json)
        self.assertEqual("ready", extra["storage_status"])
        self.assertEqual("s3", extra["storage_backend"])
        self.assertEqual("vm-assets", extra["storage_bucket"])
        self.assertEqual(2, len(extra["machine_manifest"]["disks"]))

    def test_sync_vm_export_asset_record_keeps_ready_asset_when_region_export_is_missing(self):
        parent = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="snapshot-1",
            image_url="https://download/rootdisk",
            source_type="vm_export",
            source_uri="service://service-a",
            status="ready",
            build_event_id="evt-1",
            extra_json=json.dumps({
                "asset_kind": "machine",
                "disk_count": 1,
                "source_service_id": "service-a",
                "disks": [
                    {"disk_key": "rootdisk", "disk_role": "root", "download_url": "https://download/rootdisk"},
                ]
            })
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.get_vm_export_status",
            side_effect=ServiceHandleException(
                msg={
                    "httpcode": 500,
                    "body": {"msg": "vm export evt-1 not found"},
                },
                msg_show="数据中心操作故障 vm export evt-1 not found",
                status_code=500
            )
        ):
            asset = vms.sync_vm_export_asset_record(parent, region_name="demo-region", tenant_name="demo-team")

        self.assertEqual("ready", asset.status)
        extra = json.loads(asset.extra_json)
        self.assertTrue(extra["export_record_missing"])
        self.assertEqual("vm export not found", extra["latest_export_error"])

    def test_sync_vm_export_asset_record_marks_unfinished_asset_failed_when_region_export_is_missing(self):
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
                "disk_count": 1,
                "source_service_id": "service-a",
                "disks": [
                    {"disk_key": "rootdisk", "disk_role": "root"},
                ]
            })
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.get_vm_export_status",
            side_effect=ServiceHandleException(
                msg={"body": {"msg": "vm export evt-1 not found"}},
                msg_show="数据中心操作故障 vm export evt-1 not found",
                status_code=500
            )
        ):
            asset = vms.sync_vm_export_asset_record(parent, region_name="demo-region", tenant_name="demo-team")

        self.assertEqual("failed", asset.status)
        extra = json.loads(asset.extra_json)
        self.assertTrue(extra["export_record_missing"])

    def test_sync_vm_export_asset_record_re_raises_non_missing_errors(self):
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
                "disk_count": 1,
                "source_service_id": "service-a",
                "disks": [
                    {"disk_key": "rootdisk", "disk_role": "root"},
                ]
            })
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.get_vm_export_status",
            side_effect=ServiceHandleException(
                msg="region timeout",
                msg_show="访问数据中心异常，请稍后重试",
                status_code=500
            )
        ):
            with self.assertRaises(ServiceHandleException):
                vms.sync_vm_export_asset_record(parent, region_name="demo-region", tenant_name="demo-team")

    def test_sync_vm_export_asset_record_ignores_region_404_errors(self):
        parent = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="snapshot-1",
            image_url="https://download/rootdisk",
            source_type="vm_export",
            source_uri="service://service-a",
            status="ready",
            build_event_id="evt-1",
            extra_json=json.dumps({
                "asset_kind": "machine",
                "disk_count": 1,
                "source_service_id": "service-a",
                "disks": [
                    {"disk_key": "rootdisk", "disk_role": "root", "download_url": "https://download/rootdisk"},
                ]
            })
        )

        region_404 = RegionApiBaseHttpClient.CallApiError(
            "region api",
            "http://region/v2/tenants/demo/services/demo/vm-exports/evt-1",
            "GET",
            mock.Mock(status=404),
            {"msg": "not found"},
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.get_vm_export_status",
            side_effect=region_404
        ):
            asset = vms.sync_vm_export_asset_record(parent, region_name="demo-region", tenant_name="demo-team")

        self.assertEqual("ready", asset.status)
        extra = json.loads(asset.extra_json)
        self.assertFalse(extra.get("export_record_missing", False))
