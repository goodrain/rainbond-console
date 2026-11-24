# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest import TestCase, mock

from console.tests import vm_manage_view_test  # noqa: F401
from console.services.virtual_machine import vms


# capability_id: console.vm.disk-expansion-runtime-projection
class VMDiskExpansionProjectionTests(TestCase):
    def test_disk_layout_keeps_storage_observations_including_false_and_zero(self):
        volume = {
            "ID": 42, "volume_name": "data", "volume_path": "/disk", "volume_type": "vm-csi",
            "volume_capacity": 2, "allow_expansion": False, "actual_capacity": 1,
            "requested_capacity": 2, "expansion_status": "unsupported",
            "expansion_message": "StorageClass does not allow expansion", "pvc_count": 0,
        }
        service = SimpleNamespace(extend_method="vm", service_id="vm-id")
        with mock.patch.object(vms, "get_vm_runtime_config", return_value={"disk_layout": []}), \
                mock.patch.object(vms, "get_vm_asset_for_service", return_value=None), \
                mock.patch.object(vms, "_resolve_vm_boot_source_format_for_runtime", return_value="qcow2"):
            disks = vms.list_vm_disks(service, [volume])
        self.assertEqual(len(disks), 1)
        for field in ("allow_expansion", "actual_capacity", "requested_capacity", "expansion_status",
                      "expansion_message", "pvc_count"):
            self.assertEqual(disks[0][field], volume[field])
        self.assertEqual(disks[0]["volume_id"], 42)

    def test_legacy_disk_does_not_invent_observed_capacity_or_support(self):
        disks = vms._build_vm_volume_disk_items([{
            "ID": 42, "volume_name": "data", "volume_path": "/disk", "volume_capacity": 2,
        }])
        self.assertNotIn("allow_expansion", disks[0])
        self.assertNotIn("actual_capacity", disks[0])
        self.assertNotIn("expansion_status", disks[0])
