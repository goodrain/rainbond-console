# capability_id: console.vm-restore.command-worker
import copy
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest import TestCase, mock

import urllib3
from django.conf import settings

from console.tests import vm_restore_command_journal_test as journal_fixtures
from console.tests import vm_restore_config_v11_test as configuration_fixtures
from console.services.vm_restore_journal import JournalConflict
from www.apiclient.regionapi import RegionInvokeApi


class RestoreLoopback:
    """Explicit RPC-contract server fixture, not a qualified Go/VM provider."""
    def __init__(self, manifest):
        self.manifest = manifest
        self.calls = []
        self.exists = False
        self.revision = 3
        self.epoch = 'c' * 64
        self.mode = 'applied'
        self.phase = 'prepared'
        self.applied_requests = set()
        self.pending_requests = set()
        self.status = None
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                fixture.calls.append(('GET', inner.path, None))
                if inner.path.endswith('/vm-restore-control'):
                    inner.respond(
                        200, {
                            'bean': {
                                'control_revision': fixture.revision,
                                'binding_generation': 2,
                                'fenced': fixture.exists,
                                'admission_in_progress': False,
                                **({
                                    'active_operation_id': 'restore-a'
                                } if fixture.exists else {})
                            }
                        })
                elif fixture.exists:
                    inner.respond(200, {'bean': fixture.dto()})
                else:
                    inner.respond(404, {'bean': {'error_code': 'vm_restore_not_found', 'retryable': False, 'complete': False}})

            def do_POST(inner):
                body = json.loads(inner.rfile.read(int(inner.headers['Content-Length'])))
                fixture.calls.append(('POST', inner.path, body))
                mode, fixture.mode = fixture.mode, 'applied'
                if mode == 'reject':
                    inner.respond(
                        422,
                        {'bean': {
                            'error_code': 'vm_restore_provider_not_qualified',
                            'retryable': False,
                            'complete': False
                        }})
                    return
                if mode == 'conflict':
                    fixture.revision += 1
                    inner.respond(409, {'bean': {'error_code': 'vm_restore_conflict', 'retryable': False, 'complete': False}})
                    return
                fingerprint = (inner.path, json.dumps(body, sort_keys=True, separators=(',', ':')))
                if fingerprint in fixture.applied_requests:
                    inner.respond(202, {'bean': fixture.dto(applied=True)})
                    return
                if fingerprint in fixture.pending_requests:
                    fixture.pending_requests.remove(fingerprint)
                    fixture.applied_requests.add(fingerprint)
                    fixture.revision += 1
                    inner.respond(202, {'bean': fixture.dto(applied=True)})
                    return
                if body['expected_control_revision'] != fixture.revision:
                    inner.respond(409, {'bean': {'error_code': 'vm_restore_conflict', 'retryable': False, 'complete': False}})
                    return
                fixture.exists = True
                fixture.revision += 1
                if mode == 'lost':
                    fixture.applied_requests.add(fingerprint)
                    inner.connection.shutdown(socket.SHUT_RDWR)
                    inner.connection.close()
                    return
                if mode == 'pending':
                    fixture.pending_requests.add(fingerprint)
                    inner.respond(202, {'bean': {'error_code': 'vm_restore_pending', 'retryable': True, 'complete': False}})
                    return
                fixture.phase = 'stopped' if inner.path.endswith('/halt') else 'prepared'
                fixture.applied_requests.add(fingerprint)
                inner.respond(202, {'bean': fixture.dto(applied=True)})

            def respond(inner, status, body):
                blob = json.dumps(body).encode()
                inner.send_response(status)
                inner.send_header('Content-Length', str(len(blob)))
                inner.end_headers()
                inner.wfile.write(blob)

            def log_message(inner, *_args):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()

    def dto(self, applied=False):
        m = self.manifest
        return dict(**configuration_fixtures.go_config_fixture(),
                    operation_id='restore-a',
                    operation_epoch=self.epoch,
                    target_vm_uid='target-vm-uid',
                    source=dict(snapshot_name=m['snapshot_name'],
                                snapshot_uid=m['snapshot_uid'],
                                content_uid=m['content_uid'],
                                vm_uid=m['source_vm']['uid'],
                                core_hash=m['core_hash'],
                                document_hash=m['document_hash']),
                    control_revision=self.revision,
                    binding_generation=2,
                    operation_binding_generation=2,
                    phase=self.phase,
                    applied=applied,
                    complete=False,
                    config_committed=False,
                    console_acked=False,
                    rollback_acked=False,
                    fence_owned=True,
                    fence_cleared=False,
                    snapshot_uid=m['snapshot_uid'],
                    retryable=False)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        assert not self.thread.is_alive()


