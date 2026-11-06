import unittest

from console.services.cleanup_gateway import CleanupGatewayUnavailable
from console.services.cleanup_installation import bundled_cleanup_registration, requires_cleanup_bootstrap


class EnterpriseCleanupInstallationTests(unittest.TestCase):
    def parent(self):
        return dict(plugin_id='rainbond-enterprise-base', plugin_name='企业基础', app_id='base-app',
                    namespace='plugins', frontend_component='base', entry_path='/static/main.js',
                    frontend_service='base.plugins.svc:8080/static/main.js',
                    backend_service='base.plugins.svc:8080', plugin_type='JSInject')

    def test_explicit_new_base_declaration_only(self):
        for name in ('rainbond-enterprise-base', 'rainbond-enterprise-base-ARM64', 'rainbond-enterprise-base-AMD64'):
            self.assertTrue(requires_cleanup_bootstrap({'platform_plugin': {
                'plugin_id': name, 'bundled_disk_cleanup': True}}))
        for value in ({}, {'plugin_id': 'rainbond-enterprise-base'},
                      {'plugin_id': 'other', 'bundled_disk_cleanup': True},
                      {'plugin_id': 'rainbond-enterprise-base', 'bundled_disk_cleanup': 'true'}):
            self.assertFalse(requires_cleanup_bootstrap({'platform_plugin': value}))
        self.assertTrue(requires_cleanup_bootstrap({'platform_plugin': {'plugin_id': 'rainbond-disk'}}))

    def test_new_installation_reuses_parent_app_services_and_scope(self):
        parent = self.parent()
        result = bundled_cleanup_registration(parent, [])
        self.assertEqual(result['plugin_id'], 'rainbond-disk')
        self.assertEqual(result['plugin_views'], ['Platform'])
        for field in ('app_id', 'namespace', 'frontend_service', 'backend_service'):
            self.assertEqual(result[field], parent[field])
        self.assertEqual(parent['plugin_id'], 'rainbond-enterprise-base')

    def test_reconcile_own_alias_is_idempotent(self):
        existing = dict(name='rainbond-disk', region_app_id='base-app', namespace='plugins')
        self.assertEqual(bundled_cleanup_registration(self.parent(), [existing]),
                         bundled_cleanup_registration(self.parent(), []))

    def test_existing_standalone_or_unknown_owner_is_never_overwritten(self):
        for owner in ('standalone-app', '', None):
            existing = dict(name='rainbond-disk', region_app_id=owner, namespace='plugins')
            self.assertIsNone(bundled_cleanup_registration(self.parent(), [existing]))
        existing = dict(name='rainbond-disk', region_app_id='base-app', namespace='other')
        self.assertIsNone(bundled_cleanup_registration(self.parent(), [existing]))

    def test_duplicate_alias_or_unresolved_parent_fails_closed(self):
        with self.assertRaises(CleanupGatewayUnavailable):
            bundled_cleanup_registration(self.parent(), [dict(name='rainbond-disk')] * 2)
        parent = self.parent()
        parent['app_id'] = ''
        with self.assertRaises(CleanupGatewayUnavailable):
            bundled_cleanup_registration(parent, [])
