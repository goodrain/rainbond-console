# capability_id: console.vm-jobs.scoped-status
from unittest import TestCase
from django.urls import resolve
from rest_framework.test import APIRequestFactory, force_authenticate
from console.tests import vm_snapshot_read_api_test as base


class VMJobViewTests(TestCase):
    setUp = base.VMSnapshotReadAPITestCase.setUp
    components = base.VMSnapshotReadAPITestCase.components
    application = base.VMSnapshotReadAPITestCase.application
    transport = base.VMSnapshotReadAPITestCase.transport

    def get(self, endpoint='capabilities', authenticated=True, tenant='team-a', alias='vm-a'):
        path = '/console/teams/{}/apps/{}/vm-jobs/{}'.format(tenant, alias, endpoint)
        match = resolve(path)
        request = APIRequestFactory().get(path, {'region_name': 'region-a'})
        if authenticated:
            force_authenticate(request, self.user)
        return match.func(request, **match.kwargs)

    def test_missing_runtime_is_explicit_and_does_not_call_region(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['data']['bean']['available'])
        self.assertIn(response.data['data']['bean']['reason'], ('worker_unavailable', 'region_authority_contract_unavailable'))
        self.request.assert_not_called()

    def test_scope_and_permission_checks_run_before_task_access(self):
        self.assertIn(self.get(authenticated=False).status_code, (401, 403))
        self.assertIn(self.get(tenant='team-b').status_code, (403, 404))
        self.assertEqual(self.get(alias='vm-b').status_code, 403)
        self.permissions = {}
        self.assertEqual(self.get().status_code, 403)
        self.request.assert_not_called()

    def test_public_task_uses_real_journal_rows_without_exposing_request_or_evidence(self):
        from console.tests import vm_restore_journal_test as journal_fixture
        from console.services.vm_restore_journal import TrustedContext
        fixture = journal_fixture.VMRestoreJournalTestCase(
            'test_unissued_operation_refuses_even_valid_manifest_without_mutation')
        fixture.setUp()
        try:
            fixture.service.tenant_id = 'team-a'
            fixture.service.extend_method = 'vm'
            fixture.service.save()
            self.component = fixture.service
            context = TrustedContext(fixture.service)
            fixture.journal.create_operation(context,
                                             'op-a',
                                             'request-a',
                                             'snapshot',
                                             request={
                                                 'name': 'snapshot-a',
                                                 'description': '',
                                                 'power_after': 'previous'
                                             })
            response = self.get('op-a')
            self.assertEqual(response.status_code, 200)
            public = response.data['data']['bean']
            self.assertEqual(public['operation_id'], 'op-a')
            self.assertEqual(public['phase'], 'pending')
            self.assertNotIn('request', public)
            self.assertNotIn('region_intent', public)
            self.assertNotIn('rollback_config', public)
            self.permissions = {}
            self.assertEqual(self.get('op-a').status_code, 403)
            self.request.assert_not_called()
        finally:
            fixture.doCleanups()
