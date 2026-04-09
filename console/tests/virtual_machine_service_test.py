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

from console.models.main import ComponentK8sAttributes
from console.repositories.virtual_machine import vm_repo
from console.services.virtual_machine import vms
from www.models.main import VirtualMachineImage


class VirtualMachineServiceTests(TestCase):

    def test_create_vm_image_asset_accepts_extra_metadata(self):
        asset = vms.create_vm_image_asset(
            tenant_id="tenant-a",
            name="uploaded-image",
            image_url="tenant-a:uploaded-image",
            source_type="upload",
            source_uri="/tmp/uploaded-image.qcow2",
            extra={
                "created_from": "vm_run"
            }
        )

        self.assertEqual("uploaded-image", asset.name)
        self.assertEqual({"created_from": "vm_run"}, json.loads(asset.extra_json))

    def test_get_vm_capabilities_returns_region_payload(self):
        expected = {
            "chunk_upload_supported": True,
            "network_modes": ["random", "fixed"],
            "gpu_supported": True,
        }

        with mock.patch("console.services.virtual_machine.region_api.get_vm_capabilities",
                        return_value=(None, {"bean": expected})):
            result = vms.get_vm_capabilities("demo-region", "demo-team")

        self.assertEqual(expected, result)

    def test_get_vm_capabilities_defaults_to_empty_payload(self):
        with mock.patch("console.services.virtual_machine.region_api.get_vm_capabilities",
                        return_value=(None, {})):
            result = vms.get_vm_capabilities("demo-region", "demo-team")

        self.assertEqual({}, result)

    def test_clone_vm_image_creates_logical_copy(self):
        source = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="source-image",
            image_url="demo/source-image",
            source_type="upload",
            source_uri="/tmp/source-image.qcow2",
            arch="amd64",
            os_name="Ubuntu 24.04",
            format="qcow2",
            size_bytes=1024,
            checksum="sha256:demo",
            status="ready",
            build_event_id="event-1",
            boot_mode="uefi",
            storage_backend="local",
            labels_json=json.dumps({"family": "ubuntu"}),
            extra_json=json.dumps({"note": "base-image"})
        )

        result = vms.clone_vm_image("tenant-a", source.name, "target-image")

        self.assertIsNotNone(result)
        self.assertEqual("target-image", result.name)
        self.assertEqual(source.image_url, result.image_url)
        self.assertEqual("clone", result.source_type)
        self.assertEqual(source.ID, result.source_asset_id)
        self.assertEqual("reuse", result.clone_mode)
        self.assertEqual(source.arch, result.arch)
        self.assertEqual(source.os_name, result.os_name)
        self.assertEqual(source.format, result.format)
        self.assertEqual(source.size_bytes, result.size_bytes)
        self.assertEqual(source.checksum, result.checksum)
        self.assertEqual(source.boot_mode, result.boot_mode)
        self.assertEqual(source.storage_backend, result.storage_backend)
        self.assertEqual(source.labels_json, result.labels_json)
        self.assertEqual("ready", result.status)
        self.assertEqual(source.image_url, result.source_uri)
        self.assertEqual({
            "clone_source_id": source.ID,
            "clone_source_name": source.name,
            "note": "base-image"
        }, json.loads(result.extra_json))
        self.assertEqual(2, VirtualMachineImage.objects.filter(tenant_id="tenant-a").count())

    def test_clone_vm_image_returns_none_when_source_missing(self):
        result = vms.clone_vm_image("tenant-a", "missing-image", "target-image")

        self.assertIsNone(result)

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

    def test_list_vm_image_returns_asset_catalog_metadata(self):
        source = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="source-image",
            image_url="demo/source-image",
            source_type="upload",
            source_uri="/tmp/source-image.qcow2",
            arch="amd64",
            os_name="Ubuntu 24.04",
            format="qcow2",
            size_bytes=1024,
            checksum="sha256:demo",
            status="ready",
            labels_json=json.dumps({"family": "ubuntu"}),
            extra_json=json.dumps({"note": "base-image"})
        )
        VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="target-image",
            image_url="demo/source-image",
            source_type="clone",
            source_uri="demo/source-image",
            arch="amd64",
            os_name="Ubuntu 24.04",
            format="qcow2",
            size_bytes=1024,
            checksum="sha256:demo",
            status="ready",
            source_asset_id=source.ID,
            clone_mode="reuse",
            labels_json=json.dumps({"family": "ubuntu"}),
            extra_json=json.dumps({"clone_source_name": "source-image"})
        )

        result = vms.list_vm_image("tenant-a")

        self.assertEqual(2, len(result))
        cloned = next(item for item in result if item["name"] == "target-image")
        self.assertEqual("clone", cloned["source_type"])
        self.assertEqual("qcow2", cloned["format"])
        self.assertEqual(1024, cloned["size_bytes"])
        self.assertEqual("ready", cloned["status"])
        self.assertEqual({"family": "ubuntu"}, cloned["labels"])
        self.assertEqual({"clone_source_name": "source-image"}, cloned["extra"])
        self.assertEqual({
            "id": source.ID,
            "name": source.name
        }, cloned["source_asset"])

    def test_save_vm_runtime_config_preserves_non_vm_attrs_and_refreshes_vm_extension_keys(self):
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="labels",
            save_type="json",
            attribute_value=json.dumps({"app": "demo"})
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_gpu_enabled",
            save_type="string",
            attribute_value="stale"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_fixed_ip",
            save_type="string",
            attribute_value="10.0.0.1/24"
        )

        vms.save_vm_runtime_config(
            "tenant-a",
            "service-a",
            {
                "gpu_enabled": True,
                "gpu_resources": ["gpu.example.com/A10"],
                "usb_enabled": True,
                "usb_resources": ["kubevirt.io/usb-a"],
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": "10.250.250.10/24",
                "asset_id": 18,
                "boot_mode": "uefi"
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertEqual(json.dumps({"app": "demo"}), attrs["labels"])
        self.assertEqual("fixed", attrs["vm_network_mode"])
        self.assertEqual("default/bridge-net", attrs["vm_network_name"])
        self.assertEqual("10.250.250.10/24", attrs["vm_fixed_ip"])
        self.assertEqual("true", attrs["vm_gpu_enabled"])
        self.assertEqual(json.dumps(["gpu.example.com/A10"]), attrs["vm_gpu_resources"])
        self.assertEqual("true", attrs["vm_usb_enabled"])
        self.assertEqual(json.dumps(["kubevirt.io/usb-a"]), attrs["vm_usb_resources"])
        self.assertEqual("18", attrs["vm_asset_id"])
        self.assertEqual("uefi", attrs["vm_boot_mode"])

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
            ("vm_asset_id", "18"),
        ):
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-a",
                component_id="service-a",
                name=name,
                save_type="string",
                attribute_value=value
            )

        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_usb_enabled",
            save_type="string",
            attribute_value="true"
        )

        vms.save_vm_runtime_config(
            "tenant-a",
            "service-a",
            {
                "gpu_enabled": False,
                "gpu_resources": [],
                "usb_enabled": False,
                "usb_resources": [],
                "network_mode": "random",
                "network_name": "",
                "fixed_ip": ""
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertEqual({"labels", "vm_network_mode"}, set(attrs.keys()))
        self.assertEqual(json.dumps({"app": "demo"}), attrs["labels"])
        self.assertEqual("random", attrs["vm_network_mode"])

    def test_get_vm_profile_returns_asset_runtime_and_connections(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="ubuntu-24.04-base",
            image_url="demo/ubuntu-24.04-base",
            source_type="upload",
            source_uri="/tmp/ubuntu-24.04-base.qcow2",
            arch="amd64",
            os_name="Ubuntu 24.04",
            format="qcow2",
            size_bytes=2048,
            checksum="sha256:demo",
            status="ready"
        )
        for name, value in (
            ("vm_asset_id", str(asset.ID)),
            ("vm_network_mode", "fixed"),
            ("vm_network_name", "default/bridge-net"),
            ("vm_fixed_ip", "10.250.250.10/24"),
            ("vm_gpu_enabled", "true"),
            ("vm_gpu_resources", json.dumps(["gpu.example.com/A10"])),
            ("vm_usb_enabled", "true"),
            ("vm_usb_resources", json.dumps(["kubevirt.io/usb-a"])),
        ):
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-a",
                component_id="service-a",
                name=name,
                save_type="string",
                attribute_value=value
            )

        profile = vms.get_vm_profile(
            SimpleNamespace(
                tenant_id="tenant-a",
                service_id="service-a",
                image=asset.image_url,
                extend_method="vm"
            ),
            connections={
                "vnc_url": "http://example.com/vnc",
                "console_url": ""
            }
        )

        self.assertEqual(asset.ID, profile["asset"]["id"])
        self.assertEqual(asset.name, profile["asset"]["name"])
        self.assertEqual("fixed", profile["runtime"]["network_mode"])
        self.assertEqual("default/bridge-net", profile["runtime"]["network_name"])
        self.assertEqual("10.250.250.10/24", profile["runtime"]["fixed_ip"])
        self.assertTrue(profile["runtime"]["gpu_enabled"])
        self.assertEqual(["gpu.example.com/A10"], profile["runtime"]["gpu_resources"])
        self.assertTrue(profile["runtime"]["usb_enabled"])
        self.assertEqual(["kubevirt.io/usb-a"], profile["runtime"]["usb_resources"])
        self.assertEqual("http://example.com/vnc", profile["connections"]["vnc_url"])

    def test_validate_vm_runtime_config_requires_fixed_network_name(self):
        with self.assertRaises(ValueError):
            vms.validate_vm_runtime_config({
                "network_mode": "fixed",
                "network_name": "",
                "fixed_ip": "10.250.250.10/24"
            })

    def test_validate_vm_runtime_config_requires_fixed_ip(self):
        with self.assertRaises(ValueError):
            vms.validate_vm_runtime_config({
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": ""
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
