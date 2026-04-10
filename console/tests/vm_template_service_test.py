import collections
import json
import os
from types import ModuleType

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys  # noqa: E402

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
regionapi_module = ModuleType("www.apiclient.regionapi")


class _RegionInvokeApiStub(object):
    pass


regionapi_module.RegionInvokeApi = _RegionInvokeApiStub
sys.modules.setdefault("www.apiclient.regionapi", regionapi_module)

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402

from console.services.virtual_machine import vms  # noqa: E402
from www.models.main import VMTemplate, VMTemplateDisk, VMTemplateVersion  # noqa: E402


class VMTemplateServiceTests(TestCase):

    def test_list_vm_templates_returns_latest_ready_version_summary(self):
        template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="win10-devtools",
            description="Windows 10 with tools",
            status="ready"
        )
        version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=template.ID,
            version="v3",
            status="ready",
            recoverability="full",
            disk_count=2,
            runtime_snapshot_json=json.dumps({
                "boot_mode": "uefi",
                "network_mode": "fixed"
            }),
            boot_mode="uefi",
            source_service_id="service-a",
            source_service_alias="demo-vm"
        )
        template.latest_version_id = version.ID
        template.latest_ready_version_id = version.ID
        template.save()

        result = vms.list_vm_templates("tenant-a")

        self.assertEqual(1, len(result))
        self.assertEqual(template.ID, result[0]["id"])
        self.assertEqual("win10-devtools", result[0]["name"])
        self.assertEqual("ready", result[0]["status"])
        self.assertEqual(2, result[0]["disk_count"])
        self.assertTrue(result[0]["can_instantiate"])
        self.assertEqual({
            "id": version.ID,
            "version": "v3",
            "status": "ready",
            "recoverability": "full"
        }, result[0]["latest_ready_version"])

    def test_get_vm_template_detail_includes_versions_disks_and_runtime_snapshot(self):
        template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="ubuntu-dev",
            description="Ubuntu developer template",
            status="partial",
            source_service_id="service-b"
        )
        version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=template.ID,
            version="v2",
            status="partial",
            recoverability="partial",
            disk_count=2,
            boot_mode="uefi",
            runtime_snapshot_json=json.dumps({
                "boot_mode": "uefi",
                "gpu_enabled": True,
                "gpu_resources": ["gpu.example.com/A10"]
            }),
            source_service_id="service-b",
            source_service_alias="ubuntu-vm",
            status_message="data disk missing"
        )
        template.latest_version_id = version.ID
        template.latest_ready_version_id = version.ID
        template.save()
        VMTemplateDisk.objects.create(
            tenant_id="tenant-a",
            template_version_id=version.ID,
            disk_key="rootdisk",
            disk_name="rootdisk",
            disk_role="root",
            order_index=0,
            boot=True,
            image_url="https://download/root.qcow2",
            status="ready"
        )
        VMTemplateDisk.objects.create(
            tenant_id="tenant-a",
            template_version_id=version.ID,
            disk_key="datadisk",
            disk_name="datadisk",
            disk_role="data",
            order_index=1,
            boot=False,
            image_url="https://download/data.qcow2",
            status="failed",
            status_message="missing"
        )

        detail = vms.get_vm_template_detail("tenant-a", template.ID)

        self.assertEqual(template.ID, detail["id"])
        self.assertEqual("partial", detail["status"])
        self.assertEqual(1, len(detail["versions"]))
        self.assertEqual("v2", detail["versions"][0]["version"])
        self.assertEqual("partial", detail["versions"][0]["recoverability"])
        self.assertTrue(detail["versions"][0]["can_instantiate"])
        self.assertEqual("uefi", detail["versions"][0]["runtime_snapshot"]["boot_mode"])
        self.assertEqual(2, len(detail["versions"][0]["disks"]))
        self.assertEqual("root", detail["versions"][0]["disks"][0]["disk_role"])
        self.assertTrue(detail["versions"][0]["disks"][0]["content_restore_supported"])
        self.assertEqual(1, detail["versions"][0]["disks"][0]["boot_order"])
        self.assertEqual("data", detail["versions"][0]["disks"][1]["disk_role"])
        self.assertFalse(detail["versions"][0]["disks"][1]["content_restore_supported"])

    def test_failed_template_version_cannot_instantiate(self):
        template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="broken-template",
            description="Broken template",
            status="failed"
        )
        version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=template.ID,
            version="v1",
            status="failed",
            recoverability="partial",
            status_message="root disk missing"
        )
        template.latest_version_id = version.ID
        template.save()

        detail = vms.get_vm_template_detail("tenant-a", template.ID)

        self.assertFalse(detail["can_instantiate"])
        self.assertFalse(detail["versions"][0]["can_instantiate"])

    def test_disabled_template_cannot_instantiate_even_with_ready_version(self):
        template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="disabled-template",
            description="Disabled template",
            status="disabled",
            disabled=True
        )
        version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=template.ID,
            version="v1",
            status="ready",
            recoverability="full"
        )
        template.latest_version_id = version.ID
        template.latest_ready_version_id = version.ID
        template.save()

        result = vms.list_vm_templates("tenant-a")
        detail = vms.get_vm_template_detail("tenant-a", template.ID)

        disabled_record = next(item for item in result if item["id"] == template.ID)
        self.assertFalse(disabled_record["can_instantiate"])
        self.assertFalse(detail["can_instantiate"])
