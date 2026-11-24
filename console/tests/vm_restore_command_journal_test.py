# capability_id: console.vm-restore.command-journal
from unittest import TestCase

from console.tests import vm_restore_journal_test as fixtures
from console.services.vm_restore_journal import JournalConflict, RegionTerminalEvidence


class VMRestoreCommandJournalTests(TestCase):
    setUp = fixtures.VMRestoreJournalTestCase.setUp
    close_database = fixtures.VMRestoreJournalTestCase.close_database
    begin = fixtures.VMRestoreJournalTestCase.begin
    seal = fixtures.VMRestoreJournalTestCase.seal

    def restore_operation(self):
        self.service.extend_method = 'vm'
        self.service.save(update_fields=['extend_method'])
        op, ack = self.seal()
        evidence = RegionTerminalEvidence('tenant-a', 'service-a', 'region-a', 'team-a', 'op-a', 'a' * 64,
                                          op['execution_epoch'], True, True, 'runtime_verified')
        op = self.journal.record_region_terminal(self.ctx, 'op-a', 'worker-a', op['execution_epoch'], op['revision'], evidence,
                                                 102)
        self.journal.release(self.ctx, 'op-a', 'worker-a', op['execution_epoch'], op['revision'], 102)
        op = self.journal.create_operation(self.ctx,
                                           'restore-a',
                                           'request-restore-a',
                                           'restore',
                                           snapshot_uid=ack['snapshot_uid'],
                                           document_hash=ack['manifest_document_hash'],
                                           rollback_config=self.config)
        op = self.journal.claim(self.ctx, 'restore-a', 'worker-a', op['revision'], 103, 30)
        return self.journal.initialize_restore_commands(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'],
                                                        op['revision'], 'previous', 103)

    def test_prepare_intent_is_immutable_and_issued_body_is_committed_before_any_rpc(self):
        op = self.restore_operation()
        self.assertEqual(op['rpc']['pending']['action'], 'prepare')
        body = {
            'snapshot_name': 'snapshot-a',
            'power_after': 'previous',
            'expected_control_revision': 3,
            'expected_binding_generation': 2
        }
        issued = self.journal.issue_restore_command(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'], op['revision'],
                                                    body, 104)
        saved = self.journal.read_operation(self.ctx, 'restore-a')
        self.assertEqual(saved['rpc']['pending']['request'], body)
        self.assertEqual(saved['rpc']['pending']['state'], 'issued')
        self.assertEqual(saved['rpc']['pending']['attempts'], 1)
        self.assertEqual(saved['region_intent']['operation_id'], 'restore-a')
        self.assertEqual(saved['region_intent']['source_vm_uid'], 'vm-uid-a')
        with self.assertRaises(JournalConflict):
            self.journal.initialize_restore_commands(self.ctx, 'restore-a', 'worker-a', issued['execution_epoch'],
                                                     issued['revision'], 'stopped', 105)
        with self.assertRaises(JournalConflict):
            self.journal.issue_restore_command(self.ctx, 'restore-a', 'old-owner', issued['execution_epoch'],
                                               issued['revision'], body, 105)
        public = self.journal.public_operation(self.ctx, 'restore-a')
        self.assertNotIn('request', public.get('command', {}))
        self.assertNotIn('server_epoch', str(public))
        self.assertNotIn('vm-uid-a', str(public))

    def test_unknown_and_conflict_keep_the_same_command_and_never_release_active_pointer(self):
        op = self.restore_operation()
        body = {
            'snapshot_name': 'snapshot-a',
            'power_after': 'previous',
            'expected_control_revision': 0,
            'expected_binding_generation': 0
        }
        op = self.journal.issue_restore_command(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'], op['revision'], body,
                                                104)
        for status, code in [(0, 'vm_restore_outcome_unknown'), (202, 'vm_restore_pending'), (409, 'vm_restore_conflict')]:
            op = self.journal.record_restore_command_error(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'],
                                                           op['revision'], status, code, 105)
            self.assertEqual(op['rpc']['pending']['request'], body)
            self.assertEqual(self.journal.active_operation(self.ctx), 'restore-a')
            self.assertEqual(op['phase'], 'pending')
            self.assertIsNone(op['region_terminal'])
        with self.assertRaises(JournalConflict):
            self.journal.release(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'], op['revision'], 105)
