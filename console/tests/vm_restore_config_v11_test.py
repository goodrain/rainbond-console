# capability_id: console.vm-restore.config-seals-v11
import copy
import json
from pathlib import Path
from unittest import TestCase

from console.tests import vm_snapshot_read_api_test as bootstrap  # noqa: F401
from console.services.vm_restore_journal import JournalConflict, restore_observation
from console.utils.vm_restore_config import restore_config_hash


def go_config_fixture():
    return json.loads((Path(__file__).parent / 'fixtures/vm_restore_config_v11.json').read_text())


def status_fixture():
    return {
        **go_config_fixture(), 'operation_id': 'restore-a',
        'operation_epoch': 'c' * 64,
        'target_vm_uid': 'target-vm-uid',
        'phase': 'prepared',
        'snapshot_uid': 'snapshot-uid-a',
        'source': {
            'snapshot_name': 'snapshot-a',
            'snapshot_uid': 'snapshot-uid-a',
            'content_uid': 'content-uid-a',
            'vm_uid': 'source-vm-uid',
            'core_hash': 'a' * 64,
            'document_hash': 'b' * 64
        },
        'control_revision': 4,
        'binding_generation': 2,
        'operation_binding_generation': 2,
        'fence_owned': True,
        'fence_cleared': False,
        'applied': False,
        'complete': False,
        'config_committed': False,
        'console_acked': False,
        'rollback_acked': False,
        'retryable': False
    }


class VMRestoreConfigV11Tests(TestCase):
    def test_config_hash_matches_actual_go_struct_serialization_and_sorting(self):
        fixture = go_config_fixture()
        for side in ('after', 'before'):
            config = fixture['config_' + side]
            self.assertEqual(restore_config_hash(config), fixture['config_' + side + '_hash'])
            reordered = copy.deepcopy(config)
            reordered['hardware']['disk_layout'].reverse()
            reordered['volumes'].reverse()
            self.assertEqual(restore_config_hash(reordered), fixture['config_' + side + '_hash'])

    def test_actual_sealed_A_and_full_B_and_power_intent_survive_projection(self):
        value = restore_observation(status_fixture(), 'restore-a')
        self.assertTrue(value['source_config_ready'])
        self.assertEqual(value['config_after']['volumes'][0]['access_mode'], 'ReadWriteOnce')
        self.assertEqual(value['config_before']['volumes'][0]['access_mode'], 'ReadWriteMany')
        self.assertEqual(len(value['config_before']['volumes']), 2)
        self.assertTrue(value['resume_required'])
        self.assertEqual(value['source_binding_generation'], 2)

    def test_legacy_missing_A_stays_unready_and_never_substitutes_B(self):
        wire = status_fixture()
        wire.pop('config_after')
        wire['source_config_ready'] = False
        value = restore_observation(wire, 'restore-a')
        self.assertFalse(value['source_config_ready'])
        self.assertIsNone(value.get('config_after'))
        self.assertEqual(value['config_before'], wire['config_before'])

    def test_bad_A_hash_missing_access_mode_and_inconsistent_power_are_refused(self):
        for name in ('bad-hash', 'missing-access', 'power-mismatch'):
            wire = status_fixture()
            if name == 'bad-hash':
                wire['config_after_hash'] = 'f' * 64
            elif name == 'missing-access':
                wire['config_after']['volumes'][0].pop('access_mode')
            else:
                wire['resume_required'] = False
            with self.subTest(case=name), self.assertRaises(JournalConflict):
                restore_observation(wire, 'restore-a')
