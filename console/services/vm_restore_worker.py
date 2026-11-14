"""Durable claim and Region evidence reconciliation.

Mutation production remains closed until Region supplies the authority/epoch
contract. A 202, native Ready or local lease is never terminal Region evidence.
"""
import logging
import signal
import time
import uuid

from django.db import close_old_connections

from console.models.main import ComponentK8sAttributes
from console.services import vm_job_health
from console.services.vm_restore_journal import (JournalConflict, TrustedContext, VMRestoreJournal, VM_RESTORE_ACTIVE_OPERATION,
                                                 TERMINAL)
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants

logger = logging.getLogger('default')


class DependencyPending(Exception):
    pass


class Go4SnapshotEvidence:
    def __init__(self, client=None):
        self.client = client or RegionInvokeApi()

    def observe(self, context, operation):
        if operation['kind'] != 'snapshot':
            raise DependencyPending()
        name = operation.get('request', {}).get('name')
        if not name and operation.get('snapshot_uid'):
            manifest = VMRestoreJournal().read_manifest(context, operation['snapshot_uid'], operation['document_hash'])
            name = manifest['snapshot_name']
        if not name:
            raise DependencyPending()
        pk, tenant_id, service_id, region, _alias = context.identity
        live = TenantServiceInfo.objects.get(pk=pk)
        if (live.tenant_id, live.service_id, live.service_region) != (tenant_id, service_id, region):
            raise JournalConflict()
        team = Tenants.objects.get(tenant_id=live.tenant_id)
        response, body = self.client.get_vm_snapshot(live.service_region, team.tenant_name, live.service_alias, name)
        if response.get('status') != 200 or not isinstance(body, dict) or body.get('code', 200) != 200:
            raise DependencyPending()
        value = body.get('bean')
        if not isinstance(value, dict) or 'error' in value:
            raise DependencyPending()
        keys = ('operation_id', 'snapshot_name', 'core_hash', 'source_vm_uid', 'snapshot_uid', 'phase', 'ready_to_use',
                'manifest_acked', 'finalized', 'error_code')
        result = {key: value.get(key, '' if key in ('snapshot_uid', 'error_code') else None) for key in keys}
        if result['snapshot_name'] != name:
            raise JournalConflict()
        return result


class VMJobRunner:
    def __init__(self, journal=None, driver=None, owner=None, clock=None, restore_client=None,
                 snapshot_client=None, snapshot_factory=None):
        self.journal = journal or VMRestoreJournal()
        self.driver = driver or Go4SnapshotEvidence()
        self.owner = owner or 'worker-' + uuid.uuid4().hex
        self.clock = clock or (lambda: int(time.time()))
        self.restore_client = restore_client
        self.snapshot_client = snapshot_client
        self.snapshot_factory = snapshot_factory
        self.explicit_driver = driver is not None

    def process(self, context, operation_id):
        current = self.journal.read_operation(context, operation_id)
        if current['kind'] == 'restore':
            from console.services.vm_restore_command_worker import RestoreCommandRunner
            RestoreCommandRunner(self.journal, self.restore_client, self.owner, self.clock).process(context, operation_id)
            return
        if current['kind'] == 'snapshot' and not self.explicit_driver:
            from console.services.vm_snapshot_job_worker import SnapshotJobRunner
            factory = self.snapshot_factory or SnapshotJobRunner
            factory(self.journal, self.snapshot_client, self.owner, self.clock).process(context, operation_id)
            return
        now = self.clock()
        if current['phase'] in TERMINAL or current['retry_at'] > now:
            return
        op = self.journal.claim(context, operation_id, self.owner, current['revision'], now, 30)
        try:
            if op['region_intent'] is None:
                raise DependencyPending()
            observed = self.driver.observe(context, op)
            op = self.journal.record_observation(context, operation_id, self.owner, op['execution_epoch'], op['revision'],
                                                 observed, self.clock())
            # Go4 DTO lacks complete source identity and epoch/fence terminal
            # proof. Preserve the same task and intent instead of fabricating it.
            code = 'DEPENDENCY_PENDING'
        except JournalConflict:
            raise
        except DependencyPending:
            code = 'DEPENDENCY_PENDING'
        except Exception:
            code = 'REGION_UNKNOWN'
        self.journal.advance(context,
                             operation_id,
                             self.owner,
                             op['execution_epoch'],
                             op['revision'],
                             op['phase'],
                             self.clock(),
                             retry_at=self.clock() + 30,
                             error_code=code)

    def run_once(self, limit=16):
        pointers = ComponentK8sAttributes.objects.filter(name=VM_RESTORE_ACTIVE_OPERATION).exclude(
            attribute_value__contains='"operation_id":""').order_by('pk')[:limit]
        seen = set()
        for pointer in pointers:
            key = (pointer.tenant_id, pointer.component_id)
            if key in seen:
                continue
            seen.add(key)
            services = list(
                TenantServiceInfo.objects.filter(tenant_id=pointer.tenant_id,
                                                 service_id=pointer.component_id,
                                                 extend_method='vm'))
            if len(services) != 1:
                logger.warning('vm_job_scope_conflict')
                continue
            try:
                context = TrustedContext(services[0])
                operation_id = self.journal.active_operation(context)
                if operation_id:
                    self.process(context, operation_id)
            except JournalConflict:
                logger.warning('vm_job_claim_or_record_conflict')


def run_worker(interval=2):
    stopped = [False]
    previous = {}

    def stop(_signum, _frame):
        stopped[0] = True

    for signum in (signal.SIGTERM, signal.SIGINT):
        previous[signum] = signal.signal(signum, stop)
    runner = VMJobRunner()
    try:
        while not stopped[0]:
            close_old_connections()
            try:
                runner.run_once()
                vm_job_health.publish('ready')
            except Exception:
                vm_job_health.publish('database_unavailable')
                logger.warning('vm_job_scan_unavailable')
            finally:
                close_old_connections()
            deadline = time.monotonic() + interval
            while not stopped[0] and time.monotonic() < deadline:
                time.sleep(min(.1, max(0, deadline - time.monotonic())))
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
