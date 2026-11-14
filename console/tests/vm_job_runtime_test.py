# capability_id: console.vm-jobs.durable-observation
from unittest import TestCase
from console.tests import vm_restore_journal_test as fixtures


class VMJobRuntimeTests(TestCase):
    setUp = fixtures.VMRestoreJournalTestCase.setUp
    close_database = fixtures.VMRestoreJournalTestCase.close_database

    def test_request_is_immutable_and_rejects_auth_material(self):
        request = {'name': 'snapshot-a', 'description': '', 'power_after': 'previous'}
        op = self.journal.create_operation(self.ctx, 'op-a', 'request-a', 'snapshot', request=request)
        request['name'] = 'changed'
        self.assertEqual(self.journal.read_operation(self.ctx, 'op-a')['request']['name'], 'snapshot-a')
        with self.assertRaises(Exception):
            self.journal.create_operation(self.ctx, 'op-a', 'request-a', 'snapshot', request=request)
        with self.assertRaises(Exception):
            self.journal.create_operation(self.ctx, 'op-b', 'request-b', 'snapshot', request={'jwt': 'forbidden'})
        self.assertEqual(op['phase'], 'pending')

    def test_worker_restarts_reclaims_and_persists_real_read_evidence(self):
        from console.services.vm_restore_worker import VMJobRunner
        request = {'name': 'snapshot-a', 'description': '', 'power_after': 'previous'}
        self.journal.create_operation(self.ctx, 'op-a', 'request-a', 'snapshot', request=request)
        op = self.journal.claim(self.ctx, 'op-a', 'old-worker', 1, 100, 2)
        self.journal.mark_region_issued(self.ctx, None, 'op-a', 'old-worker', op['execution_epoch'], op['revision'], '', 100)
        reads = []

        class Driver:
            def observe(inner, context, operation):
                reads.append(operation['operation_id'])
                return dict(operation_id='op-a',
                            snapshot_name='snapshot-a',
                            core_hash='a' * 64,
                            source_vm_uid='vm-uid-a',
                            snapshot_uid='',
                            phase='creating',
                            ready_to_use=False,
                            manifest_acked=False,
                            finalized=False,
                            error_code='')

        runner = VMJobRunner(journal=self.journal, driver=Driver(), owner='new-worker', clock=lambda: 103)
        runner.process(self.ctx, 'op-a')
        saved = self.journal.read_operation(self.ctx, 'op-a')
        self.assertEqual(saved['execution_epoch'], 2)
        self.assertEqual(saved['observation']['phase'], 'creating')
        self.assertEqual(saved['error_code'], 'DEPENDENCY_PENDING')
        self.assertIsNone(saved['region_terminal'])
        self.assertEqual(reads, ['op-a'])
        self.assertNotIn('source_vm_uid', str(self.journal.public_operation(self.ctx, 'op-a').get('observation')))

    def test_real_sdk_loopback_reconciles_lost_ack_without_false_terminal_release(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from types import SimpleNamespace
        import urllib3
        from django.conf import settings
        from console.services.vm_restore_worker import VMJobRunner, Go4SnapshotEvidence
        from www.apiclient.regionapi import RegionInvokeApi
        from unittest import mock
        self.journal.create_operation(self.ctx,
                                      'op-a',
                                      'request-a',
                                      'snapshot',
                                      request={
                                          'name': 'snapshot-a',
                                          'description': '',
                                          'power_after': 'previous'
                                      })
        op = self.journal.claim(self.ctx, 'op-a', 'old-worker', 1, 100, 2)
        self.journal.mark_region_issued(self.ctx, self.go, 'op-a', 'old-worker', op['execution_epoch'], op['revision'],
                                        'a' * 64, 100)
        hits = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                hits.append((inner.command, inner.path))
                body = json.dumps({
                    'bean': {
                        'operation_id': 'op-a',
                        'snapshot_name': 'snapshot-a',
                        'core_hash': 'a' * 64,
                        'source_vm_uid': 'vm-uid-a',
                        'snapshot_uid': 'snapshot-uid-a',
                        'phase': 'ready',
                        'ready_to_use': True,
                        'manifest_acked': True,
                        'finalized': True
                    }
                }).encode()
                inner.send_response(200)
                inner.send_header('Content-Length', str(len(body)))
                inner.end_headers()
                inner.wfile.write(body)

            def log_message(inner, *_args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        client = RegionInvokeApi()
        try:
            with mock.patch.object(
                    client,
                    '_RegionInvokeApi__get_region_access_info',
                    return_value=('http://127.0.0.1:{}'.format(server.server_port), '')), mock.patch.object(
                        client,
                        '_RegionInvokeApi__get_tenant_region_info',
                        return_value=SimpleNamespace(region_tenant_name='team-a')), mock.patch.object(
                            client, 'get_client', return_value=pool), mock.patch.dict(
                                settings.MODULES, {'RegionToken': False}), mock.patch(
                                    'console.services.vm_restore_worker.Tenants.objects.get',
                                    return_value=SimpleNamespace(tenant_name='console-team')), mock.patch(
                                        'www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name',
                                        return_value=SimpleNamespace(region_name='region-a')):
                VMJobRunner(journal=self.journal, driver=Go4SnapshotEvidence(client), owner='new-worker',
                            clock=lambda: 103).process(self.ctx, 'op-a')
            saved = self.journal.read_operation(self.ctx, 'op-a')
            self.assertTrue(saved['observation']['manifest_acked'])
            self.assertTrue(saved['observation']['finalized'])
            self.assertNotIn(saved['phase'], ('runtime_verified', 'rolled_back', 'cancelled'))
            self.assertIsNone(saved['region_terminal'])
            self.assertEqual(self.journal.active_operation(self.ctx), 'op-a')
            self.assertEqual(hits, [('GET', '/v2/tenants/team-a/services/vm-a/vm-snapshots/snapshot-a')])
        finally:
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

    def test_expired_owner_cannot_save_a_late_observation(self):
        from console.services.vm_restore_worker import VMJobRunner
        from console.services.vm_restore_journal import JournalConflict
        self.journal.create_operation(self.ctx,
                                      'op-a',
                                      'request-a',
                                      'snapshot',
                                      request={
                                          'name': 'snapshot-a',
                                          'description': '',
                                          'power_after': 'previous'
                                      })
        op = self.journal.claim(self.ctx, 'op-a', 'old-worker', 1, 100, 2)
        self.journal.mark_region_issued(self.ctx, None, 'op-a', 'old-worker', op['execution_epoch'], op['revision'], '', 100)
        current = [103]

        class Driver:
            def observe(inner, context, operation):
                current[0] = 140
                return dict(operation_id='op-a',
                            snapshot_name='snapshot-a',
                            core_hash='a' * 64,
                            source_vm_uid='vm-uid-a',
                            snapshot_uid='',
                            phase='creating',
                            ready_to_use=False,
                            manifest_acked=False,
                            finalized=False,
                            error_code='')

        with self.assertRaises(JournalConflict):
            VMJobRunner(journal=self.journal, driver=Driver(), owner='new-worker', clock=lambda: current[0]).process(
                self.ctx, 'op-a')
        self.assertNotIn('observation', self.journal.read_operation(self.ctx, 'op-a'))
