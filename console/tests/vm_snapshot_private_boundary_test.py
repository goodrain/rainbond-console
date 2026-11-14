# capability_id: console.vm-snapshot.private-control-boundary
"""Public guard controls and original exposure, using synthetic records in isolated actual SQL."""
import ast
import json
import os
from pathlib import Path
import unicodedata
from unittest import TestCase, mock

from django.db import transaction
from rest_framework.test import APIRequestFactory

from console.tests import vm_restore_private_attributes_test as fixtures
from console.exception.main import ServiceHandleException
from console.models.main import ComponentK8sAttributes
from console.repositories import k8s_attribute as repository
from console.services import k8s_attribute as services
from console.services.vm_restore_journal import TrustedContext, VMRestoreJournal
from console.utils.vm_restore_attributes import is_private_vm_attribute
from console.views.app_config.base import AppBaseView
from console.views.k8s_attribute import ComponentK8sAttributeListView


class SnapshotPrivateBoundaryTests(TestCase):
    setUp = fixtures.VMRestorePrivateAttributesTestCase.setUp
    close_database = fixtures.VMRestorePrivateAttributesTestCase.close_database
    attr = fixtures.VMRestorePrivateAttributesTestCase.attr
    snapshot = fixtures.VMRestorePrivateAttributesTestCase.snapshot

    def test_original_fixed_base_exposure_then_current_guard_without_printing_record(self):
        base = Path(os.environ['VM_PRIVATE_GUARD_BEFORE_SOURCE'])

        def old_class(file, name, namespace):
            tree = ast.parse((base / file).read_text())
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
            exec(compile(ast.Module(body=[cls], type_ignores=[]), '<original-controlled-public-boundary>', 'exec'), namespace)
            return namespace[name]()

        old_repo = old_class('console/repositories/k8s_attribute.py', 'ComponentK8sAttributeRepo', dict(vars(repository)))
        ns = dict(vars(services))
        ns['k8s_attribute_repo'] = old_repo
        old_service = old_class('console/services/k8s_attribute.py', 'ComponentK8sAttributeService', ns)
        private = self.attr('vm_restore_operation_synthetic')
        original = self.snapshot()
        leaked_count = sum(is_private_vm_attribute(item['name']) for item in old_service.list_by_component_ids(['service-a']))
        self.assertEqual(leaked_count, 1)
        with transaction.atomic(using=self.alias):
            altered = old_repo.update('service-a', private.name, attribute_value='synthetic-replacement')
            self.assertEqual(altered, 1)
            transaction.set_rollback(True, using=self.alias)
        self.assertEqual(self.snapshot(), original)
        with self.assertRaises(ServiceHandleException):
            repository.k8s_attribute_repo.update('service-a', private.name, attribute_value='synthetic-replacement')
        self.assertFalse(services.k8s_attribute_service.list_by_component_ids(['service-a']))
        self.assertEqual(self.snapshot(), original)
        output = os.environ.get('VM_PRIVATE_GUARD_COUNTEREXAMPLE')
        if output:
            Path(output).write_text(
                json.dumps(
                    {
                        'old_public_private_count': leaked_count,
                        'old_private_update_count': altered,
                        'current_private_update_forbidden': True,
                        'current_public_private_count': 0,
                        'real_SQL_rollback_preserved_record': True,
                        'record_values_exported': False
                    },
                    indent=2) + '\n')

    def test_actual_matched_row_is_checked_under_case_accent_alias_collation(self):
        private = self.attr('vm_restore_state')
        alias = 'vm\u0301_restore_state'
        self.assertFalse(is_private_vm_attribute(alias))
        ordinary = self.attr(alias, 'ordinary-control')

        def fold(value):
            return ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c)).casefold()

        self.database.connection.create_collation('VM_TEST_ALIAS', lambda a, b: (fold(a) > fold(b)) - (fold(a) < fold(b)))

        def candidates(component_id, name):
            return ComponentK8sAttributes.objects.filter(component_id=component_id).extra(
                where=['name COLLATE VM_TEST_ALIAS = %s'], params=[name]).order_by('pk')

        with mock.patch.object(repository.k8s_attribute_repo, 'get_by_component_id_name', side_effect=candidates):
            result = services.k8s_attribute_service.get_by_component_ids_and_name('service-a', alias)
            self.assertEqual(list(result.values_list('pk', flat=True)), [ordinary.pk])
            self.assertEqual(repository.k8s_attribute_repo.update('service-a', alias, attribute_value='ordinary-new'), 1)
            private.refresh_from_db()
            self.assertEqual(private.attribute_value, 'control-sentinel')
            count, _ = repository.k8s_attribute_repo.delete('service-a', alias)
            self.assertEqual(count, 1)
            self.assertTrue(ComponentK8sAttributes.objects.filter(pk=private.pk).exists())

    def test_public_flags_and_non_vm_scope_do_not_reveal_retained_control_records(self):
        self.attr('vm_restore_manifest_synthetic')
        self.attr('labels', 'ordinary')
        for kind in ('vm', 'application', ''):
            self.service.extend_method = kind
            self.service.save()
            request = APIRequestFactory().get('/local/attributes', {'include_private': 'true', 'trusted': 'true'})
            tenant, service = self.tenant, self.service

            def initial(view, _request, *args, **kwargs):
                view.tenant, view.service, view.region_name = tenant, service, 'region-a'

            with mock.patch.object(AppBaseView, 'initial', initial):
                response = ComponentK8sAttributeListView.as_view()(request, tenantName='team-a', serviceAlias='service-a')
            self.assertEqual(response.status_code, 200)
            names = [v['name'] for v in response.data['data']['list']]
            self.assertEqual(names, ['labels'])
            self.assertEqual(ComponentK8sAttributes.objects.count(), 2)

    def test_internal_journal_stays_usable_and_public_scope_rename_fields_are_denied(self):
        self.service.extend_method = 'vm'
        self.service.save()
        journal = VMRestoreJournal()
        context = TrustedContext(self.service)
        op = journal.create_operation(context,
                                      'internal-a',
                                      'internal-a',
                                      'snapshot',
                                      request=dict(name='snapshot-a', description='', power_after='previous', operator='17'))
        self.assertEqual(journal.read_operation(context, 'internal-a')['request']['operator'], '17')
        self.assertEqual(journal.active_operation(context), 'internal-a')
        self.assertFalse(services.k8s_attribute_service.list_by_component_ids(['service-a']))
        public = self.attr('labels', 'ordinary')
        for key in ('ID', 'pk', 'tenant_id'):
            with self.assertRaises(ServiceHandleException):
                repository.k8s_attribute_repo.update('service-a', 'labels', **{key: 'forbidden'})
        with self.assertRaises(TypeError):
            repository.k8s_attribute_repo.update('service-a', 'labels', **{'component_id': 'forbidden'})
        public.refresh_from_db()
        self.assertEqual(public.attribute_value, 'ordinary')
        self.assertEqual(journal.read_operation(context, 'internal-a')['operation_id'], op['operation_id'])
