import json
import unittest
from console.services.cleanup_inventory import snapshot_reference_resource


class SnapshotReferenceTests(unittest.TestCase):
    def test_projects_images_without_snapshot_configuration(self):
        row = {'ID': 7, 'snapshot': json.dumps({
            'component_group': {'group_name': '订单系统', 'group_version': 'v1'},
            'components': [{'service_base': {'service_id': 's', 'image': 'goodrain.me/app:v1'},
                            'service_source': {'image': 'goodrain.me/app:v0'},
                            'service_env_vars': [{'value': 'do-not-export'}],
                            'service_auths': [{'value': 'do-not-export'}]}]})}
        result = snapshot_reference_resource(row, 'r')
        self.assertEqual(result['images'], ['goodrain.me/app:v0', 'goodrain.me/app:v1'])
        self.assertEqual(result['name'], '订单系统 / v1')
        self.assertTrue(result['observed'])
        self.assertEqual(result['protection'], 'referenced')
        self.assertNotIn('do-not-export', json.dumps(result))
        self.assertNotIn('retirement', result)

    def test_unknown_code_build_or_sidecar_references_are_incomplete(self):
        for component in [
                {'service_base': {'service_id': 's', 'image': ''}},
                {'service_base': {'service_id': 's', 'image': 'goodrain.me/app:v1'},
                 'service_plugin_relation': [{'plugin_id': 'p'}]},
                {'service_base': {'service_id': 's', 'image': 'https://do-not-export@example.invalid'}},
                {'service_base': {'service_id': 's', 'image': 'goodrain.me/app:v1'},
                 'component_k8s_attributes': [{'name': 'custom'}]}]:
            result = snapshot_reference_resource({'ID': 7, 'snapshot': json.dumps({'components': [component]})}, 'r')
            self.assertFalse(result['observed'])
            self.assertEqual(result['protection'], 'reference_unknown')
            self.assertNotIn('do-not-export', json.dumps(result))

    def test_malformed_snapshot_does_not_become_empty_complete_inventory(self):
        for raw in ['invalid', 'null', '{}', '{"components":[null]}']:
            result = snapshot_reference_resource({'ID': 7, 'snapshot': raw}, 'r')
            self.assertFalse(result['observed'])
