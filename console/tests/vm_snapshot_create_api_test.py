# -*- coding: utf-8 -*-
# capability_id: console.vm-snapshot.sdk-hooks
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import urllib3
from django.conf import settings
from unittest import TestCase, mock

from console.tests import vm_snapshot_read_api_test as reads


class VMSnapshotSDKHooksTestCase(TestCase):
    components = reads.VMSnapshotReadAPITestCase.components
    application = reads.VMSnapshotReadAPITestCase.application
    call = reads.VMSnapshotReadAPITestCase.call
    collection = reads.VMSnapshotReadAPITestCase.collection
    transport = reads.VMSnapshotReadAPITestCase.transport

    def setUp(self):
        reads.VMSnapshotReadAPITestCase.setUp(self)
        self.permissions = {42: [300002, 300003]}
        self.body = dict(name='point-a', description='Before update', request_id='request-one', power_after='previous')
        self.upstream_status = 202
        self.upstream_body = {
            'bean':
            dict(reads.snapshot(),
                 operation_id='request-one',
                 phase='prepared',
                 description='Before update',
                 power_after='previous')
        }
        patch = mock.patch('console.views.app_config.base.group_service.set_app_update_time_by_service')
        patch.start()
        self.addCleanup(patch.stop)
        audit = mock.patch('console.views.vm_snapshot.operation_log_service.create_log')
        self.audit = audit.start()
        self.addCleanup(audit.stop)

    def test_snapshot_command_uses_existing_routes_and_keeps_raw_worker_identity(self):
        self.upstream_status = 202
        self.upstream_body = {'bean': {'operation_id': 'request-one', 'native_proof_hash': 'raw-worker-proof'}}
        for action in ('halt', 'create', 'resume', 'finalize', 'cancel', 'delete'):
            command = {'operation_id': 'request-one', 'core_hash': 'a' * 64, 'request_id': 'request-one'}
            result, body = self.client.command_vm_snapshot('region-a', 'team-a', 'vm-a', 'point-a', action, command)
            self.assertEqual(result['status'], 202)
            self.assertEqual(body, self.upstream_body)
            args = self.request.call_args
            suffix = '/vm-snapshots/point-a' + ('' if action == 'delete' else '/' + action)
            self.assertTrue(args.args[0].endswith(suffix))
            self.assertEqual(args.args[1], 'DELETE' if action == 'delete' else 'POST')
            self.assertEqual(args.kwargs['retries'], 0)
        for action, body in [('ack', {}), ('halt', {
                'namespace': 'other'
        }), ('delete', []), ('create', {
                'operation_id': 'request-one',
                'force': True
        })]:
            self.request.reset_mock()
            with self.assertRaises(Exception):
                self.client.command_vm_snapshot('region-a', 'team-a', 'vm-a', 'point-a', action, body)
            self.request.assert_not_called()

    def test_real_loopback_sdk_post_reaches_prepare_once_and_preserves_matching_request(self):
        owner = self
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                value = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                captured.append((self.path, value))
                raw = json.dumps(owner.upstream_body).encode()
                self.send_response(202)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
        actual = RegionApiBaseHttpClient._request.__get__(self.client)
        try:
            with mock.patch.object(self.client, '_request', side_effect=actual), \
                    mock.patch.object(self.client, 'get_client', return_value=pool), \
                    mock.patch('www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name',
                               return_value=SimpleNamespace()), \
                    mock.patch.object(self.client, '_RegionInvokeApi__get_region_access_info',
                                      return_value=('http://127.0.0.1:' + str(server.server_port), '')), \
                    mock.patch.dict(settings.MODULES, {'RegionToken': False}):
                response, result = self.client.create_vm_snapshot('region-a', 'team-a', 'vm-a',
                                                                  dict(self.body, manifest_id='request-one', operator='17'))
            self.assertEqual(response['status'], 202)
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0][0], '/v2/tenants/region-team-a/services/vm-a/vm-snapshots')
            self.assertEqual(captured[0][1]['request_id'], captured[0][1]['manifest_id'])
            self.assertEqual(result['bean']['operation_id'], captured[0][1]['request_id'])
        finally:
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_snapshot_sdk_create_refuses_unrecognized_fields_without_any_request(self):
        with self.assertRaises(Exception):
            self.client.create_vm_snapshot('region-a', 'team-a', 'vm-a', {'name': 'point-a', 'namespace': 'other'})
        self.request.assert_not_called()

    def test_worker_hooks_keep_actual_non_success_status_and_full_raw_bean(self):
        self.upstream_status = 409
        self.upstream_body = {
            'code': 409,
            'msg': 'vm_snapshot_pending',
            'bean': {
                'error': {
                    'code': 'vm_snapshot_pending'
                },
                'operation_id': 'request-one',
                'manifest_id': 'request-one',
                'source_vm_name': 'worker-only-source'
            }
        }
        command = {'operation_id': 'request-one', 'core_hash': 'a' * 64, 'request_id': 'request-one'}
        status, value = self.client.command_vm_snapshot('region-a', 'team-a', 'vm-a', 'point-a', 'finalize', command)
        self.assertEqual(status['status'], 409)
        self.assertEqual(value, self.upstream_body)
        status, value = self.client.get_vm_snapshot('region-a', 'team-a', 'vm-a', 'point-a')
        self.assertEqual(status['status'], 409)
        self.assertEqual(value, self.upstream_body)
