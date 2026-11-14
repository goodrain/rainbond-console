# capability_id: console.vm-snapshot.manifest-ack-helper
import copy
import json
from unittest import TestCase

from django.db import DatabaseError, transaction

from console.tests import vm_restore_journal_test as fixtures
from console.models.main import ComponentK8sAttributes
from console.services.vm_restore_journal import JournalConflict
from www.models.main import TenantServiceVolume


class SnapshotManifestAckTests(TestCase):
    setUp = fixtures.VMRestoreJournalTestCase.setUp
    close_database = fixtures.VMRestoreJournalTestCase.close_database

    def prepared(self):
        self.service.extend_method = 'vm'
        self.service.min_cpu, self.service.min_memory = 1000, 1024
        self.service.save()
        with self.database.schema_editor() as schema:
            schema.create_model(TenantServiceVolume)
        TenantServiceVolume.objects.using(self.alias).create(ID=101,
                                                             service_id='service-a',
                                                             volume_name='root',
                                                             volume_path='/disk',
                                                             volume_type='csi-a',
                                                             volume_capacity=1)
        for name, kind, value in [('vm_boot_mode', 'string', 'bios'),
                                  ('vm_disk_layout', 'json',
                                   json.dumps([{
                                       'disk_key': 'root',
                                       'disk_name': 'system-disk',
                                       'disk_role': 'root',
                                       'device_type': 'disk',
                                       'source_kind': 'volume',
                                       'order_index': 0,
                                       'boot': True
                                   }]))]:
            ComponentK8sAttributes.objects.create(tenant_id='tenant-a',
                                                  component_id='service-a',
                                                  name=name,
                                                  save_type=kind,
                                                  attribute_value=value)
        op = self.journal.create_operation(self.ctx,
                                           'op-a',
                                           'ui-request-a',
                                           'snapshot',
                                           request={
                                               'name': 'snapshot-a',
                                               'description': '',
                                               'power_after': 'previous'
                                           })
        op = self.journal.claim(self.ctx, 'op-a', 'worker-a', op['revision'], 100, 30)
        op = self.journal.mark_region_issued(self.ctx, self.go, 'op-a', 'worker-a', op['execution_epoch'], op['revision'],
                                             'a' * 64, 101)
        self.observed = {
            **copy.deepcopy(self.document), 'operation_id': 'op-a',
            'source_vm_uid': 'vm-uid-a',
            'description': '',
            'ready_to_use': True,
            'source_lock_clear': True,
            'was_running': True,
            'power_after': 'previous',
            'source_stopped': True,
            'source_running': False,
            'manifest_acked': False,
            'finalized': False,
            'cancelled': False,
            'deleted': False,
            'error_code': '',
            'coverage': {
                'complete': True,
                'expected_writable_disks': 1,
                'included_disks': 1,
                'missing_disk_keys': [],
                'excluded_read_only': []
            }
        }
        return op

    def commit(self, op):
        from console.services.vm_snapshot_manifest_ack import SnapshotManifestService
        return SnapshotManifestService(self.journal).commit(self.ctx, self.go, 'op-a', 'worker-a', op['execution_epoch'],
                                                            op['revision'], self.observed, 102)

    def test_prepare_and_ready_request_keep_go_manifest_id_separate_from_snapshot_uid(self):
        from console.services.vm_snapshot_manifest_ack import SnapshotManifestService, snapshot_prepare_body
        op = self.prepared()
        prepare = snapshot_prepare_body(op)
        self.assertEqual(prepare['request_id'], 'op-a')
        self.assertEqual(prepare['manifest_id'], 'op-a')
        self.assertNotEqual(prepare['request_id'], op['request_id'])
        manifest = self.commit(op)
        saved = self.journal.read_operation(self.ctx, 'op-a')
        request = SnapshotManifestService(self.journal).ready_request(self.ctx, 'op-a', 'worker-a', saved['execution_epoch'],
                                                                      saved['revision'], self.observed, 103)
        self.assertEqual(request['manifest_id'], prepare['manifest_id'])
        self.assertNotEqual(request['manifest_id'], manifest['snapshot_uid'])
        self.assertEqual(request['manifest_document_hash'], manifest['document_hash'])
        self.assertEqual(request['native_proof_hash'], manifest['native_proof_hash'])
        self.assertEqual(TenantServiceVolume.objects.using(self.alias).get(ID=101).volume_name, 'root')
        self.assertIsNone(saved['region_terminal'])
        self.assertEqual(self.journal.active_operation(self.ctx), 'op-a')

    def test_missing_source_authority_or_foreign_operation_never_seals(self):
        from console.services.vm_snapshot_manifest_ack import SnapshotManifestService
        op = self.prepared()
        with self.assertRaises(JournalConflict):
            SnapshotManifestService(self.journal).commit(self.ctx, None, 'op-a', 'worker-a', op['execution_epoch'],
                                                         op['revision'], self.observed, 102)
        self.observed['operation_id'] = 'foreign-op'
        with self.assertRaises(JournalConflict):
            self.commit(op)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['snapshot_uid'], '')

    def test_native_ready_without_complete_coverage_or_proof_cannot_seal(self):
        op = self.prepared()
        original = copy.deepcopy(self.observed)
        for field, value in [('native_proof_hash', ''), ('ready_to_use', False),
                             ('coverage', {
                                 'complete': False,
                                 'expected_writable_disks': 2,
                                 'included_disks': 1,
                                 'missing_disk_keys': ['data'],
                                 'excluded_read_only': []
                             })]:
            self.observed = {**original, field: value}
            with self.subTest(field=field), self.assertRaises(JournalConflict):
                self.commit(op)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['snapshot_uid'], '')

    def test_console_config_drift_before_seal_is_refused_without_defaults(self):
        op = self.prepared()
        self.service.min_cpu = 2000
        self.service.save()
        with self.assertRaises(JournalConflict):
            self.commit(op)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['snapshot_uid'], '')

    def test_outer_transaction_and_real_sql_abort_never_return_ack_material(self):
        from console.services.vm_snapshot_manifest_ack import SnapshotManifestService
        op = self.prepared()
        with transaction.atomic(using=self.alias), self.assertRaises(JournalConflict):
            self.commit(op)
        with self.database.cursor() as cursor:
            cursor.execute('''CREATE TRIGGER abort_manifest BEFORE INSERT ON component_k8s_attributes
                WHEN NEW.name LIKE 'vm_restore_manifest_%' BEGIN SELECT RAISE(ABORT,'MANIFEST_ABORT'); END''')
        try:
            with self.assertRaises(DatabaseError):
                self.commit(op)
        finally:
            with self.database.cursor() as cursor:
                cursor.execute('DROP TRIGGER abort_manifest')
        with self.assertRaises(JournalConflict):
            SnapshotManifestService(self.journal).ready_request(self.ctx, 'op-a', 'worker-a', op['execution_epoch'],
                                                                op['revision'], self.observed, 103)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['snapshot_uid'], '')

    def test_changed_native_proof_or_live_fields_after_commit_block_ack(self):
        from console.services.vm_snapshot_manifest_ack import SnapshotManifestService
        op = self.prepared()
        self.commit(op)
        saved = self.journal.read_operation(self.ctx, 'op-a')
        service = SnapshotManifestService(self.journal)
        for field in ('native_proof_hash', 'content_uid', 'was_running'):
            changed = {**self.observed, field: False if field == 'was_running' else 'f' * 64}
            with self.subTest(field=field), self.assertRaises(JournalConflict):
                service.ready_request(self.ctx, 'op-a', 'worker-a', saved['execution_epoch'], saved['revision'], changed, 103)
        self.service.min_memory = 2048
        self.service.save()
        with self.assertRaises(JournalConflict):
            service.ready_request(self.ctx, 'op-a', 'worker-a', saved['execution_epoch'], saved['revision'], self.observed, 103)

    def test_next_action_requires_actual_power_and_unlock_not_phase_or_acked_bool(self):
        from console.services.vm_snapshot_manifest_ack import ready_action
        op = self.prepared()
        with self.assertRaises(JournalConflict):
            ready_action(op, self.observed)
        self.commit(op)
        op = self.journal.read_operation(self.ctx, 'op-a')
        self.assertEqual(ready_action(op, self.observed), 'resume')
        self.assertEqual(ready_action(op, {**self.observed, 'source_running': True, 'source_stopped': False}), 'finalize')
        self.assertIsNone(ready_action(op, {**self.observed, 'source_lock_clear': False, 'manifest_acked': True}))
        self.assertIsNone(ready_action(op, {**self.observed, 'error_code': 'vm_snapshot_resume_outcome_pending'}))

    def test_missing_layout_and_changed_logical_disk_capacity_never_seal(self):
        op = self.prepared()
        row = ComponentK8sAttributes.objects.get(name='vm_disk_layout')
        original = row.attribute_value
        row.attribute_value = '[]'
        row.save()
        with self.assertRaises(JournalConflict):
            self.commit(op)
        row.attribute_value = original
        row.save()
        TenantServiceVolume.objects.using(self.alias).filter(ID=101).update(volume_capacity=2)
        with self.assertRaises(JournalConflict):
            self.commit(op)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['snapshot_uid'], '')

    def test_manifest_replay_and_ack_re_read_are_idempotent_and_keep_job_active(self):
        from console.services.vm_snapshot_manifest_ack import SnapshotManifestService
        op = self.prepared()
        first = self.commit(op)
        saved = self.journal.read_operation(self.ctx, 'op-a')
        row = ComponentK8sAttributes.objects.get(name='vm_restore_manifest_snapshot-uid-a')
        original = row.attribute_value
        self.assertEqual(self.commit(saved), first)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a'), saved)
        service = SnapshotManifestService(self.journal)
        body = service.ready_request(self.ctx, 'op-a', 'worker-a', saved['execution_epoch'], saved['revision'], self.observed,
                                     103)
        self.assertEqual(
            service.ready_request(self.ctx, 'op-a', 'worker-a', saved['execution_epoch'], saved['revision'], {
                **self.observed, 'manifest_acked': True
            }, 103), body)
        row.refresh_from_db()
        self.assertEqual(row.attribute_value, original)
        self.assertIsNone(self.journal.read_operation(self.ctx, 'op-a')['region_terminal'])
        self.assertEqual(self.journal.active_operation(self.ctx), 'op-a')
