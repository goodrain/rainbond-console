"""Durable bounded prepare/halt commands over the frozen actual Region SDK.

This is transport progress, not a second Region engine. Complete configuration,
rollback and power intent reads remain required before the later producer steps.
"""
import time
import uuid
from django.db import connections

from console.services.vm_restore_journal import (JournalConflict, RESTORE_RPC_ERRORS, TERMINAL, VMRestoreJournal, fields,
                                                 integer, require)
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants

ERROR_STATUS = {
    'vm_restore_invalid_request': 400,
    'vm_restore_forbidden': 403,
    'vm_restore_not_found': 404,
    'vm_restore_conflict': 409,
    'vm_restore_provider_not_qualified': 422,
    'vm_restore_capacity_insufficient': 422,
    'vm_restore_pending': 202,
    'vm_restore_outcome_unknown': 202,
    'vm_restore_dependency_unavailable': 503,
    'vm_restore_internal_error': 500
}


class RestoreCommandRunner:
    def __init__(self, journal=None, client=None, owner=None, clock=None):
        self.journal = journal or VMRestoreJournal()
        self.client = client or RegionInvokeApi()
        self.owner = owner or 'worker-' + uuid.uuid4().hex
        self.clock = clock or (lambda: int(time.time()))

    @staticmethod
    def _scope(context):
        pk, tenant_id, service_id, region, alias = context.identity
        live = TenantServiceInfo.objects.get(pk=pk)
        require((live.tenant_id, live.service_id, live.service_region, live._state.db,
                 live.extend_method) == (tenant_id, service_id, region, alias, 'vm'))
        team = Tenants.objects.get(tenant_id=tenant_id)
        return live.service_region, team.tenant_name, live.service_alias

    def _error(self, context, op, status=0, code='vm_restore_outcome_unknown'):
        if op['rpc']['pending'] is None:
            return self.journal.advance(context,
                                        op['operation_id'],
                                        self.owner,
                                        op['execution_epoch'],
                                        op['revision'],
                                        op['phase'],
                                        self.clock(),
                                        retry_at=self.clock() + 30,
                                        error_code='REGION_UNKNOWN')
        return self.journal.record_restore_command_error(context, op['operation_id'], self.owner, op['execution_epoch'],
                                                         op['revision'], status, code, self.clock())

    @staticmethod
    def _failure(status, bean):
        code = bean.get('error_code') if isinstance(bean, dict) else None
        if type(code) is str and code in RESTORE_RPC_ERRORS and ERROR_STATUS[code] == status:
            return status, code
        return 0, 'vm_restore_outcome_unknown'

    @staticmethod
    def _envelope(response, body):
        if not (isinstance(response, dict) and type(response.get('status')) is int and isinstance(body, dict)
                and isinstance(body.get('bean'), dict)):
            raise ValueError('Invalid restore RPC envelope')
        return response['status'], body['bean']

    def process(self, context, operation_id):
        require(not connections[context.identity[4]].in_atomic_block)
        current = self.journal.read_operation(context, operation_id)
        if current['kind'] != 'restore' or current['phase'] in TERMINAL or current['retry_at'] > self.clock():
            return
        if (current.get('rpc', {}).get('pending') or {}).get('state') in ('rejected', 'conflict'):
            return
        op = self.journal.claim(context, operation_id, self.owner, current['revision'], self.clock(), 30)
        if 'rpc' not in op:
            # Old restore rows have no sealed command/power intent. Never infer it.
            self._await_producer(context, op)
            return
        op = self.journal.plan_next_restore_command(context, operation_id, self.owner, op['execution_epoch'], op['revision'],
                                                    self.clock())
        if op['rpc']['completed'] == ['prepare', 'halt', 'config-ack'] or (op['rpc']['observation'] or {}).get('complete'):
            self._await_producer(context, op)
            return
        try:
            scope = self._scope(context)
            response, body = self.client.get_vm_restore(*scope, operation_id)
            status, bean = self._envelope(response, body)
        except JournalConflict:
            raise
        except Exception:
            self._error(context, op)
            return
        pending = op['rpc']['pending']
        if status == 404 and pending and pending['action'] == 'prepare' and not op['rpc']['server_epoch']:
            # A lost prepare can be reissued only under the original op/intent,
            # after observing no Region fence or admission. A new op is forbidden.
            try:
                response, body = self.client.get_vm_restore_control(*scope)
                control_status, control = self._envelope(response, body)
                if control_status != 200:
                    self._error(context, op, *self._failure(control_status, control))
                    return
                fields(control, ('control_revision', 'binding_generation', 'fenced', 'admission_in_progress'),
                       ('active_operation_id', ))
                for key in ('control_revision', 'binding_generation'):
                    integer(control[key], maximum=2**64 - 1)
                require(
                    type(control['fenced']) is bool and type(control['admission_in_progress']) is bool
                    and type(control.get('active_operation_id', '')) is str)
                if control['fenced'] or control['admission_in_progress'] or control.get('active_operation_id', ''):
                    self._error(context, op, 409, 'vm_restore_conflict')
                    return
            except JournalConflict:
                raise
            except Exception:
                self._error(context, op)
                return
        elif status == 200:
            op = self.journal.record_restore_status(context, operation_id, self.owner, op['execution_epoch'], op['revision'],
                                                    bean, self.clock())
            if op['rpc']['observation']['complete'] or not op['rpc']['observation']['source_config_ready']:
                self._await_producer(context, op)
                return
            control = op['rpc']['observation']
            if pending is None:
                if not control['config_committed']:
                    self._await_producer(context, op)
                    return
                from console.services.vm_restore_config_commit import RestoreConfigCommitter
                store = RestoreConfigCommitter(self.journal)
                op = store.commit(context, operation_id, self.owner, op['execution_epoch'], op['revision'], self.clock())
                op = self.journal.plan_restore_ack(context, operation_id, self.owner, op['execution_epoch'], op['revision'],
                                                   self.clock())
                pending = op['rpc']['pending']
        else:
            self._error(context, op, *self._failure(status, bean))
            return
        document = None
        if pending['action'] == 'config-ack':
            from console.services.vm_restore_config_commit import RestoreConfigCommitter
            document = RestoreConfigCommitter(self.journal).read_committed(context, operation_id, self.owner,
                                                                           op['execution_epoch'], op['revision'], self.clock())
        if pending['request'] is not None:
            request = dict(pending['request'])
        else:
            request = dict(expected_control_revision=control['control_revision'],
                           expected_binding_generation=control['binding_generation'])
            if op['rpc']['server_epoch']:
                request['expected_operation_epoch'] = op['rpc']['server_epoch']
            if pending['action'] == 'prepare':
                manifest = self.journal.read_manifest(context, op['snapshot_uid'], op['document_hash'])
                request.update(snapshot_name=manifest['snapshot_name'], power_after=op['rpc']['power_after'])
            elif pending['action'] == 'config-ack':
                request.update(commit_hash=document['commit_hash'], document_hash=document['document_hash'])
        op = self.journal.issue_restore_command(context, operation_id, self.owner, op['execution_epoch'], op['revision'],
                                                request, self.clock())
        # The real transaction above commits before _any_ POST or network wait.
        try:
            scope = self._scope(context)
            response, body = self.client.command_vm_restore(*scope, operation_id, pending['action'], request)
            status, bean = self._envelope(response, body)
        except JournalConflict:
            raise
        except Exception:
            self._error(context, op)
            return
        if status == 202 and bean.get('applied') is True and not bean.get('error_code'):
            op = self.journal.record_restore_status(context,
                                                    operation_id,
                                                    self.owner,
                                                    op['execution_epoch'],
                                                    op['revision'],
                                                    bean,
                                                    self.clock(),
                                                    command_applied=bean.get('source_config_ready') is True)
            if not op['rpc']['observation']['source_config_ready']:
                self._await_producer(context, op)
        elif status == 202 and bean.get('applied') is False and 'operation_id' in bean:
            op = self.journal.record_restore_status(context, operation_id, self.owner, op['execution_epoch'], op['revision'],
                                                    bean, self.clock())
            self._error(context, op, 202, 'vm_restore_pending')
        else:
            self._error(context, op, *self._failure(status, bean))

    def _await_producer(self, context, op):
        self.journal.advance(context,
                             op['operation_id'],
                             self.owner,
                             op['execution_epoch'],
                             op['revision'],
                             op['phase'],
                             self.clock(),
                             retry_at=self.clock() + 30,
                             error_code='DEPENDENCY_PENDING')
