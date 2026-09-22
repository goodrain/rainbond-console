import hashlib
import hmac
import unittest
from console.services.cleanup_retirement import (
    verify_retirement_request, retirement_payload, validate_template_retirement, RetirementConflict
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
