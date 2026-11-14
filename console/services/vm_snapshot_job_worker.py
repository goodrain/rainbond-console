"""One bounded snapshot command in the existing durable VM job worker."""
import time
import uuid
import json

from django.db import connections

from console.services.vm_restore_journal import (JournalConflict, TERMINAL, VMRestoreJournal, canonical, require)
from console.services.vm_snapshot_authority import (SnapshotProofPending, observation, source_context, terminal_evidence)
from console.services.vm_snapshot_manifest_ack import SnapshotManifestService, ready_action, snapshot_prepare_body
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants


class SnapshotJobRunner:
    def __init__(self, journal=None, client=None, owner=None, clock=None):
        self.journal = journal or VMRestoreJournal()
        self.client = client or RegionInvokeApi()
        self.owner = owner or 'worker-' + uuid.uuid4().hex
        self.clock = clock or (lambda: int(time.time()))

    @staticmethod
    def _scope(context):
        alias = context.identity[4]
        live = TenantServiceInfo.objects.using(alias).get(pk=context.identity[0])
        require((live.tenant_id, live.service_id, live.service_region) == context.identity[1:4] and live.extend_method == 'vm')
        team = Tenants.objects.using(alias).get(tenant_id=live.tenant_id)
        return live.service_region, team.tenant_name, live.service_alias

    @staticmethod
    def _envelope(response, body):
        require(
            isinstance(response, dict) and type(response.get('status')) is int and isinstance(body, dict)
            and isinstance(body.get('bean'), dict))
        raw = json.loads(canonical(body['bean']))
        if 'error' not in raw:
            raw.setdefault('error_code', '')
            raw.setdefault('snapshot_uid', '')
        return response['status'], raw

    def _wait(self, context, operation, code='DEPENDENCY_PENDING'):
        return self.journal.advance(context,
                                    operation['operation_id'],
                                    self.owner,
                                    operation['execution_epoch'],
                                    operation['revision'],
                                    operation['phase'],
                                    self.clock(),
                                    retry_at=self.clock() + 30 if code != 'CONFLICT' else 0,
                                    error_code=code)

    def _record(self, context, operation, raw):
        request = operation['request']
        require(
            raw.get('operation_id') == operation['operation_id'] == operation['request_id']
            and raw.get('snapshot_name') == request['name'] and raw.get('description') == request['description']
            and raw.get('power_after') == request['power_after'])
        previous = operation.get('observation')
        if previous:
            require(previous['core_hash'] == raw.get('core_hash') and previous['source_vm_uid'] == raw.get('source_vm_uid'))
        try:
            server = source_context(operation, raw)
        except SnapshotProofPending:
            if operation['region_intent']['namespace']:
                raise
            basic = observation(raw)
            basic = {
                key: value
                for key, value in basic.items()
                if key in ('operation_id', 'snapshot_name', 'core_hash', 'source_vm_uid', 'snapshot_uid', 'phase',
                           'ready_to_use', 'manifest_acked', 'finalized', 'error_code')
            }
            operation = self.journal.mark_region_issued(context, None, operation['operation_id'], self.owner,
                                                        operation['execution_epoch'], operation['revision'], raw['core_hash'],
                                                        self.clock())
            self.journal.record_observation(context, operation['operation_id'], self.owner, operation['execution_epoch'],
                                            operation['revision'], basic, self.clock())
            raise
        operation = self.journal.mark_region_issued(context, server, operation['operation_id'], self.owner,
                                                    operation['execution_epoch'], operation['revision'], raw['core_hash'],
                                                    self.clock())
        operation = self.journal.record_observation(context, operation['operation_id'], self.owner,
                                                    operation['execution_epoch'], operation['revision'], observation(raw),
                                                    self.clock())
        return operation

    def _prepare(self, context, operation):
        body = snapshot_prepare_body(operation)
        operation = self.journal.mark_region_issued(context, None, operation['operation_id'], self.owner,
                                                    operation['execution_epoch'], operation['revision'], '', self.clock())
        response, payload = self.client.create_vm_snapshot(*self._scope(context), body)
        status, raw = self._envelope(response, payload)
        if status != 202 or 'error' in raw:
            self._wait(context, operation, 'CONFLICT' if status in (400, 403, 404, 409, 422) else 'REGION_UNKNOWN')
            return
        operation = self._record(context, operation, raw)
        self._wait(context, operation)

    def process(self, context, operation_id):
        require(not connections[context.identity[4]].in_atomic_block)
        current = self.journal.read_operation(context, operation_id)
        if current['kind'] != 'snapshot' or current['phase'] in TERMINAL or current['retry_at'] > self.clock():
            return
        if current['error_code'] == 'CONFLICT':
            return
        operation = self.journal.claim(context, operation_id, self.owner, current['revision'], self.clock(), 30)
        # Old immutable three-field requests cannot acquire a new actor/body.
        actor = operation.get('request', {}).get('operator')
        if (not actor or actor.strip() != actor or actor.casefold() in ('none', 'anonymous', 'anonymoususer', 'system')
                or operation['request_id'] != operation_id):
            self._wait(context, operation)
            return
        if not all(
                callable(getattr(self.client, name, None))
                for name in ('create_vm_snapshot', 'get_vm_snapshot', 'command_vm_snapshot')):
            self._wait(context, operation)
            return
        try:
            scope = self._scope(context)
            if operation['region_intent'] is None:
                self._prepare(context, operation)
                return
            response, payload = self.client.get_vm_snapshot(*scope, operation['request']['name'])
            status, raw = self._envelope(response, payload)
            if status == 404 and not operation['region_intent']['core_hash'] and 'observation' not in operation:
                # Formal Prepare is idempotent by the original request ID and
                # immutable body. Replay only that exact durable request after
                # authoritative absence, never after an unknown read or bind.
                self._prepare(context, operation)
                return
            if status != 200 or 'error' in raw:
                # The original Prepare may have committed before a lost reply.
                # No by-name adoption, replacement key or blind resubmission.
                self._wait(context, operation, 'REGION_UNKNOWN')
                return
            operation = self._record(context, operation, raw)
            if raw.get('error_code'):
                self._wait(context, operation)
                return
            if raw['finalized']:
                if not operation['snapshot_uid']:
                    self._wait(context, operation)
                    return
                manifest = self.journal.read_manifest(context, operation['snapshot_uid'], operation['document_hash'])
                evidence = terminal_evidence(context, operation, manifest, raw)
                if evidence is not None:
                    operation = self.journal.record_region_terminal(
                        context, operation_id, self.owner, operation['execution_epoch'], operation['revision'], evidence,
                        self.clock())
                    self.journal.release(context, operation_id, self.owner, operation['execution_epoch'], operation['revision'],
                                         self.clock())
                else:
                    self._wait(context, operation)
                return
            if not raw['fence_owned'] or raw['fence_cleared']:
                self._wait(context, operation)
                return
            body = dict(operation_id=operation_id, core_hash=raw['core_hash'], request_id=operation_id)
            if raw['ready_to_use']:
                store = SnapshotManifestService(self.journal)
                if not operation['snapshot_uid']:
                    store.commit(context, source_context(operation, raw), operation_id, self.owner,
                                 operation['execution_epoch'], operation['revision'], raw, self.clock())
                    operation = self.journal.read_operation(context, operation_id)
                body = store.ready_request(context, operation_id, self.owner, operation['execution_epoch'],
                                           operation['revision'], raw, self.clock())
                action = ready_action(operation, raw)
                if action is None:
                    self._wait(context, operation)
                    return
            elif raw.get('snapshot_uid'):
                self._wait(context, operation)
                return
            elif raw['source_stopped']:
                action = 'create'
            else:
                action = 'halt'
            # All body values come from original immutable request/issued core
            # or the re-read committed manifest; no local lease enters Go.
            operation = self.journal.mark_region_issued(context, source_context(operation, raw), operation_id, self.owner,
                                                        operation['execution_epoch'], operation['revision'], raw['core_hash'],
                                                        self.clock())
            scope = self._scope(context)
            response, payload = self.client.command_vm_snapshot(*scope, operation['request']['name'], action, body)
            status, result = self._envelope(response, payload)
            if status != 202 or 'error' in result:
                self._wait(context, operation, 'CONFLICT' if status in (400, 403, 404, 422) else 'REGION_UNKNOWN')
                return
            operation = self._record(context, operation, result)
            self._wait(context, operation)
        except SnapshotProofPending:
            operation = self.journal.read_operation(context, operation_id)
            self._wait(context, operation)
        except JournalConflict:
            # Expired/stolen leases cannot even save this refusal.
            operation = self.journal.read_operation(context, operation_id)
            self._wait(context, operation, 'CONFLICT')
        except Exception:
            operation = self.journal.read_operation(context, operation_id)
            self._wait(context, operation, 'REGION_UNKNOWN')
