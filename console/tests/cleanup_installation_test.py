import base64
import unittest
from console.services.cleanup_gateway import CleanupGatewayUnavailable
from console.services.cleanup_installation import decode_gateway_secret, gateway_secret_name, bootstrap_volumes


class CleanupInstallationTests(unittest.TestCase):
    def secret(self):
        return {'metadata': {'name': gateway_secret_name(), 'namespace': 'plugins', 'annotations': {
            'cleanup.rainbond.io/enterprise': 'e', 'cleanup.rainbond.io/region': 'r'}},
            'data': {'key': base64.b64encode(b'x' * 64).decode()}}

    def test_scoped_secret(self):
        self.assertEqual(decode_gateway_secret(self.secret(), 'plugins', 'e', 'r'), b'x' * 64)

    def test_foreign_namespace_or_scope_fails_closed(self):
        for namespace, enterprise, region in [('other', 'e', 'r'), ('plugins', 'other', 'r'), ('plugins', 'e', 'other')]:
            with self.assertRaises(CleanupGatewayUnavailable):
                decode_gateway_secret(self.secret(), namespace, enterprise, region)

    def test_corrupt_or_short_key_fails_closed(self):
        for value in ['!', '', base64.b64encode(b'short').decode()]:
            secret = self.secret()
            secret['data']['key'] = value
            with self.assertRaises(CleanupGatewayUnavailable):
                decode_gateway_secret(secret, 'plugins', 'e', 'r')

    def test_unlabelled_secret_is_not_automatically_trusted(self):
        secret = self.secret()
        secret['metadata']['annotations'] = {}
        with self.assertRaises(CleanupGatewayUnavailable):
            decode_gateway_secret(secret, 'plugins', 'e', 'r')

    def test_only_gateway_volume_becomes_optional(self):
        volumes = [{"name": "gateway", "secret": {"secretName": "rainbond-disk-cleanup-gateway"}},
                   {"name": "registry", "secret": {"secretName": "registry-auth"}},
                   {"name": "data", "persistentVolumeClaim": {"claimName": "data"}}]
        updated = bootstrap_volumes(volumes)
        self.assertTrue(updated[0]["secret"]["optional"])
        self.assertEqual(updated[1:], volumes[1:])
        self.assertNotIn("optional", volumes[0]["secret"])


class CleanupInstallationResolutionTests(unittest.TestCase):
    def dependencies(self):
        from types import ModuleType, SimpleNamespace
        from unittest.mock import Mock
        modules = {}

        def module(name, **values):
            item = ModuleType(name)
            item.__dict__.update(values)
            modules[name] = item
        api = Mock()
        api.list_plugins.return_value = (None, {'list': [{'name': 'rainbond-disk', 'region_app_id': 'installed-app'}]})
        api.get_tenant_ns_resource.return_value = (None, {'bean': CleanupInstallationTests().secret()})
        region_repo = Mock()
        region_repo.get_enterprise_region_by_region_name.return_value = True
        apps = Mock()
        apps.objects.get.return_value = SimpleNamespace(tenant_id='owned-team')
        tenants = Mock()
        tenants.objects.get.return_value = SimpleNamespace(tenant_name='team', namespace='plugins')
        module('console.repositories.region_repo', region_repo=region_repo)
        module('console.repositories.region_app', region_app_repo=SimpleNamespace(get_app_id=Mock(return_value=42)))
        module('www.apiclient.regionapi', RegionInvokeApi=Mock(return_value=api))
        module('www.models.main', ServiceGroup=apps, Tenants=tenants)
        return modules, api, region_repo, apps, tenants

    def test_installed_owner_resolves_key_without_environment(self):
        import os
        from unittest.mock import patch
        from console.services.cleanup_installation import resolve_gateway_key
        modules, api, _, apps, tenants = self.dependencies()
        with patch.dict('sys.modules', modules), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_gateway_key('e', 'r'), b'x' * 64)
        apps.objects.get.assert_called_once_with(ID=42, region_name='r')
        tenants.objects.get.assert_called_once_with(tenant_id='owned-team', enterprise_id='e')
        api.get_tenant_ns_resource.assert_called_once_with(
            'r', 'team', 'rainbond-disk-gateway', {'group': '', 'version': 'v1', 'resource': 'secrets'})

    def test_uninstalled_plugin_never_reads_secret(self):
        from unittest.mock import patch
        from console.services.cleanup_installation import resolve_gateway_key
        modules, api, _, _, _ = self.dependencies()
        api.list_plugins.return_value = (None, {'list': []})
        with patch.dict('sys.modules', modules), self.assertRaises(CleanupGatewayUnavailable):
            resolve_gateway_key('e', 'r')
        api.get_tenant_ns_resource.assert_not_called()

    def test_foreign_region_never_contacts_cluster(self):
        from unittest.mock import patch
        from console.services.cleanup_installation import resolve_gateway_key
        modules, api, region_repo, _, _ = self.dependencies()
        region_repo.get_enterprise_region_by_region_name.return_value = False
        with patch.dict('sys.modules', modules), self.assertRaises(CleanupGatewayUnavailable):
            resolve_gateway_key('e', 'r')
        api.list_plugins.assert_not_called()
        api.get_tenant_ns_resource.assert_not_called()

    def test_foreign_app_owner_never_reads_secret(self):
        from unittest.mock import patch
        from console.services.cleanup_installation import resolve_gateway_key
        modules, api, _, _, tenants = self.dependencies()
        tenants.objects.get.side_effect = LookupError('foreign app owner')
        with patch.dict('sys.modules', modules), self.assertRaises(CleanupGatewayUnavailable):
            resolve_gateway_key('e', 'r')
        api.get_tenant_ns_resource.assert_not_called()


