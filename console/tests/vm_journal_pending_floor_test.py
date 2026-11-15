# capability_id: console.vm-restore.pending-read-floor
import copy
import json
from unittest import TestCase, mock

from console.tests import vm_restore_command_worker_test as wire
from console.models.main import ComponentK8sAttributes
from console.services.vm_restore_journal import JournalConflict
from console.services.vm_restore_worker import VMJobRunner


class PendingReadFloorTests(TestCase):
    setUp = wire.VMRestoreCommandWorkerTests.setUp
    close_database = wire.VMRestoreCommandWorkerTests.close_database
    begin = wire.VMRestoreCommandWorkerTests.begin
    seal = wire.VMRestoreCommandWorkerTests.seal
    restore_operation = wire.VMRestoreCommandWorkerTests.restore_operation

    def pending(self, binding=2, observed=True):
        op = self.restore_operation()
        body = dict(snapshot_name='snapshot-a',
                    power_after='previous',
                    expected_control_revision=7,
                    expected_binding_generation=binding)
        op = self.journal.issue_restore_command(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'], op['revision'], body,
                                                104)
        if observed:
            server = wire.RestoreLoopback(self.journal.read_manifest(self.ctx, 'snapshot-uid-a'))
            self.addCleanup(server.close)
            server.revision = 8
            value = server.dto()
            value['binding_generation'] = binding
            op = self.journal.record_restore_status(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'], op['revision'],
                                                    value, 104)
        return op

    def test_all_persisted_pending_states_refuse_old_observation_before_worker_side_effects(self):
        self.pending()
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_restore-a')
        original = json.loads(row.attribute_value)
        with mock.patch('console.services.vm_restore_command_worker.RegionInvokeApi') as rpc:
            for state in ('issued', 'unknown', 'pending', 'conflict'):
                value = copy.deepcopy(original)
                value['rpc']['pending']['state'] = state
                value['rpc']['observation']['control_revision'] = 6
                encoded = json.dumps(value, sort_keys=True, separators=(',', ':'))
                ComponentK8sAttributes.objects.filter(pk=row.pk).update(attribute_value=encoded)
                with self.subTest(state=state), self.assertRaises(JournalConflict):
                    self.journal.read_operation(self.ctx, 'restore-a')
                with self.assertRaises(JournalConflict):
                    VMJobRunner(journal=self.journal, owner='restarted', clock=lambda: 180).process(self.ctx, 'restore-a')
                self.assertEqual(ComponentK8sAttributes.objects.get(pk=row.pk).attribute_value, encoded)
            rpc.assert_not_called()

    def test_pending_binding_floor_is_checked_even_when_not_below_sealed_source_generation(self):
        self.pending(binding=3)
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_restore-a')
        value = json.loads(row.attribute_value)
        value['rpc']['observation']['binding_generation'] = 2
        self.assertEqual(value['rpc']['observation']['source_binding_generation'], 2)
        ComponentK8sAttributes.objects.filter(pk=row.pk).update(attribute_value=json.dumps(value))
        with self.assertRaises(JournalConflict):
            self.journal.read_operation(self.ctx, 'restore-a')

    def test_unobserved_unknown_outcome_is_retained_without_inventing_an_observation(self):
        op = self.pending(observed=False)
        self.journal.record_restore_command_error(self.ctx, 'restore-a', 'worker-a', op['execution_epoch'], op['revision'], 0,
                                                  'vm_restore_outcome_unknown', 105)
        saved = self.journal.read_operation(self.ctx, 'restore-a')
        self.assertIsNone(saved['rpc']['observation'])
        self.assertEqual(saved['rpc']['pending']['request']['expected_control_revision'], 7)
        self.assertEqual(saved['rpc']['completed'], [])

    def test_equal_and_higher_observed_floors_remain_valid_without_mutation(self):
        self.pending()
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_restore-a')
        original = json.loads(row.attribute_value)
        for revision in (7, 8):
            value = copy.deepcopy(original)
            value['rpc']['observation']['control_revision'] = revision
            encoded = json.dumps(value, sort_keys=True, separators=(',', ':'))
            ComponentK8sAttributes.objects.filter(pk=row.pk).update(attribute_value=encoded)
            self.assertEqual(
                self.journal.read_operation(self.ctx, 'restore-a')['rpc']['observation']['control_revision'], revision)
            self.assertEqual(ComponentK8sAttributes.objects.get(pk=row.pk).attribute_value, encoded)