class VMRestoreCommandWorkerTests(TestCase):
    setUp = journal_fixtures.VMRestoreCommandJournalTests.setUp
    close_database = journal_fixtures.VMRestoreCommandJournalTests.close_database
    begin = journal_fixtures.VMRestoreCommandJournalTests.begin
    seal = journal_fixtures.VMRestoreCommandJournalTests.seal
    restore_operation = journal_fixtures.VMRestoreCommandJournalTests.restore_operation

    def loopback(self):
        self.restore_operation()
        manifest = self.journal.read_manifest(self.ctx, 'snapshot-uid-a')
        server = RestoreLoopback(manifest)
        self.addCleanup(server.close)
        client, pool = RegionInvokeApi(), urllib3.PoolManager()
        self.addCleanup(pool.clear)
        patches = [
            mock.patch.object(client,
                              '_RegionInvokeApi__get_region_access_info',
                              return_value=('http://127.0.0.1:{}'.format(server.server.server_port), '')),
            mock.patch.object(client,
                              '_RegionInvokeApi__get_tenant_region_info',
                              return_value=SimpleNamespace(region_tenant_name='team-a')),
            mock.patch.object(client, 'get_client', return_value=pool),
            mock.patch.dict(settings.MODULES, {'RegionToken': False}),
            mock.patch('www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name',
                       return_value=SimpleNamespace(region_name='region-a')),
            mock.patch('console.services.vm_restore_command_worker.Tenants.objects.get',
                       return_value=SimpleNamespace(tenant_name='console-team'))
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return client, server

    def process(self, client, now=104, owner='worker-a'):
        from console.services.vm_restore_worker import VMJobRunner
        VMJobRunner(journal=self.journal, restore_client=client, owner=owner, clock=lambda: now).process(self.ctx, 'restore-a')
        return self.journal.read_operation(self.ctx, 'restore-a')

    def test_lost_prepare_reply_reconciles_original_op_and_server_epoch_after_lease_takeover(self):
        client, server = self.loopback()
        server.mode = 'lost'
        saved = self.process(client)
        self.assertEqual(saved['rpc']['pending']['state'], 'unknown')
        self.assertEqual(saved['rpc']['pending']['attempts'], 1)
        self.assertEqual(saved['rpc']['server_epoch'], '')
        saved = self.process(client, 140, 'worker-restarted')
        self.assertEqual(saved['execution_epoch'], 2)
        self.assertEqual(saved['rpc']['server_epoch'], server.epoch)
        self.assertEqual(saved['rpc']['completed'], ['prepare'])
        posts = [call for call in server.calls if call[0] == 'POST']
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0][1], posts[1][1])
        self.assertEqual(posts[0][2], posts[1][2], 'unknown replay must preserve the original complete request')
        self.assertNotIn('expected_operation_epoch', posts[1][2])
        self.assertEqual(posts[1][2]['expected_control_revision'], 3)
        self.assertEqual(self.journal.active_operation(self.ctx), 'restore-a')
        self.assertIsNone(saved['region_terminal'])

    def test_202_pending_and_409_only_replay_same_halt_after_fresh_matching_status(self):
        client, server = self.loopback()
        self.process(client)
        server.mode = 'pending'
        saved = self.process(client, 105)
        self.assertEqual(saved['rpc']['pending']['action'], 'halt')
        self.assertEqual(saved['rpc']['pending']['state'], 'pending')
        server.mode = 'conflict'
        saved = self.process(client, 140)
        self.assertEqual(saved['rpc']['pending']['state'], 'conflict')
        before_conflict_calls = len(server.calls)
        saved = self.process(client, 180)
        self.assertEqual(saved['rpc']['completed'], ['prepare'])
        self.assertEqual(saved['rpc']['pending']['state'], 'conflict')
        self.assertEqual(len(server.calls), before_conflict_calls)
        self.assertEqual(saved['phase'], 'prepared')
        self.assertIsNone(saved['region_terminal'])
        before = len(server.calls)
        self.process(client, 181)
        self.assertEqual(len(server.calls), before, 'missing configuration contract cannot issue commit or fake Ready')
        halts = [call for call in server.calls if call[0] == 'POST' and call[1].endswith('/halt')]
        self.assertEqual(len(halts), 2)
        self.assertTrue(all(call[2]['expected_operation_epoch'] == server.epoch for call in halts))
        self.assertEqual(halts[0][2], halts[1][2])

    def test_default_provider_refusal_remains_rejected_and_cannot_be_automatically_retried(self):
        client, server = self.loopback()
        server.mode = 'reject'
        saved = self.process(client)
        self.assertEqual(saved['rpc']['pending']['state'], 'rejected')
        self.assertEqual(saved['rpc']['pending']['http_status'], 422)
        self.assertEqual(
            self.journal.public_operation(self.ctx, 'restore-a')['command']['error_code'], 'vm_restore_provider_not_qualified')
        self.assertFalse(server.exists)
        before = len(server.calls)
        self.process(client, 140)
        self.assertEqual(len(server.calls), before)
        self.assertEqual(self.journal.active_operation(self.ctx), 'restore-a')
        saved = self.journal.claim(self.ctx, 'restore-a', 'worker-a', saved['revision'], 140, 30)
        self.journal.retry_rejected_restore_command(self.ctx, 'restore-a', 'worker-a', saved['execution_epoch'],
                                                    saved['revision'], 140)
        saved = self.process(client, 141)
        self.assertEqual(saved['rpc']['completed'], ['prepare'])
        self.assertTrue(all('/vm-restores/restore-a/' in call[1] for call in server.calls if call[0] == 'POST'))

    def test_foreign_epoch_source_or_target_after_prepare_never_sends_another_command(self):
        client, server = self.loopback()
        self.process(client)
        original = server.dto
        before = len([call for call in server.calls if call[0] == 'POST'])
        for key in ['operation_epoch', 'target_vm_uid', 'source']:

            def changed(applied=False):
                value = copy.deepcopy(original(applied))
                value[key] = ({
                    **value[key], 'content_uid': 'foreign-content'
                } if key == 'source' else 'd' * 64 if key == 'operation_epoch' else 'foreign-vm-uid')
                return value

            server.dto = changed
            with self.subTest(key=key), self.assertRaises(JournalConflict):
                self.process(client, 105)
        self.assertEqual(len([call for call in server.calls if call[0] == 'POST']), before)
        self.assertEqual(self.journal.active_operation(self.ctx), 'restore-a')

    def test_complete_get_is_not_an_ack_or_permission_to_release_the_console_job(self):
        client, server = self.loopback()
        self.process(client)
        original = server.dto

        def completed(applied=False):
            return {**original(applied), 'complete': True, 'fence_owned': False, 'fence_cleared': True, 'outcome': 'restored'}

        server.dto = completed
        saved = self.process(client, 105)
        self.assertTrue(saved['rpc']['observation']['complete'])
        self.assertIsNone(saved['region_terminal'])
        self.assertEqual(self.journal.active_operation(self.ctx), 'restore-a')
        self.assertNotIn(saved['phase'], ('runtime_verified', 'rolled_back', 'cancelled'))

    def test_post_completion_after_local_lease_expiry_cannot_overwrite_a_future_owner(self):
        from console.services.vm_restore_worker import VMJobRunner
        client, server = self.loopback()
        now = [104]
        original = client.command_vm_restore

        def delayed(*args, **kwargs):
            result = original(*args, **kwargs)
            now[0] = 200
            return result

        client.command_vm_restore = delayed
        with self.assertRaises(JournalConflict):
            VMJobRunner(journal=self.journal, restore_client=client, owner='worker-a', clock=lambda: now[0]).process(
                self.ctx, 'restore-a')
        saved = self.journal.read_operation(self.ctx, 'restore-a')
        self.assertEqual(saved['rpc']['pending']['state'], 'issued')
        self.assertEqual(saved['rpc']['server_epoch'], '')
        client.command_vm_restore = original
        saved = self.process(client, 201, 'new-owner')
        self.assertEqual(saved['rpc']['completed'], ['prepare'])
        self.assertEqual(saved['lease_owner'], 'new-owner')
        self.assertEqual(saved['rpc']['server_epoch'], server.epoch)

    def test_supervised_worker_scan_dispatches_the_durable_restore_through_actual_sdk(self):
        from console.services.vm_restore_worker import VMJobRunner
        client, server = self.loopback()
        VMJobRunner(journal=self.journal, restore_client=client, owner='worker-a', clock=lambda: 104).run_once()
        saved = self.journal.read_operation(self.ctx, 'restore-a')
        self.assertEqual(saved['rpc']['completed'], ['prepare'])
        self.assertEqual(len([call for call in server.calls if call[0] == 'POST']), 1)

    def test_changed_live_component_scope_cannot_send_rpc_under_old_context(self):
        client, server = self.loopback()
        self.service.service_region = 'foreign-region'
        self.service.save(update_fields=['service_region'])
        with self.assertRaises(JournalConflict):
            self.process(client)
        self.assertEqual(server.calls, [])

    def test_existing_receipt_missing_A_does_not_halt_or_allow_local_only_cancel(self):
        client, server = self.loopback()
        server.exists = True
        original = server.dto

        def legacy(applied=False):
            value = original(applied)
            value.pop('config_after')
            value['source_config_ready'] = False
            return value

        server.dto = legacy
        saved = self.process(client)
        self.assertFalse(saved['rpc']['observation']['source_config_ready'])
        self.assertNotIn('config_after', saved['rpc']['observation'])
        self.assertEqual([call for call in server.calls if call[0] == 'POST'], [])
        self.assertIsNotNone(saved['region_intent'])
        with self.assertRaises(JournalConflict):
            self.journal.advance(self.ctx, 'restore-a', 'worker-a', saved['execution_epoch'], saved['revision'], 'cancelled',
                                 104)
        self.assertEqual(self.journal.active_operation(self.ctx), 'restore-a')
