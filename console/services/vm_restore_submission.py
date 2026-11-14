"""Authorized immutable restore submission; no RPC or current-B/A guessing."""
import hashlib

from console.services.vm_restore_journal import (HASH, TrustedContext, VMRestoreJournal, canonical, fields, identifier, require)


class RestoreSubmissionService:
    def __init__(self, journal=None):
        self.journal = journal or VMRestoreJournal()

    def submit(self, context, selection):
        require(type(context) is TrustedContext)
        fields(selection, ('request_id', 'snapshot_uid', 'document_hash', 'power_after'))
        identifier(selection['request_id'])
        identifier(selection['snapshot_uid'])
        require(type(selection['document_hash']) is str and HASH.fullmatch(selection['document_hash']) is not None)
        require(selection['power_after'] in ('previous', 'stopped'))
        manifest = self.journal.read_manifest(context, selection['snapshot_uid'], selection['document_hash'])
        identity = dict(tenant_id=context.identity[1],
                        service_id=context.identity[2],
                        region=context.identity[3],
                        request_id=selection['request_id'])
        operation_id = 'restore-' + hashlib.sha256(canonical(identity)).hexdigest()[:32]
        return self.journal.create_operation(context,
                                             operation_id,
                                             selection['request_id'],
                                             'restore',
                                             snapshot_uid=selection['snapshot_uid'],
                                             document_hash=selection['document_hash'],
                                             request=dict(name=manifest['snapshot_name'],
                                                          description='',
                                                          power_after=selection['power_after']))


restore_submission_service = RestoreSubmissionService()
