# capability_id: console.vm-restore.command-process-restart
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from unittest import TestCase

from console.tests import vm_restore_command_journal_test as fixtures
from console.tests import vm_restore_command_worker_test as wire

CHILD = r'''
import os, sys
from types import SimpleNamespace
from unittest import mock
import django
django.setup()
from console.tests import vm_snapshot_read_api_test as import_only_optional_sdk
from django.db import connections
from django.conf import settings
from console.models.main import ComponentK8sAttributes
from www.models.main import TenantServiceInfo
from console.services.vm_restore_journal import TrustedContext, VMRestoreJournal
from console.services.vm_restore_worker import VMJobRunner
from www.apiclient.regionapi import RegionInvokeApi
import urllib3
db_path, endpoint, crash, now = sys.argv[1:]
connections.databases['restart'] = dict(connections.databases['default'], NAME=db_path)
pool = urllib3.PoolManager()
client = RegionInvokeApi()
journal = VMRestoreJournal()
with mock.patch.object(TenantServiceInfo, 'objects', TenantServiceInfo.objects.db_manager('restart')), \
     mock.patch.object(ComponentK8sAttributes, 'objects', ComponentK8sAttributes.objects.db_manager('restart')), \
     mock.patch.object(client, '_RegionInvokeApi__get_region_access_info', return_value=(endpoint, '')), \
     mock.patch.object(client, '_RegionInvokeApi__get_tenant_region_info',
                       return_value=SimpleNamespace(region_tenant_name='team-a')), \
     mock.patch.object(client, 'get_client', return_value=pool), \
     mock.patch.dict(settings.MODULES, {'RegionToken':False}), \
     mock.patch('www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name',
                return_value=SimpleNamespace(region_name='region-a')), \
     mock.patch('console.services.vm_restore_command_worker.Tenants.objects.get',
                return_value=SimpleNamespace(tenant_name='console-team')):
    if crash == 'before-post':
        original = journal.issue_restore_command
        def issue(*args, **kwargs):
            original(*args, **kwargs)
            os._exit(23)
        journal.issue_restore_command = issue
    if crash == 'after-post':
        original = client.command_vm_restore
        def post(*args, **kwargs):
            original(*args, **kwargs)
            os._exit(24)
        client.command_vm_restore = post
    context = TrustedContext(TenantServiceInfo.objects.get(service_id='service-a'))
    VMJobRunner(journal=journal, restore_client=client, owner='crashing' if crash!='none' else 'restarted',
                clock=lambda:int(now)).process(context, 'restore-a')
pool.clear()
connections.close_all()
'''


class VMRestoreCommandProcessRestartTests(TestCase):
    setUp = fixtures.VMRestoreCommandJournalTests.setUp
    close_database = fixtures.VMRestoreCommandJournalTests.close_database
    begin = fixtures.VMRestoreCommandJournalTests.begin
    seal = fixtures.VMRestoreCommandJournalTests.seal
    restore_operation = fixtures.VMRestoreCommandJournalTests.restore_operation

    def exercise(self, crash):
        self.restore_operation()
        manifest = self.journal.read_manifest(self.ctx, 'snapshot-uid-a')
        server = wire.RestoreLoopback(manifest)
        self.addCleanup(server.close)
        with tempfile.TemporaryDirectory(prefix='vm-command-restart-') as directory:
            database = Path(directory) / 'journal.sqlite3'
            raw = sqlite3.connect(database)
            self.database.connection.backup(raw)
            raw.close()
            command = [
                sys.executable, '-B', '-c', CHILD,
                str(database), 'http://127.0.0.1:{}'.format(server.server.server_port)
            ]
            result = subprocess.run(command + [crash, '140'], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 23 if crash == 'before-post' else 24, 'child must exit at the real crash point')

            def read_operation():
                with sqlite3.connect(database) as connection:
                    row = connection.execute('SELECT attribute_value FROM component_k8s_attributes WHERE name=?',
                                             ('vm_restore_operation_restore-a', )).fetchone()
                    return json.loads(row[0])

            issued = read_operation()
            self.assertEqual(issued['rpc']['pending']['state'], 'issued')
            self.assertEqual(issued['rpc']['pending']['attempts'], 1)
            self.assertEqual(issued['rpc']['server_epoch'], '')
            self.assertEqual(server.exists, crash == 'after-post')
            result = subprocess.run(command + ['none', '180'], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, 'new OS process must reconnect and reconcile the same command')
            saved = read_operation()
            self.assertEqual(saved['operation_id'], 'restore-a')
            self.assertEqual(saved['execution_epoch'], issued['execution_epoch'] + 1)
            self.assertEqual(saved['rpc']['server_epoch'], server.epoch)
            self.assertEqual(saved['rpc']['completed'], ['prepare'])
            self.assertEqual(saved['rpc']['commands'][0]['attempts'], 2)
            self.assertIsNone(saved['region_terminal'])
            with sqlite3.connect(database) as connection:
                pointer = json.loads(
                    connection.execute('SELECT attribute_value FROM component_k8s_attributes WHERE name=?',
                                       ('vm_restore_active_operation', )).fetchone()[0])
            self.assertEqual(pointer['operation_id'], 'restore-a')
            posts = [call for call in server.calls if call[0] == 'POST']
            self.assertTrue(all('/vm-restores/restore-a/steps/prepare' in call[1] for call in posts))
            if crash == 'after-post':
                self.assertEqual(posts[0][2], posts[-1][2], 'restart cannot rewrite the issued request after observing epoch')

    def test_hard_exit_after_sql_commit_before_post_restarts_with_same_operation(self):
        self.exercise('before-post')

    def test_hard_exit_after_post_before_observation_restarts_with_server_epoch(self):
        self.exercise('after-post')
