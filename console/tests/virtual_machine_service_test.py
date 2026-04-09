import collections
import json
import os
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
sys.modules.setdefault("openapi_client", ModuleType("openapi_client"))

import django

django.setup()

from django.test import TestCase

from console.models.main import ComponentK8sAttributes
from console.repositories.virtual_machine import vm_repo
from console.services.virtual_machine import vms
from www.models.main import VirtualMachineImage


class VirtualMachineServiceTests(TestCase):

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
            image_url="demo/source-image"
        )

        result = vms.clone_vm_image("tenant-a", source.name, "target-image")

        self.assertIsNotNone(result)
        self.assertEqual("target-image", result.name)
        self.assertEqual(source.image_url, result.image_url)
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

    def test_save_vm_runtime_config_preserves_non_vm_envs_and_refreshes_vm_extension_keys(self):
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="env",
            save_type="json",
            attribute_value=json.dumps([
                {"name": "KEEP_ME", "value": "1"},
                {"name": "ES_VM_GPU_ENABLED", "value": "stale"},
                {"name": "ES_VM_FIXED_IP", "value": "10.0.0.1/24"}
            ])
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
                "fixed_ip": "10.250.250.10/24"
            }
        )

        attr = ComponentK8sAttributes.objects.get(component_id="service-a", name="env")
        envs = {item["name"]: item["value"] for item in json.loads(attr.attribute_value)}

        self.assertEqual("1", envs["KEEP_ME"])
        self.assertEqual("fixed", envs["ES_VM_NETWORK_MODE"])
        self.assertEqual("default/bridge-net", envs["ES_VM_NETWORK_NAME"])
        self.assertEqual("10.250.250.10/24", envs["ES_VM_FIXED_IP"])
        self.assertEqual("true", envs["ES_VM_GPU_ENABLED"])
        self.assertEqual("[\"gpu.example.com/A10\"]", envs["ES_VM_GPU_RESOURCES"])
        self.assertEqual("true", envs["ES_VM_USB_ENABLED"])
        self.assertEqual("[\"kubevirt.io/usb-a\"]", envs["ES_VM_USB_RESOURCES"])

    def test_save_vm_runtime_config_removes_disabled_vm_extension_keys(self):
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="env",
            save_type="json",
            attribute_value=json.dumps([
                {"name": "KEEP_ME", "value": "1"},
                {"name": "ES_VM_NETWORK_MODE", "value": "fixed"},
                {"name": "ES_VM_NETWORK_NAME", "value": "default/bridge-net"},
                {"name": "ES_VM_FIXED_IP", "value": "10.250.250.10/24"},
                {"name": "ES_VM_GPU_ENABLED", "value": "true"},
                {"name": "ES_VM_GPU_RESOURCES", "value": "[\"gpu.example.com/A10\"]"}
            ])
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

        attr = ComponentK8sAttributes.objects.get(component_id="service-a", name="env")
        envs = {item["name"]: item["value"] for item in json.loads(attr.attribute_value)}

        self.assertEqual({"KEEP_ME", "ES_VM_NETWORK_MODE"}, set(envs.keys()))
        self.assertEqual("1", envs["KEEP_ME"])
        self.assertEqual("random", envs["ES_VM_NETWORK_MODE"])

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
