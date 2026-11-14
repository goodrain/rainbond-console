# capability_id: console.vm-snapshot.existing-capability
import copy
import json
from unittest import TestCase

from django.urls import resolve
from rest_framework.test import force_authenticate

from console.tests import vm_snapshot_read_api_test as fixtures


def capability():
    return {
        'supported':
        False,
        'status':
        'unsupported',
        'reason_code':
        'participating_volume_unsupported',
        'message':
        '有磁盘不支持快照',
        'operation':
        'create_snapshot',
        'complete':
        True,
        'control_revision':
        3,
        'binding_generation':
        2,
        'volumes': [{
            'key': 'manual42',
            'volume_id': 42,
            'disk_key': 'root',
            'role': 'root',
            'read_only': False,
            'supported': True,
            'status': 'supported',
            'reason_code': 'ready',
            'message': '已确认',
            'storage_class': 'fast'
        }, {
            'key': 'manual43',
            'volume_id': 43,
            'disk_key': 'data',
            'role': 'data',
            'read_only': True,
            'supported': False,
            'status': 'unsupported',
            'reason_code': 'csi_driver_not_registered',
            'message': '未发现可用快照驱动',
            'storage_class': 'legacy'
        }],
        'excluded_volumes': [{
            'key': 'vmimage',
            'role': 'installation_media',
            'reason_code': 'read_only_installation_media'
        }, {
            'key': 'manual42',
            'role': 'detached',
            'reason_code': 'detached_retained_volume'
        }]
    }


class ExistingVMSnapshotCapabilityTests(TestCase):
    setUp = fixtures.VMSnapshotReadAPITestCase.setUp
    components = fixtures.VMSnapshotReadAPITestCase.components
    application = fixtures.VMSnapshotReadAPITestCase.application
    transport = fixtures.VMSnapshotReadAPITestCase.transport

    def call_capability(self, authenticated=True, alias='vm-a', tenant='team-a', query=None, method='get'):
        path = '/console/teams/{}/apps/{}/vm-snapshot-capability'.format(tenant, alias)
        match = resolve(path)
        request = getattr(self.factory, method)(path, query or {'region_name': 'region-a'})
        if authenticated:
            force_authenticate(request, self.user)
        return match.func(request, **match.kwargs)

    def test_scoped_real_sdk_preserves_all_participants_readonly_and_explicit_exclusions(self):
        self.upstream_body = {'bean': capability()}
        self.upstream_body['bean']['native_receipt'] = 'PRIVATE_CAPABILITY_SENTINEL'
        self.upstream_body['bean']['volumes'][0]['source_pvc'] = 'PRIVATE_CAPABILITY_SENTINEL'
        result = self.call_capability(query={
            'region_name': 'region-a',
            'namespace': 'foreign',
            'volume_id': 9,
            'service_id': 'x'
        })
        self.assertEqual(result.status_code, 200)
        bean = result.data['data']['bean']
        self.assertFalse(bean['supported'])
        self.assertEqual(len(bean['volumes']), 2)
        self.assertTrue(bean['volumes'][1]['read_only'])
        self.assertEqual(bean['excluded_volumes'], capability()['excluded_volumes'])
        self.assertNotIn('PRIVATE_CAPABILITY_SENTINEL', json.dumps(result.data))
        self.assertEqual(self.request.call_args.args[:2],
                         ('https://region.invalid/v2/tenants/region-team-a/services/vm-a/vm-snapshot-capability', 'GET'))
        self.assertEqual(self.request.call_args.kwargs['retries'], 0)
        self.assertIsNone(self.request.call_args.kwargs.get('body'))

    def test_unknown_drift_cannot_be_promoted_by_ready_rows_and_malformed_success_never_is_ready(self):
        data = capability()
        data.update(status='unknown', reason_code='vm_changed_during_check', complete=False)
        data['volumes'] = [data['volumes'][0]]
        self.upstream_body = {'bean': data}
        result = self.call_capability()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['data']['bean']['status'], 'unknown')
        self.assertFalse(result.data['data']['bean']['supported'])
        for key, invalid in [('operation', 'restore'), ('volumes', None), ('excluded_volumes', None), ('supported', True)]:
            self.upstream_body = {'bean': {**copy.deepcopy(data), key: invalid}}
            self.assertEqual(self.call_capability().status_code, 502)

    def test_permissions_wrong_scope_and_mutations_never_reach_the_sdk(self):
        self.upstream_body = {'bean': capability()}
        self.assertIn(self.call_capability(authenticated=False).status_code, (401, 403))
        self.assertIn(self.call_capability(alias='vm-b').status_code, (403, 404))
        self.assertIn(self.call_capability(query={'region_name': 'other-region'}).status_code, (403, 404))
        for method in ('post', 'put', 'delete'):
            self.assertIn(self.call_capability(method=method).status_code, (403, 405))
        self.request.assert_not_called()

    def test_old_missing_endpoint_and_dependency_failures_remain_http_errors(self):
        for status in (404, 503):
            self.upstream_status = status
            self.upstream_body = {'msg': 'PRIVATE_CAPABILITY_SENTINEL'}
            result = self.call_capability()
            self.assertEqual(result.status_code, status)
            self.assertNotIn('PRIVATE_CAPABILITY_SENTINEL', json.dumps(result.data))
