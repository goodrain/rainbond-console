import os
import unittest
from unittest.mock import Mock, patch

from console.services.cleanup_writer_registration import announce_console_writer, _announced


class ConsoleWriterRegistrationTests(unittest.TestCase):
    def setUp(self):
        _announced.clear()
        self.api = Mock()
        self.api.register_cleanup_console_writer.return_value = (200, {'bean': {'protocol': 1, 'recorded': True}})

    def test_only_downward_identity_is_sent_and_success_is_idempotent(self):
        with patch.dict(os.environ, {'POD_NAME': 'console-pod', 'POD_UID': 'pod-uid'}, clear=True):
            self.assertTrue(announce_console_writer('enterprise', 'rainbond', self.api))
            self.assertTrue(announce_console_writer('enterprise', 'rainbond', self.api))
        self.api.register_cleanup_console_writer.assert_called_once_with('enterprise', 'rainbond', 'console-pod', 'pod-uid')

    def test_missing_identity_and_failed_or_old_core_never_claim_registration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(announce_console_writer('enterprise', 'rainbond', self.api))
        self.api.register_cleanup_console_writer.assert_not_called()
        with patch.dict(os.environ, {'POD_NAME': 'console-pod', 'POD_UID': 'pod-uid'}, clear=True):
            self.api.register_cleanup_console_writer.return_value = (404, {})
            self.assertFalse(announce_console_writer('enterprise', 'rainbond', self.api))
            self.api.register_cleanup_console_writer.side_effect = RuntimeError('private-fixture-detail')
            self.assertFalse(announce_console_writer('enterprise', 'rainbond', self.api))
        self.assertEqual(_announced, set())
