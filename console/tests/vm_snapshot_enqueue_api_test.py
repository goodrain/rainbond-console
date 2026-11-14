# capability_id: console.vm-snapshot.enqueue-api
"""Actual scoped HTTP -> actual SQL job -> actual loopback SDK worker (LOCAL only)."""
import json
import os
import tempfile
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import TestCase, mock

from django.urls import resolve
from rest_framework.test import APIRequestFactory, force_authenticate

from console.tests import vm_restore_journal_test as journal_fixtures
from console.tests import vm_snapshot_jobs_worker_test as worker_fixtures
from console.models.main import ComponentK8sAttributes
from console.services import vm_job_health
from console.services.vm_restore_journal import VMRestoreJournal
from console.services.vm_restore_worker import VMJobRunner
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants, TenantServiceInfo


class SnapshotEnqueueAPITests(TestCase):
    close_database = journal_fixtures.VMRestoreJournalTestCase.close_database
    configure = worker_fixtures.SnapshotJobsWorkerTests.configure
    transport = worker_fixtures.SnapshotJobsWorkerTests.transport

    def setUp(self):
        journal_fixtures.VMRestoreJournalTestCase.setUp(self)
        self.configure()
        self.tenant = Tenants.objects.using(self.alias).get(tenant_id='tenant-a')
        self.tenant.enterprise_id, self.tenant.creater = 'enterprise-a', 99
        self.tenant.save()
        self.component = self.service
        self.other_component = TenantServiceInfo.objects.create(tenant_id='tenant-a',
                                                                service_id='service-b',
                                                                service_alias='vm-b',
                                                                service_region='region-a',
                                                                service_key='local-fixture',
                                                                extend_method='vm')
        self.user = SimpleNamespace(user_id=17, enterprise_id='enterprise-a', nick_name='submitter', is_authenticated=True)
        self.app, self.other_app = SimpleNamespace(ID=42, username='other'), SimpleNamespace(ID=99, username='other')
        self.permissions = {42: [300002, 300003]}
        self.factory = APIRequestFactory()
        self.selection = dict(request_id='job-a', name='snapshot-a', description='', power_after='previous')
        self.body = dict(self.selection)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        patches = [
            mock.patch('console.views.base.Tenants.objects.get', side_effect=lambda **q: self.tenant),
            mock.patch('console.views.base.TenantEnterprise.objects.filter'),
            mock.patch('console.views.base.EnterpriseUserPerm.objects.filter'),
            mock.patch('console.views.base.user_services.list_roles', return_value=[]),
            mock.patch('console.views.base.perms.list_enterprise_perm_codes_by_roles', return_value=[]),
            mock.patch('console.views.base.optimized_role_perm_repo.get_user_team_all_perms',
                       side_effect=lambda **scope: {
                           'global_perms': [],
                           'app_perms': self.permissions
                       }),
            mock.patch('console.views.base.ServiceGroup.objects.filter'),
            mock.patch('console.views.base.TenantServiceInfo.objects.filter', side_effect=self.components),
            mock.patch('console.views.app_config.base.group_service.get_service_group_info',
                       side_effect=lambda service_id: self.app if service_id == 'service-a' else self.other_app),
            mock.patch('console.views.app_config.base.group_service.get_app_by_id', return_value=self.app),
            mock.patch('console.views.app_config.base.group_service.set_app_update_time_by_service'),
            mock.patch('console.views.base.region_repo.get_region_by_region_name',
                       side_effect=lambda name: SimpleNamespace(region_name=name)),
            mock.patch('console.views.vm_snapshot.operation_log_service.create_log')
        ]
        for patch in patches:
            value = self.stack.enter_context(patch)
            if patch.attribute == 'filter':
                value.return_value.first.return_value = None
                value.return_value.values_list.return_value = []
        self.rpc = [
            self.stack.enter_context(
                mock.patch.object(RegionInvokeApi, name, side_effect=AssertionError('HTTP thread must not call Region')))
            for name in ('create_vm_snapshot', 'get_vm_snapshot', 'command_vm_snapshot')
        ]
        self.runtime = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime.cleanup)
        self.stack.enter_context(
            mock.patch.dict(os.environ, {
                'VM_JOB_RUNTIME_DIR': self.runtime.name,
                'VM_JOB_INSTANCE_ID': 'local-http-worker'
            }))
        vm_job_health.publish('ready')

    def components(self, **query):
        for value in (self.component, self.other_component):
            if query == {'service_alias': value.service_alias, 'tenant_id': value.tenant_id}:
                return [value]
        return []

    def call(self, method='post', body=None, operation='job-a', authenticated=True, alias='vm-a', query=None):
        path = '/console/teams/team-a/apps/{}/{}'.format(alias, 'vm-snapshots' if method == 'post' else 'vm-jobs/' + operation)
        match = resolve(path)
        if method == 'post':
            request = self.factory.post(path, self.body if body is None else body, format='json', HTTP_X_REGION_NAME='region-a')
        else:
            request = self.factory.get(path, query or {}, HTTP_X_REGION_NAME='region-a')
        if authenticated:
            force_authenticate(request, self.user)
        return match.func(request, **match.kwargs)

    def assert_no_http_rpc(self):
        for rpc in self.rpc:
            rpc.assert_not_called()

    def test_post_durably_enqueues_server_actor_and_no_region_or_same_name_lookup(self):
        response = self.call()
        self.assertEqual(response.status_code, 202)
        bean = response.data['data']['bean']
        self.assertEqual((bean['operation_id'], bean['request_id'], bean['kind']), ('job-a', 'job-a', 'snapshot'))
        self.assertFalse(bean['complete'])
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_job-a')
        operation = json.loads(row.attribute_value)
        self.assertEqual(operation['request'], dict(name='snapshot-a', description='', power_after='previous', operator='17'))
        self.assertIsNone(operation['region_intent'])
        self.assertEqual(self.journal.active_operation(self.ctx), 'job-a')
        self.assert_no_http_rpc()
        original = row.attribute_value
        self.assertEqual(self.call().status_code, 202)
        row.refresh_from_db()
        self.assertEqual(row.attribute_value, original)
        self.assert_no_http_rpc()

    def test_status_uses_real_scoped_job_alias_not_query_echo_and_does_not_advance(self):
        self.assertEqual(self.call().status_code, 202)
        row = ComponentK8sAttributes.objects.get(name='vm_restore_operation_job-a')
        original = row.attribute_value
        response = self.call('get', query={'request_id': 'forged', 'expected_request_id': 'forged', 'namespace': 'forged'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['bean']['request_id'], 'job-a')
        self.assertFalse(response.data['data']['bean']['complete'])
        self.assertNotIn('operator', json.dumps(response.data))
        row.refresh_from_db()
        self.assertEqual(row.attribute_value, original)
        self.assertEqual(self.call('get', operation='missing').status_code, 409)
        self.assertEqual(self.call('get', alias='vm-b').status_code, 403)
        self.assert_no_http_rpc()

    def test_scope_permissions_actor_override_and_health_are_checked_before_enqueue(self):
        for body in (dict(self.body, operator='other'), dict(
                self.body, namespace='forged'), dict(self.body, service_id='service-b'), dict(self.body, request_id='UPPER')):
            self.assertIn(self.call(body=body).status_code, (400, 409))
        self.permissions = {42: [300002]}
        self.assertEqual(self.call().status_code, 403)
        self.permissions = {42: [300002, 300003]}
        self.assertIn(self.call(authenticated=False).status_code, (401, 403))
        vm_job_health.publish('stopping')
        self.assertEqual(self.call().status_code, 503)
        self.assertEqual(self.journal.active_operation(self.ctx), '')
        self.assert_no_http_rpc()

    def test_real_http_job_then_default_worker_has_single_prepare_and_status_stays_safe(self):
        self.transport()
        self.assertEqual(self.call().status_code, 202)
        self.assertEqual(self.server.calls, [])
        VMJobRunner(journal=VMRestoreJournal(), snapshot_client=self.client, owner='worker-local', clock=lambda: 100).process(
            self.ctx, 'job-a')
        posts = [call for call in self.server.calls if call[0] == 'POST' and call[1].endswith('/vm-snapshots')]
        self.assertEqual(len(posts), 1)
        self.assertEqual((posts[0][2]['request_id'], posts[0][2]['manifest_id'], posts[0][2]['operator']),
                         ('job-a', 'job-a', '17'))
        status = self.call('get')
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.data['data']['bean']['request_id'], 'job-a')
        self.assertFalse(status.data['data']['bean']['complete'])
        self.assert_no_http_rpc()
        self.server.mode = 'lost'
        # New process/owner reconciliation uses GET, never a second HTTP-thread Prepare.
        VMJobRunner(journal=VMRestoreJournal(), snapshot_client=self.client, owner='new-owner', clock=lambda: 140).process(
            self.ctx, 'job-a')
        self.assertEqual(len([c for c in self.server.calls if c[0] == 'POST' and c[1].endswith('/vm-snapshots')]), 1)
        self.assert_no_http_rpc()

    def test_failed_sql_enqueue_never_returns_202_or_dispatches_region(self):
        with self.database.cursor() as cursor:
            cursor.execute("""CREATE TRIGGER abort_public_snapshot_enqueue BEFORE INSERT ON component_k8s_attributes
                WHEN NEW.name='vm_restore_operation_job-a' BEGIN SELECT RAISE(ABORT,'LOCAL_ENQUEUE_ABORT'); END""")
        try:
            response = self.call()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.data['data']['bean']['error']['code'], 'vm_snapshot_enqueue_outcome_unknown')
            self.assertEqual(self.journal.active_operation(self.ctx), '')
            self.assert_no_http_rpc()
        finally:
            with self.database.cursor() as cursor:
                cursor.execute('DROP TRIGGER abort_public_snapshot_enqueue')
