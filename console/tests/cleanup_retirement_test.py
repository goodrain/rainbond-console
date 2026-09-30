import hashlib
import hmac
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from console.services.cleanup_retirement import (
    verify_retirement_request, retirement_payload, validate_template_retirement,
    validate_upload_chunk_retirement, retire_upload_chunks, inspection_payload,
    verify_inspection_request, inspect_upload_chunks, inspect_template_identity, RetirementConflict
)


class RetirementGuardTests(unittest.TestCase):
    def test_signature_binds_body_scope_method_and_time(self):
        key = bytes(range(32))
        body = b'{"actor":"7","operationId":"operation-1"}'
        path = '/console/cleanup/internal/retire/e/r'
        raw = retirement_payload('POST', path, 'e', 'r', '1000', body)
        signature = hmac.new(key, raw, hashlib.sha256).hexdigest()
        self.assertTrue(verify_retirement_request('POST', path, 'e', 'r', '1000', signature, body, key, now=1000))
        self.assertFalse(verify_retirement_request('POST', path, 'e', 'r', '1000', signature, body + b' ', key, now=1000))
        self.assertFalse(verify_retirement_request('GET', path, 'e', 'r', '1000', signature, body, key, now=1000))
        self.assertFalse(verify_retirement_request('POST', path, 'other', 'r', '1000', signature, body, key, now=1000))
        self.assertFalse(verify_retirement_request('POST', path, 'e', 'r', '1000', signature, body, key, now=1201))

    def test_inspection_signature_is_distinct_and_binds_exact_request(self):
        key = bytes(range(32))
        body = b'{"actor":"7","operationId":"operation-1"}'
        path = '/console/cleanup/internal/inspect/e/r'
        raw = inspection_payload('POST', path, 'e', 'r', '1000', body)
        signature = hmac.new(key, raw, hashlib.sha256).hexdigest()
        self.assertTrue(verify_inspection_request('POST', path, 'e', 'r', '1000', signature, body, key, now=1000))
        self.assertFalse(verify_inspection_request('POST', path, 'e', 'r', '1000', signature, body + b' ', key, now=1000))
        retirement = hmac.new(key, retirement_payload('POST', path, 'e', 'r', '1000', body), hashlib.sha256).hexdigest()
        self.assertFalse(verify_inspection_request('POST', path, 'e', 'r', '1000', retirement, body, key, now=1000))

    def test_template_rechecks_identity_and_all_reference_guards(self):
        expected = {'id': 12, 'app_id': 'model', 'version': 'v1', 'content_hash': 'h'}
        current = dict(expected, current=False, referenced=False, active_operation=False, managed=True)
        validate_template_retirement(current, expected)
        for key in ('current', 'referenced', 'active_operation'):
            with self.assertRaises(RetirementConflict):
                validate_template_retirement(dict(current, **{key: True}), expected)
        with self.assertRaises(RetirementConflict):
            validate_template_retirement(dict(current, content_hash='changed'), expected)
        with self.assertRaises(RetirementConflict):
            validate_template_retirement(dict(current, managed=False), expected)
        with self.assertRaises(RetirementConflict):
            validate_template_retirement(expected, expected)

    def test_template_rejects_a_new_activation_checkpoint(self):
        expected = {'id': 12, 'app_id': 'model', 'version': 'v1', 'content_hash': 'h', 'activation_revision': 'old'}
        current = dict(expected, current=False, referenced=False, active_operation=False, managed=True)
        current['activation_revision'] = 'used-after-scan'
        with self.assertRaises(RetirementConflict):
            validate_template_retirement(current, expected)

    def test_template_inspection_distinguishes_absent_and_changed_identity(self):
        expected = {'id': 12, 'app_id': 'model', 'version': 'v1', 'content_hash': 'a' * 64,
                    'activation_revision': 'revision'}
        self.assertEqual(inspect_template_identity(None, expected), 'absent')
        self.assertEqual(inspect_template_identity(dict(expected), expected), 'present')
        with self.assertRaises(RetirementConflict):
            inspect_template_identity(dict(expected, content_hash='b' * 64), expected)

    def test_upload_chunk_retirement_is_enterprise_scoped_and_checks_exact_core_receipt(self):
        expected = {
            'session_id': 'session', 'event_id': 'event', 'state_fingerprint': 'b' * 64,
            'storage_fingerprint': 'a' * 64, 'idle_days': 9,
        }
        validate_upload_chunk_retirement(expected)
        for change in ({'idle_days': 0}, {'session_id': '../other'}, {'state_fingerprint': 'short'},
                       {'path': '/foreign'}):
            with self.assertRaises(ValueError):
                validate_upload_chunk_retirement(dict(expected, **change))
        teams = Mock()
        teams.objects.filter.return_value.values_list.return_value = ['owned-team']
        records = Mock()
        records.objects.filter.return_value.exists.return_value = True
        api = Mock()
        api.delete_cleanup_upload_chunks.return_value = (200, {'bean': {
            'protocol': 1, 'operation_id': 'operation', 'event_id': 'event',
            'session_id': 'session', 'state': 'deleted',
        }})
        modules = {
            'console.models.main': SimpleNamespace(PackageUploadRecord=records),
            'www.models.main': SimpleNamespace(Tenants=teams),
            'www.apiclient.regionapi': SimpleNamespace(RegionInvokeApi=lambda: api),
        }
        with patch.dict('sys.modules', modules):
            result = retire_upload_chunks('enterprise', 'rainbond', expected, 'operation')
        self.assertTrue(result['record_retired'])
        self.assertTrue(result['chunks_deleted'])
        teams.objects.filter.assert_called_once_with(enterprise_id='enterprise')
        records.objects.filter.assert_called_once_with(
            event_id='event', region='rainbond', team_name__in=['owned-team'])
        api.delete_cleanup_upload_chunks.assert_called_once_with(
            'enterprise', 'rainbond', dict(expected, operation_id='operation'))
        records.objects.filter.return_value.exists.return_value = False
        with patch.dict('sys.modules', modules), self.assertRaises(RetirementConflict):
            retire_upload_chunks('enterprise', 'rainbond', expected, 'operation')
        records.objects.filter.return_value.exists.return_value = True
        api.delete_cleanup_upload_chunks.return_value = (200, {'bean': dict(
            protocol=1, operation_id='other', event_id='event', session_id='session', state='deleted')})
        with patch.dict('sys.modules', modules), self.assertRaises(RetirementConflict):
            retire_upload_chunks('enterprise', 'rainbond', expected, 'operation')
        api.delete_cleanup_upload_chunks.return_value = (503, {})
        with patch.dict('sys.modules', modules), self.assertRaises(RuntimeError):
            retire_upload_chunks('enterprise', 'rainbond', expected, 'operation')

    def test_upload_chunk_inspection_is_enterprise_scoped_and_exact(self):
        expected = {
            'session_id': 'session', 'event_id': 'event', 'state_fingerprint': 'b' * 64,
            'storage_fingerprint': 'a' * 64, 'idle_days': 9,
        }
        teams = Mock()
        teams.objects.filter.return_value.values_list.return_value = ['owned-team']
        records = Mock()
        records.objects.filter.return_value.exists.return_value = True
        api = Mock()
        api.inspect_cleanup_upload_chunks.return_value = (200, {'bean': {
            'protocol': 1, 'operation_id': 'operation', 'event_id': 'event',
            'session_id': 'session', 'state': 'deleted',
        }})
        modules = {
            'console.models.main': SimpleNamespace(PackageUploadRecord=records),
            'www.models.main': SimpleNamespace(Tenants=teams),
            'www.apiclient.regionapi': SimpleNamespace(RegionInvokeApi=lambda: api),
        }
        with patch.dict('sys.modules', modules):
            self.assertEqual(inspect_upload_chunks('enterprise', 'rainbond', expected, 'operation'), 'deleted')
        api.inspect_cleanup_upload_chunks.assert_called_once_with('enterprise', 'rainbond', {
            'operation_id': 'operation', 'session_id': 'session', 'event_id': 'event',
            'state_fingerprint': 'b' * 64, 'storage_fingerprint': 'a' * 64,
        })
        api.inspect_cleanup_upload_chunks.return_value = (200, {'bean': {
            'protocol': 1, 'operation_id': 'operation', 'event_id': 'event',
            'session_id': 'session', 'state': 'invented',
        }})
        with patch.dict('sys.modules', modules), self.assertRaises(RuntimeError):
            inspect_upload_chunks('enterprise', 'rainbond', expected, 'operation')

    def test_region_client_uses_only_fixed_upload_delete_path(self):
        import ast
        import json
        import re
        from pathlib import Path
        from typing import Any, Dict, Tuple
        path = Path(__file__).resolve().parents[2] / 'www/apiclient/regionapi.py'
        cls = next(node for node in ast.parse(path.read_text()).body
                   if isinstance(node, ast.ClassDef) and node.name == 'RegionInvokeApi')
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'delete_cleanup_upload_chunks')
        isolated = ast.ClassDef(name='Client', bases=[], keywords=[], body=[method], decorator_list=[])
        scope = {'Any': Any, 'Dict': Dict, 'Tuple': Tuple, 're': re, 'json': json}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), scope)
        api = scope['Client']()
        api._cleanup_control_request = Mock(return_value=(200, {}))
        command = {
            'operation_id': 'operation', 'session_id': 'session', 'event_id': 'event',
            'state_fingerprint': 'b' * 64, 'storage_fingerprint': 'a' * 64, 'idle_days': 9,
        }
        api.delete_cleanup_upload_chunks('enterprise', 'rainbond', command)
        api._cleanup_control_request.assert_called_once_with(
            'enterprise', 'rainbond', '/v2/cleanup/uploads/chunks/delete',
            b'{"operation_id": "operation", "session_id": "session", "event_id": "event", '
            b'"state_fingerprint": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", '
            b'"storage_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", '
            b'"idle_days": 9}')
        for change in ({'path': '/foreign'}, {'idle_days': 0}, {'session_id': '../other'}):
            with self.assertRaises(ValueError):
                api.delete_cleanup_upload_chunks('enterprise', 'rainbond', dict(command, **change))
        self.assertEqual(api._cleanup_control_request.call_count, 1)

    def test_region_client_uses_only_fixed_upload_inspection_path(self):
        import ast
        import json
        import re
        from pathlib import Path
        from typing import Any, Dict, Tuple
        path = Path(__file__).resolve().parents[2] / 'www/apiclient/regionapi.py'
        cls = next(node for node in ast.parse(path.read_text()).body
                   if isinstance(node, ast.ClassDef) and node.name == 'RegionInvokeApi')
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'inspect_cleanup_upload_chunks')
        isolated = ast.ClassDef(name='Client', bases=[], keywords=[], body=[method], decorator_list=[])
        scope = {'Any': Any, 'Dict': Dict, 'Tuple': Tuple, 're': re, 'json': json}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), scope)
        api = scope['Client']()
        api._cleanup_control_request = Mock(return_value=(200, {}))
        command = {
            'operation_id': 'operation', 'session_id': 'session', 'event_id': 'event',
            'state_fingerprint': 'b' * 64, 'storage_fingerprint': 'a' * 64,
        }
        api.inspect_cleanup_upload_chunks('enterprise', 'rainbond', command)
        api._cleanup_control_request.assert_called_once_with(
            'enterprise', 'rainbond', '/v2/cleanup/uploads/chunks/inspect',
            b'{"operation_id": "operation", "session_id": "session", "event_id": "event", '
            b'"state_fingerprint": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", '
            b'"storage_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}')
        for change in ({'path': '/foreign'}, {'session_id': '../other'}):
            with self.assertRaises(ValueError):
                api.inspect_cleanup_upload_chunks('enterprise', 'rainbond', dict(command, **change))
        self.assertEqual(api._cleanup_control_request.call_count, 1)
