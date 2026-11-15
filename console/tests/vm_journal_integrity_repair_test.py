# capability_id: console.vm-restore.journal-integrity
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from unittest import TestCase

from console.tests import vm_restore_command_worker_test as wire
from console.tests import vm_restore_command_process_restart_test as restart
from console.services.vm_restore_journal import JournalConflict
from console.utils.vm_restore_config import restore_config_hash


class VMJournalIntegrityRepairTests(TestCase):
    setUp = wire.VMRestoreCommandWorkerTests.setUp
    close_database = wire.VMRestoreCommandWorkerTests.close_database
    begin = wire.VMRestoreCommandWorkerTests.begin
    seal = wire.VMRestoreCommandWorkerTests.seal
    restore_operation = wire.VMRestoreCommandWorkerTests.restore_operation
    loopback = wire.VMRestoreCommandWorkerTests.loopback
    process = wire.VMRestoreCommandWorkerTests.process

    def test_local_A_volume_fields_and_membership_cannot_be_replaced_by_a_self_hashed_payload(self):
        op = self.restore_operation()
        manifest = self.journal.read_manifest(self.ctx, 'snapshot-uid-a')
        server = wire.RestoreLoopback(manifest)
        self.addCleanup(server.close)
        before = self.journal.read_operation(self.ctx, 'restore-a')
        for field in ('storage_class', 'capacity_gib', 'membership'):
            value = server.dto()
            config = value['config_after']
            if field == 'membership':
                config['volumes'].append(copy.deepcopy(value['config_before']['volumes'][1]))
            else:
                config['volumes'][0][field] = 'other-class' if field == 'storage_class' else 99
            value['config_after_hash'] = restore_config_hash(config)
            with self.subTest(field=field), self.assertRaises(JournalConflict):
                self.journal.record_restore_status(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'], op['revision'],
                                                   value, 104)
            self.assertEqual(before, self.journal.read_operation(self.ctx, 'restore-a'))

    def restart_from_file(self, server, expect_conflict=False):
        with tempfile.TemporaryDirectory(prefix='journal-integrity-restart-') as directory:
            database = Path(directory) / 'journal.sqlite3'
            raw = sqlite3.connect(database)
            self.database.connection.backup(raw)
            raw.close()
            before = len([call for call in server.calls if call[0] == 'POST'])
            command = [
                sys.executable, '-B', '-c', restart.CHILD,
                str(database), 'http://127.0.0.1:{}'.format(server.server.server_port), 'none', '180'
            ]
            result = subprocess.run(command, text=True, capture_output=True, timeout=15)
            if expect_conflict:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('VM journal conflict', result.stderr)
            else:
                self.assertEqual(result.returncode, 0)
            self.assertEqual(before, len([call for call in server.calls if call[0] == 'POST']))
            with sqlite3.connect(database) as connection:

                def read(name):
                    return json.loads(
                        connection.execute('SELECT attribute_value FROM component_k8s_attributes WHERE name=?',
                                           (name, )).fetchone()[0])

                saved = read('vm_restore_operation_restore-a')
                self.assertEqual(read('vm_restore_active_operation')['operation_id'], 'restore-a')
            self.assertIsNone(saved['region_terminal'])
            return saved

    def test_409_stays_blocked_with_original_request_after_a_real_process_restart(self):
        client, server = self.loopback()
        self.process(client)
        server.mode = 'conflict'
        conflicted = self.process(client, 105)
        saved = self.restart_from_file(server)
        self.assertEqual(saved['rpc']['pending']['state'], 'conflict')
        self.assertEqual(saved['rpc']['pending']['request'], conflicted['rpc']['pending']['request'])
        self.assertEqual(saved['rpc']['completed'], ['prepare'])

    def test_stale_control_revision_is_refused_after_a_real_process_restart(self):
        client, server = self.loopback()
        saved = self.process(client)
        original = server.dto
        server.dto = lambda applied=False: {
            **original(applied), 'control_revision': saved['rpc']['observation']['control_revision'] - 1
        }
        after = self.restart_from_file(server, expect_conflict=True)
        self.assertEqual(after['rpc']['observation'], saved['rpc']['observation'])

    def test_self_hashed_B_as_A_is_refused_after_a_real_process_restart(self):
        client, server = self.loopback()
        saved = self.process(client)
        original = server.dto

        def changed(applied=False):
            value = original(applied)
            value['config_after'] = copy.deepcopy(value['config_before'])
            value['config_after_hash'] = restore_config_hash(value['config_after'])
            return value

        server.dto = changed
        after = self.restart_from_file(server, expect_conflict=True)
        self.assertEqual(after['rpc']['observation'], saved['rpc']['observation'])
