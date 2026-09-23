import json
import unittest
from console.services.cleanup_inventory import snapshot_reference_resource, failed_scope_label


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

    def test_scheduling_attributes_do_not_add_image_references(self):
        component = {'service_base': {'service_id': 's', 'image': 'goodrain.me/app:v1'},
                     'component_k8s_attributes': [
                         {'name': name, 'attribute_value': 'do-not-export'}
                         for name in ('affinity', 'nodeSelector', 'tolerations')]}
        result = snapshot_reference_resource({'ID': 7, 'snapshot': json.dumps({'components': [component]})}, 'r')
        self.assertTrue(result['observed'])
        self.assertEqual(result['images'], ['goodrain.me/app:v1'])
        self.assertNotIn('do-not-export', json.dumps(result))

    def test_incomplete_components_keep_other_known_image_evidence(self):
        components = [None, {'service_base': {'service_id': 's', 'image': 'goodrain.me/app:v1'},
                             'service_source': 'invalid'}]
        result = snapshot_reference_resource({'ID': 7, 'snapshot': json.dumps({'components': components})}, 'r')
        self.assertFalse(result['observed'])
        self.assertEqual(result['images'], ['goodrain.me/app:v1'])
        self.assertIn('snapshot_invalid_structure', result['incompleteReasons'])

    def test_unknown_overrides_and_missing_runtime_images_remain_protected(self):
        components = [
            {'service_base': {'service_id': 's', 'image': ''}},
            {'service_base': {'service_id': 't', 'image': 'goodrain.me/app:v1'},
             'component_k8s_attributes': [{'name': 'containers', 'attribute_value': 'do-not-export'}],
             'service_plugin_relation': [{'plugin_id': 'p'}]}]
        result = snapshot_reference_resource({'ID': 7, 'snapshot': json.dumps({'components': components})}, 'r')
        self.assertFalse(result['observed'])
        self.assertEqual(result['protection'], 'reference_unknown')
        self.assertEqual(set(result['incompleteReasons']), {
            'snapshot_missing_runtime_image', 'snapshot_plugin_reference_unknown', 'snapshot_k8s_override_unknown'})
        self.assertNotIn('do-not-export', json.dumps(result))

    def test_failure_labels_use_known_reasons_only(self):
        result = failed_scope_label({'id': 'snapshot:1', 'name': '订单 / v1', 'incompleteReasons': [
            'snapshot_missing_runtime_image', 'do-not-export', {}]})
        self.assertIn('未记录可核对的镜像', result)
        self.assertNotIn('do-not-export', result)

    def test_malformed_optional_fields_do_not_become_complete(self):
        for field, value in [('component_k8s_attributes', {}), ('component_k8s_attributes', ''),
                             ('component_k8s_attributes', [{'name': []}]),
                             ('service_plugin_relation', {}), ('service_source', [])]:
            component = {'service_base': {'service_id': 's', 'image': 'goodrain.me/app:v1'}, field: value}
            result = snapshot_reference_resource({'ID': 7, 'snapshot': json.dumps({'components': [component]})}, 'r')
            self.assertFalse(result['observed'], (field, value))
            self.assertEqual(result['images'], ['goodrain.me/app:v1'])
