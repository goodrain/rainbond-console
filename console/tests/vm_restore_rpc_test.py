# capability_id: console.vm-restore.region-rpc-v1
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest import TestCase, mock

from console.tests import vm_snapshot_read_api_test as bootstrap  # noqa: F401
import urllib3
from django.conf import settings
from www.apiclient.regionapi import RegionInvokeApi
from console.exception.main import ServiceHandleException


class VMRestoreRPCSDKTests(TestCase):
    def test_actual_sdk_loopback_preserves_control_pending_and_default_provider_refusal(self):
        hits = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                hits.append((inner.command, inner.path, None))
                if inner.path.endswith('/vm-restore-control'):
                    body = {
                        'control_revision': 9,
                        'binding_generation': 4,
                        'fenced': False,
                        'admission_in_progress': False,
                        'active_operation_id': ''
                    }
                    status = 200
                else:
                    body = {
                        'operation_id': 'restore-a',
                        'operation_epoch': 'a' * 64,
                        'complete': False,
                        'fence_cleared': False,
                        'fence_owned': True
                    }
                    status = 200
                inner.respond(status, {'bean': body})

            def do_POST(inner):
                body = json.loads(inner.rfile.read(int(inner.headers['Content-Length'])))
                hits.append((inner.command, inner.path, body))
                code = 'vm_restore_provider_not_qualified' if inner.path.endswith('/prepare') else 'vm_restore_outcome_unknown'
                inner.respond(422 if inner.path.endswith('/prepare') else 202, {
                    'msg': code,
                    'bean': {
                        'error_code': code,
                        'retryable': code.endswith('unknown'),
                        'complete': False
                    }
                })

            def respond(inner, status, body):
                blob = json.dumps(body).encode()
                inner.send_response(status)
                inner.send_header('Content-Length', str(len(blob)))
                inner.end_headers()
                inner.wfile.write(blob)

            def log_message(inner, *_args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        client, pool = RegionInvokeApi(), urllib3.PoolManager()
        try:
            with mock.patch.object(client, '_RegionInvokeApi__get_region_access_info',
                                   return_value=('http://127.0.0.1:{}'.format(server.server_port), '')), \
                    mock.patch.object(client, '_RegionInvokeApi__get_tenant_region_info',
                                      return_value=SimpleNamespace(region_tenant_name='team-a')), \
                    mock.patch.object(client, 'get_client', return_value=pool), \
                    mock.patch.dict(settings.MODULES, {'RegionToken': False}), \
                    mock.patch('www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name',
                               return_value=SimpleNamespace(region_name='region-a')):
                response, body = client.get_vm_restore_control('region-a', 'console-team', 'vm-a')
                self.assertEqual(response['status'], 200)
                self.assertEqual(body['bean']['control_revision'], 9)
                payload = {
                    'snapshot_name': 'snapshot-a',
                    'power_after': 'previous',
                    'expected_control_revision': 9,
                    'expected_binding_generation': 4
                }
                response, body = client.command_vm_restore('region-a', 'console-team', 'vm-a', 'restore-a', 'prepare', payload)
                self.assertEqual(response['status'], 422)
                self.assertEqual(body['bean']['error_code'], 'vm_restore_provider_not_qualified')
                response, body = client.get_vm_restore('region-a', 'console-team', 'vm-a', 'restore-a')
                self.assertFalse(body['bean']['complete'])
                payload = {
                    'expected_operation_epoch': 'a' * 64,
                    'expected_control_revision': 10,
                    'expected_binding_generation': 4
                }
                response, body = client.command_vm_restore('region-a', 'console-team', 'vm-a', 'restore-a', 'halt', payload)
                self.assertEqual(response['status'], 202)
                self.assertFalse(body['bean']['complete'])
                self.assertTrue(body['bean']['retryable'])
            self.assertEqual(hits[0][1], '/v2/tenants/team-a/services/vm-a/vm-restore-control')
            self.assertEqual(hits[1][1], '/v2/tenants/team-a/services/vm-a/vm-restores/restore-a/steps/prepare')
            self.assertEqual(hits[-1][2], payload)
        finally:
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

    def test_unknown_fields_wrong_epoch_and_untrusted_config_never_reach_transport(self):
        client = RegionInvokeApi()
        base = {'expected_control_revision': 0, 'expected_binding_generation': 0, 'expected_operation_epoch': 'a' * 64}
        bad = [('halt', {
            **base, 'namespace': 'foreign'
        }), ('halt', {
            **base, 'expected_operation_epoch': ''
        }), ('halt', {
            **base, 'expected_control_revision': True
        }), ('commit', {
            **base, 'config': {
                'cloud_init': 'blocked'
            }
        }), ('finalize', {
            **base, 'rollback': True,
            'cancelled': True
        })]
        with mock.patch.object(client, '_request') as transport:
            for action, body in bad:
                with self.subTest(action=action), self.assertRaises(ServiceHandleException):
                    client.command_vm_restore('region-a', 'team-a', 'vm-a', 'restore-a', action, body)
            for op in ['../other', '.', 'UPPER', 'x' * 64]:
                with self.subTest(op=op), self.assertRaises(ServiceHandleException):
                    client.get_vm_restore('region-a', 'team-a', 'vm-a', op)
            transport.assert_not_called()
