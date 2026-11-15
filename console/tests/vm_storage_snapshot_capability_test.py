# -*- coding: utf-8 -*-
# capability_id: console.vm-storage.snapshot-capability
from types import SimpleNamespace
from unittest import TestCase, mock

import django

django.setup()

from console.services.app_config.volume_service import volume_service  # noqa: E402


class VMStorageSnapshotCapabilityTestCase(TestCase):
    def test_creation_options_preserve_authority_and_drop_private_storage_configuration(self):
        options = [{
            "volume_type": "pool-a",
            "name_show": "Data storage",
            "enable": True,
            "storage_class_detail": {
                "parameters": {
                    "private": "must-not-leave-console"
                }
            },
            "snapshot_capability": {
                "supported": False,
                "status": "unsupported",
                "reason_code": "snapshot_class_missing",
                "message": "upstream-raw",
                "driver": "private-driver"
            }
        }, {
            "volume_type": "pool-b",
            "name_show": "Other storage",
            "snapshot_capability": {
                "supported": True,
                "status": "supported",
                "reason_code": "ready"
            }
        }]
        with mock.patch.object(volume_service, "get_region_volume_options", return_value=options):
            result = volume_service.get_vm_persistent_storage_options(SimpleNamespace(), "region-a")
        self.assertFalse(result[0]["snapshot_capability"]["supported"])
        self.assertEqual(result[0]["snapshot_capability"]["status"], "unsupported")
        self.assertEqual(result[1]["snapshot_capability"]["status"], "supported")
        self.assertNotIn("storage_class_detail", result[0])
        self.assertNotIn("driver", result[0]["snapshot_capability"])
        self.assertNotIn("message", result[0]["snapshot_capability"])
        self.assertIn("storage_class_detail", options[0], "projection must not mutate the shared Region object")

    def test_missing_or_inconsistent_evidence_is_unknown_without_removing_the_storage(self):
        for capability in [
                None, {}, {
                    "supported": True,
                    "status": "unsupported"
                }, {
                    "supported": "true",
                    "status": "supported"
                }, {
                    "supported": True,
                    "status": "future"
                }
        ]:
            with self.subTest(capability=capability), mock.patch.object(volume_service,
                                                                        "get_region_volume_options",
                                                                        return_value=[{
                                                                            "volume_type": "nfs-or-ceph-name-is-not-evidence",
                                                                            "snapshot_capability": capability
                                                                        }]):
                result = volume_service.get_vm_persistent_storage_options(SimpleNamespace(), "region-a")
            self.assertEqual(len(result), 1)
            self.assertIs(result[0]["snapshot_capability"]["supported"], False)
            self.assertEqual(result[0]["snapshot_capability"]["status"], "unknown")

    def test_failed_region_envelope_is_not_an_empty_or_successful_storage_result(self):
        for body in [{
                "code": 503,
                "list": []
        }, {
                "code": 500,
                "list": [{
                    "volume_type": "pool"
                }]
        }, {
                "code": "200",
                "list": []
        }, {
                "list": None
        }]:
            with self.subTest(body=body), mock.patch("console.services.app_config.volume_service.region_api.get_volume_options",
                                                     return_value=body), mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(ValueError):
                    volume_service.get_vm_persistent_storage_options(SimpleNamespace(tenant_name="team-a"), "region-a")
