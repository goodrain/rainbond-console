import collections
import json
import os
from types import ModuleType, SimpleNamespace
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys  # noqa: E402

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
regionapi_module = ModuleType("www.apiclient.regionapi")


class _RegionInvokeApiStub(object):
    def create_vm_snapshot(self, *args, **kwargs):
        return None, {}

    def start_vm_export(self, *args, **kwargs):
        return None, {}


regionapi_module.RegionInvokeApi = _RegionInvokeApiStub
sys.modules.setdefault("www.apiclient.regionapi", regionapi_module)

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402

from console.services.virtual_machine import vms  # noqa: E402
from www.models.main import TenantServiceInfo, VMTemplate, VMTemplateDisk, VMTemplateVersion, VirtualMachineImage  # noqa: E402


class VMTemplateGenerationTests(TestCase):

    def _create_vm_service(self, tenant_id="tenant-a", service_id="service-a", service_alias="demo-vm"):
        return TenantServiceInfo.objects.create(
            tenant_id=tenant_id,
            service_id=service_id,
            service_alias=service_alias,
            service_key=service_id,
            service_region="demo-region",
            category="application",
            version="v1",
            image="demo/image",
            extend_method="vm",
            k8s_component_name="{}-k8s".format(service_id)
        )

    def _create_source_asset(self, tenant_id="tenant-a"):
        return VirtualMachineImage.objects.create(
            tenant_id=tenant_id,
            name="source-image",
            image_url="demo/image",
            source_type="upload",
            source_uri="/tmp/demo.qcow2",
            arch="amd64",
            os_name="Ubuntu",
            format="qcow2",
            status="ready"
        )

    def test_save_vm_template_creates_snapshot_when_vm_running(self):
        source_asset = self._create_source_asset()
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image=source_asset.image_url
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.create_vm_snapshot",
            return_value=(None, {"bean": {"snapshot_name": "snap-1"}})
        ) as snapshot_mock, mock.patch(
            "console.services.virtual_machine.region_api.start_vm_export",
            return_value=(None, {
                "bean": {
                    "export_id": "evt-1",
                    "status": "exporting",
                    "disks": [
                        {
                            "disk_key": "rootdisk",
                            "disk_name": "rootdisk",
                            "disk_role": "root",
                            "boot_order": 1,
                            "status": "exporting",
                            "download_url": ""
                        },
                        {
                            "disk_key": "data-1",
                            "disk_name": "data-1",
                            "disk_role": "data",
                            "boot_order": 2,
                            "status": "exporting",
                            "download_url": ""
                        }
                    ]
                }
            })
        ) as export_mock:
            result = vms.save_vm_template(
                service,
                region_name="demo-region",
                tenant_name="demo-team",
                template_name="win10-devtools",
                vm_status="running",
                description="Windows 10 dev template",
                include_data_disks=True
            )

        template = VMTemplate.objects.get(tenant_id="tenant-a", name="win10-devtools")
        version = VMTemplateVersion.objects.get(template_id=template.ID)
        disks = list(VMTemplateDisk.objects.filter(template_version_id=version.ID).order_by("order_index"))

        self.assertEqual(template.ID, result["id"])
        self.assertEqual("generating", template.status)
        self.assertEqual(version.ID, template.latest_version_id)
        self.assertEqual("v1", version.version)
        self.assertEqual("snap-1", version.snapshot_name)
        self.assertEqual("snapshot", version.snapshot_source)
        self.assertEqual("generating", version.status)
        self.assertEqual(2, len(disks))
        self.assertEqual("root", disks[0].disk_role)
        self.assertEqual(1, json.loads(disks[0].extra_json)["boot_order"])
        snapshot_mock.assert_called_once()
        export_mock.assert_called_once()
        export_request = export_mock.call_args[0][3]
        self.assertEqual("snapshot", export_request["source_kind"])
        self.assertEqual("snap-1", export_request["snapshot_name"])

    def test_save_vm_template_uses_export_directly_when_vm_closed(self):
        source_asset = self._create_source_asset()
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image=source_asset.image_url
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.create_vm_snapshot"
        ) as snapshot_mock, mock.patch(
            "console.services.virtual_machine.region_api.start_vm_export",
            return_value=(None, {
                "bean": {
                    "export_id": "evt-2",
                    "status": "ready",
                    "disks": [
                        {
                            "disk_key": "rootdisk",
                            "disk_name": "rootdisk",
                            "disk_role": "root",
                            "boot_order": 1,
                            "status": "ready",
                            "download_url": "https://download/root.qcow2"
                        }
                    ]
                }
            })
        ) as export_mock:
            result = vms.save_vm_template(
                service,
                region_name="demo-region",
                tenant_name="demo-team",
                template_name="ubuntu-dev",
                vm_status="closed",
                description="Ubuntu dev template",
                include_data_disks=False
            )

        template = VMTemplate.objects.get(tenant_id="tenant-a", name="ubuntu-dev")
        version = VMTemplateVersion.objects.get(template_id=template.ID)
        disks = list(VMTemplateDisk.objects.filter(template_version_id=version.ID))

        self.assertEqual("ready", template.status)
        self.assertEqual(version.ID, template.latest_ready_version_id)
        self.assertEqual("ready", version.status)
        self.assertEqual("full", version.recoverability)
        self.assertEqual(1, len(disks))
        self.assertEqual("root", disks[0].disk_role)
        self.assertEqual(template.ID, result["id"])
        snapshot_mock.assert_not_called()
        export_request = export_mock.call_args[0][3]
        self.assertEqual("vm", export_request["source_kind"])
        self.assertEqual(False, export_request["export_all_disks"])

    def test_save_vm_template_with_data_disks_marks_partial_until_disk_restore_supported(self):
        source_asset = self._create_source_asset()
        service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image=source_asset.image_url
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.start_vm_export",
            return_value=(None, {
                "bean": {
                    "export_id": "evt-3",
                    "status": "ready",
                    "disks": [
                        {
                            "disk_key": "rootdisk",
                            "disk_name": "rootdisk",
                            "disk_role": "root",
                            "boot_order": 1,
                            "status": "ready",
                            "download_url": "https://download/root.qcow2"
                        },
                        {
                            "disk_key": "data-1",
                            "disk_name": "data-1",
                            "disk_role": "data",
                            "boot_order": 2,
                            "status": "ready",
                            "download_url": "https://download/data.qcow2"
                        }
                    ]
                }
            })
        ):
            vms.save_vm_template(
                service,
                region_name="demo-region",
                tenant_name="demo-team",
                template_name="ubuntu-data",
                vm_status="closed",
                description="Ubuntu with data disk",
                include_data_disks=True
            )

        template = VMTemplate.objects.get(tenant_id="tenant-a", name="ubuntu-data")
        version = VMTemplateVersion.objects.get(template_id=template.ID)

        self.assertEqual("partial", template.status)
        self.assertEqual("partial", version.status)
        self.assertEqual("partial", version.recoverability)
        self.assertIn("data disk content restore", version.status_message)

    def test_retry_vm_template_version_restarts_generation(self):
        service = self._create_vm_service()
        template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="ubuntu-dev",
            description="Ubuntu dev template",
            status="failed",
            latest_version_id=1,
            source_service_id=service.service_id
        )
        version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=template.ID,
            version="v1",
            status="failed",
            recoverability="partial",
            status_message="old failure",
            source_service_id=service.service_id,
            source_service_alias=service.service_alias,
            source_vm_status="closed",
            include_data_disks=True,
            runtime_snapshot_json=json.dumps({"boot_mode": "uefi"})
        )
        template.latest_version_id = version.ID
        template.save()
        VMTemplateDisk.objects.create(
            tenant_id="tenant-a",
            template_version_id=version.ID,
            disk_key="old-root",
            disk_name="old-root",
            disk_role="root",
            order_index=0,
            boot=True,
            image_url="https://old/root.qcow2",
            status="failed"
        )

        with mock.patch(
            "console.services.virtual_machine.region_api.start_vm_export",
            return_value=(None, {
                "bean": {
                    "export_id": "evt-retry",
                    "status": "exporting",
                    "disks": [
                        {
                            "disk_key": "rootdisk",
                            "disk_name": "rootdisk",
                            "disk_role": "root",
                            "status": "exporting",
                            "download_url": ""
                        }
                    ]
                }
            })
        ) as export_mock:
            result = vms.retry_vm_template_version(
                tenant_id="tenant-a",
                template_id=template.ID,
                version_id=version.ID,
                region_name="demo-region",
                tenant_name="demo-team"
            )

        version.refresh_from_db()
        disks = list(VMTemplateDisk.objects.filter(template_version_id=version.ID))

        self.assertEqual(version.ID, result["id"])
        self.assertEqual("generating", version.status)
        self.assertEqual("", version.status_message)
        self.assertEqual("evt-retry", version.export_id)
        self.assertEqual(1, len(disks))
        self.assertEqual("rootdisk", disks[0].disk_key)
        export_request = export_mock.call_args[0][3]
        self.assertEqual("vm", export_request["source_kind"])
