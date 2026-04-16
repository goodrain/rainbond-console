# capability_id: rainbond-console.vm-run.disk-asset-create
# capability_id: rainbond-console.vm-run.vm-export-multi-disk-create
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

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.models.main import ComponentK8sAttributes  # noqa: E402
from console.views.app_create.vm_run import VMRunCreateView  # noqa: E402
from www.models.main import VirtualMachineImage  # noqa: E402


class VMAssetInstantiationTests(TestCase):
    def test_vm_run_create_from_existing_disk_asset_uses_source_uri_for_vm_build(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="uploaded-root",
            image_url="tenant-ns:uploaded-root",
            source_type="upload",
            source_uri="/grdata/package_build/temp/events/uploaded-root.qcow2",
            status="ready",
            format="qcow2",
            boot_mode="uefi"
        )
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "uploaded-root-vm",
                "k8s_component_name": "uploaded-root-vm",
                "asset_id": asset.ID,
                "image_name": asset.name,
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new-uploaded-root",
            service_alias="gr123461",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new-uploaded-root", "service_alias": "gr123461"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.app_service.create_vm_run_app",
                    return_value=(200, "创建成功", new_service),
                    create=True) as create_vm_run_app_mock, \
                mock.patch(
                    "console.views.app_create.vm_run.group_service.add_service_to_group",
                    return_value=(200, "success")):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        _, create_args, _ = create_vm_run_app_mock.mock_calls[0]
        self.assertEqual("tenant-ns:uploaded-root", create_args[5])
        self.assertEqual("/grdata/package_build/temp/events/uploaded-root.qcow2", create_args[8])
        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-new-uploaded-root")
        }
        self.assertEqual("uefi", attrs["vm_boot_mode"])
        self.assertEqual("qcow2", attrs["vm_boot_source_format"])

    def test_vm_run_create_from_iso_asset_keeps_boot_media_out_of_root_imports(self):
        iso_asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="windows-installer",
            image_url="https://download/windows-server.iso",
            source_type="upload",
            source_uri="/tmp/windows-server.iso",
            status="ready",
            format="iso"
        )
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "installer-vm",
                "k8s_component_name": "installer-vm",
                "asset_id": iso_asset.ID,
                "image_name": iso_asset.name
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new-iso",
            service_alias="gr123457",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new-iso", "service_alias": "gr123457"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.app_service.create_vm_run_app",
                    return_value=(200, "创建成功", new_service),
                    create=True) as create_vm_run_app_mock, \
                mock.patch(
                    "console.views.app_create.vm_run.group_service.add_service_to_group",
                    return_value=(200, "success")):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        _, create_args, _ = create_vm_run_app_mock.mock_calls[0]
        self.assertEqual("tenant-ns:windows-installer", create_args[5])
        self.assertEqual("https://download/windows-server.iso", create_args[8])
        self.assertFalse(
            ComponentK8sAttributes.objects.filter(component_id="service-new-iso", name="vm_disk_imports").exists()
        )

    def test_vm_run_create_uses_exported_root_and_restores_data_disks(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="exported-root",
            image_url="s3://vm-assets/vm-export/assets/101/rootdisk.qcow2",
            source_type="vm_export",
            source_uri="service://service-a",
            status="ready",
            extra_json=json.dumps({
                "asset_kind": "machine",
                "storage_status": "ready",
                "machine_manifest": {
                    "version": "v1",
                    "root_disk_key": "rootdisk",
                    "disks": [
                        {
                            "disk_key": "rootdisk",
                            "disk_role": "root",
                            "format": "qcow2",
                            "size_bytes": 42949672960
                        },
                        {
                            "disk_key": "data-1",
                            "disk_role": "data",
                            "format": "qcow2",
                            "size_bytes": 214748364800
                        }
                    ]
                },
                "disks": [
                    {"disk_key": "rootdisk", "disk_role": "root"},
                    {"disk_key": "data-1", "disk_role": "data"}
                ]
            })
        )
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "exported-root-vm",
                "k8s_component_name": "exported-root-vm",
                "asset_id": asset.ID,
                "image_name": asset.name
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new-exported-root",
            service_alias="gr123462",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new-exported-root", "service_alias": "gr123462"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.app_service.create_vm_run_app",
                    return_value=(200, "创建成功", new_service),
                    create=True) as create_vm_run_app_mock, \
                mock.patch(
                    "console.views.app_create.vm_run.group_service.add_service_to_group",
                    return_value=(200, "success")), \
                mock.patch(
                    "console.views.app_create.vm_run.volume_service.add_service_volume"
                ) as add_volume_mock, \
                mock.patch(
                    "console.views.app_create.vm_run.vms.sync_vm_export_asset_record",
                    side_effect=lambda current_asset, region_name, tenant_name: current_asset), \
                mock.patch(
                    "console.views.app_create.vm_run.vms.resolve_vm_export_restore_plan",
                    return_value={
                        "boot_source_format": "disk",
                        "disk_layout": [
                            {"disk_key": "rootdisk", "disk_role": "root", "boot_order": 1, "boot": True},
                            {"disk_key": "data-1", "disk_role": "data", "boot_order": 2, "boot": False}
                        ],
                        "disk_imports": [
                            {"volume_name": "disk", "disk_key": "rootdisk", "disk_name": "rootdisk", "image_url": "https://signed/rootdisk.qcow2", "format": "qcow2"},
                            {"volume_name": "data-1", "disk_key": "data-1", "disk_name": "data-1", "image_url": "https://signed/data-1.qcow2", "format": "qcow2"}
                        ]
                    }):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        _, create_args, _ = create_vm_run_app_mock.mock_calls[0]
        self.assertEqual("tenant-ns:exported-root", create_args[5])
        self.assertEqual("https://signed/rootdisk.qcow2", create_args[8])
        disk_imports = json.loads(ComponentK8sAttributes.objects.get(
            component_id="service-new-exported-root",
            name="vm_disk_imports"
        ).attribute_value)
        self.assertEqual("https://signed/rootdisk.qcow2", disk_imports["disk"]["image_url"])
        self.assertEqual("https://signed/data-1.qcow2", disk_imports["data-1"]["image_url"])
        add_volume_mock.assert_called_once()
        _, _, volume_path, volume_type, volume_name = add_volume_mock.call_args[0][:5]
        self.assertEqual("/disk", volume_path)
        self.assertEqual("vm-file", volume_type)
        self.assertEqual("data-1", volume_name)