class CleanupInstallationLifecycleTests(unittest.TestCase):
    def test_scope_configuration_is_idempotent_and_preserves_external_console(self):
        from types import ModuleType, SimpleNamespace
        from unittest.mock import Mock, patch
        from console.services.cleanup_installation import configure_installation
        envs = {
            'CLEANUP_CONSOLE_URL': SimpleNamespace(ID=1, attr_value='https://console.example.test'),
            'CLEANUP_CONSOLE_ALLOW_HTTP': SimpleNamespace(ID=2, attr_value='false'),
        }
        service = Mock()
        service.get_env_by_attr_name.side_effect = lambda tenant, backend, name: envs.get(name)

        def create(**values):
            envs[values['attr_name']] = SimpleNamespace(ID=len(envs)+1, attr_value=values['attr_value'])
            return 200, '', None
        service.add_service_env_var.side_effect = create
        attrs = Mock()
        attrs.get_by_component_ids_and_name.return_value = []
        env_module = ModuleType('console.services.app_config')
        env_module.env_var_service = service
        attr_module = ModuleType('console.services.k8s_attribute')
        attr_module.k8s_attribute_service = attrs
        modules = {'console.services.app_config': env_module, 'console.services.k8s_attribute': attr_module}
        with patch.dict('sys.modules', modules):
            for _ in range(2):
                configure_installation(SimpleNamespace(enterprise_id='e'), SimpleNamespace(region_name='r'),
                                       SimpleNamespace(service_id='backend'))
        self.assertEqual(service.add_service_env_var.call_count, 3)
        service.update_env_by_env_id.assert_not_called()
        self.assertEqual(envs['CLEANUP_SOURCE_ENTERPRISE_ID'].attr_value, 'e')
        self.assertEqual(envs['CLEANUP_CONSOLE_URL'].attr_value, 'https://console.example.test')

    def test_disk_install_configures_before_first_deployment(self):
        import ast
        from pathlib import Path
        from types import ModuleType, SimpleNamespace
        from unittest.mock import Mock, patch
        path = Path(__file__).resolve().parents[1] / 'services/market_app/app_upgrade.py'
        tree = ast.parse(path.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'AppUpgrade')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'install')
        from typing import Any, List
        namespace = {'Any': Any, 'List': List}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), namespace)
        for plugin, expected in [('rainbond-disk', ['configure', 'deploy']), ('unrelated', ['deploy'])]:
            calls = []
            sync = ModuleType('console.services.rbd_plugin_sync_service')
            sync.rbd_plugin_sync_service = SimpleNamespace(reconcile=lambda *args: calls.append('configure'))
            obj = SimpleNamespace(install_plugins=Mock(), sync_new_app=Mock(), save_new_app=Mock(),
                                  create_service_tcp_domains=Mock(), region=object(), tenant=object(),
                                  app=SimpleNamespace(ID=42), app_template={'platform_plugin': {'plugin_id': plugin}},
                                  is_deploy=True, _install_deploy=lambda: calls.append('deploy') or [])
            with patch.dict('sys.modules', {'console.services.rbd_plugin_sync_service': sync}):
                namespace['install'](obj)
            self.assertEqual(calls, expected)

    def test_upgrade_configures_before_replacing_pods(self):
        import ast
        from pathlib import Path
        from types import ModuleType, SimpleNamespace
        from unittest.mock import Mock, patch
        path = Path(__file__).resolve().parents[1] / 'services/market_app/app_upgrade.py'
        tree = ast.parse(path.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'AppUpgrade')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'upgrade')
        namespace = {'AppUpgradeRecord': object}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), namespace)
        calls = []
        sync = ModuleType('console.services.rbd_plugin_sync_service')
        sync.rbd_plugin_sync_service = SimpleNamespace(reconcile=lambda *args: calls.append('configure'))
        obj = SimpleNamespace(install_plugins=Mock(), sync_new_app=Mock(), _save_app=Mock(), region=object(),
                              tenant=object(), app=SimpleNamespace(ID=42), record=object(),
                              app_template={'platform_plugin': {'plugin_id': 'rainbond-disk'}},
                              _deploy=lambda record: calls.append('deploy'))
        with patch.dict('sys.modules', {'console.services.rbd_plugin_sync_service': sync}):
            namespace['upgrade'](obj)
        self.assertEqual(calls, ['configure', 'deploy'])
