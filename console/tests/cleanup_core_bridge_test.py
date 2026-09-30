import hashlib
import hmac
import json
import unittest

from console.services.cleanup_core_bridge import decode_core_request, verify_core_request


class CleanupCoreBridgeTests(unittest.TestCase):
    def test_only_fixed_cleanup_operations_are_forwardable(self):
        for path in [
                '/v2/cleanup/managed-cache/inventory', '/v2/cleanup/managed-packages/prepare',
                '/v2/cleanup/stores/s/operations', '/v2/cleanup/stores/s/observation-permit',
                '/v2/cleanup/stores/s/operations/o/node/recover', '/v2/cleanup/stores/s/operations/o/maintenance/job/status'
        ]:
            raw = json.dumps({'path': path, 'body': '{}'}).encode()
            self.assertEqual(decode_core_request(raw), (path, b'{}'))
        for path in [
                'https://foreign.invalid/v2/cleanup/stores/discover', '/v2/tenants/team/services',
                '/v2/cleanup/reference-writers/console',
                '/v2/cleanup/stores/s/force-ready', '/v2/cleanup/stores/s/operations/o/../../delete',
                '/v2/cleanup/stores/s/operations/o/node/status?other=true', '/v2/cleanup/stores/%2e%2e/status'
        ]:
            with self.assertRaises(ValueError):
                decode_core_request(json.dumps({'path': path, 'body': '{}'}).encode())

    # capability_id: console.cleanup.coordination-signature
    def test_signature_binds_scope_path_time_and_exact_body(self):
        key = b'isolated-fixture-' * 4
        path = '/console/cleanup/internal/coordination/e/r'
        body = b'{"path":"/v2/cleanup/managed-cache/prepare","body":"{}"}'
        payload = '\n'.join(['cleanup-coordination-v1', 'POST', path, 'e', 'r', '100',
                             hashlib.sha256(body).hexdigest()]).encode()
        signature = hmac.new(key, payload, hashlib.sha256).hexdigest()
        self.assertTrue(verify_core_request(path, 'e', 'r', '100', signature, body, key, now=100))
        for candidate_path, enterprise, region, candidate_body, now in [(path, 'other', 'r', body, 100),
                                                                        (path, 'e', 'other', body, 100),
                                                                        (path + '?x=1', 'e', 'r', body, 100),
                                                                        (path, 'e', 'r', body + b' ', 100),
                                                                        (path, 'e', 'r', body, 200)]:
            self.assertFalse(
                verify_core_request(candidate_path, enterprise, region, '100', signature, candidate_body, key, now=now))

    def test_payload_is_bounded_and_cannot_add_headers_or_urls(self):
        for body in [
                b'{}', b'[]', b'x' * 65537,
                json.dumps({
                    'path': '/v2/cleanup/stores/discover',
                    'body': '[]'
                }).encode(),
                json.dumps({
                    'path': '/v2/cleanup/stores/discover',
                    'body': '{}',
                    'headers': {
                        'Authorization': 'caller-claim'
                    }
                }).encode()
        ]:
            with self.assertRaises(ValueError):
                decode_core_request(body)


