# -*- coding: utf-8 -*-
"""Internal VM journal contracts against real isolated SQLite ORM rows."""
# capability_id: console.vm-restore.journal
import hashlib
import json
from types import SimpleNamespace
from unittest import TestCase, mock

from console.tests import vm_restore_private_attributes_test as bootstrap  # noqa: F401
from django.db import connections, transaction

from console.models.main import ComponentK8sAttributes
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.services.vm_restore_journal import JournalConflict, ServerGoContext, TrustedContext, VMRestoreJournal
from www.models.main import TenantServiceInfo


class VMRestoreJournalTestCase(TestCase):
    def setUp(self):
        self.alias = 'vm_restore_journal'
        connections.databases[self.alias] = dict(connections.databases['default'], NAME=':memory:')
        self.database = connections[self.alias]
        with self.database.schema_editor() as schema:
            schema.create_model(TenantServiceInfo)
            schema.create_model(ComponentK8sAttributes)
        self.addCleanup(self.close_database)
        for model in (TenantServiceInfo, ComponentK8sAttributes):
            patcher = mock.patch.object(model, 'objects', model.objects.db_manager(self.alias))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.service = TenantServiceInfo.objects.create(tenant_id='tenant-a',
                                                        service_id='service-a',
                                                        service_alias='vm-a',
                                                        service_region='region-a',
                                                        service_key='fixture')
        self.ctx = TrustedContext(self.service)
        self.go = ServerGoContext(namespace='team-a', source_vm_name='vm-a', source_vm_uid='vm-uid-a')
        self.journal = VMRestoreJournal()
        self.config = dict(cpu_milli=1000,
                           memory_mib=1024,
                           boot_mode='bios',
                           disk_layout=[
                               dict(volume_id=1,
                                    disk_key='root',
                                    canonical_name='manual1',
                                    role='root',
                                    device='disk',
                                    bus='virtio',
                                    boot_order=1,
                                    read_only=False)
                           ])
        self.document = dict(snapshot_name='snapshot-a',
                             snapshot_uid='snapshot-uid-a',
                             content_name='content-a',
                             content_uid='content-uid-a',
                             core_hash='a' * 64,
                             native_proof_hash='b' * 64,
                             creation_time='2026-11-12T00:00:00Z',
                             consistency='offline',
                             config=self.config,
                             disks=[
                                 dict(volume_id=1,
                                      disk_key='root',
                                      canonical_name='manual1',
                                      role='root',
                                      source_pvc=dict(kind='PersistentVolumeClaim',
                                                      namespace='team-a',
                                                      name='pvc-a',
                                                      uid='pvc-uid-a'),
                                      read_only=False,
                                      storage_class='csi-a',
                                      requested_bytes=1073741824,
                                      volume_snapshot=dict(kind='VolumeSnapshot',
                                                           namespace='team-a',
                                                           name='vs-a',
                                                           uid='vs-uid-a'))
                             ])

    def close_database(self):
        self.database.close()
        del connections[self.alias]
        connections.databases.pop(self.alias, None)

    def rows(self):
        return list(ComponentK8sAttributes.objects.order_by('pk').values())

    def row(self, name):
        return ComponentK8sAttributes.objects.get(name=name)

    def corrupt(self, name, transform):
        row = self.row(name)
        data = json.loads(row.attribute_value)
        transform(data)
        row.attribute_value = json.dumps(data)
        row.save()

    def begin(self):
        op = self.journal.create_operation(self.ctx, 'op-a', 'request-a', 'snapshot')
        return self.journal.claim(self.ctx, 'op-a', 'worker-a', op['revision'], now=100, lease_seconds=20)

    def seal(self):
        op = self.begin()
        op = self.journal.mark_region_issued(self.ctx,
                                             self.go,
                                             'op-a',
                                             'worker-a',
                                             op['execution_epoch'],
                                             op['revision'],
                                             core_hash='a' * 64,
                                             now=101)
        ack = self.journal.seal_manifest(self.ctx,
                                         self.go,
                                         'op-a',
                                         'worker-a',
                                         op['execution_epoch'],
                                         op['revision'],
                                         self.document,
                                         now=101)
        return self.journal.read_operation(self.ctx, 'op-a'), ack

    def advance(self, op, phase='prepared', now=102, **kwargs):
        return self.journal.advance(self.ctx,
                                    op['operation_id'],
                                    op['lease_owner'],
                                    op['execution_epoch'],
                                    op['revision'],
                                    phase=phase,
                                    now=now,
                                    **kwargs)

    def assert_sealable_control(self, op):
        before = self.rows()
        self.assertFalse(ComponentK8sAttributes.objects.filter(name='vm_restore_manifest_snapshot-uid-a').exists())
        # Roll the valid seal back so each following mutation gets the same
        # issued, unsealed operation instead of hitting immutable replay checks.
        with transaction.atomic(using=self.alias):
            ack = self.journal.seal_manifest(self.ctx,
                                             self.go,
                                             'op-a',
                                             'worker-a',
                                             op['execution_epoch'],
                                             op['revision'],
                                             self.document,
                                             now=101)
            manifest = self.journal.read_manifest(self.ctx, ack['snapshot_uid'])
            self.assertEqual(manifest['config'], self.config)
            self.assertEqual(manifest['document_hash'], ack['manifest_document_hash'])
            self.assertEqual(len(self.rows()), len(before) + 1)
            transaction.set_rollback(True, using=self.alias)
        self.assertEqual(self.rows(), before)

    def assert_rejected_after_sealable_control(self, op, payload):
        self.assert_sealable_control(op)
        before = self.rows()
        with self.assertRaises(JournalConflict) as caught:
            self.journal.seal_manifest(self.ctx,
                                       self.go,
                                       'op-a',
                                       'worker-a',
                                       op['execution_epoch'],
                                       op['revision'],
                                       payload,
                                       now=101)
        self.assertEqual(str(caught.exception), 'VM journal conflict')
        self.assertNotIn('fixed-nonsecret-sentinel', str(caught.exception))
        self.assertEqual(self.rows(), before)

    def test_snapshot_can_start_without_region_context_and_only_one_operation_owns_pointer(self):
        op = self.journal.create_operation(self.ctx, 'op-a', 'request-a', 'snapshot')
        self.assertEqual(op['scope'], dict(tenant_id='tenant-a', service_id='service-a', region='region-a'))
        self.assertNotIn('namespace', op['scope'])
        self.assertEqual(self.journal.create_operation(self.ctx, 'op-a', 'request-a', 'snapshot'), op)
        before = self.rows()
        for args in [('op-b', 'request-b', 'snapshot'), ('op-a', 'other-request', 'snapshot')]:
            with self.assertRaises(JournalConflict):
                self.journal.create_operation(self.ctx, *args)
        self.assertEqual(self.rows(), before)

    def test_seal_durable_canonical_hash_and_exact_replay_then_restore_reference(self):
        op, ack = self.seal()
        manifest = self.journal.read_manifest(self.ctx, 'snapshot-uid-a', expected_document_hash=ack['manifest_document_hash'])
        material = dict(manifest)
        material.pop('document_hash')
        digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(',', ':'),
                                           ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(ack['manifest_document_hash'], digest)
        self.assertEqual(ack['native_proof_hash'], 'b' * 64)
        before = self.rows()
        self.assertEqual(
            self.journal.seal_manifest(self.ctx,
                                       self.go,
                                       'op-a',
                                       'worker-a',
                                       op['execution_epoch'],
                                       op['revision'],
                                       self.document,
                                       now=102), ack)
        self.assertEqual(self.rows(), before)
        op = self.journal.record_region_terminal(self.ctx,
                                                 'op-a',
                                                 'worker-a',
                                                 op['execution_epoch'],
                                                 op['revision'],
                                                 self.terminal_evidence(op, outcome='runtime_verified'),
                                                 now=102)
        self.journal.release(self.ctx, 'op-a', 'worker-a', op['execution_epoch'], op['revision'], now=103)
        restored = self.journal.create_operation(self.ctx,
                                                 'restore-a',
                                                 'restore-request',
                                                 'restore',
                                                 snapshot_uid='snapshot-uid-a',
                                                 document_hash=digest,
                                                 rollback_config=self.config)
        self.assertEqual(restored['document_hash'], digest)
        self.assertEqual(restored['rollback_config'], self.config)
        self.assertEqual(self.journal.read_manifest(self.ctx, 'snapshot-uid-a'), manifest)

    def test_sealed_manifest_rejects_changed_hash_uid_proof_and_document_without_mutation(self):
        op, ack = self.seal()
        before = self.rows()
        for field, value in [('core_hash', 'c' * 64), ('native_proof_hash', 'd' * 64), ('snapshot_uid', 'another-uid'),
                             ('config', dict(self.config, memory_mib=2048))]:
            payload = dict(self.document, **{field: value})
            with self.subTest(field=field), self.assertRaises(JournalConflict):
                self.journal.seal_manifest(self.ctx,
                                           self.go,
                                           'op-a',
                                           'worker-a',
                                           op['execution_epoch'],
                                           op['revision'],
                                           payload,
                                           now=102)
        with self.assertRaises(JournalConflict):
            self.journal.read_manifest(self.ctx, 'snapshot-uid-a', expected_document_hash='f' * 64)
        self.assertEqual(self.rows(), before)
        self.assertEqual(ack['snapshot_uid'], 'snapshot-uid-a')

    def test_manifest_content_hash_and_key_identity_are_validated_on_every_read(self):
        self.seal()
        original = self.row('vm_restore_manifest_snapshot-uid-a').attribute_value
        for field, value in [('native_proof_hash', 'c' * 64), ('snapshot_uid', 'foreign-uid'), ('core_hash', 'd' * 64)]:
            self.corrupt('vm_restore_manifest_snapshot-uid-a', lambda data: data.update({field: value}))
            with self.subTest(field=field), self.assertRaises(JournalConflict):
                self.journal.read_manifest(self.ctx, 'snapshot-uid-a')
            ComponentK8sAttributes.objects.filter(name='vm_restore_manifest_snapshot-uid-a').update(attribute_value=original)

    def test_missing_pointer_or_operation_cannot_be_reinitialized(self):
        self.begin()
        pointer = self.row('vm_restore_active_operation')
        pointer.delete()
        with self.assertRaises(JournalConflict):
            self.journal.create_operation(self.ctx, 'op-b', 'request-b', 'snapshot')
        pointer.pk = None
        pointer.save()
        self.row('vm_restore_operation_op-a').delete()
        with self.assertRaises(JournalConflict):
            self.journal.create_operation(self.ctx, 'op-b', 'request-b', 'snapshot')

    def test_deleted_manifest_reference_cannot_be_treated_as_empty_or_advanced(self):
        op, _ = self.seal()
        self.row('vm_restore_manifest_snapshot-uid-a').delete()
        for action in (lambda: self.journal.read_operation(self.ctx, 'op-a'), lambda: self.advance(op)):
            with self.assertRaises(JournalConflict):
                action()

    def test_duplicate_and_malformed_records_fail_closed_with_fixed_diagnostics(self):
        op = self.begin()
        original = self.row('vm_restore_operation_op-a').attribute_value
        for value in [
                '{', '{"schema_version":1,"schema_version":1}', '[]', 'NaN', 'x' * 32769,
                original.replace('"schema_version":1', '"schema_version":999')
        ]:
            ComponentK8sAttributes.objects.filter(name='vm_restore_operation_op-a').update(attribute_value=value)
            with self.subTest(value_length=len(value)), self.assertRaises(JournalConflict) as caught:
                self.journal.read_operation(self.ctx, 'op-a')
            self.assertEqual(str(caught.exception), 'VM journal conflict')
        ComponentK8sAttributes.objects.filter(name='vm_restore_operation_op-a').update(attribute_value=original)
        row = self.row('vm_restore_operation_op-a')
        row.pk = None
        row.save()
        with self.assertRaises(JournalConflict):
            self.advance(op)

    def test_missing_required_unknown_fields_bad_nested_types_and_credentials_are_rejected(self):
        op = self.issued()
        payloads = []
        missing = dict(self.document)
        missing.pop('content_uid')
        payloads.append(('missing_content_uid', missing))
        for key in ('raw_vm', 'cloud_init', 'secret', 'password', 'user_data', 'commands', 'ID', 'component_id', 'namespace'):
            payloads.append(('unknown_' + key, dict(self.document, **{key: 'fixed-nonsecret-sentinel'})))
        payloads.extend(
            [('cpu_boolean', dict(self.document, config=dict(self.config, cpu_milli=True))),
             ('startup_commands', dict(self.document, startup={'commands': ['fixed-nonsecret-sentinel']})),
             ('pvc_missing_identity', dict(self.document, disks=[dict(self.document['disks'][0], source_pvc={'name': 'x'})])),
             ('too_many_disks', dict(self.document, disks=self.document['disks'] * 17))])
        for case, payload in payloads:
            with self.subTest(case=case):
                self.assert_rejected_after_sealable_control(op, payload)

    def test_scope_comes_from_live_model_and_rejects_stale_or_unsaved_context_and_foreign_rows(self):
        self.begin()
        before = self.rows()
        with self.assertRaises(JournalConflict):
            TrustedContext(TenantServiceInfo(service_id='service-a'))
        with self.assertRaises(JournalConflict):
            self.journal.read_operation(SimpleNamespace(service=self.service), 'op-a')
        TenantServiceInfo.objects.filter(pk=self.service.pk).update(service_region='region-b')
        with self.assertRaises(JournalConflict):
            self.journal.read_operation(self.ctx, 'op-a')
        TenantServiceInfo.objects.filter(pk=self.service.pk).update(service_region='region-a')
        ComponentK8sAttributes.objects.filter(name='vm_restore_operation_op-a').update(tenant_id='tenant-b')
        with self.assertRaises(JournalConflict):
            self.journal.read_operation(self.ctx, 'op-a')
        self.assertEqual(len(self.rows()), len(before))

    def test_expired_lease_takeover_keeps_active_and_fences_old_owner_epoch_and_revision(self):
        op = self.begin()
        with self.assertRaises(JournalConflict):
            self.journal.claim(self.ctx, 'op-a', 'worker-b', op['revision'], now=119, lease_seconds=20)
        replacement = self.journal.claim(self.ctx, 'op-a', 'worker-b', op['revision'], now=120, lease_seconds=20)
        self.assertEqual(replacement['execution_epoch'], op['execution_epoch'] + 1)
        for action in (
                lambda: self.advance(op, now=121),
                lambda: self.journal.release(self.ctx, 'op-a', 'worker-a', op['execution_epoch'], op['revision'], now=121),
                lambda: self.journal.create_operation(self.ctx, 'op-b', 'request-b', 'snapshot')):
            with self.assertRaises(JournalConflict):
                action()
        changed = self.advance(replacement, phase='failed', now=121, retry_at=130, error_code='REGION_UNKNOWN')
        self.assertEqual(changed['retry_count'], 1)
        self.assertEqual(changed['retry_at'], 130)
        with self.assertRaises(JournalConflict):
            self.journal.release(self.ctx, 'op-a', 'worker-b', changed['execution_epoch'], changed['revision'], now=122)
        with self.assertRaises(JournalConflict):
            self.advance(replacement, now=122)

    def test_terminal_release_retains_audit_and_idle_pointer_detects_lost_history(self):
        op = self.begin()
        with self.assertRaises(JournalConflict):
            self.journal.release(self.ctx, 'op-a', 'worker-a', op['execution_epoch'], op['revision'], now=101)
        terminal = self.advance(op, phase='cancelled')
        self.journal.release(self.ctx, 'op-a', 'worker-a', terminal['execution_epoch'], terminal['revision'], now=103)
        pointer = json.loads(self.row('vm_restore_active_operation').attribute_value)
        self.assertEqual(pointer['operation_id'], '')
        self.assertEqual(pointer['last_operation_id'], 'op-a')
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['phase'], 'cancelled')
        self.row('vm_restore_operation_op-a').delete()
        with self.assertRaises(JournalConflict):
            self.journal.create_operation(self.ctx, 'op-b', 'request-b', 'snapshot')

    def test_public_overwrite_preserves_journal_and_public_projection_has_no_private_payload(self):
        op, _ = self.seal()
        before = self.rows()
        k8s_attribute_repo.overwrite_by_component_ids(['service-a'], [])
        self.assertEqual(self.rows(), before)
        projected = self.journal.public_operation(self.ctx, 'op-a')
        self.assertEqual(projected['operation_id'], 'op-a')
        self.assertFalse(
            set(projected) & {
                'lease_owner', 'lease_until', 'execution_epoch', 'rollback_config', 'scope', 'document_hash', 'core_hash',
                'native_proof_hash', 'region_intent', 'region_terminal'
            })
        self.assertNotIn('worker-a', json.dumps(projected))
        self.assertEqual(op['operation_id'], 'op-a')

    def test_failure_during_second_write_rolls_back_operation_pointer_and_manifest(self):
        original = ComponentK8sAttributes.objects.create
        count = [0]

        def fail_second(**kwargs):
            count[0] += 1
            if count[0] == 2:
                raise RuntimeError('fixed-write-failure')
            return original(**kwargs)

        with mock.patch.object(ComponentK8sAttributes.objects, 'create', side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                self.journal.create_operation(self.ctx, 'op-a', 'request-a', 'snapshot')
        self.assertEqual(self.rows(), [])
        op = self.begin()
        op = self.journal.mark_region_issued(self.ctx,
                                             self.go,
                                             'op-a',
                                             'worker-a',
                                             op['execution_epoch'],
                                             op['revision'],
                                             core_hash='a' * 64,
                                             now=101)
        before = self.rows()
        with mock.patch.object(ComponentK8sAttributes, 'save', side_effect=RuntimeError('fixed-write-failure')):
            with self.assertRaises(RuntimeError):
                self.journal.seal_manifest(self.ctx,
                                           self.go,
                                           'op-a',
                                           'worker-a',
                                           op['execution_epoch'],
                                           op['revision'],
                                           self.document,
                                           now=101)
        self.assertEqual(self.rows(), before)

    def test_go_context_startup_and_restore_hash_requirements(self):
        op = self.issued()
        payload = dict(self.document, startup={'was_running': True, 'power_after': 'stopped'})
        for go in (None, ServerGoContext('', 'vm-a', 'vm-uid-a')):
            with self.assertRaises(JournalConflict):
                self.journal.seal_manifest(self.ctx,
                                           go,
                                           'op-a',
                                           'worker-a',
                                           op['execution_epoch'],
                                           op['revision'],
                                           payload,
                                           now=101)
        ack = self.journal.seal_manifest(self.ctx,
                                         self.go,
                                         'op-a',
                                         'worker-a',
                                         op['execution_epoch'],
                                         op['revision'],
                                         payload,
                                         now=101)
        manifest = self.journal.read_manifest(self.ctx, 'snapshot-uid-a')
        self.assertEqual(manifest['startup'], payload['startup'])
        with self.assertRaises(JournalConflict):
            self.journal.read_manifest(self.ctx, 'snapshot-uid-a', expected_native_proof_hash='c' * 64)
        self.assertEqual(ack['manifest_id'], 'snapshot-uid-a')

    def test_terminal_worker_crash_can_be_taken_over_for_release(self):
        op = self.begin()
        terminal = self.advance(op, phase='cancelled')
        takeover = self.journal.claim(self.ctx, 'op-a', 'worker-b', terminal['revision'], now=121, lease_seconds=20)
        self.assertEqual(takeover['phase'], 'cancelled')
        self.journal.release(self.ctx, 'op-a', 'worker-b', takeover['execution_epoch'], takeover['revision'], now=122)
        self.assertEqual(json.loads(self.row('vm_restore_active_operation').attribute_value)['operation_id'], '')

    def test_all_stored_schema_type_errors_remain_fixed_conflicts(self):
        self.begin()
        row = self.row('vm_restore_operation_op-a')
        original = row.attribute_value
        for key, value in [('snapshot_uid', []), ('document_hash', []), ('phase', []), ('kind', {}), ('error_code', {}),
                           ('lease_owner', []), ('revision', True)]:
            self.corrupt(row.name, lambda data: data.update({key: value}))
            with self.subTest(key=key), self.assertRaises(JournalConflict):
                self.journal.read_operation(self.ctx, 'op-a')
            ComponentK8sAttributes.objects.filter(pk=row.pk).update(attribute_value=original)

    def test_older_audit_loss_is_detected_even_with_intact_last_pointer(self):
        for name in ('op-a', 'op-b'):
            op = self.journal.create_operation(self.ctx, name, 'request-' + name, 'snapshot')
            op = self.journal.claim(self.ctx, name, 'worker-a', op['revision'], now=100, lease_seconds=20)
            op = self.advance(op, phase='cancelled')
            self.journal.release(self.ctx, name, 'worker-a', op['execution_epoch'], op['revision'], now=103)
        self.row('vm_restore_operation_op-a').delete()
        with self.assertRaises(JournalConflict):
            self.journal.create_operation(self.ctx, 'op-c', 'request-c', 'snapshot')

    def test_cross_namespace_refs_wrong_root_identity_and_duplicate_disks_fail_closed(self):
        op = self.issued()
        payloads = []
        for field, value in [('namespace', 'foreign-namespace'), ('kind', 'Secret')]:
            disk = dict(self.document['disks'][0], source_pvc=dict(self.document['disks'][0]['source_pvc'], **{field: value}))
            payloads.append(('pvc_wrong_' + field, dict(self.document, disks=[disk])))
        config = dict(self.config, disk_layout=[dict(self.config['disk_layout'][0], canonical_name='foreign-name')])
        payloads.append(('wrong_canonical_name',
                         dict(self.document,
                              config=config,
                              disks=[dict(self.document['disks'][0], canonical_name='foreign-name')])))
        config = dict(self.config, disk_layout=[dict(self.config['disk_layout'][0], role='data')])
        payloads.append(
            ('missing_root_disk', dict(self.document, config=config, disks=[dict(self.document['disks'][0], role='data')])))
        payloads.append(('duplicate_disk', dict(self.document, disks=self.document['disks'] * 2)))
        for case, payload in payloads:
            with self.subTest(case=case):
                self.assert_rejected_after_sealable_control(op, payload)

    def test_restore_requires_matching_sealed_document_and_immutable_rollback(self):
        op, ack = self.seal()
        op = self.journal.record_region_terminal(self.ctx,
                                                 'op-a',
                                                 'worker-a',
                                                 op['execution_epoch'],
                                                 op['revision'],
                                                 self.terminal_evidence(op, outcome='runtime_verified'),
                                                 now=102)
        self.journal.release(self.ctx, 'op-a', 'worker-a', op['execution_epoch'], op['revision'], now=103)
        before = self.rows()
        for uid, doc_hash, rollback in [('absent', 'c' * 64, self.config), ('snapshot-uid-a', 'c' * 64, self.config),
                                        ('snapshot-uid-a', ack['manifest_document_hash'], None)]:
            with self.assertRaises(JournalConflict):
                self.journal.create_operation(self.ctx,
                                              'restore-a',
                                              'request-restore',
                                              'restore',
                                              snapshot_uid=uid,
                                              document_hash=doc_hash,
                                              rollback_config=rollback)
            self.assertEqual(self.rows(), before)
        self.journal.create_operation(self.ctx,
                                      'restore-a',
                                      'request-restore',
                                      'restore',
                                      snapshot_uid='snapshot-uid-a',
                                      document_hash=ack['manifest_document_hash'],
                                      rollback_config=self.config)
        with self.assertRaises(JournalConflict):
            self.journal.create_operation(self.ctx,
                                          'restore-a',
                                          'request-restore',
                                          'restore',
                                          snapshot_uid='snapshot-uid-a',
                                          document_hash=ack['manifest_document_hash'],
                                          rollback_config=dict(self.config, memory_mib=2048))

    def test_lease_renewal_and_expiry_require_cas_and_bounded_values(self):
        op = self.begin()
        renewed = self.journal.claim(self.ctx, 'op-a', 'worker-a', op['revision'], now=110, lease_seconds=20)
        self.assertEqual(renewed['execution_epoch'], op['execution_epoch'])
        for now, duration in [(110, 0), (110, 301), (True, 20)]:
            with self.assertRaises(JournalConflict):
                self.journal.claim(self.ctx, 'op-a', 'worker-a', renewed['revision'], now=now, lease_seconds=duration)
        with self.assertRaises(JournalConflict):
            self.advance(renewed, now=130)
        with self.assertRaises(JournalConflict):
            self.advance(renewed, now=112, retry_at=111)
        with self.assertRaises(JournalConflict):
            self.advance(renewed, now=112, phase='cancelled', error_code='REGION_UNKNOWN')

    def test_history_bound_rejects_new_operation_atomically(self):
        op = self.begin()
        template = dict(op, phase='cancelled')
        records = []
        for index in range(1, 255):
            record = dict(template, operation_id='audit-' + str(index), request_id='audit-request-' + str(index))
            records.append(
                ComponentK8sAttributes(tenant_id='tenant-a',
                                       component_id='service-a',
                                       save_type='json',
                                       name='vm_restore_operation_' + record['operation_id'],
                                       attribute_value=json.dumps(record)))
        ComponentK8sAttributes.objects.bulk_create(records)
        self.corrupt('vm_restore_operation_op-a', lambda data: data.update(phase='cancelled'))
        self.corrupt('vm_restore_active_operation',
                     lambda data: data.update(operation_count=255, operation_id='', last_operation_id='op-a'))
        before = self.rows()
        with self.assertRaises(JournalConflict):
            self.journal.create_operation(self.ctx, 'op-b', 'request-b', 'snapshot')
        self.assertEqual(self.rows(), before)

    def issued(self):
        op = self.begin()
        return self.journal.mark_region_issued(self.ctx,
                                               self.go,
                                               'op-a',
                                               'worker-a',
                                               op['execution_epoch'],
                                               op['revision'],
                                               core_hash='a' * 64,
                                               now=101)

    def terminal_evidence(self, op, **changes):
        from console.services.vm_restore_journal import RegionTerminalEvidence
        values = dict(tenant_id='tenant-a',
                      service_id='service-a',
                      region='region-a',
                      namespace='team-a',
                      operation_id='op-a',
                      core_hash='a' * 64,
                      execution_epoch=op['execution_epoch'],
                      finalized=True,
                      fence_released=True,
                      outcome='cancelled')
        values.update(changes)
        return RegionTerminalEvidence(**values)

    def test_issued_unknown_and_accepted_unfinalized_region_work_cannot_release(self):
        op = self.issued()
        failed = self.advance(op, phase='failed', error_code='REGION_UNKNOWN')
        with self.assertRaises(JournalConflict):
            self.journal.release(self.ctx, 'op-a', 'worker-a', failed['execution_epoch'], failed['revision'], now=103)
        with self.assertRaises(JournalConflict):
            self.advance(failed, phase='cancelled', now=104)
        cancelled = failed
        with self.assertRaises(JournalConflict):
            self.journal.release(self.ctx, 'op-a', 'worker-a', cancelled['execution_epoch'], cancelled['revision'], now=105)
        for changes in ({'finalized': False}, {'fence_released': False}):
            with self.assertRaises(JournalConflict):
                self.journal.record_region_terminal(self.ctx,
                                                    'op-a',
                                                    'worker-a',
                                                    cancelled['execution_epoch'],
                                                    cancelled['revision'],
                                                    self.terminal_evidence(cancelled, **changes),
                                                    now=105)
        self.assertEqual(json.loads(self.row('vm_restore_active_operation').attribute_value)['operation_id'], 'op-a')

    def test_terminal_evidence_requires_exact_scope_op_core_and_current_epoch(self):
        op = self.issued()
        for changes in ({
                'tenant_id': 'tenant-b'
        }, {
                'service_id': 'service-b'
        }, {
                'region': 'region-b'
        }, {
                'namespace': 'foreign'
        }, {
                'operation_id': 'other-op'
        }, {
                'core_hash': 'b' * 64
        }, {
                'execution_epoch': 99
        }):
            with self.assertRaises(JournalConflict):
                self.journal.record_region_terminal(self.ctx,
                                                    'op-a',
                                                    'worker-a',
                                                    op['execution_epoch'],
                                                    op['revision'],
                                                    self.terminal_evidence(op, **changes),
                                                    now=102)
        with self.assertRaises(JournalConflict):
            self.journal.mark_region_issued(self.ctx,
                                            self.go,
                                            'op-a',
                                            'worker-a',
                                            op['execution_epoch'],
                                            op['revision'],
                                            core_hash='c' * 64,
                                            now=102)
        takeover = self.journal.claim(self.ctx, 'op-a', 'worker-b', op['revision'], now=120, lease_seconds=20)
        with self.assertRaises(JournalConflict):
            self.journal.record_region_terminal(self.ctx,
                                                'op-a',
                                                'worker-a',
                                                op['execution_epoch'],
                                                op['revision'],
                                                self.terminal_evidence(op),
                                                now=121)
        with self.assertRaises(JournalConflict):
            self.journal.record_region_terminal(self.ctx,
                                                'op-a',
                                                'worker-b',
                                                takeover['execution_epoch'],
                                                takeover['revision'],
                                                self.terminal_evidence(op),
                                                now=121)

    def test_durable_terminal_region_evidence_survives_crash_and_lease_takeover(self):
        op = self.issued()
        terminal = self.journal.record_region_terminal(self.ctx,
                                                       'op-a',
                                                       'worker-a',
                                                       op['execution_epoch'],
                                                       op['revision'],
                                                       self.terminal_evidence(op),
                                                       now=102)
        takeover = self.journal.claim(self.ctx, 'op-a', 'worker-b', terminal['revision'], now=120, lease_seconds=20)
        with self.assertRaises(JournalConflict):
            self.journal.release(self.ctx, 'op-a', 'worker-a', terminal['execution_epoch'], terminal['revision'], now=121)
        self.journal.release(self.ctx, 'op-a', 'worker-b', takeover['execution_epoch'], takeover['revision'], now=122)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['region_terminal'], terminal['region_terminal'])

    def test_unknown_first_rpc_intent_pins_active_until_bound_and_terminal(self):
        op = self.begin()
        op = self.journal.mark_region_issued(self.ctx,
                                             None,
                                             'op-a',
                                             'worker-a',
                                             op['execution_epoch'],
                                             op['revision'],
                                             core_hash='',
                                             now=101)
        with self.assertRaises(JournalConflict):
            self.advance(op, phase='cancelled')
        with self.assertRaises(JournalConflict):
            self.journal.release(self.ctx, 'op-a', 'worker-a', op['execution_epoch'], op['revision'], now=103)
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['region_intent']['core_hash'], '')

    def test_unknown_intent_can_bind_only_once_from_server_response_before_seal(self):
        op = self.begin()
        op = self.journal.mark_region_issued(self.ctx,
                                             None,
                                             'op-a',
                                             'worker-a',
                                             op['execution_epoch'],
                                             op['revision'],
                                             core_hash='',
                                             now=101)
        ack = self.journal.seal_manifest(self.ctx,
                                         self.go,
                                         'op-a',
                                         'worker-a',
                                         op['execution_epoch'],
                                         op['revision'],
                                         self.document,
                                         now=102)
        current = self.journal.read_operation(self.ctx, 'op-a')
        self.assertEqual(current['region_intent']['core_hash'], ack['core_hash'])
        with self.assertRaises(JournalConflict):
            self.journal.mark_region_issued(self.ctx,
                                            self.go,
                                            'op-a',
                                            'worker-a',
                                            current['execution_epoch'],
                                            current['revision'],
                                            core_hash='c' * 64,
                                            now=103)

    def test_idle_pointer_cannot_hide_issued_operation_without_release_evidence(self):
        self.issued()
        self.corrupt('vm_restore_operation_op-a', lambda data: data.update(phase='cancelled'))
        self.corrupt('vm_restore_active_operation', lambda data: data.update(operation_id='', last_operation_id='op-a'))
        with self.assertRaises(JournalConflict):
            self.journal.create_operation(self.ctx, 'op-b', 'request-b', 'snapshot')

    def test_valid_manifest_in_negative_case_setup_can_seal(self):
        self.assert_sealable_control(self.issued())

    def test_unissued_operation_refuses_even_valid_manifest_without_mutation(self):
        op = self.begin()
        before = self.rows()
        with self.assertRaises(JournalConflict):
            self.journal.seal_manifest(self.ctx,
                                       self.go,
                                       'op-a',
                                       'worker-a',
                                       op['execution_epoch'],
                                       op['revision'],
                                       self.document,
                                       now=101)
        self.assertEqual(self.rows(), before)
