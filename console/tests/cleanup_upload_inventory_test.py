"""Upload inventory must preserve ownership and unknown storage measurements."""
import copy
import unittest

from console.services.cleanup_upload_inventory import upload_resources


class UploadInventoryTests(unittest.TestCase):
    # capability_id: console.cleanup.upload-size-projection
    def test_actual_size_and_unavailable_measurements_remain_distinct(self):
        records = [{'event_id': 'owned', 'team_name': 'team', 'status': 'uploaded'}]
        bean = {'protocol': 1, 'scope': 'upload_chunks', 'items': [
            {'id': 'session', 'event_id': 'owned', 'file_name': '应用.zip', 'status': 'completed',
             'size_status': 'measured', 'bytes': 17, 'objects': 2, 'storage_path': 'never-export'},
            {'id': 'unknown', 'event_id': 'owned', 'size_status': 'unavailable', 'bytes': None, 'objects': None}]}
        resources = upload_resources(records, bean, 'rainbond')
        self.assertEqual(resources[0]['name'], '应用.zip / 上传分片')
        self.assertEqual(resources[0]['sizeBytes'], 17)
        self.assertTrue(resources[0]['sizeKnown'])
        self.assertFalse(resources[1]['sizeKnown'])
        for resource in resources:
            self.assertEqual(resource['actions'], [])
            self.assertEqual(resource['decision'], 'protected')
            self.assertIsNone(resource['unusedSince'])
            self.assertNotIn('never-export', str(resource))
        for change in [{'event_id': 'foreign'}, {'bytes': -1}, {'bytes': True}, {'bytes': None},
                       {'objects': -1}, {'id': '../escape'}]:
            invalid = copy.deepcopy(bean)
            invalid['items'][0].update(change)
            with self.assertRaises(ValueError):
                upload_resources(records, invalid, 'rainbond')
        duplicate = copy.deepcopy(bean)
        duplicate['items'].append(duplicate['items'][0])
        with self.assertRaises(ValueError):
            upload_resources(records, duplicate, 'rainbond')
        with self.assertRaises(ValueError):
            upload_resources(records, {'items': []}, 'rainbond')

    # capability_id: console.cleanup.upload-package-size-projection
    def test_package_size_is_separate_from_chunks_and_event_is_unique(self):
        records = [{'event_id': 'owned'}]
        bean = {'protocol': 1, 'scope': 'upload_chunks', 'items': [
            {'id': 'session', 'event_id': 'owned', 'file_name': '应用.zip', 'size_status': 'measured',
             'bytes': 17, 'objects': 2}], 'packages': [
            {'event_id': 'owned', 'size_status': 'measured', 'bytes': 97, 'objects': 3}]}
        resources = upload_resources(records, bean, 'rainbond')
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[1]['resourceType'], 'upload_package')
        self.assertEqual(resources[1]['sizeBytes'], 97)
        self.assertEqual(resources[1]['name'], '应用.zip / 上传包')
        self.assertEqual(resources[1]['actions'], [])
        bean['packages'][0]['referenced'] = True
        protected = upload_resources(records, bean, 'rainbond')[1]
        self.assertEqual(protected['protection'], 'referenced')
        self.assertEqual(protected['usageStatus'], 'referenced')
        self.assertEqual(protected['decision'], 'protected')

        for packages in [bean['packages'] * 2, [{'event_id': 'foreign', 'size_status': 'unavailable'}],
                         [{'event_id': 'owned', 'size_status': 'measured', 'bytes': True, 'objects': 1}]]:
            invalid = dict(bean, packages=packages)
            with self.assertRaises(ValueError):
                upload_resources(records, invalid, 'rainbond')

    # capability_id: console.cleanup.upload-inventory-scope
    def test_console_derives_event_scope_from_enterprise_and_region(self):
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        from typing import Any
        from unittest.mock import Mock
        path = Path(__file__).resolve().parents[1] / 'views/cleanup_inventory.py'
        cls = next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef))
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_upload_inventory')
        method.decorator_list = []
        teams = Mock()
        teams.values_list.return_value = ['owned-team']
        tenants = Mock()
        tenants.objects.filter.return_value = teams
        records = Mock()
        query = Mock()
        records.objects.filter.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.values_list.return_value.first.return_value = 9
        query.values.return_value = [{'ID': 9, 'event_id': 'owned'}]
        api = Mock()
        api.cleanup_upload_inventory.return_value = (200, {'bean': {'protocol': 1, 'scope': 'upload_chunks', 'items': []}})
        scope = {'Any': Any, 'Response': lambda data, status=200: SimpleNamespace(data=data, status_code=status),
                 'Tenants': tenants, 'PackageUploadRecord': records, 'RegionInvokeApi': lambda: api,
                 'upload_resources': upload_resources}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), scope)
        response = scope['_upload_inventory']('enterprise', 'region', 0, 0)
        self.assertEqual(response.status_code, 200)
        tenants.objects.filter.assert_called_once_with(enterprise_id='enterprise')
        records.objects.filter.assert_called_once_with(team_name__in=['owned-team'], region='region')
        api.cleanup_upload_inventory.assert_called_once_with('enterprise', 'region', ['owned'])
        self.assertFalse(response.data['referencesComplete'])
        self.assertIn('upload_package_and_reference_inventory_incomplete', response.data['failedScopes'])
        api.cleanup_upload_inventory.return_value = (200, {'bean': {'protocol': 1, 'scope': 'upload_chunks', 'items': [
            {'id': 'foreign', 'event_id': 'another-team', 'size_status': 'unavailable'}]}})
        response = scope['_upload_inventory']('enterprise', 'region', 0, 9)
        self.assertEqual(response.data['resources'], [])
        self.assertEqual(response.data['failedScopes'], ['upload_chunk_inventory_unavailable'])
        query.values.return_value = [{'ID': 8, 'event_id': None}, {'ID': 9, 'event_id': 'owned'}]
        api.cleanup_upload_inventory.return_value = (200, {'bean': {'protocol': 1, 'scope': 'upload_chunks', 'items': []}})
        response = scope['_upload_inventory']('enterprise', 'region', 0, 9)
        api.cleanup_upload_inventory.assert_called_with('enterprise', 'region', ['owned'])
        self.assertIn('upload_event_identity_unavailable', response.data['failedScopes'])
        query.values.return_value = [{'ID': index, 'event_id': 'event-{}'.format(index)} for index in range(1, 27)]
        response = scope['_upload_inventory']('enterprise', 'region', 0, 30)
        self.assertEqual(response.data['cursor'], 25)
        self.assertEqual(len(api.cleanup_upload_inventory.call_args.args[2]), 25)
        self.assertNotIn('event-26', api.cleanup_upload_inventory.call_args.args[2])

    def test_upload_measurement_cannot_be_called_through_generic_plugin_bridge(self):
        from console.services.cleanup_core_bridge import allowed_core_path
        self.assertFalse(allowed_core_path('/v2/cleanup/uploads/inventory'))

    def test_region_client_restricts_upload_request_path_and_identifiers(self):
        import ast
        import json
        import re
        from pathlib import Path
        from typing import Any, Dict, Tuple
        from unittest.mock import Mock
        path = Path(__file__).resolve().parents[2] / 'www/apiclient/regionapi.py'
        cls = next(node for node in ast.parse(path.read_text()).body
                   if isinstance(node, ast.ClassDef) and node.name == 'RegionInvokeApi')
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'cleanup_upload_inventory')
        isolated = ast.ClassDef(name='Client', bases=[], keywords=[], body=[method], decorator_list=[])
        scope = {'Any': Any, 'Dict': Dict, 'Tuple': Tuple, 're': re, 'json': json}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), scope)
        client = scope['Client']()
        client._cleanup_control_request = Mock(return_value=(200, {}))
        client.cleanup_upload_inventory('e', 'r', ['owned'])
        client._cleanup_control_request.assert_called_once_with(
            'e', 'r', '/v2/cleanup/uploads/inventory', b'{"event_ids": ["owned"]}')
        for ids in [[], ['owned', 'owned'], ['../other'], [None], 'owned', ['a'] * 51]:
            with self.assertRaises(ValueError):
                client.cleanup_upload_inventory('e', 'r', ids)
        self.assertEqual(client._cleanup_control_request.call_count, 1)
