import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from console.services.cleanup_gateway import CleanupGatewayUnavailable
from console.services.cleanup_system_coordination import resolve_system_coordination_key


class SystemCoordinationKeyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'credential.json'
        self.key = os.urandom(64)
        self.document = {'enterprise': 'e', 'region': 'r', 'key': base64.b64encode(self.key).decode()}
        self.path.write_text(json.dumps(self.document))
        self.repo = Mock()
        self.repo.get_enterprise_region_by_region_name.return_value = True
        module = ModuleType('console.repositories.region_repo')
        module.region_repo = self.repo
        self.modules = patch.dict('sys.modules', {'console.repositories.region_repo': module})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.environment = patch.dict(os.environ, {'CLEANUP_SYSTEM_COORDINATION_FILE': str(self.path)}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_system_key_needs_no_plugin_installation_and_reloads_rotation(self):
        self.assertEqual(resolve_system_coordination_key('e', 'r'), self.key)
        replacement = os.urandom(64)
        self.document['key'] = base64.b64encode(replacement).decode()
        self.path.write_text(json.dumps(self.document))
        self.assertEqual(resolve_system_coordination_key('e', 'r'), replacement)

    def test_scope_mismatch_and_removed_region_fail_closed(self):
        for enterprise, region in [('other', 'r'), ('e', 'other')]:
            with self.assertRaises(CleanupGatewayUnavailable):
                resolve_system_coordination_key(enterprise, region)
        self.repo.get_enterprise_region_by_region_name.return_value = False
        with self.assertRaises(CleanupGatewayUnavailable):
            resolve_system_coordination_key('e', 'r')

    def test_missing_unconfigured_corrupt_and_oversized_credentials_never_fallback(self):
        for raw in ['{}', '[]', 'invalid', 'x' * 16385,
                    json.dumps(dict(self.document, key='!')),
                    json.dumps(dict(self.document, key=base64.b64encode(b'short').decode())),
                    json.dumps(dict(self.document, extra='unexpected'))]:
            self.path.write_text(raw)
            with self.assertRaises(CleanupGatewayUnavailable):
                resolve_system_coordination_key('e', 'r')
        self.path.unlink()
        with self.assertRaises(CleanupGatewayUnavailable):
            resolve_system_coordination_key('e', 'r')
        os.environ.pop('CLEANUP_SYSTEM_COORDINATION_FILE')
        with self.assertRaises(CleanupGatewayUnavailable):
            resolve_system_coordination_key('e', 'r')

    def test_repository_failure_is_redacted(self):
        self.repo.get_enterprise_region_by_region_name.side_effect = RuntimeError('private-detail')
        with self.assertRaises(CleanupGatewayUnavailable) as failure:
            resolve_system_coordination_key('e', 'r')
        self.assertEqual(str(failure.exception), '')
