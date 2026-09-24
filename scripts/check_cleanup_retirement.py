"""Run retirement ORM checks against a new in-memory SQLite database only."""
import os
import unittest


def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'goodrain_web.test_settings'
    os.environ['SENTRY_ENABLED'] = 'false'
    import django
    django.setup()
    from django.conf import settings
    settings.DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
    settings.DATABASES['default']['NAME'] = ':memory:'
    from django.db import connection
    if connection.settings_dict['NAME'] != ':memory:':
        raise RuntimeError('refusing to use a persistent database')
    from console.models.main import (RainbondCenterApp, RainbondCenterAppVersion, AppUpgradeRecord,
                                     AppVersionTemplateRelation, AppUpgradeSnapshot)
    from www.models.main import Tenants, TenantServiceGroup
    from console.services.cleanup_retirement import retire_template, RetirementConflict, lock_template_use, template_fingerprint
    models = [Tenants, RainbondCenterApp, RainbondCenterAppVersion, AppUpgradeRecord,
              AppVersionTemplateRelation, AppUpgradeSnapshot, TenantServiceGroup]
    with connection.schema_editor() as editor:
        for model in models:
            editor.create_model(model)

    class RetirementORMTests(unittest.TestCase):
        key = b'test-only-fingerprint-key-material'

        def setUp(self):
            from unittest.mock import patch
            self.coordination_calls = []

            def coordinate(region, tenant, action, storage, body):
                self.coordination_calls.append((action, body))
                if action == 'discover':
                    return {'bean': {'protocol': 1, 'stores': [{'storage_id': 'hub', 'generation': 'one'}]}}
                return {'bean': {'protocol': 1, 'newly_admitted': True, 'recorded': True}}
            coordinator = patch('www.apiclient.regionapi.RegionInvokeApi.cleanup_reference_operation', side_effect=coordinate)
            coordinator.start()
            self.addCleanup(coordinator.stop)
            for model in reversed(models):
                model.objects.all()._raw_delete('default')
            Tenants.objects.create(tenant_id='team', tenant_name='team', namespace='team', enterprise_id='e')
            RainbondCenterApp.objects.create(app_id='model', app_name='Example', enterprise_id='e', source='local')
            values = dict(app_id='model', enterprise_id='e', share_team='team', record_id=1, share_user=1,
                          source='local', region_name='r', is_complete=True, app_template='{"apps":[]}')
            self.old = RainbondCenterAppVersion.objects.create(version='v1', **values)
            self.latest = RainbondCenterAppVersion.objects.create(version='v2', **values)
            self.expected = {'id': self.old.ID, 'app_id': 'model', 'version': 'v1',
                             'content_hash': template_fingerprint(self.old.app_template, self.key),
                             'activation_revision': ''}

        def test_only_selected_record_is_removed(self):
            result = retire_template('e', 'r', self.expected, self.key)
            self.assertTrue(result['record_retired'])
            self.assertFalse(result['image_deleted'])
            self.assertIsNone(result['reclaimed_bytes'])
            self.assertFalse(RainbondCenterAppVersion.objects.filter(ID=self.old.ID).exists())
            self.assertTrue(RainbondCenterAppVersion.objects.filter(ID=self.latest.ID).exists())

        def test_retained_snapshot_protects_template_record(self):
            import json
            AppUpgradeSnapshot.objects.create(tenant_id='team', snapshot_id='retained', upgrade_group_id=1,
                                              snapshot=json.dumps({'component_group': {'group_key': 'model',
                                                                                       'group_version': 'v1'}}))
            with self.assertRaises(RetirementConflict):
                retire_template('e', 'r', self.expected, self.key)
            self.assertTrue(RainbondCenterAppVersion.objects.filter(ID=self.old.ID).exists())

        def test_latest_is_protected(self):
            expected = dict(self.expected, id=self.latest.ID, version='v2')
            with self.assertRaises(RetirementConflict):
                retire_template('e', 'r', expected, self.key)

        def test_installed_version_is_protected(self):
            TenantServiceGroup.objects.create(tenant_id='team', group_key='model', group_version='v1', region_name='r')
            with self.assertRaises(RetirementConflict):
                retire_template('e', 'r', self.expected, self.key)

        def test_new_use_changes_checkpoint(self):
            with lock_template_use('model', 'v1', 'r', 'team'):
                pass
            with self.assertRaises(RetirementConflict):
                retire_template('e', 'r', self.expected, self.key)
            self.assertTrue(RainbondCenterAppVersion.objects.filter(ID=self.old.ID).exists())

        def test_outer_transaction_retains_reference_occupancy(self):
            from django.db import transaction
            with transaction.atomic():
                with lock_template_use('model', 'v1', 'r', 'team'):
                    pass
                self.assertEqual([item[0] for item in self.coordination_calls], ['discover', 'acquire'])
            self.assertEqual(self.coordination_calls[-1][0], 'finish')
            self.assertTrue(self.coordination_calls[-1][1]['confirmed'])

        def test_retired_version_cannot_start_installation(self):
            retire_template('e', 'r', self.expected, self.key)
            with self.assertRaises(RetirementConflict):
                with lock_template_use('model', 'v1', 'r', 'team'):
                    self.fail('retired template entered installation')

        def test_invalid_snapshot_preserves_inventory_but_blocks_retirement(self):
            from types import SimpleNamespace
            from unittest.mock import patch
            from console.views.cleanup_inventory import CleanupInventoryView
            AppUpgradeSnapshot.objects.create(tenant_id='team', snapshot_id='broken', snapshot='invalid', upgrade_group_id=1)
            request = SimpleNamespace(method='GET', headers={}, query_params={'kind': 'templates'},
                                      get_full_path=lambda: '/inventory')
            with patch('console.views.cleanup_inventory.resolve_gateway_key', return_value=self.key), \
                    patch('console.views.cleanup_inventory.verify_source_request', return_value=True), \
                    patch('console.views.cleanup_inventory.region_repo.get_enterprise_region_by_region_name', return_value=True):
                response = CleanupInventoryView().get(request, 'e', 'r')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['resources']), 2)
            self.assertTrue(all(not row.get('retirement') for row in response.data['resources']))
            self.assertIn('snapshot_references_unavailable', response.data['failedScopes'])
            with self.assertRaises(RetirementConflict):
                retire_template('e', 'r', self.expected, self.key)

        def test_snapshot_reference_page_is_scoped_and_sanitized(self):
            import json
            from types import SimpleNamespace
            from unittest.mock import patch
            from console.views.cleanup_inventory import CleanupInventoryView
            Tenants.objects.create(tenant_id='other', tenant_name='other', namespace='other', enterprise_id='other')
            for team, image in [('team', 'goodrain.me/owned:v1'), ('other', 'goodrain.me/foreign:v1')]:
                AppUpgradeSnapshot.objects.create(tenant_id=team, snapshot_id=team, snapshot=json.dumps({
                    'components': [{'service_base': {'service_id': team, 'image': image},
                                    'service_auths': [{'value': 'do-not-export'}]}]}))
            request = SimpleNamespace(method='GET', headers={}, query_params={'kind': 'snapshots'},
                                      get_full_path=lambda: '/inventory')
            with patch('console.views.cleanup_inventory.resolve_gateway_key', return_value=self.key), \
                    patch('console.views.cleanup_inventory.verify_source_request', return_value=True), \
                    patch('console.views.cleanup_inventory.region_repo.get_enterprise_region_by_region_name', return_value=True):
                response = CleanupInventoryView().get(request, 'e', 'r')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['resources']), 1)
            self.assertEqual(response.data['resources'][0]['images'], ['goodrain.me/owned:v1'])
            self.assertNotIn('do-not-export', json.dumps(response.data))
            self.assertFalse(response.data['referencesComplete'])

        def test_foreign_region_is_protected(self):
            with self.assertRaises(RetirementConflict):
                retire_template('e', 'other', self.expected, self.key)

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RetirementORMTests))
    connection.close()
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
