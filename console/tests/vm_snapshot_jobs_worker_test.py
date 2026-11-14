# capability_id: console.vm-snapshot.durable-worker
"""Real Console SQL + the sealed SDK; server is an explicit LOCAL RPC fixture."""
import copy
import ast
import hashlib
import json
import os
from pathlib import Path
import socket
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest import TestCase, mock

import urllib3
from django.conf import settings
from django.db import DatabaseError, connections, transaction

from console.tests import vm_restore_journal_test as fixtures
from console.models.main import ComponentK8sAttributes
from console.services.vm_restore_journal import JournalConflict, TrustedContext
from console.services.vm_restore_worker import VMJobRunner
from console.services.vm_snapshot_jobs import SnapshotJobService
from www.models.main import Tenants, TenantServiceInfo, TenantServiceVolume


def actual_snapshot_sdk():
    path = Path(os.environ['VM_SNAPSHOT_SDK_SOURCE'])
    require_hash = 'bdf1bc91503bf34ad0734f840c145fc1a491586c4495d0c29099f41b56332831'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == require_hash
    from www.apiclient import regionapi
    from addict import Dict as AttributeDict
    # Assemble only the owner's frozen snapshot methods on the actual current
    # base client; unrelated SDK methods belong to a different runtime base.
    names = {
        'create_vm_snapshot', '_vm_snapshot_request', '_validated_vm_snapshot_request_id', 'command_vm_snapshot',
        '_validated_vm_snapshot_name', '_vm_snapshot_access', 'get_vm_snapshot'
    }
    original = next(
        node for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef) and node.name == 'RegionInvokeApi')
    methods = [node for node in original.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    assembled = ast.Module(body=[
        ast.ClassDef(name='RegionInvokeApi',
                     bases=[ast.Name(id='_SDKBase', ctx=ast.Load())],
                     keywords=[],
                     body=methods,
                     decorator_list=[])
    ],
                           type_ignores=[])
    namespace = dict(vars(regionapi), _SDKBase=regionapi.RegionInvokeApi, AttributeDict=AttributeDict)
    exec(compile(ast.fix_missing_locations(assembled), str(path), 'exec'), namespace)
    return namespace['RegionInvokeApi']()


class SnapshotLoopback:
    """LOCAL protocol fixture. It does not qualify or execute native storage."""
    def __init__(self, document):
        self.document = copy.deepcopy(document)
        self.calls = []
        self.original = None
        self.stage = ''
        self.mode = ''
        self.omit_source = False
        self.omit_accepted = False
        self.foreign_operation = False
        self.new_fence = False
        self.same_fence = False
        self.accepted = ''
        self.reject_prepare = False
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                fixture.calls.append(('GET', inner.path, None))
                if fixture.original is None:
                    inner.respond(404, {'error': {'code': 'vm_snapshot_not_found', 'retryable': False}})
                else:
                    inner.respond(200, fixture.dto())

            def do_POST(inner):
                body = json.loads(inner.rfile.read(int(inner.headers['Content-Length'])))
                fixture.calls.append(('POST', inner.path, body))
                if inner.path.endswith('/vm-snapshots'):
                    if fixture.reject_prepare:
                        inner.respond(422, {'error': {'code': 'vm_snapshot_storage_unsupported', 'retryable': False}})
                        return
                    if fixture.original is not None and fixture.original != body:
                        inner.respond(409, {'error': {'code': 'vm_restore_conflict', 'retryable': False}})
                        return
                    fixture.original = body
                    fixture.stage = 'prepared'
                elif inner.path.endswith('/halt'):
                    fixture.stage = 'stopped'
                elif inner.path.endswith('/create'):
                    fixture.stage = 'ready'
                elif inner.path.endswith('/resume') or inner.path.endswith('/finalize'):
                    if body['manifest_id'] != fixture.original['manifest_id']:
                        inner.respond(409, {'error': {'code': 'vm_restore_conflict', 'retryable': False}})
                        return
                    fixture.accepted = body['manifest_document_hash']
                    fixture.stage = 'running' if inner.path.endswith('/resume') else 'finalized'
                mode, fixture.mode = fixture.mode, ''
                if mode == 'lost':
                    inner.connection.shutdown(socket.SHUT_RDWR)
                    inner.connection.close()
                    return
                inner.respond(202, fixture.dto())

            def respond(inner, status, value):
                data = json.dumps({'bean': value}).encode()
                inner.send_response(status)
                inner.send_header('Content-Length', str(len(data)))
                inner.end_headers()
                inner.wfile.write(data)

            def log_message(inner, *_args):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()

    def dto(self):
        ready = self.stage in ('ready', 'running', 'finalized')
        running = self.stage in ('prepared', 'running', 'finalized')
        value = dict(operation_id=self.original['request_id'],
                     snapshot_name=self.original['name'],
                     description=self.original['description'],
                     core_hash='a' * 64,
                     source_vm_uid='vm-uid-a',
                     namespace='team-a',
                     source_vm_name='vm-a',
                     manifest_id=self.original['manifest_id'],
                     phase='ready' if ready else self.stage,
                     ready_to_use=ready,
                     was_running=True,
                     power_after=self.original['power_after'],
                     source_stopped=not running,
                     source_running=running,
                     source_lock_clear=True,
                     manifest_acked=bool(self.accepted),
                     finalized=self.stage == 'finalized',
                     cancelled=False,
                     deleted=False,
                     fence_owned=self.stage != 'finalized',
                     fence_cleared=self.stage == 'finalized',
                     consistency='offline',
                     snapshot_uid='',
                     coverage=dict(complete=ready,
                                   expected_writable_disks=1,
                                   included_disks=1 if ready else 0,
                                   missing_disk_keys=[] if ready else ['root'],
                                   excluded_read_only=[]))
        if ready:
            value.update(copy.deepcopy(self.document))
        if self.accepted and not self.omit_accepted:
            value['manifest_document_hash'] = self.accepted
        if self.stage == 'finalized':
            value['finalized_control_revision'] = 9
        if self.omit_source:
            for key in ('namespace', 'source_vm_name', 'fence_owned', 'fence_cleared'):
                value.pop(key, None)
        if self.foreign_operation:
            value['operation_id'] = 'foreign-operation'
        if self.new_fence:
            value['fence_owned'], value['fence_cleared'] = False, False
        if self.same_fence:
            value['fence_owned'], value['fence_cleared'] = True, False
        return value

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        assert not self.thread.is_alive()


class SnapshotJobsWorkerTests(TestCase):
    setUp = fixtures.VMRestoreJournalTestCase.setUp
    close_database = fixtures.VMRestoreJournalTestCase.close_database

    def configure(self):
        self.service.extend_method = 'vm'
        self.service.min_cpu, self.service.min_memory = 1000, 1024
        self.service.save()
        with self.database.schema_editor() as schema:
            schema.create_model(TenantServiceVolume)
            schema.create_model(Tenants)
        Tenants.objects.using(self.alias).create(tenant_id='tenant-a', tenant_name='team-a', namespace='team-a')
        TenantServiceVolume.objects.using(self.alias).create(ID=101,
                                                             service_id='service-a',
                                                             volume_name='root',
                                                             volume_path='/disk',
                                                             volume_type='csi-a',
                                                             volume_capacity=1)
        layout = [{
            'disk_key': 'root',
            'disk_name': 'system-disk',
            'disk_role': 'root',
            'device_type': 'disk',
            'source_kind': 'volume',
            'order_index': 0,
            'boot': True
        }]
        for name, kind, value in [('vm_boot_mode', 'string', 'bios'), ('vm_disk_layout', 'json', json.dumps(layout))]:
            ComponentK8sAttributes.objects.create(tenant_id='tenant-a',
                                                  component_id='service-a',
                                                  name=name,
                                                  save_type=kind,
                                                  attribute_value=value)
        self.selection = dict(request_id='job-a', name='snapshot-a', description='', power_after='previous')
        self.jobs = SnapshotJobService(self.journal)

    def transport(self):
        self.server = SnapshotLoopback(self.document)
        self.addCleanup(self.server.close)
        self.client = actual_snapshot_sdk()
        pool = urllib3.PoolManager()
        self.addCleanup(pool.clear)
        for patcher in [
                mock.patch.object(self.client,
                                  '_RegionInvokeApi__get_region_access_info',
                                  return_value=('http://127.0.0.1:{}'.format(self.server.server.server_port), '')),
                mock.patch.object(self.client,
                                  '_RegionInvokeApi__get_tenant_region_info',
                                  return_value=SimpleNamespace(region_tenant_name='team-a')),
                mock.patch.object(self.client, 'get_client', return_value=pool),
                mock.patch.dict(settings.MODULES, {'RegionToken': False}),
                mock.patch('www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name',
                           return_value=SimpleNamespace(region_name='region-a'))
        ]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_job(self, now, owner='worker-a'):
        VMJobRunner(journal=self.journal, snapshot_client=self.client, owner=owner, clock=lambda: now).process(
            self.ctx, 'job-a')
        return self.journal.read_operation(self.ctx, 'job-a')

    def test_submit_is_real_sql_durable_idempotent_and_never_dispatches_prepare(self):
        self.configure()
        self.transport()
        first = self.jobs.submit(self.ctx, self.selection, '42')
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_job-a')
        original = row.attribute_value
        self.assertFalse(first['complete'])
        self.assertEqual((first['operation_id'], first['request_id']), ('job-a', 'job-a'))
        self.assertEqual(self.jobs.submit(self.ctx, self.selection, '42'), first)
        row.refresh_from_db()
        self.assertEqual(row.attribute_value, original)
        self.assertEqual(self.server.calls, [])
        for changed, actor in [(self.selection, '43'), ({
                **self.selection, 'name': 'changed'
        }, '42'), ({
                **self.selection, 'operator': '42'
        }, '42')]:
            with self.subTest(changed=changed, actor=actor), self.assertRaises(JournalConflict):
                self.jobs.submit(self.ctx, changed, actor)
        row.refresh_from_db()
        self.assertEqual(row.attribute_value, original)

    def test_missing_or_go_byte_length_invalid_actor_and_client_scope_fields_are_refused(self):
        self.configure()
        for actor in (None, '', 'None', 'anonymous', 'system', 'x' * 41, '界' * 14, '\ud800'):
            with self.subTest(actor_type=type(actor).__name__), self.assertRaises(JournalConflict):
                self.jobs.submit(self.ctx, self.selection, actor)
        for key in ('namespace', 'trusted', 'operator'):
            with self.subTest(key=key), self.assertRaises(JournalConflict):
                self.jobs.submit(self.ctx, {**self.selection, key: 'forbidden'}, '42')
        self.assertEqual(self.journal.active_operation(self.ctx), '')

    def test_enqueue_sql_abort_and_outer_atomic_cannot_return_accepted(self):
        self.configure()
        with transaction.atomic(using=self.alias), self.assertRaises(JournalConflict):
            self.jobs.submit(self.ctx, self.selection, '42')
        with self.database.cursor() as cursor:
            cursor.execute('''CREATE TRIGGER abort_snapshot_enqueue BEFORE INSERT ON component_k8s_attributes
                WHEN NEW.name='vm_restore_operation_job-a' BEGIN SELECT RAISE(ABORT,'ENQUEUE_ABORT'); END''')
        try:
            with self.assertRaises(DatabaseError):
                self.jobs.submit(self.ctx, self.selection, '42')
        finally:
            with self.database.cursor() as cursor:
                cursor.execute('DROP TRIGGER abort_snapshot_enqueue')
        self.assertEqual(self.journal.active_operation(self.ctx), '')

    def test_go_description_utf8_limit_refuses_before_durable_enqueue(self):
        self.configure()
        for description in ('界' * 684, '\ud800'):
            with self.subTest(byte_limit=True), self.assertRaises(JournalConflict):
                self.jobs.submit(self.ctx, {**self.selection, 'description': description}, '42')
        self.assertEqual(self.journal.active_operation(self.ctx), '')

    def test_existing_three_field_request_read_preserves_bytes_and_cannot_gain_actor(self):
        self.configure()
        self.transport()
        body = {key: self.selection[key] for key in ('name', 'description', 'power_after')}
        self.journal.create_operation(self.ctx, 'job-a', 'job-a', 'snapshot', request=body)
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_job-a')
        original = row.attribute_value
        self.jobs.status(self.ctx, 'job-a')
        row.refresh_from_db()
        self.assertEqual(row.attribute_value, original)
        with self.assertRaises(JournalConflict):
            self.jobs.submit(self.ctx, self.selection, '42')
        self.run_job(100)
        saved = self.journal.read_operation(self.ctx, 'job-a')
        self.assertEqual(saved['request'], body)
        self.assertNotIn('operator', saved['request'])
        self.assertEqual(self.server.calls, [])

    def test_default_worker_is_unique_prepare_and_real_sql_seal_precedes_ack_and_terminal(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        for now in (100, 140, 180, 220, 260):
            self.run_job(now)
            self.assertFalse(self.jobs.status(self.ctx, 'job-a')['complete'])
            self.assertEqual(self.journal.active_operation(self.ctx), 'job-a')
        self.run_job(300)
        status = self.jobs.status(self.ctx, 'job-a')
        self.assertTrue(status['complete'])
        self.assertEqual(self.journal.active_operation(self.ctx), '')
        self.assertFalse(self.jobs.submit(self.ctx, self.selection, '42')['complete'])
        self.assertTrue(self.jobs.status(self.ctx, 'job-a')['complete'])
        posts = [call for call in self.server.calls if call[0] == 'POST']
        self.assertEqual(len([call for call in posts if call[1].endswith('/vm-snapshots')]), 1)
        self.assertEqual(
            posts[0][2], {
                **{
                    k: self.selection[k]
                    for k in ('name', 'description', 'power_after')
                }, 'operator': '42',
                'request_id': 'job-a',
                'manifest_id': 'job-a'
            })
        manifest = self.journal.read_manifest(self.ctx, 'snapshot-uid-a')
        for _method, path, body in posts:
            self.assertNotIn('expected_operation_epoch', body)
            if path.endswith('/resume') or path.endswith('/finalize'):
                self.assertEqual(body['manifest_document_hash'], manifest['document_hash'])
                self.assertEqual(body['manifest_id'], 'job-a')

    def test_actual_management_command_starts_default_dispatcher_and_scans_durable_jobs(self):
        from django.core.management import call_command
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        self.assertEqual(self.server.calls, [])
        handlers = {}
        published = []

        def install(signum, handler):
            handlers[signum] = handler
            return None

        def heartbeat(status):
            published.append(status)
            handlers[signal.SIGTERM](signal.SIGTERM, None)

        with mock.patch('console.services.vm_restore_worker.signal.signal', side_effect=install), \
                mock.patch('console.services.vm_restore_worker.vm_job_health.publish', side_effect=heartbeat), \
                mock.patch('console.services.vm_snapshot_job_worker.RegionInvokeApi', return_value=self.client):
            call_command('run_vm_restore_jobs', skip_checks=True)
        self.assertEqual(published, ['ready'])
        self.assertEqual(self.server.original['request_id'], 'job-a')
        self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST']), 1)

    def test_lost_prepare_response_restarts_owner_by_same_get_without_new_prepare(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        self.server.mode = 'lost'
        self.run_job(100)
        self.run_job(140, 'new-worker')
        saved = self.journal.read_operation(self.ctx, 'job-a')
        self.assertEqual(saved['request']['operator'], '42')
        self.assertEqual(saved['execution_epoch'], 2)
        self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST' and c[1].endswith('/vm-snapshots')]), 1)
        self.assertIsNone(saved['region_terminal'])

    def test_missing_source_projection_old_go_and_storage_refusal_never_progress(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        self.server.omit_source = True
        self.run_job(100)
        self.run_job(140, 'new-worker')
        self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST']), 1)
        self.assertFalse(self.jobs.status(self.ctx, 'job-a')['complete'])
        self.assertEqual(self.journal.active_operation(self.ctx), 'job-a')

    def test_finalized_bool_without_accepted_document_or_current_clear_proof_never_releases(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        for now in (100, 140, 180, 220, 260):
            self.run_job(now)
        self.server.omit_accepted = True
        self.run_job(300)
        self.assertFalse(self.jobs.status(self.ctx, 'job-a')['complete'])
        self.server.omit_accepted = False
        self.server.new_fence = True
        self.run_job(340, 'new-worker')
        status = self.jobs.status(self.ctx, 'job-a')
        self.assertEqual(self.journal.read_operation(self.ctx, 'job-a')['observation']['finalized_control_revision'], 9)
        self.assertFalse(status['fence_cleared'])
        self.assertTrue(status['complete'])
        self.assertEqual(self.journal.active_operation(self.ctx), '')
        self.assertFalse(any(c[1].endswith('/release') for c in self.server.calls))

    def test_storage_refusal_and_missing_sdk_never_fall_back_to_another_producer(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        self.server.reject_prepare = True
        self.run_job(100)
        self.run_job(140, 'new-worker')
        saved = self.journal.read_operation(self.ctx, 'job-a')
        self.assertEqual(saved['error_code'], 'CONFLICT')
        self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST']), 1)
        self.assertFalse(self.jobs.status(self.ctx, 'job-a')['complete'])
        self.assertEqual(self.journal.active_operation(self.ctx), 'job-a')

    def test_explicit_missing_snapshot_sdk_does_not_fall_back_to_legacy_write_or_read(self):
        self.configure()
        self.jobs.submit(self.ctx, self.selection, '42')
        with mock.patch('www.apiclient.regionapi.RegionInvokeApi._request') as request:
            VMJobRunner(journal=self.journal, snapshot_client=SimpleNamespace(), owner='worker-a', clock=lambda: 100).process(
                self.ctx, 'job-a')
        request.assert_not_called()
        saved = self.journal.read_operation(self.ctx, 'job-a')
        self.assertIsNone(saved['region_intent'])
        self.assertEqual(saved['error_code'], 'DEPENDENCY_PENDING')

    def test_noncanonical_legacy_request_id_never_becomes_a_new_go_key(self):
        self.configure()
        self.transport()
        body = {key: self.selection[key] for key in ('name', 'description', 'power_after')}
        body['operator'] = '42'
        self.journal.create_operation(self.ctx, 'job-a', 'legacy-ui-request', 'snapshot', request=body)
        self.run_job(100)
        self.assertEqual(self.server.calls, [])
        self.assertEqual(self.journal.read_operation(self.ctx, 'job-a')['request_id'], 'legacy-ui-request')

    def test_same_operation_owned_fence_after_finalize_cannot_finish_job(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        for now in (100, 140, 180, 220, 260):
            self.run_job(now)
        self.server.same_fence = True
        posts = len([c for c in self.server.calls if c[0] == 'POST'])
        self.run_job(300)
        status = self.jobs.status(self.ctx, 'job-a')
        self.assertEqual(self.journal.read_operation(self.ctx, 'job-a')['observation']['finalized_control_revision'], 9)
        self.assertTrue(status['fence_owned'])
        self.assertFalse(status['complete'])
        self.assertEqual(self.journal.active_operation(self.ctx), 'job-a')
        self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST']), posts)

    def test_foreign_same_name_result_cannot_replace_original_request_or_source(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        self.run_job(100)
        original = self.journal.read_operation(self.ctx, 'job-a')
        self.server.foreign_operation = True
        self.run_job(140, 'new-worker')
        saved = self.journal.read_operation(self.ctx, 'job-a')
        self.assertEqual(saved['request'], original['request'])
        self.assertEqual(saved['region_intent'], original['region_intent'])
        self.assertEqual(saved['error_code'], 'CONFLICT')
        self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST']), 1)

    def test_invalid_terminal_hash_or_revision_or_missing_proof_never_finishes(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        for now in (100, 140, 180, 220, 260):
            self.run_job(now)
        original = self.server.dto
        before = self.journal.read_operation(self.ctx, 'job-a')['request']
        self.server.dto = lambda: {**original(), 'finalized_control_revision': 0}
        self.run_job(300)
        self.assertFalse(self.jobs.status(self.ctx, 'job-a')['complete'])
        self.assertEqual(self.journal.read_operation(self.ctx, 'job-a')['request'], before)

    def test_two_live_owners_cannot_both_dispatch_prepare(self):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        with tempfile.TemporaryDirectory(prefix='snapshot-owner-') as directory:
            path = Path(directory) / 'console.sqlite3'
            with sqlite3.connect(path) as raw:
                self.database.connection.backup(raw)
            alias = 'snapshot_owner_control'
            connections.databases[alias] = dict(connections.databases['default'], NAME=str(path))
            entered, release = threading.Event(), threading.Event()
            errors = []
            actual = self.client.create_vm_snapshot

            def blocked(*args, **kwargs):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('LOCAL owner barrier timed out')
                return actual(*args, **kwargs)

            self.client.create_vm_snapshot = blocked
            try:
                with ExitStack() as stack:
                    for model in (TenantServiceInfo, ComponentK8sAttributes):
                        stack.enter_context(mock.patch.object(model, 'objects', model.objects.db_manager(alias)))
                    ctx = TrustedContext(TenantServiceInfo.objects.get(service_id='service-a'))

                    def first():
                        try:
                            VMJobRunner(journal=self.journal, snapshot_client=self.client, owner='owner-a',
                                        clock=lambda: 100).process(ctx, 'job-a')
                        except Exception as error:
                            errors.append(type(error).__name__)
                        finally:
                            connections[alias].close()

                    thread = threading.Thread(target=first)
                    thread.start()
                    try:
                        self.assertTrue(entered.wait(5))
                        with self.assertRaises(JournalConflict):
                            VMJobRunner(journal=self.journal, snapshot_client=self.client, owner='owner-b',
                                        clock=lambda: 101).process(ctx, 'job-a')
                    finally:
                        release.set()
                        thread.join(timeout=8)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(errors, [])
            finally:
                connections[alias].close()
                del connections[alias]
                connections.databases.pop(alias, None)
            self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST']), 1)

    def exercise_os_restart(self, crash):
        self.configure()
        self.transport()
        self.jobs.submit(self.ctx, self.selection, '42')
        with tempfile.TemporaryDirectory(prefix='snapshot-process-') as directory:
            database = Path(directory) / 'console.sqlite3'
            with sqlite3.connect(database) as raw:
                self.database.connection.backup(raw)
            command = [
                sys.executable, '-B', '-c', SNAPSHOT_CHILD,
                str(database), 'http://127.0.0.1:{}'.format(self.server.server.server_port)
            ]
            first = subprocess.run(command + [crash, '100'], capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 23 if crash == 'before-post' else 24)
            second = subprocess.run(command + ['none', '140'], capture_output=True, text=True, timeout=15)
            self.assertEqual(second.returncode, 0)
            with sqlite3.connect(database) as raw:
                saved = json.loads(
                    raw.execute('SELECT attribute_value FROM component_k8s_attributes WHERE name=?',
                                ('vm_restore_operation_job-a', )).fetchone()[0])
            self.assertEqual(saved['execution_epoch'], 2)
            self.assertEqual(saved['request'], {
                **{
                    k: self.selection[k]
                    for k in ('name', 'description', 'power_after')
                }, 'operator': '42'
            })
            self.assertIsNone(saved['region_terminal'])
            prepares = [c[2] for c in self.server.calls if c[0] == 'POST' and c[1].endswith('/vm-snapshots')]
            self.assertEqual(len(prepares), 1)
            self.assertEqual(prepares[0]['request_id'], 'job-a')
            self.assertEqual(prepares[0]['operator'], '42')

    def test_os_exit_after_durable_intent_before_prepare_keeps_original_body(self):
        self.exercise_os_restart('before-post')

    def test_os_exit_after_prepare_before_record_observes_original_operation(self):
        self.exercise_os_restart('after-post')


SNAPSHOT_CHILD = r'''
import os,sys
from types import SimpleNamespace
from unittest import mock
from console.tests.vm_snapshot_jobs_worker_test import actual_snapshot_sdk
from django.conf import settings
from django.db import connections
from console.models.main import ComponentK8sAttributes
from www.models.main import TenantServiceInfo
from console.services.vm_restore_journal import TrustedContext
from console.services.vm_restore_worker import VMJobRunner
import urllib3
path,endpoint,crash,now=sys.argv[1:]
connections.databases['snapshot_child']=dict(connections.databases['default'],NAME=path)
client=actual_snapshot_sdk()
pool=urllib3.PoolManager()
original=client.create_vm_snapshot
def post(*args,**kwargs):
    if crash=='before-post': os._exit(23)
    result=original(*args,**kwargs)
    if crash=='after-post': os._exit(24)
    return result
client.create_vm_snapshot=post
with mock.patch.object(TenantServiceInfo,'objects',TenantServiceInfo.objects.db_manager('snapshot_child')), \
     mock.patch.object(ComponentK8sAttributes,'objects',ComponentK8sAttributes.objects.db_manager('snapshot_child')), \
     mock.patch.object(client,'_RegionInvokeApi__get_region_access_info',return_value=(endpoint,'')), \
     mock.patch.object(client,'_RegionInvokeApi__get_tenant_region_info',
                       return_value=SimpleNamespace(region_tenant_name='team-a')), \
     mock.patch.object(client,'get_client',return_value=pool), \
     mock.patch.dict(settings.MODULES,{'RegionToken':False}), \
     mock.patch('www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name',
                return_value=SimpleNamespace(region_name='region-a')):
    ctx=TrustedContext(TenantServiceInfo.objects.get(service_id='service-a'))
    runner=VMJobRunner(snapshot_client=client,owner='first' if crash!='none' else 'restarted',clock=lambda:int(now))
    runner.process(ctx,'job-a')
pool.clear()
connections.close_all()
'''


class SnapshotJobsHTTPStatusTests(TestCase):
    from console.tests import vm_snapshot_read_api_test as api_fixture
    setUp = api_fixture.VMSnapshotReadAPITestCase.setUp
    components = api_fixture.VMSnapshotReadAPITestCase.components
    application = api_fixture.VMSnapshotReadAPITestCase.application
    transport = api_fixture.VMSnapshotReadAPITestCase.transport

    def job(self):
        fixture = SnapshotJobsWorkerTests('test_submit_is_real_sql_durable_idempotent_and_never_dispatches_prepare')
        fixture.setUp()
        fixture.configure()
        self.addCleanup(fixture.doCleanups)
        fixture.service.tenant_id = 'team-a'
        fixture.service.save()
        ComponentK8sAttributes.objects.update(tenant_id='team-a')
        fixture.ctx = TrustedContext(fixture.service)
        fixture.jobs.submit(fixture.ctx, fixture.selection, '42')
        self.component = fixture.service
        return fixture

    def get(self, operation='job-a', tenant='team-a', region='region-a', alias='vm-a'):
        from django.urls import resolve
        from rest_framework.test import force_authenticate
        path = '/console/teams/{}/apps/{}/vm-jobs/{}'.format(tenant, alias, operation)
        match = resolve(path)
        request = self.factory.get(path, {'region_name': region, 'expected_request_id': 'forged-query-id'})
        force_authenticate(request, self.user)
        return match.func(request, **match.kwargs)

    def test_existing_status_route_delegates_only_canonical_snapshot_and_never_advances(self):
        fixture = self.job()
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_job-a')
        before = row.attribute_value
        result = self.get()
        self.assertEqual(result.status_code, 200)
        public = result.data['data']['bean']
        self.assertEqual(public['request_id'], 'job-a')
        self.assertFalse(public['complete'])
        for key in ('request', 'operator', 'manifest', 'core_hash', 'native_proof_hash', 'region_intent',
                    'finalized_control_revision'):
            self.assertNotIn(key, public)
        row.refresh_from_db()
        self.assertEqual(row.attribute_value, before)
        self.request.assert_not_called()
        self.assertEqual(fixture.journal.active_operation(fixture.ctx), 'job-a')

    def test_status_wrong_scope_or_id_refuses_without_query_identity_echo(self):
        self.job()
        self.assertIn(self.get(tenant='team-b').status_code, (403, 404))
        self.assertIn(self.get(alias='vm-b').status_code, (403, 404))
        self.assertIn(self.get(region='wrong-region').status_code, (403, 404, 409))
        self.assertEqual(self.get(operation='wrong-id').status_code, 409)
        self.request.assert_not_called()
