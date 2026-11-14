"""Scoped durable snapshot submission. The HTTP thread never calls Region."""
import re

from django.db import connections

from console.services.vm_restore_journal import (TrustedContext, VMRestoreJournal, fields, require, snapshot_request)
from www.models.main import TenantServiceInfo


class SnapshotJobService:
    def __init__(self, journal=None):
        self.journal = journal or VMRestoreJournal()

    def submit(self, context, selection, operator):
        require(type(context) is TrustedContext and not connections[context.identity[4]].in_atomic_block)
        fields(selection, ('request_id', 'name', 'description', 'power_after'))
        request_id = selection['request_id']
        require(type(request_id) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', request_id) is not None)
        require(
            type(operator) is str and bool(operator) and operator.strip() == operator
            and operator.casefold() not in ('none', 'anonymous', 'anonymoususer', 'system'))
        request = {key: selection[key] for key in ('name', 'description', 'power_after')}
        request['operator'] = operator
        snapshot_request(request)
        try:
            require(len(request['description'].encode('utf-8')) <= 2048)
        except UnicodeError:
            require(False)
        with self.journal._locked(context):
            live = TenantServiceInfo.objects.using(context.identity[4]).get(pk=context.identity[0])
            require(live.extend_method == 'vm')
            self.journal.create_operation(context, request_id, request_id, 'snapshot', request=request)
        accepted = self.status(context, request_id)
        accepted['complete'] = False
        return accepted

    def status(self, context, request_id):
        operation = self.journal.read_operation(context, request_id)
        require(operation['kind'] == 'snapshot' and operation['request_id'] == request_id)
        public = self.journal.public_operation(context, request_id)
        public.update(request_id=operation['request_id'],
                      complete=operation['phase'] == 'runtime_verified' and operation['region_terminal'] is not None)
        observation = operation.get('observation', {})
        # Keep this job's historical finalize distinct from current scope fences.
        for key in ('fence_owned', 'fence_cleared'):
            if key in observation:
                public[key] = observation[key]
        return public


snapshot_job_service = SnapshotJobService()
