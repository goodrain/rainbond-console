import unittest

from console.services.cleanup_coordination import protect_references, CoordinationUnavailable, template_reference_scopes


class CoordinationTests(unittest.TestCase):
    def test_snapshot_entrypoints_acquire_before_reading_or_writing(self):
        import ast
        import json
        from pathlib import Path
        from types import SimpleNamespace
        from typing import Any, Optional
        from unittest.mock import Mock, patch
        for file, method_name in [('app_version_service.py', 'create_snapshot'),
                                  ('market_app/app_upgrade.py', '_take_snapshot'),
                                  ('share_services.py', 'update_or_create_rainbond_center_app_version')]:
            path = Path(__file__).resolve().parents[1] / 'services' / file
            tree = ast.parse(path.read_text())
            method = next(n for c in tree.body if isinstance(c, ast.ClassDef) for n in c.body
                          if isinstance(n, ast.FunctionDef) and n.name == method_name)
            method.decorator_list = []
            namespace = dict(Optional=Optional,
                             Any=Any,
                             Tenants=object,
                             RegionConfig=object,
                             Users=object,
                             ServiceGroup=object,
                             json=json,
                             RainbondCenterAppVersion=SimpleNamespace(
                                 objects=Mock(get=Mock(side_effect=AssertionError("unprotected template write"))),
                                 DoesNotExist=LookupError))
            exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), namespace)
            obj = SimpleNamespace(region_name='r',
                                  tenant=SimpleNamespace(tenant_name='team'),
                                  get_or_create_hidden_template=Mock(side_effect=AssertionError('unprotected snapshot work')))
            with patch('console.services.cleanup_coordination.protect_region_references',
                       side_effect=CoordinationUnavailable('occupied')):
                with self.assertRaises(CoordinationUnavailable):
                    if method_name == 'create_snapshot':
                        namespace[method_name](obj, obj.tenant, SimpleNamespace(region_name='r'), object(), object())
                    elif method_name == 'update_or_create_rainbond_center_app_version':
                        namespace[method_name](obj, obj.tenant, SimpleNamespace(region_name='r'), object(), 'app', 'v1', {})
                    else:
                        namespace[method_name](obj)

    def test_region_transport_only_exposes_producer_routes(self):
        import ast
        import json
        import re
        from pathlib import Path
        from types import SimpleNamespace
        from typing import Any, Dict, Optional
        from urllib.parse import quote
        source = Path(__file__).resolve().parents[2] / 'www/apiclient/regionapi.py'
        tree = ast.parse(source.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RegionInvokeApi')
        cls.bases = []
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'cleanup_reference_operation']
        namespace = dict(re=re, json=json, quote=quote, Optional=Optional, Dict=Dict, Any=Any)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(source), 'exec'), namespace)
        api = namespace['RegionInvokeApi']()
        api.default_headers = {}
        api._RegionInvokeApi__get_region_access_info = lambda *args: ('http://region.invalid', SimpleNamespace())
        api._set_headers = lambda value: None
        calls = []
        api._post = lambda url, headers, **kwargs: (calls.append(url), {'bean': {'protocol': 1}})
        body = dict(kind='producer', operation_id='operation')
        for action in ('discover', 'acquire', 'finish'):
            api.cleanup_reference_operation('r', 'team', action, 'hub', body if action != 'discover' else {})
        self.assertEqual(calls, [
            'http://region.invalid/v2/cleanup/stores/discover', 'http://region.invalid/v2/cleanup/stores/hub/operations',
            'http://region.invalid/v2/cleanup/stores/hub/operations/operation/finish'
        ])
        with self.assertRaises(ValueError):
            api.cleanup_reference_operation('r', 'team', 'acquire', 'hub', dict(kind='delete'))
        with self.assertRaises(ValueError):
            api.cleanup_reference_operation('r', 'team', 'finish', '../hub', body)
        self.assertEqual(len(calls), 3)

    def test_template_scopes_preserve_repository_and_unknown_dependencies(self):
        self.assertEqual(template_reference_scopes(['{"apps":[{"image":"goodrain.me/team/app:v1"}]}']), ['team/app'])
        self.assertEqual(template_reference_scopes(['{"apps":[{"image":"app:v1"}]}']), ['*'])
        self.assertEqual(template_reference_scopes(['{"apps":[{"image":"goodrain.me/team/app:v1"},{}]}']), ['*'])
        self.assertEqual(template_reference_scopes(['invalid']), ['*'])

    def test_embedded_kubernetes_resources_require_conservative_scope(self):
        raw = '{"apps":[{"image":"goodrain.me/team/app:v1"}],"k8s_resources":[{"kind":"Job"}]}'
        self.assertEqual(template_reference_scopes([raw]), ['*'])

    def test_occupancy_lasts_until_database_commit(self):
        calls, commits = [], []

        def api(action, storage, body):
            calls.append((action, storage, body))
            if action == 'discover':
                return {'bean': {'protocol': 1, 'stores': [{'storage_id': 'hub', 'generation': 'one'}]}}
            return {'bean': {'protocol': 1, 'newly_admitted': True, 'recorded': True}}

        with protect_references(api, ['team/app'], commits.append):
            self.assertEqual([c[0] for c in calls], ['discover', 'acquire'])
        self.assertEqual([c[0] for c in calls], ['discover', 'acquire'])
        commits[0]()
        self.assertTrue(calls[-1][2]['confirmed'])
        self.assertEqual(calls[1][2]['operation_id'], calls[-1][2]['operation_id'])

    def test_failure_does_not_release_uncertain_work(self):
        calls = []

        def api(action, storage, body):
            calls.append((action, body))
            if action == 'discover':
                return {'bean': {'protocol': 1, 'stores': [{'storage_id': 'hub', 'generation': 'one'}]}}
            return {'bean': {'protocol': 1, 'newly_admitted': True, 'recorded': True}}

        with self.assertRaises(ValueError):
            with protect_references(api, ['team/app'], lambda callback: callback()):
                raise ValueError('operation interrupted')
        self.assertFalse(calls[-1][1]['confirmed'])

    def test_invalid_discovery_never_runs_action(self):
        with self.assertRaises(CoordinationUnavailable):
            with protect_references(lambda *args: {'bean': {'protocol': 1}}, ['team/app'], lambda cb: cb()):
                self.fail('missing source inventory was treated as empty')
