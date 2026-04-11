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


class VMCreateFlowRegressionTests(TestCase):

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
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": "10.250.250.10/24",
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
        self.assertEqual("fixed", attrs["vm_network_mode"])
        self.assertEqual("default/bridge-net", attrs["vm_network_name"])
        self.assertEqual("10.250.250.10/24", attrs["vm_fixed_ip"])
        self.assertEqual("true", attrs["vm_gpu_enabled"])
        self.assertEqual("[\"gpu.example.com/A10\"]", attrs["vm_gpu_resources"])
        self.assertEqual("true", attrs["vm_usb_enabled"])
        self.assertEqual("[\"kubevirt.io/usb-a\"]", attrs["vm_usb_resources"])
        self.assertEqual("18", attrs["vm_asset_id"])
        self.assertEqual("7", attrs["vm_asset_clone_source"])
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
                "network_mode": "random",
                "network_name": "",
                "fixed_ip": "",
                "asset_id": "",
                "clone_source_id": "",
                "boot_mode": ""
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertEqual({"labels", "vm_network_mode"}, set(attrs.keys()))
        self.assertEqual(json.dumps({"app": "demo"}), attrs["labels"])
        self.assertEqual("random", attrs["vm_network_mode"])

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

    def test_is_vm_asset_ready_requires_ready_status_and_image_url(self):
        ready_asset = SimpleNamespace(status="ready", image_url="demo/image")
        exporting_asset = SimpleNamespace(status="exporting", image_url="")

        self.assertTrue(vms.is_vm_asset_ready(ready_asset))
        self.assertFalse(vms.is_vm_asset_ready(exporting_asset))
