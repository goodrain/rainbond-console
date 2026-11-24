# capability_id: console.vm-jobs.durable-observation
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase


class VMJobProcessRestartTests(TestCase):
    def test_committed_task_survives_real_process_exit_and_new_owner_reconnects(self):
        with tempfile.TemporaryDirectory(prefix='vm-job-restart-') as root:
            database = str(Path(root) / 'journal.sqlite3')
            common = '''import os,sys
from django.conf import settings
settings.DATABASES['default']['NAME']=sys.argv[1]
from console.tests import vm_restore_private_attributes_test
from django.db import connection
from console.models.main import ComponentK8sAttributes
from www.models.main import TenantServiceInfo
from console.services.vm_restore_journal import VMRestoreJournal,TrustedContext
journal=VMRestoreJournal()
'''
            first = common + '''
with connection.schema_editor() as schema:
 schema.create_model(TenantServiceInfo);schema.create_model(ComponentK8sAttributes)
service=TenantServiceInfo.objects.create(
 tenant_id='tenant-a',service_id='service-a',service_alias='vm-a',
 service_region='region-a',extend_method='vm',service_key='fixture')
context=TrustedContext(service)
journal.create_operation(context,'op-a','request-a','snapshot',request={'name':'snapshot-a','description':'','power_after':'previous'})
op=journal.claim(context,'op-a','dead-worker',1,100,2)
journal.mark_region_issued(context,None,'op-a','dead-worker',op['execution_epoch'],op['revision'],'',100)
os._exit(23)
'''
            second = common + '''
from console.services.vm_restore_worker import VMJobRunner
service=TenantServiceInfo.objects.get(service_id='service-a');context=TrustedContext(service)
class Driver:
 def observe(self,context,operation):
  return dict(operation_id='op-a',snapshot_name='snapshot-a',core_hash='a'*64,source_vm_uid='vm-uid-a',snapshot_uid='',
              phase='creating',ready_to_use=False,manifest_acked=False,finalized=False,error_code='')
VMJobRunner(journal=journal,driver=Driver(),owner='replacement-worker',clock=lambda:103).process(context,'op-a')
op=journal.read_operation(context,'op-a')
assert op['execution_epoch']==2 and op['lease_owner']=='replacement-worker'
assert op['observation']['phase']=='creating' and op['region_terminal'] is None
assert journal.active_operation(context)=='op-a'
print('RECONNECTED_SAME_DURABLE_OPERATION')
'''
            environment = dict(os.environ,
                               DJANGO_SETTINGS_MODULE='goodrain_web.test_settings',
                               PYTHONDONTWRITEBYTECODE='1',
                               HOME_DIR=root,
                               DATA_DIR=root,
                               PYTHONPATH=str(Path.cwd()))
            crashed = subprocess.run([sys.executable, '-c', first, database], env=environment, capture_output=True, timeout=10)
            self.assertEqual(crashed.returncode, 23, crashed.stderr.decode()[-800:])
            resumed = subprocess.run([sys.executable, '-c', second, database], env=environment, capture_output=True, timeout=10)
            self.assertEqual(resumed.returncode, 0, resumed.stderr.decode()[-800:])
            self.assertIn('RECONNECTED_SAME_DURABLE_OPERATION', resumed.stdout.decode())
