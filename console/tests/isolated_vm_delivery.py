"""Delivery capture lifecycle with real SQLite persistence and simulated Region I/O."""
import copy
import unittest
from console.tests import isolated_delivery_workflow as f
from console.services.vm_delivery_preparation import VMDeliveryPreparation


class VMDeliveryPreparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f.DeliveryWorkflowTest.setUpClass()

    def setUp(self):
        self.fixture = f.DeliveryWorkflowTest()
        self.fixture.setUp()
        self.service = self.fixture.service
        self.service.update_metadata(f.USER, f.SCOPE, f.PAYLOAD)
        self.source = copy.deepcopy(f.SOURCE)
        self.source['apps'][0].update(extend_method='vm',
                                      service_source='vm_run',
                                      vm={
                                          'boot_mode':
                                          'uefi',
                                          'disk_layout': [{
                                              'disk_key': 'disk',
                                              'volume_name': 'disk',
                                              'disk_role': 'root',
                                              'image': 'registry.test/base:original',
                                              'source_type': 'registry',
                                              'format': 'iso'
                                          }]
                                      },
                                      component_k8s_attributes=[{
                                          'name': 'vm_disk_imports',
                                          'attribute_value': 'old-import'
                                      }, {
                                          'name': 'vm_disk_layout',
                                          'attribute_value': 'old-layout'
                                      }])
        self.fixture.gateway.source = lambda scope: (copy.deepcopy(self.source), 'VM app')
        self.calls = []
        self.phase = 'ready'
        self.preparation = VMDeliveryPreparation(self.service)
        self.fixture.gateway.vm_capture = self.capture

    def capture(self, task, item, action):
        from django.db import connection
        self.assertFalse(connection.in_atomic_block, 'Region I/O held a DB transaction')
        self.calls.append((action, item.result['capture_id']))
        if action == 'release':
            return {'phase': 'released'}
        return {
            'phase': self.phase,
            'capture_id': item.result['capture_id'],
            'image_name': 'registry.test/vm:captured',
            'event_id': 'captured-event',
            'boot_mode': 'uefi'
        }

    def test_export_build_and_cleanup_are_distinct_persistent_steps(self):
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'stages')
        for phase, expected in [('exporting', 'exporting'), ('ready', 'ready'), ('building', 'building'),
                                ('building', 'building'), ('success', 'releasing')]:
            self.phase = phase
            self.preparation.advance(task.id)
            self.assertEqual(task.items.get().status, expected)
            self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)
        self.preparation.advance(task.id)
        task.refresh_from_db()
        self.assertEqual(task.status, 'succeeded')
        public = self.preparation.status(f.SCOPE, task.id)
        self.assertEqual(public['version_id'], str(task.version_id))
        previous = len(self.calls)
        self.preparation.advance(task.id)
        self.assertEqual(len(self.calls), previous)
        with self.assertRaises(f.DeliveryError):
            self.preparation.cancel(f.SCOPE, task.id)
        with self.assertRaises(f.DeliveryError):
            self.preparation.retry(f.SCOPE, task.id)

    def test_transport_failure_never_exposes_error_details_or_publishes_a_version(self):
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'transport')
        original = self.capture

        def unavailable(task, item, action):
            if action == 'prepare':
                raise RuntimeError('UPSTREAM_PRIVATE_DETAIL')
            return original(task, item, action)

        self.fixture.gateway.vm_capture = unavailable
        self.complete(task)
        self.assertEqual(task.status, 'failed')
        self.assertNotIn('UPSTREAM_PRIVATE_DETAIL', str(self.preparation.data(task)))
        self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)

    def test_cancellation_during_a_remote_write_wins_over_success(self):
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'cancel-race')
        original = self.capture

        def cancel_during_prepare(live, item, action):
            if action == 'prepare':
                self.preparation.cancel(f.SCOPE, live.id)
            return original(live, item, action)

        self.fixture.gateway.vm_capture = cancel_during_prepare
        self.phase = 'success'
        self.complete(task)
        self.assertEqual(task.status, 'cancelled')
        self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)

    def test_expired_job_cleans_resources_and_an_owned_lease_prevents_duplicate_io(self):
        import time
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'expired')
        task.payload['lease_until'] = int(time.time()) + 60
        task.save()
        self.preparation.advance(task.id)
        self.assertEqual(self.calls, [])
        task.payload['lease_until'] = 0
        task.payload['deadline'] = 0
        task.save()
        self.complete(task)
        self.assertEqual(task.status, 'failed')
        self.assertTrue(all(action == 'release' for action, _ in self.calls))

    def test_a_late_worker_cannot_overwrite_a_new_lease(self):
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'late-worker')
        original = self.capture

        def renew_lease(live, item, action):
            row = f.models.DeliveryTask.objects.get(pk=live.id)
            row.payload['lease'] = 'new-worker'
            row.save()
            return original(live, item, action)

        self.fixture.gateway.vm_capture = renew_lease
        self.phase = 'success'
        self.preparation.advance(task.id)
        self.assertEqual(task.items.get().status, 'queued')
        self.assertNotIn('image_name', task.items.get().result)
        self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)

    def test_request_identity_and_capture_result_identity_cannot_be_reused(self):
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'identity')
        with self.assertRaises(f.DeliveryError):
            self.preparation.submit(f.USER, f.SCOPE, {**f.PAYLOAD, 'version': '2.0.0'}, 'identity')
        original = self.capture

        def foreign_capture(live, item, action):
            result = original(live, item, action)
            if action != 'release':
                result['capture_id'] = 'foreign'
            return result

        self.fixture.gateway.vm_capture = foreign_capture
        self.complete(task)
        self.assertEqual(task.status, 'failed')
        self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)

    def test_capture_records_physical_capacity_for_the_installed_vm(self):
        self.source['apps'][0]['service_volume_map_list'] = [{
            'volume_name': 'disk',
            'volume_capacity': 1
        }, {
            'volume_name': 'installation-media',
            'volume_capacity': 1
        }]
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'capacity')
        original = self.capture

        def sized(live, item, action):
            return {**original(live, item, action), 'request_size': '40Gi', 'capacity_gib': 40}

        self.fixture.gateway.vm_capture = sized
        self.phase = 'success'
        self.complete(task)
        app = task.version.manifest['apps'][0]
        self.assertEqual(app['vm']['disk_layout'][0]['request_size'], '40Gi')
        self.assertEqual(app['service_volume_map_list'], [{'volume_name': 'disk', 'volume_capacity': 40}])

    def complete(self, task):
        for _ in range(15):
            self.preparation.advance(task.id)
            task.refresh_from_db()
            if task.status in ('succeeded', 'failed', 'cancelled'):
                return task
        self.fail('capture did not settle')

    def test_vm_cannot_be_created_by_retaining_the_base_image(self):
        with self.assertRaises(f.DeliveryError):
            self.service.create(f.USER, f.SCOPE, f.PAYLOAD, 'unsafe-direct')

    def test_capture_freezes_current_image_without_changing_original_source(self):
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'capture-one')
        self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)
        self.assertEqual(task.id, self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'capture-one').id)
        self.preparation.advance(task.id)
        self.phase = 'success'
        self.complete(task)
        self.assertEqual(task.status, 'succeeded')
        app = task.version.manifest['apps'][0]
        self.assertEqual(app['share_image'], 'registry.test/vm:captured')
        self.assertEqual(app['vm']['disk_layout'][0]['format'], 'raw.gz')
        self.assertEqual(app['vm']['disk_layout'][0]['source_type'], 'http-artifact')
        self.assertEqual(app['vm']['boot_mode'], 'uefi')
        self.assertFalse(any(a['name'] in ('vm_disk_imports', 'vm_disk_layout') for a in app['component_k8s_attributes']))
        self.assertEqual(self.source['apps'][0]['delivered_path'], f.SOURCE['apps'][0]['delivered_path'])
        self.assertIn('release', [action for action, _ in self.calls])

    def test_failed_capture_is_cleaned_and_retry_gets_a_new_capture_identity(self):
        self.phase = 'failed'
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'retry-one')
        self.complete(task)
        self.assertEqual(task.status, 'failed')
        first_id = task.items.get().result['capture_id']
        self.preparation.retry(f.SCOPE, task.id)
        task.refresh_from_db()
        self.assertNotEqual(first_id, task.items.get().result['capture_id'])
        self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)
        self.phase = 'success'
        self.complete(task)
        self.assertEqual(task.status, 'succeeded')

    def test_cancel_waits_for_cleanup_and_never_creates_a_version(self):
        task = self.preparation.submit(f.USER, f.SCOPE, f.PAYLOAD, 'cancel-one')
        self.preparation.advance(task.id)
        self.preparation.cancel(f.SCOPE, task.id)
        self.complete(task)
        self.assertEqual(task.status, 'cancelled')
        self.assertEqual(f.models.DeliveryTemplateVersion.objects.count(), 0)

    def test_version_is_reserved_and_mixed_application_uses_original_container_artifact(self):
        container = copy.deepcopy(f.SOURCE['apps'][0])
        container.update(service_id='container', service_key='container', service_share_uuid='container+container')
        self.source['apps'].append(container)
        payload = {**f.PAYLOAD, 'service_ids': ['web', 'container']}
        task = self.preparation.submit(f.USER, f.SCOPE, payload, 'mixed-one')
        with self.assertRaises(f.DeliveryError):
            self.preparation.submit(f.USER, f.SCOPE, payload, 'mixed-two')
        self.phase = 'success'
        self.complete(task)
        self.assertEqual(task.status, 'succeeded')
        self.assertEqual(task.version.manifest['apps'][1]['share_image'], container['delivered_path'])


if __name__ == '__main__':
    unittest.main()