class CleanupCoreForwardingTests(unittest.TestCase):
    # capability_id: console.cleanup.coordination-upstream
    def test_forwarder_uses_verified_tls_without_retries_or_caller_headers(self):
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock
        from typing import Any, Dict, Tuple
        path = Path(__file__).resolve().parents[2] / 'www/apiclient/regionapi.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'RegionInvokeApi')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in (
            'cleanup_proxy_request', '_cleanup_control_request', 'register_cleanup_console_writer')]
        isolated = ast.ClassDef(name='RegionInvokeApi', bases=[], keywords=[], body=methods, decorator_list=[])
        config = SimpleNamespace(verify_ssl=False)

        class Unavailable(Exception):
            def __init__(self, message, status_code):
                super().__init__(message)
                self.status_code = status_code

        scope = {
            'Any': Any,
            'Dict': Dict,
            'Tuple': Tuple,
            'json': json,
            're': __import__('re'),
            'Configuration': lambda _: config,
            'ServiceHandleException': Unavailable,
            'urllib3': SimpleNamespace(Timeout=lambda **kwargs: kwargs)
        }
        exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), scope)
        api = scope['RegionInvokeApi']()
        api.get_region_info = Mock(return_value=SimpleNamespace(url='https://core.invalid'))
        api._RegionInvokeApi__get_region_access_info_by_enterprise_id = Mock(return_value=('https://core.invalid',
                                                                                           'Token isolated-fixture'))
        response = SimpleNamespace(status=409, read=Mock(return_value=b'{"msg":"COORDINATION_BUSY"}'), release_conn=Mock())
        client = SimpleNamespace(request=Mock(return_value=response), clear=Mock())
        api.create_client = Mock(return_value=client)
        status, result = api.cleanup_proxy_request('e', 'r', '/v2/cleanup/stores/discover', b'{}')
        self.assertEqual((status, result), (409, {'msg': 'COORDINATION_BUSY'}))
        self.assertTrue(config.verify_ssl)
        kwargs = client.request.call_args.kwargs
        self.assertFalse(kwargs['retries'])
        self.assertFalse(kwargs['redirect'])
        self.assertEqual(set(kwargs['headers']), {'Authorization', 'Content-Type'})
        self.assertEqual(kwargs['body'], b'{}')
        response.release_conn.assert_called_once()
        client.clear.assert_called_once()
        api._RegionInvokeApi__get_region_access_info_by_enterprise_id.return_value = ('https://core.invalid', '')
        config.cert_file = '/fixture/client.crt'
        config.key_file = '/fixture/client.key'
        self.assertEqual(api.cleanup_proxy_request('e', 'r', '/v2/cleanup/stores/discover', b'{}')[0], 409)
        self.assertEqual(client.request.call_args.kwargs['headers'], {'Content-Type': 'application/json'})
        self.assertTrue(config.verify_ssl)
        config.key_file = ''
        previous_calls = client.request.call_count
        with self.assertRaises(Unavailable):
            api.cleanup_proxy_request('e', 'r', '/v2/cleanup/stores/discover', b'{}')
        self.assertEqual(client.request.call_count, previous_calls)
        config.key_file = '/fixture/client.key'
        self.assertEqual(api.register_cleanup_console_writer('e', 'r', 'console-pod', 'pod-uid')[0], 409)
        self.assertTrue(client.request.call_args.args[1].endswith('/v2/cleanup/reference-writers/console'))
        self.assertEqual(json.loads(client.request.call_args.kwargs['body']), {
            'pod': 'console-pod', 'pod_uid': 'pod-uid', 'protocol': 'registry-reference-v1'})
        client.request.side_effect = RuntimeError('private-fixture-detail')
        with self.assertRaises(Unavailable) as error:
            api.cleanup_proxy_request('e', 'r', '/v2/cleanup/stores/discover', b'{}')
        self.assertNotIn('private-fixture-detail', str(error.exception))

    # capability_id: console.cleanup.coordination-view
    def test_view_rejects_browser_credentials_and_forwards_only_signed_envelopes(self):
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock
        from console.services.cleanup_gateway import CleanupGatewayUnavailable
        path = Path(__file__).resolve().parents[1] / 'views/cleanup_core_bridge.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef))
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'post')
        key = b'isolated-fixture-' * 4
        api = SimpleNamespace(cleanup_proxy_request=Mock(return_value=(200, {'bean': {'protocol': 1}})))
        factory = Mock(return_value=api)
        scope = {
            'os': SimpleNamespace(environ={}),
            'Request': object,
            'Response': lambda value, status: SimpleNamespace(data=value, status_code=status),
            'decode_core_request': decode_core_request,
            'verify_core_request': verify_core_request,
            'resolve_gateway_key': Mock(return_value=key),
            'CleanupGatewayUnavailable': CleanupGatewayUnavailable,
            'RegionInvokeApi': factory
        }
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), scope)
        request_path = '/console/cleanup/internal/coordination/e/r'
        raw = b'{"path":"/v2/cleanup/stores/discover","body":"{}"}'
        request = SimpleNamespace(META={},
                                  body=raw,
                                  headers={'Cookie': 'browser-session', 'Authorization': 'caller'},
                                  get_full_path=lambda: request_path)
        view = SimpleNamespace(resolve_key=scope['resolve_gateway_key'])
        self.assertEqual(scope['post'](view, request, 'e', 'r').status_code, 403)
        factory.assert_not_called()
        import time
        issued = str(int(time.time()))
        payload = '\n'.join(
            ['cleanup-coordination-v1', 'POST', request_path, 'e', 'r', issued,
             hashlib.sha256(raw).hexdigest()]).encode()
        request.headers = {
            'X-Cleanup-Coordination-Time': issued,
            'X-Cleanup-Coordination-Signature': hmac.new(key, payload, hashlib.sha256).hexdigest()
        }
        self.assertEqual(scope['post'](view, request, 'e', 'r').status_code, 200)
        api.cleanup_proxy_request.assert_called_once_with('e', 'r', '/v2/cleanup/stores/discover', b'{}')

        # A plugin signature cannot be replayed to the independently keyed system URL.
        request.get_full_path = lambda: '/console/cleanup/internal/system-coordination/e/r'
        self.assertEqual(scope['post'](SimpleNamespace(resolve_key=lambda *_: key), request, 'e', 'r').status_code, 403)
        system_resolver = Mock(side_effect=CleanupGatewayUnavailable())
        self.assertEqual(scope['post'](SimpleNamespace(resolve_key=system_resolver), request, 'e', 'r').status_code, 503)
        self.assertEqual(api.cleanup_proxy_request.call_count, 1)
        # The routed subclass selects only the system resolver, with no plugin fallback.
        subclass = next(n for n in ast.parse(path.read_text()).body
                        if isinstance(n, ast.ClassDef) and n.name == 'CleanupSystemCoreBridgeView')
        scope.update(CleanupCoreBridgeView=object, resolve_system_coordination_key=system_resolver)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[subclass], type_ignores=[])), str(path), 'exec'), scope)
        self.assertIs(scope['CleanupSystemCoreBridgeView']().resolve_key, system_resolver)

        import os
        system_key = os.urandom(64)
        payload = '\n'.join(['cleanup-coordination-v1', 'POST', request.get_full_path(), 'e', 'r', issued,
                             hashlib.sha256(raw).hexdigest()]).encode()
        request.headers['X-Cleanup-Coordination-Signature'] = hmac.new(system_key, payload, hashlib.sha256).hexdigest()
        system_resolver.side_effect = None
        system_resolver.return_value = system_key
        self.assertEqual(scope['post'](scope['CleanupSystemCoreBridgeView'](), request, 'e', 'r').status_code, 200)
        self.assertEqual(api.cleanup_proxy_request.call_count, 2)
