# capability_id: console.vm-storage.managed-snapshot-projection
"""Separate response-only storage eligibility projection; never a VM execution permit."""
from types import SimpleNamespace
from unittest import TestCase, mock

import django

django.setup()

from console.services.vm_storage_snapshot import project_creation_storage_option  # noqa: E402
from console.services.app_config.volume_service import volume_service  # noqa: E402


class ManagedStorageProjectionTests(TestCase):
    def test_generic_facts_do_not_fill_missing_or_bad_managed_evidence(self):
        generic = {'status': 'supported', 'supported': True, 'reason_code': 'native_ready'}
        for managed in (None, [], {}, {'status': 'supported', 'supported': False}, {'status': 'supported', 'supported': 1}):
            value = {
                'volume_type': 'arbitrary-storage',
                'name_show': 'Storage',
                'snapshot_capability': generic,
                'managed_snapshot_capability': managed,
                'parameters': {
                    'private-fixture': 'not-forwarded'
                }
            }
            result = project_creation_storage_option(value)
            self.assertTrue(result['snapshot_capability']['supported'])
            self.assertEqual(result['managed_snapshot_capability']['status'], 'unknown')
            self.assertFalse(result['managed_snapshot_capability']['supported'])
            self.assertNotIn('parameters', result)

    def test_explicit_managed_result_is_independently_normalized_without_name_guess(self):
        for name in ('named-like-supported', 'unrelated-name'):
            result = project_creation_storage_option({
                'volume_type': name,
                'snapshot_capability': {
                    'status': 'supported',
                    'supported': True
                },
                'managed_snapshot_capability': {
                    'status': 'unsupported',
                    'supported': False,
                    'reason_code': 'managed_driver_unsupported',
                    'message': 'not-forwarded'
                }
            })
            self.assertEqual(result['managed_snapshot_capability'], {
                'status': 'unsupported',
                'supported': False,
                'reason_code': 'managed_driver_unsupported'
            })
            self.assertNotIn('message', result['managed_snapshot_capability'])

    def test_actual_existing_storage_getter_preserves_choices_independent_of_snapshot_status(self):
        options = [{
            'volume_type': 'first',
            'name_show': 'First',
            'snapshot_capability': {
                'status': 'supported',
                'supported': True
            },
            'managed_snapshot_capability': {
                'status': 'unsupported',
                'supported': False
            }
        }, {
            'volume_type': 'second',
            'name_show': 'Second'
        }, {
            'volume_type': 'memoryfs'
        }, {
            'volume_type': 'disabled',
            'enable': False
        }]
        with mock.patch.object(volume_service, 'get_region_volume_options', return_value=options) as source:
            result = volume_service.get_vm_persistent_storage_options(SimpleNamespace(tenant_name='team-a'), 'region-a')
        source.assert_called_once()
        self.assertEqual([x['volume_type'] for x in result], ['first', 'second'])
        self.assertEqual(result[0]['managed_snapshot_capability']['status'], 'unsupported')
        self.assertEqual(result[1]['managed_snapshot_capability']['status'], 'unknown')
