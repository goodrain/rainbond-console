# capability_id: rainbond-console.vm-disks.iso-installer-compat
import collections
import os
import unittest
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

from console.services.virtual_machine import vms


class VMInstallerMediaCompatUnitTests(unittest.TestCase):

    def test_get_vm_runtime_config_includes_boot_source_format(self):
        attrs = [
            SimpleNamespace(name="vm_boot_source_format", attribute_value="iso"),
            SimpleNamespace(name="vm_network_mode", attribute_value="random"),
        ]

        with mock.patch("console.services.virtual_machine.k8s_attribute_repo.get_by_component_id", return_value=attrs):
            runtime = vms.get_vm_runtime_config("service-a")

        self.assertEqual("iso", runtime["boot_source_format"])

    def test_list_vm_disks_falls_back_to_asset_format_for_legacy_iso_vm_without_runtime_hint(self):
        service = SimpleNamespace(service_id="service-a", extend_method="vm", tenant_id="tenant-a", image="demo/image")
        volumes = [{
            "ID": 1,
            "volume_name": "disk",
            "volume_path": "/disk",
            "volume_type": "vm-file",
            "volume_capacity": 40,
            "status": "mounted"
        }]
        asset = SimpleNamespace(
            format="iso",
            source_uri="/tmp/windows-server.iso",
            image_url="tenant-ns:windows-installer",
            name="windows-installer",
            os_name="Windows Server"
        )

        with mock.patch.object(vms, "get_vm_runtime_config", return_value={
            "asset_id": 9,
            "asset_clone_source": "",
            "boot_mode": "",
            "boot_source_format": "",
            "disk_layout": [],
            "network_mode": "random",
            "network_name": "",
            "fixed_ip": "",
            "gateway": "",
            "dns_servers": "",
            "os_family": "windows",
            "os_name": "Windows Server",
            "gpu_enabled": False,
            "gpu_resources": [],
            "gpu_count": 0,
            "usb_enabled": False,
            "usb_resources": [],
        }), mock.patch.object(vms, "get_vm_asset_for_service", return_value=asset):
            disks = vms.list_vm_disks(service, volumes)

        self.assertEqual(2, len(disks))
        self.assertEqual("installer_media", disks[0]["source_kind"])
        self.assertEqual("disk", disks[1]["disk_key"])
