# capability_id: rainbond-console.vm-export.asset-ready-storage-status
# capability_id: rainbond-console.vm-run.vm-export-ignore-stale-boot-mode
# capability_id: rainbond-console.vm-disks.container-disk-cdrom
import collections
import json
import os
from types import ModuleType, SimpleNamespace
import unittest
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

from console.models.main import ComponentK8sAttributes
from console.repositories.virtual_machine import vm_repo
from console.services.virtual_machine import vms
from www.models.main import VirtualMachineImage


class VMCreateFlowRegressionTests(TestCase):

    def test_get_vm_capabilities_returns_region_payload(self):
        expected = {
            "chunk_upload_supported": True,
            "gpu_supported": True,
        }

        with mock.patch("console.services.virtual_machine.region_api.get_vm_capabilities",
                        return_value=(None, {"bean": expected})):
            result = vms.get_vm_capabilities("demo-region", "demo-team")

        self.assertEqual(expected, result)

    # capability_id: console.virtual-machine.platform-runtime-guard
    def test_ensure_vm_platform_running_delegates_to_platform_plugin_guard(self):
        with mock.patch(
                "console.services.platform_plugin_service.platform_plugin_service.ensure_vm_plugin_running"
        ) as ensure_guard:
            vms.ensure_vm_platform_running("eid", "demo-region")

        ensure_guard.assert_called_once_with("eid", "demo-region")

    def test_delete_vm_image_by_image_url_preserves_shared_image_records(self):
        VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="image-a",
            image_url="demo/shared-image"
        )
        VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="image-b",
            image_url="demo/shared-image"
        )

        deleted = vm_repo.delete_vm_image_by_image_url("tenant-a", "demo/shared-image")

        self.assertEqual((0, {}), deleted)
        self.assertEqual(2, VirtualMachineImage.objects.filter(tenant_id="tenant-a").count())

    def test_save_vm_runtime_config_creates_vm_runtime_attrs_without_touching_other_k8s_attrs(self):
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="labels",
            save_type="json",
            attribute_value=json.dumps({"app": "demo"})
        )

        vms.save_vm_runtime_config(
            "tenant-a",
            "service-a",
            {
                "gpu_enabled": True,
                "gpu_resources": ["gpu.example.com/A10"],
                "usb_enabled": True,
                "usb_resources": ["kubevirt.io/usb-a"],
                "asset_id": 18,
                "clone_source_id": 7,
                "boot_mode": "uefi"
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertEqual(json.dumps({"app": "demo"}), attrs["labels"])
        self.assertNotIn("vm_network_mode", attrs)
        self.assertNotIn("vm_network_name", attrs)
        self.assertNotIn("vm_fixed_ip", attrs)
        self.assertEqual("true", attrs["vm_gpu_enabled"])
        self.assertEqual("[\"gpu.example.com/A10\"]", attrs["vm_gpu_resources"])
        self.assertEqual("true", attrs["vm_usb_enabled"])
        self.assertEqual("[\"kubevirt.io/usb-a\"]", attrs["vm_usb_resources"])
        self.assertEqual("18", attrs["vm_asset_id"])
        self.assertEqual("7", attrs["vm_asset_clone_source"])
        self.assertEqual("uefi", attrs["vm_boot_mode"])

    def test_save_vm_runtime_config_ignores_removed_network_fields(self):
        vms.save_vm_runtime_config(
            "tenant-a",
            "service-a",
            {
                "network_mode": "fixed",
                "network_name": "",
                "fixed_ip": "10.42.124.90/24"
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertNotIn("vm_network_mode", attrs)
        self.assertNotIn("vm_network_name", attrs)
        self.assertNotIn("vm_fixed_ip", attrs)

    def test_save_vm_runtime_config_removes_disabled_vm_extension_keys(self):
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="labels",
            save_type="json",
            attribute_value=json.dumps({"app": "demo"})
        )
        for name, value in (
            ("vm_network_mode", "fixed"),
            ("vm_network_name", "default/bridge-net"),
            ("vm_fixed_ip", "10.250.250.10/24"),
            ("vm_gpu_enabled", "true"),
            ("vm_gpu_resources", json.dumps(["gpu.example.com/A10"])),
            ("vm_usb_enabled", "true"),
            ("vm_usb_resources", json.dumps(["kubevirt.io/usb-a"])),
            ("vm_asset_id", "18"),
            ("vm_asset_clone_source", "7"),
            ("vm_boot_mode", "uefi"),
        ):
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-a",
                component_id="service-a",
                name=name,
                save_type="string",
                attribute_value=value
            )

        vms.save_vm_runtime_config(
            "tenant-a",
            "service-a",
            {
                "gpu_enabled": False,
                "gpu_resources": [],
                "usb_enabled": False,
                "usb_resources": [],
                "asset_id": "",
                "clone_source_id": "",
                "boot_mode": ""
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertEqual({"labels"}, set(attrs.keys()))
        self.assertEqual(json.dumps({"app": "demo"}), attrs["labels"])

    def test_validate_vm_runtime_config_ignores_removed_network_fields(self):
        vms.validate_vm_runtime_config({
            "network_mode": "fixed",
            "network_name": "",
            "fixed_ip": "10.250.250.10/24"
        })

    def test_validate_vm_runtime_config_requires_gpu_resources_when_enabled(self):
        with self.assertRaises(ValueError):
            vms.validate_vm_runtime_config({
                "gpu_enabled": True,
                "gpu_resources": []
            })

    def test_validate_vm_runtime_config_requires_usb_resources_when_enabled(self):
        with self.assertRaises(ValueError):
            vms.validate_vm_runtime_config({
                "usb_enabled": True,
                "usb_resources": []
            })

    def test_is_vm_asset_ready_requires_ready_status_and_image_url(self):
        ready_asset = SimpleNamespace(status="ready", image_url="demo/image")
        exporting_asset = SimpleNamespace(status="exporting", image_url="")

        self.assertTrue(vms.is_vm_asset_ready(ready_asset))
        self.assertFalse(vms.is_vm_asset_ready(exporting_asset))


class VMCreateFlowRegressionUnitTests(unittest.TestCase):

    def test_build_initial_vm_disk_layout_for_iso_keeps_installer_first(self):
        layout = vms.build_initial_vm_disk_layout(boot_source_format="iso")

        self.assertEqual(2, len(layout))
        self.assertEqual("installer_media", layout[0]["source_kind"])
        self.assertEqual("vmimage", layout[0]["disk_key"])
        self.assertTrue(layout[0]["boot"])
        self.assertEqual("root", layout[1]["disk_role"])
        self.assertEqual("disk", layout[1]["disk_key"])

    def test_build_initial_vm_disk_layout_for_qcow2_keeps_root_only(self):
        layout = vms.build_initial_vm_disk_layout(boot_source_format="qcow2")

        self.assertEqual(1, len(layout))
        self.assertEqual("disk", layout[0]["disk_key"])
        self.assertEqual("root", layout[0]["disk_role"])
        self.assertTrue(layout[0]["boot"])

    def test_build_vm_volume_disk_items_recognizes_indexed_disk_paths_as_disk_device(self):
        items = vms._build_vm_volume_disk_items([{
            "ID": 2,
            "volume_name": "data-1",
            "volume_path": "/disk-1",
            "volume_type": "nfs-storage",
            "volume_capacity": 20,
            "status": "mounted"
        }])

        self.assertEqual(1, len(items))
        self.assertEqual("disk", items[0]["device_type"])

    def test_list_vm_disks_auto_exposes_installer_for_legacy_iso_vm_without_layout(self):
        service = SimpleNamespace(service_id="service-a", extend_method="vm", tenant_id="tenant-a", image="demo/image")
        volumes = [{
            "ID": 1,
            "volume_name": "disk",
            "volume_path": "/disk",
            "volume_type": "vm-file",
            "volume_capacity": 40,
            "status": "mounted"
        }]

        with mock.patch.object(vms, "get_vm_runtime_config", return_value={
            "asset_id": None,
            "asset_clone_source": "",
            "boot_mode": "",
            "disk_layout": [],
            "network_mode": "random",
            "network_name": "",
            "fixed_ip": "",
            "gateway": "",
            "dns_servers": "",
            "os_family": "linux",
            "os_name": "Ubuntu 22.04.5 LTS",
            "gpu_enabled": False,
            "gpu_resources": [],
            "gpu_count": 0,
            "usb_enabled": False,
            "usb_resources": [],
            "boot_source_format": "iso"
        }), mock.patch.object(vms, "get_vm_asset_for_service", return_value=None):
            disks = vms.list_vm_disks(service, volumes)

        self.assertEqual(2, len(disks))
        self.assertEqual("installer_media", disks[0]["source_kind"])
        self.assertEqual("disk", disks[1]["disk_key"])

    def test_list_vm_disks_keeps_installer_removed_when_layout_persisted_without_it(self):
        service = SimpleNamespace(service_id="service-a", extend_method="vm", tenant_id="tenant-a", image="demo/image")
        volumes = [{
            "ID": 1,
            "volume_name": "disk",
            "volume_path": "/disk",
            "volume_type": "vm-file",
            "volume_capacity": 40,
            "status": "mounted"
        }]

        with mock.patch.object(vms, "get_vm_runtime_config", return_value={
            "asset_id": None,
            "asset_clone_source": "",
            "boot_mode": "",
            "disk_layout": [{
                "disk_key": "disk",
                "disk_role": "root",
                "device_type": "disk",
                "source_kind": "volume",
                "order_index": 0,
                "boot": True
            }],
            "network_mode": "random",
            "network_name": "",
            "fixed_ip": "",
            "gateway": "",
            "dns_servers": "",
            "os_family": "linux",
            "os_name": "Ubuntu 22.04.5 LTS",
            "gpu_enabled": False,
            "gpu_resources": [],
            "gpu_count": 0,
            "usb_enabled": False,
            "usb_resources": [],
            "boot_source_format": "iso"
        }), mock.patch.object(vms, "get_vm_asset_for_service", return_value=None):
            disks = vms.list_vm_disks(service, volumes)

        self.assertEqual(1, len(disks))
        self.assertEqual("disk", disks[0]["disk_key"])

    def test_validate_vm_disk_layout_rejects_removing_volume_backed_disk(self):
        service = SimpleNamespace(service_id="service-a", extend_method="vm", tenant_id="tenant-a", image="demo/image")
        volumes = [{
            "ID": 1,
            "volume_name": "disk",
            "volume_path": "/disk",
            "volume_type": "vm-file",
            "volume_capacity": 40,
            "status": "mounted"
        }]

        with mock.patch.object(vms, "get_vm_runtime_config", return_value={
            "asset_id": None,
            "asset_clone_source": "",
            "boot_mode": "",
            "disk_layout": [],
            "network_mode": "random",
            "network_name": "",
            "fixed_ip": "",
            "gateway": "",
            "dns_servers": "",
            "os_family": "linux",
            "os_name": "Ubuntu 22.04.5 LTS",
            "gpu_enabled": False,
            "gpu_resources": [],
            "gpu_count": 0,
            "usb_enabled": False,
            "usb_resources": [],
            "boot_source_format": "iso"
        }), mock.patch.object(vms, "get_vm_asset_for_service", return_value=None):
            with self.assertRaises(ValueError):
                vms.validate_vm_disk_layout(service, volumes, [{
                    "disk_key": "vmimage",
                    "disk_role": "installer",
                    "device_type": "cdrom",
                    "source_kind": "installer_media",
                    "order_index": 0
                }])

    def test_validate_vm_disk_layout_accepts_container_disk_cdrom(self):
        service = SimpleNamespace(service_id="service-a", extend_method="vm", tenant_id="tenant-a", image="demo/image")
        volumes = [{
            "ID": 1,
            "volume_name": "disk",
            "volume_path": "/disk",
            "volume_type": "vm-file",
            "volume_capacity": 40,
            "status": "mounted"
        }]

        with mock.patch.object(vms, "get_vm_runtime_config", return_value={
            "asset_id": None,
            "asset_clone_source": "",
            "boot_mode": "",
            "disk_layout": [],
            "os_name": "Windows Server 2022",
            "gpu_enabled": False,
            "gpu_resources": [],
            "gpu_count": 0,
            "usb_enabled": False,
            "usb_resources": [],
            "boot_source_format": "qcow2"
        }), mock.patch.object(vms, "get_vm_asset_for_service", return_value=None):
            normalized = vms.validate_vm_disk_layout(service, volumes, [{
                "disk_key": "disk",
                "disk_role": "root",
                "device_type": "disk",
                "source_kind": "volume",
                "order_index": 0
            }, {
                "disk_key": "driver-media",
                "disk_name": "driver-media",
                "disk_role": "data",
                "device_type": "cdrom",
                "source_kind": "container_disk",
                "image": "registry.example.com/team/windows-driver:virtio",
                "order_index": 1
            }])

        self.assertEqual("container_disk", normalized[1]["source_kind"])
        self.assertEqual("cdrom", normalized[1]["device_type"])
        self.assertEqual("registry.example.com/team/windows-driver:virtio", normalized[1]["image"])

    def test_validate_vm_disk_layout_rejects_container_disk_without_image(self):
        service = SimpleNamespace(service_id="service-a", extend_method="vm", tenant_id="tenant-a", image="demo/image")
        volumes = [{
            "ID": 1,
            "volume_name": "disk",
            "volume_path": "/disk",
            "volume_type": "vm-file",
            "volume_capacity": 40,
            "status": "mounted"
        }]

        with mock.patch.object(vms, "get_vm_runtime_config", return_value={
            "asset_id": None,
            "asset_clone_source": "",
            "boot_mode": "",
            "disk_layout": [],
            "os_name": "Windows Server 2022",
            "gpu_enabled": False,
            "gpu_resources": [],
            "gpu_count": 0,
            "usb_enabled": False,
            "usb_resources": [],
            "boot_source_format": "qcow2"
        }), mock.patch.object(vms, "get_vm_asset_for_service", return_value=None):
            with self.assertRaises(ValueError):
                vms.validate_vm_disk_layout(service, volumes, [{
                    "disk_key": "disk",
                    "disk_role": "root",
                    "device_type": "disk",
                    "source_kind": "volume",
                    "order_index": 0
                }, {
                    "disk_key": "driver-media",
                    "disk_role": "data",
                    "device_type": "cdrom",
                    "source_kind": "container_disk",
                    "image": "",
                    "order_index": 1
                }])

    def test_save_vm_runtime_config_does_not_persist_removed_network_fields(self):
        with mock.patch("console.services.virtual_machine.k8s_attribute_repo.get_by_component_id", return_value=[]), \
                mock.patch.object(vms, "_persist_managed_k8s_attribute") as persist_attr:
            vms.save_vm_runtime_config(
                "tenant-a",
                "service-a",
                {
                    "network_mode": "fixed",
                    "network_name": "",
                    "fixed_ip": "10.42.124.90/24"
                },
                sync_context={"skip": True}
            )

        persisted = {
            call.args[2]: call.args[4]
            for call in persist_attr.call_args_list
        }

        self.assertNotIn("vm_network_mode", persisted)
        self.assertNotIn("vm_network_name", persisted)
        self.assertNotIn("vm_fixed_ip", persisted)

    def test_resolve_vm_boot_mode_prefers_asset_metadata_when_request_omits_it(self):
        mode = vms.resolve_vm_boot_mode(
            requested_boot_mode="",
            asset=SimpleNamespace(boot_mode="uefi", os_name="Windows 10", name="win10"),
            runtime_config={"os_family": "windows"},
            image_name="win10"
        )

        self.assertEqual("uefi", mode)

    def test_resolve_vm_boot_mode_defaults_windows_disk_source_to_uefi(self):
        mode = vms.resolve_vm_boot_mode(
            requested_boot_mode="",
            runtime_config={"os_family": "windows"},
            image_name="win1021h1",
            boot_source_format="disk"
        )

        self.assertEqual("uefi", mode)

    def test_resolve_vm_boot_mode_does_not_infer_windows_from_image_name_alone(self):
        mode = vms.resolve_vm_boot_mode(
            requested_boot_mode="",
            runtime_config={},
            image_name="win1021h1",
            boot_source_format="disk"
        )

        self.assertEqual("", mode)

    def test_resolve_vm_boot_mode_does_not_force_uefi_for_windows_iso(self):
        mode = vms.resolve_vm_boot_mode(
            requested_boot_mode="",
            runtime_config={"os_family": "windows"},
            image_name="windows-installer",
            boot_source_format="iso"
        )

        self.assertEqual("", mode)

    def test_resolve_vm_boot_mode_ignores_asset_boot_mode_for_windows_iso(self):
        mode = vms.resolve_vm_boot_mode(
            requested_boot_mode="",
            asset=SimpleNamespace(boot_mode="uefi", os_name="Windows Server", name="windows-installer"),
            runtime_config={"os_family": "windows"},
            image_name="windows-installer",
            boot_source_format="iso"
        )

        self.assertEqual("", mode)

    def test_infer_vm_boot_source_format_keeps_legacy_upload_asset_unspecified_when_unknown(self):
        fmt = vms.infer_vm_boot_source_format(
            asset=SimpleNamespace(
                source_type="upload",
                format="",
                source_uri="/grdata/package_build/temp/events/evt-1",
                image_url="tenant-ns:windows-installer",
                name="windows-installer"
            ),
            image_name="windows-installer"
        )

        self.assertEqual("", fmt)

    def test_build_vm_root_disk_import_accepts_registry_root_disk_from_template_payload(self):
        root_import = vms._build_vm_root_disk_import(
            template_payload={
                "disk_layout": [{
                    "disk_key": "disk",
                    "disk_name": "system-disk",
                    "disk_role": "root",
                    "image_url": "docker://registry.example.com/team/windows-root:v1",
                    "source_uri": "registry.example.com/team/windows-root:v1",
                    "source_type": "registry",
                    "format": "qcow2",
                    "checksum": "sha256:test",
                }]
            },
            image_url="registry.example.com/team/windows-root:v1",
            source_uri="registry.example.com/team/windows-root:v1",
        )

        self.assertEqual(
            {
                "volume_name": "disk",
                "disk_key": "disk",
                "disk_name": "system-disk",
                "image_url": "docker://registry.example.com/team/windows-root:v1",
                "source_uri": "registry.example.com/team/windows-root:v1",
                "format": "qcow2",
                "checksum": "sha256:test",
                "source_type": "registry",
            },
            root_import,
        )

    def test_build_vm_root_disk_import_accepts_registry_root_disk_from_asset_metadata(self):
        asset = SimpleNamespace(
            image_url="docker://registry.example.com/team/windows-root:v1",
            source_uri="registry.example.com/team/windows-root:v1",
            extra_json=json.dumps({
                "disks": [{
                    "disk_key": "disk",
                    "disk_name": "system-disk",
                    "disk_role": "root",
                    "download_url": "docker://registry.example.com/team/windows-root:v1",
                    "source_uri": "registry.example.com/team/windows-root:v1",
                    "source_type": "registry",
                    "format": "qcow2",
                    "checksum": "sha256:test",
                }]
            }),
        )

        root_import = vms._build_vm_root_disk_import(asset=asset)

        self.assertEqual("registry", root_import["source_type"])
        self.assertEqual("docker://registry.example.com/team/windows-root:v1", root_import["image_url"])
        self.assertEqual("qcow2", root_import["format"])

    def test_build_vm_root_disk_import_accepts_registry_root_disk_without_docker_scheme(self):
        root_import = vms._build_vm_root_disk_import(
            template_payload={
                "disk_layout": [{
                    "disk_key": "disk",
                    "disk_name": "system-disk",
                    "disk_role": "root",
                    "image_url": "registry.example.com/team/windows-root:v1",
                    "source_uri": "vm-publish/windows-root",
                    "source_type": "registry",
                    "format": "qcow2",
                }]
            }
        )

        self.assertEqual("registry", root_import["source_type"])
        self.assertEqual("registry.example.com/team/windows-root:v1", root_import["image_url"])

    def test_build_vm_root_disk_import_reads_vm_block_disk_layout(self):
        root_import = vms._build_vm_root_disk_import(
            template_payload={
                "vm": {
                    "disk_layout": [{
                        "disk_key": "disk",
                        "disk_name": "system-disk",
                        "disk_role": "root",
                        "image": "registry.example.com/team/windows-root:v2",
                        "source_uri": "vm-publish/windows-root",
                        "source_type": "registry",
                        "format": "qcow2",
                    }]
                }
            }
        )

        self.assertEqual("registry", root_import["source_type"])
        self.assertEqual("registry.example.com/team/windows-root:v2", root_import["image_url"])
