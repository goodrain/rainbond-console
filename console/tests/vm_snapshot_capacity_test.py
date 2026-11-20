# capability_id: console.vm-snapshot.capacity-evidence
"""Logical capacity checks never reinterpret the snapshot's physical PVC bytes."""
from dataclasses import replace
from unittest import TestCase

from console.tests import vm_snapshot_manifest_ack_test as fixtures
from console.services.vm_snapshot_manifest_ack import SnapshotCapacityEvidence, SnapshotManifestService
from console.services.vm_restore_journal import JournalConflict
from www.models.main import TenantServiceVolume


class SnapshotCapacityTests(TestCase):
    setUp = fixtures.SnapshotManifestAckTests.setUp
    close_database = fixtures.SnapshotManifestAckTests.close_database
    prepared = fixtures.SnapshotManifestAckTests.prepared

    def prepare_capacity(self):
        op = self.prepared()
        self.observed['disks'][0]['requested_bytes'] = 1138166334
        evidence = SnapshotCapacityEvidence(self.ctx.identity, 'op-a', 'a' * 64, (('root', 'csi-a', 1073741824), ))
        return op, evidence

    def seal(self, op, evidence):
        return SnapshotManifestService(self.journal).commit(self.ctx, self.go, 'op-a', 'worker-a', op['execution_epoch'],
                                                            op['revision'], self.observed, 102, evidence)

    def test_overhead_keeps_physical_manifest_and_checks_current_logical_capacity_before_ack(self):
        op, evidence = self.prepare_capacity()
        manifest = self.seal(op, evidence)
        self.assertEqual(manifest['disks'][0]['requested_bytes'], 1138166334)
        self.assertNotIn('logical_capacity', manifest)
        saved = self.journal.read_operation(self.ctx, 'op-a')
        store = SnapshotManifestService(self.journal)
        body = store.ready_request(self.ctx, 'op-a', 'worker-a', saved['execution_epoch'], saved['revision'], self.observed,
                                   103, evidence)
        self.assertEqual(body['manifest_document_hash'], manifest['document_hash'])
        TenantServiceVolume.objects.using(self.alias).filter(ID=101).update(volume_capacity=2)
        with self.assertRaises(JournalConflict):
            store.ready_request(self.ctx, 'op-a', 'worker-a', saved['execution_epoch'], saved['revision'], self.observed, 104,
                                evidence)

    def test_foreign_evidence_cannot_seal_or_replace_the_original_scope_and_operation(self):
        op, evidence = self.prepare_capacity()
        for invalid in [
                replace(evidence, scope=('other', ) + evidence.scope[1:]),
                replace(evidence, operation_id='other-operation'),
                replace(evidence, core_hash='b' * 64),
                replace(evidence, volumes=()),
                replace(evidence, volumes=(('other-disk', 'csi-a', 1073741824), ))
        ]:
            with self.subTest(evidence=invalid), self.assertRaises(JournalConflict):
                self.seal(op, invalid)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['snapshot_uid'], '')

    def test_legacy_no_evidence_remains_strict_and_undersized_physical_snapshot_is_refused(self):
        op, evidence = self.prepare_capacity()
        with self.assertRaises(JournalConflict):
            self.seal(op, None)
        self.observed['disks'][0]['requested_bytes'] = 1073741823
        with self.assertRaises(JournalConflict):
            self.seal(op, evidence)
