"""Consume the frozen snapshot readback25b191 contract, with no Go epoch."""
from console.services.vm_restore_journal import (HASH, SnapshotTerminalEvidence, ServerGoContext, identifier, integer, require,
                                                 validate_manifest)


class SnapshotProofPending(Exception):
    pass


def source_context(operation, raw):
    require(isinstance(raw, dict))
    request = operation['request']
    require(
        raw.get('operation_id') == operation['operation_id'] == operation['request_id']
        and raw.get('snapshot_name') == request['name'] and raw.get('description') == request['description']
        and raw.get('power_after') == request['power_after'])
    for key in ('core_hash', ):
        require(type(raw.get(key)) is str and HASH.fullmatch(raw[key]) is not None)
    identifier(raw.get('source_vm_uid'))
    required = ('namespace', 'source_vm_name', 'manifest_id', 'fence_owned', 'fence_cleared')
    if any(key not in raw for key in required):
        raise SnapshotProofPending()
    for key in ('namespace', 'source_vm_name', 'manifest_id'):
        identifier(raw[key])
    require(raw['manifest_id'] == operation['operation_id'])
    for key in ('fence_owned', 'fence_cleared', 'was_running', 'source_stopped', 'source_running', 'source_lock_clear',
                'ready_to_use', 'manifest_acked', 'finalized', 'cancelled', 'deleted'):
        require(type(raw.get(key)) is bool)
    require(not (raw['source_stopped'] and raw['source_running']) and not (raw['fence_owned'] and raw['fence_cleared']))
    intent = operation['region_intent']
    require(intent is not None)
    for key, actual in (('core_hash', raw['core_hash']), ('namespace', raw['namespace']), ('source_vm_uid',
                                                                                           raw['source_vm_uid'])):
        require(not intent[key] or intent[key] == actual)
    previous = operation.get('observation')
    if previous:
        require(previous['core_hash'] == raw['core_hash'] and previous['source_vm_uid'] == raw['source_vm_uid'])
        for key in ('namespace', 'source_vm_name', 'manifest_id'):
            require(key not in previous or previous[key] == raw[key])
    return ServerGoContext(raw['namespace'], raw['source_vm_name'], raw['source_vm_uid'])


def observation(raw):
    result = {
        key: raw.get(key, '' if key in ('snapshot_uid', 'error_code') else None)
        for key in ('operation_id', 'snapshot_name', 'core_hash', 'source_vm_uid', 'snapshot_uid', 'phase', 'ready_to_use',
                    'manifest_acked', 'finalized', 'error_code')
    }
    for key in ('namespace', 'source_vm_name', 'manifest_id', 'manifest_document_hash', 'finalized_control_revision',
                'fence_owned', 'fence_cleared'):
        if key in raw:
            result[key] = raw[key]
    return result


def terminal_evidence(context, operation, manifest, raw):
    source_context(operation, raw)
    validate_manifest(manifest, operation['scope'])
    if not raw['finalized']:
        return None
    if any(key not in raw for key in ('finalized_control_revision', 'manifest_document_hash')):
        raise SnapshotProofPending()
    integer(raw['finalized_control_revision'], 1, 2**64 - 1)
    require(raw['manifest_acked'] and raw['manifest_id'] == operation['operation_id']
            and raw['manifest_document_hash'] == manifest['document_hash'])
    require(raw['namespace'] == manifest['namespace'] and raw['source_vm_name'] == manifest['source_vm']['name']
            and raw['source_vm_uid'] == manifest['source_vm']['uid'] and not raw['cancelled']
            and not raw['deleted'] and not raw.get('error_code'))
    for key in ('snapshot_name', 'snapshot_uid', 'content_name', 'content_uid', 'core_hash', 'native_proof_hash', 'consistency',
                'config', 'disks'):
        require(raw.get(key) == manifest[key])
    require(raw['was_running'] == manifest['startup']['was_running']
            and raw['power_after'] == manifest['startup']['power_after'])
    # Finalize proved this operation's desired power/unlock at its saved
    # revision. A later operation may change today's power or native lock.
    if raw['fence_owned']:
        raise SnapshotProofPending()
    return SnapshotTerminalEvidence(context.identity[1], context.identity[2], context.identity[3], raw['namespace'],
                                    operation['operation_id'], raw['core_hash'], operation['execution_epoch'], True, True,
                                    'runtime_verified', 'snapshot_operation_history', raw['finalized_control_revision'], False,
                                    raw['fence_cleared'])
