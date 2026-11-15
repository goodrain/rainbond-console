# capability_id: console.vm-jobs.supervised-runtime
import os
from pathlib import Path
import tempfile
from unittest import TestCase, mock
from console.services import vm_job_health
from console.services.vm_snapshot_admission import snapshot_write_capability, require_snapshot_writer


class VMJobHealthTests(TestCase):
    def test_old_instance_stale_heartbeat_and_symlink_are_not_readiness(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.dict(os.environ, {
                'VM_JOB_RUNTIME_DIR': root,
                'VM_JOB_INSTANCE_ID': 'current-instance'
        }):
            self.assertFalse(vm_job_health.ready(now=100))
            vm_job_health.publish('ready', now=100)
            self.assertTrue(vm_job_health.ready(now=101))
            self.assertFalse(vm_job_health.ready(now=111))
            with mock.patch.dict(os.environ, {'VM_JOB_INSTANCE_ID': 'new-instance'}):
                self.assertFalse(vm_job_health.ready(now=101))
            vm_job_health.publish('database_unavailable', now=100)
            self.assertFalse(vm_job_health.ready(now=101))
            path = Path(root) / 'worker.json'
            path.unlink()
            path.symlink_to(Path(root) / 'absent')
            self.assertFalse(vm_job_health.ready(now=101))

    def test_live_worker_does_not_manufacture_missing_region_write_authority(self):
        with mock.patch.object(vm_job_health, 'ready', return_value=True):
            self.assertEqual(snapshot_write_capability(), {
                'available': False,
                'reason': 'region_authority_contract_unavailable'
            })
            with self.assertRaises(Exception) as captured:
                require_snapshot_writer()
            self.assertEqual(captured.exception.status_code, 503)
