# -*- coding: utf-8 -*-
"""Private durable VM journal. No HTTP, Region calls, worker or binding authority.

Callers must obtain TrustedContext from the authorized live Console service and
ServerGoContext from server-side Region preflight. Neither is a request DTO.
Every transaction locks the live service before attributes, matching public
attribute overwrite. The idle pointer and counters are retained as loss markers.
"""
import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime

from django.db import transaction

from console.models.main import ComponentK8sAttributes
from console.utils.vm_restore_attributes import GO_WHITESPACE, VM_RESTORE_ACTIVE_OPERATION
from www.models.main import TenantServiceInfo

MAX_RECORD_BYTES = 32768
MAX_HISTORY_RECORDS = 256
MANIFEST_PREFIX = 'vm_restore_manifest_'
OPERATION_PREFIX = 'vm_restore_operation_'
PHASES = {
    'pending', 'prepared', 'region_committed', 'console_committed', 'runtime_verified', 'rollback_pending', 'rolled_back',
    'failed', 'cancelled'
}
TERMINAL = {'runtime_verified', 'rolled_back', 'cancelled'}
ID = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,127}$')
HASH = re.compile(r'^[0-9a-f]{64}$')
RESTORE_RPC_ERRORS = {
    'vm_restore_outcome_unknown', 'vm_restore_pending', 'vm_restore_conflict', 'vm_restore_forbidden', 'vm_restore_not_found',
    'vm_restore_invalid_request', 'vm_restore_provider_not_qualified', 'vm_restore_capacity_insufficient',
    'vm_restore_dependency_unavailable', 'vm_restore_internal_error'
}


class JournalConflict(Exception):
    """Fixed diagnostic; never includes persisted or caller-supplied content."""
    def __init__(self):
        super().__init__('VM journal conflict')


def require(condition):
    if not condition:
        raise JournalConflict()


def identifier(value):
    require(isinstance(value, str) and ID.fullmatch(value) is not None)


def integer(value, minimum=0, maximum=2**63 - 1):
    require(type(value) is int and minimum <= value <= maximum)


def fields(value, required, optional=()):
    require(type(value) is dict and set(required) <= set(value) <= set(required) | set(optional))


def canonical(value):
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise JournalConflict() from None
    require(len(encoded) <= MAX_RECORD_BYTES)
    return encoded


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def reject_constant(_value):
    raise JournalConflict()


def object_ref(value, kind, namespace):
    fields(value, ('kind', 'namespace', 'name', 'uid'))
    require(value['kind'] == kind and value['namespace'] == namespace)
    identifier(value['name'])
    identifier(value['uid'])


def snapshot_request(value):
    fields(value, ('name', 'description', 'power_after'), ('operator', ))
    require(type(value['name']) is str and 1 <= len(value['name']) <= 253)
    require(re.fullmatch(r'[a-z0-9](?:[-a-z0-9]*[a-z0-9])?(?:\.[a-z0-9](?:[-a-z0-9]*[a-z0-9])?)*', value['name']) is not None)
    require(type(value['description']) is str and len(value['description']) <= 2048)
    require(value['power_after'] in ('previous', 'stopped'))
    if 'operator' in value:
        require(type(value['operator']) is str)
        try:
            require(len(value['operator'].encode('utf-8')) <= 40)
        except UnicodeError:
            raise JournalConflict() from None


def observed_snapshot(value, operation_id):
    fields(value, ('operation_id', 'snapshot_name', 'core_hash', 'source_vm_uid', 'snapshot_uid', 'phase', 'ready_to_use',
                   'manifest_acked', 'finalized', 'error_code'),
           ('namespace', 'source_vm_name', 'manifest_id', 'manifest_document_hash', 'finalized_control_revision',
            'fence_owned', 'fence_cleared'))
    require(value['operation_id'] == operation_id)
    for key in ('snapshot_name', 'source_vm_uid'):
        require(type(value[key]) is str and 0 < len(value[key]) <= 253)
    require(type(value['core_hash']) is str and HASH.fullmatch(value['core_hash']) is not None)
    for key in ('snapshot_uid', 'phase', 'error_code'):
        require(type(value[key]) is str and len(value[key]) <= 128)
    require(re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', value['phase']) is not None)
    require(not value['error_code'] or re.fullmatch(r'vm_snapshot_[a-z_]{1,96}', value['error_code']) is not None)
    for key in ('ready_to_use', 'manifest_acked', 'finalized'):
        require(type(value[key]) is bool)
    for key in ('namespace', 'source_vm_name', 'manifest_id'):
        if key in value:
            identifier(value[key])
    if 'manifest_document_hash' in value:
        require(type(value['manifest_document_hash']) is str
                and (not value['manifest_document_hash'] or HASH.fullmatch(value['manifest_document_hash']) is not None))
    if 'finalized_control_revision' in value:
        integer(value['finalized_control_revision'], maximum=2**64 - 1)
    for key in ('fence_owned', 'fence_cleared'):
        if key in value:
            require(type(value[key]) is bool)


def restore_observation(value, operation_id):
    """Project actual RPC facts; never infer execution from a phase or HTTP 202."""
    require(isinstance(value, dict))
    strings = ('operation_id', 'operation_epoch', 'target_vm_uid', 'phase', 'snapshot_uid')
    counters = ('control_revision', 'binding_generation', 'operation_binding_generation')
    booleans = ('fence_owned', 'fence_cleared', 'applied', 'complete', 'config_committed', 'console_acked', 'rollback_acked',
                'retryable')
    result = {key: value.get(key) for key in strings + counters + booleans}
    result.update({
        key: value.get(key, '')
        for key in ('resource_frame_hash', 'outcome', 'config_commit_hash', 'rollback_config_hash', 'error_code')
    })
    require(result['operation_id'] == operation_id)
    for key in ('operation_epoch', ):
        require(type(result[key]) is str and HASH.fullmatch(result[key]) is not None)
    for key in ('target_vm_uid', 'snapshot_uid'):
        identifier(result[key])
    require(type(result['phase']) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', result['phase']) is not None)
    for key in counters:
        integer(result[key], maximum=2**64 - 1)
    for key in booleans:
        require(type(result[key]) is bool)
    for key in ('resource_frame_hash', 'config_commit_hash', 'rollback_config_hash'):
        require(type(result[key]) is str and (not result[key] or HASH.fullmatch(result[key]) is not None))
    require(type(result['error_code']) is str and (result['error_code'] == '' or result['error_code'] in RESTORE_RPC_ERRORS))
    require(result['outcome'] in ('', 'restored', 'rolled-back', 'cancelled'))
    if result['complete']:
        require(result['fence_cleared'] and not result['fence_owned'] and bool(result['outcome']))
    else:
        require(not result['fence_cleared'] and result['outcome'] == '')
    source = value.get('source')
    require(isinstance(source, dict))
    result['source'] = {
        key: source.get(key)
        for key in ('snapshot_name', 'snapshot_uid', 'content_uid', 'vm_uid', 'core_hash', 'document_hash')
    }
    for key in ('snapshot_name', 'snapshot_uid', 'content_uid', 'vm_uid'):
        identifier(result['source'][key])
    for key in ('core_hash', 'document_hash'):
        require(type(result['source'][key]) is str and HASH.fullmatch(result['source'][key]) is not None)
    require(result['snapshot_uid'] == result['source']['snapshot_uid'])
    for key in ('source_config_ready', 'was_running', 'resume_required'):
        require(type(value.get(key)) is bool)
        result[key] = value[key]
    require(value.get('power_after') in ('previous', 'stopped'))
    result['power_after'] = value['power_after']
    require(result['resume_required'] == (result['was_running'] and result['power_after'] == 'previous'))
    integer(value.get('source_binding_generation'), maximum=2**64 - 1)
    result['source_binding_generation'] = value['source_binding_generation']
    require(result['binding_generation'] >= result['source_binding_generation']
            and result['operation_binding_generation'] >= result['source_binding_generation']
            and result['operation_binding_generation'] <= result['binding_generation'])
    for key in ('config_after_hash', 'config_before_hash'):
        require(type(value.get(key)) is str and HASH.fullmatch(value[key]) is not None)
        result[key] = value[key]
    from console.exception.main import ServiceHandleException
    from console.utils.vm_restore_config import canonical_restore_config, restore_config_hash
    try:
        before = canonical_restore_config(value.get('config_before'))
        require(restore_config_hash(before) == result['config_before_hash'])
        result['config_before'] = before
        if result['source_config_ready']:
            after = canonical_restore_config(value.get('config_after'))
            require(restore_config_hash(after) == result['config_after_hash'])
            result['config_after'] = after
        else:
            require(value.get('config_after') is None)
    except (ServiceHandleException, ValueError, TypeError, KeyError):
        raise JournalConflict() from None
    return json.loads(canonical(result))


def bind_restore_source_config(observed, manifest):
    """Bind received A to the immutable local A, not to its self-reported hash."""
    if not observed['source_config_ready']:
        return
    from console.utils.vm_restore_config import restore_config_hash
    hardware = json.loads(canonical(manifest['config']))
    hardware['disk_layout'].sort(key=lambda disk: disk['volume_id'])
    after = observed['config_after']
    require(after['hardware'] == hardware)
    volumes = {disk['volume_id']: disk for disk in after['volumes']}
    require(len(volumes) == len(after['volumes']) and set(volumes) == {disk['volume_id'] for disk in hardware['disk_layout']})
    for disk in manifest['disks']:
        actual = volumes[disk['volume_id']]
        require(actual['disk_key'] == disk['disk_key'] and actual['storage_class'] == disk['storage_class']
                and actual['read_only'] == disk['read_only']
                and actual['capacity_gib'] == (disk['requested_bytes'] + 1073741823) // 1073741824)
    # Legacy manifests do not assert an access mode. It remains server-sealed,
    # never inferred from B/defaults; all locally sealed fields above must match.
    require(restore_config_hash({'hardware': hardware, 'volumes': after['volumes']}) == observed['config_after_hash'])


def restore_rpc_state(value, op):
    fields(value, ('schema_version', 'power_after', 'server_epoch', 'target_vm_uid', 'source', 'pending', 'completed',
                   'commands', 'observation'))
    require(value['schema_version'] == 1 and type(value['schema_version']) is int)
    require(value['power_after'] in ('previous', 'stopped'))
    require(value['completed'] in ([], ['prepare'], ['prepare', 'halt'], ['prepare', 'halt', 'config-ack']))
    require(type(value['commands']) is list and len(value['commands']) == len(value['completed']))
    for index, command in enumerate(value['commands']):
        fields(command, ('action', 'request', 'attempts', 'server_epoch', 'control_revision'))
        require(command['action'] == value['completed'][index] and command['server_epoch'] == value['server_epoch'])
        integer(command['attempts'], 1)
        integer(command['control_revision'], maximum=2**64 - 1)
        require(type(command['request']) is dict)
        from console.utils.vm_restore_rpc import command_body
        from console.exception.main import ServiceHandleException
        try:
            command_body(command['action'], command['request'])
        except ServiceHandleException:
            raise JournalConflict() from None
        require(command['request'].get('expected_operation_epoch', '') in ('', value['server_epoch']))
        require(command['control_revision'] >= command['request']['expected_control_revision'])
        if value['observation'] is not None:
            require(value['observation']['control_revision'] >= command['control_revision']
                    and value['observation']['binding_generation'] >= command['request']['expected_binding_generation'])

    require(type(value['server_epoch']) is str and (not value['server_epoch'] or HASH.fullmatch(value['server_epoch'])))
    require(type(value['target_vm_uid']) is str)
    if value['observation'] is None:
        require(value['source'] is None and value['server_epoch'] == value['target_vm_uid'] == '')
    else:
        observed = restore_observation(value['observation'], op['operation_id'])
        require(observed['source'] == value['source'] and observed['operation_epoch'] == value['server_epoch']
                and observed['target_vm_uid'] == value['target_vm_uid'])
    pending = value['pending']
    if pending is None:
        require(bool(value['completed']))
        return
    fields(pending, ('action', 'request', 'state', 'attempts', 'http_status', 'error_code'))
    require(len(value['completed']) < 3 and pending['action'] == ('prepare', 'halt', 'config-ack')[len(value['completed'])])
    require(pending['state'] in ('planned', 'issued', 'unknown', 'pending', 'conflict', 'rejected'))
    integer(pending['attempts'])
    integer(pending['http_status'], maximum=599)
    require(type(pending['error_code']) is str and (pending['error_code'] == '' or pending['error_code'] in RESTORE_RPC_ERRORS))
    if pending['request'] is None:
        require(pending['attempts'] == 0)
    else:
        from console.utils.vm_restore_rpc import command_body
        from console.exception.main import ServiceHandleException
        try:
            command_body(pending['action'], pending['request'])
        except ServiceHandleException:
            raise JournalConflict() from None
        require(pending['attempts'] > 0)
        epoch = pending['request'].get('expected_operation_epoch', '')
        require(not epoch or epoch == value['server_epoch'])
        if value['observation'] is not None:
            require(value['observation']['control_revision'] >= pending['request']['expected_control_revision']
                    and value['observation']['binding_generation'] >= pending['request']['expected_binding_generation'])


def selected_config(value):
    fields(value, ('cpu_milli', 'memory_mib', 'boot_mode', 'disk_layout'))
    integer(value['cpu_milli'], 1, 1048576000)
    integer(value['memory_mib'], 1, 2**40)
    require(value['boot_mode'] in ('bios', 'uefi'))
    layout = value['disk_layout']
    require(type(layout) is list and 1 <= len(layout) <= 16)
    ids, keys, names, boots = set(), set(), set(), set()
    for disk in layout:
        fields(disk, ('volume_id', 'disk_key', 'canonical_name', 'role', 'device', 'bus', 'boot_order', 'read_only'))
        integer(disk['volume_id'], 1)
        identifier(disk['disk_key'])
        identifier(disk['canonical_name'])
        require(disk['canonical_name'] == 'manual' + str(disk['volume_id']))
        require(disk['role'] in ('root', 'data') and disk['device'] in ('disk', 'lun', 'cdrom'))
        require(disk['bus'] in ('virtio', 'sata', 'scsi') and type(disk['read_only']) is bool)
        integer(disk['boot_order'], 0, 65535)
        require(disk['volume_id'] not in ids and disk['disk_key'] not in keys and disk['canonical_name'] not in names)
        if disk['boot_order']:
            require(disk['boot_order'] not in boots)
            boots.add(disk['boot_order'])
        ids.add(disk['volume_id'])
        keys.add(disk['disk_key'])
        names.add(disk['canonical_name'])
    require(sum(disk['role'] == 'root' and not disk['read_only'] for disk in layout) == 1)


def validate_manifest(value, scope):
    fields(value,
           ('schema_version', 'scope', 'namespace', 'source_vm', 'snapshot_name', 'snapshot_uid', 'content_name', 'content_uid',
            'core_hash', 'native_proof_hash', 'creation_time', 'consistency', 'config', 'disks', 'document_hash'),
           ('startup', ))
    require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['scope'] == scope)
    identifier(value['namespace'])
    object_ref(value['source_vm'], 'VirtualMachine', value['namespace'])
    for key in ('snapshot_name', 'snapshot_uid', 'content_name', 'content_uid'):
        identifier(value[key])
    for key in ('core_hash', 'native_proof_hash', 'document_hash'):
        require(isinstance(value[key], str) and HASH.fullmatch(value[key]) is not None)
    require(value['consistency'] == 'offline')
    try:
        datetime.strptime(value['creation_time'], '%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, TypeError):
        raise JournalConflict() from None
    selected_config(value['config'])
    disks = value['disks']
    require(type(disks) is list and 1 <= len(disks) <= 16)
    identities, pvc_uids, vs_uids = set(), set(), set()
    layout = {disk['volume_id']: disk for disk in value['config']['disk_layout'] if not disk['read_only']}
    for disk in disks:
        fields(disk, ('volume_id', 'disk_key', 'canonical_name', 'role', 'source_pvc', 'read_only', 'storage_class',
                      'requested_bytes', 'volume_snapshot'), ('source_dv', ))
        integer(disk['volume_id'], 1)
        require(disk['volume_id'] not in identities and disk['volume_id'] in layout and disk['read_only'] is False)
        for key in ('disk_key', 'canonical_name', 'role'):
            require(disk[key] == layout[disk['volume_id']][key])
        object_ref(disk['source_pvc'], 'PersistentVolumeClaim', value['namespace'])
        object_ref(disk['volume_snapshot'], 'VolumeSnapshot', value['namespace'])
        if 'source_dv' in disk:
            object_ref(disk['source_dv'], 'DataVolume', value['namespace'])
        require(disk['source_pvc']['uid'] not in pvc_uids and disk['volume_snapshot']['uid'] not in vs_uids)
        pvc_uids.add(disk['source_pvc']['uid'])
        vs_uids.add(disk['volume_snapshot']['uid'])
        identifier(disk['storage_class'])
        integer(disk['requested_bytes'], 1)
        identities.add(disk['volume_id'])
    require(identities == set(layout))
    if 'startup' in value:
        fields(value['startup'], ('was_running', 'power_after'))
        require(type(value['startup']['was_running']) is bool and value['startup']['power_after'] in ('stopped', 'previous'))
    material = dict(value)
    material.pop('document_hash')
    require(digest(material) == value['document_hash'])


@dataclass(frozen=True)
class TrustedContext:
    service: TenantServiceInfo = field(repr=False)
    identity: tuple = field(init=False, repr=False)

    def __post_init__(self):
        service = self.service
        require(isinstance(service, TenantServiceInfo) and service.pk is not None and not service._state.adding)
        object.__setattr__(self, 'identity',
                           (service.pk, service.tenant_id, service.service_id, service.service_region, service._state.db))


@dataclass(frozen=True)
class ServerGoContext:
    namespace: str
    source_vm_name: str
    source_vm_uid: str


@dataclass(frozen=True)
class RegionTerminalEvidence:
    """Safe projection of a server-observed authoritative Region terminal receipt.

    The future adapter must construct this from a Region response, never an HTTP
    body. Accepted/unknown receipts are not terminal evidence.
    """
    tenant_id: str
    service_id: str
    region: str
    namespace: str
    operation_id: str
    core_hash: str
    execution_epoch: int
    finalized: bool
    fence_released: bool
    outcome: str


@dataclass(frozen=True)
class SnapshotTerminalEvidence(RegionTerminalEvidence):
    """This snapshot's historical fence release; current scope flags stay separate."""
    proof_kind: str
    finalized_control_revision: int
    fence_owned: bool
    fence_cleared: bool


class VMRestoreJournal:
    @contextmanager
    def _locked(self, context):
        require(type(context) is TrustedContext)
        pk, tenant_id, service_id, region, alias = context.identity
        require(alias == ComponentK8sAttributes.objects.db == TenantServiceInfo.objects.db)
        with transaction.atomic(using=alias):
            services = list(TenantServiceInfo.objects.select_for_update().filter(service_id=service_id))
            require(len(services) == 1)
            live = services[0]
            require((live.pk, live.tenant_id, live.service_region) == (pk, tenant_id, region))
            scope = dict(tenant_id=live.tenant_id, service_id=live.service_id, region=live.service_region)
            rows = list(ComponentK8sAttributes.objects.select_for_update().filter(component_id=live.service_id).order_by('pk'))
            records, attributes = {}, {}
            for row in rows:
                require(row.tenant_id == live.tenant_id)
                normalized = row.name.strip(GO_WHITESPACE).replace('\u0130', 'i').lower()
                if normalized != VM_RESTORE_ACTIVE_OPERATION and not normalized.startswith((MANIFEST_PREFIX, OPERATION_PREFIX)):
                    continue
                require(row.name == normalized and row.name not in records and row.save_type == 'json')
                try:
                    require(len(row.attribute_value.encode('utf-8')) <= MAX_RECORD_BYTES)
                    value = json.loads(row.attribute_value, object_pairs_hook=strict_pairs, parse_constant=reject_constant)
                except (ValueError, TypeError, UnicodeError, RecursionError):
                    raise JournalConflict() from None
                require(type(value) is dict)
                records[row.name], attributes[row.name] = value, row
            require(len(records) <= MAX_HISTORY_RECORDS)
            self._validate_ledger(records, scope)
            yield scope, records, attributes

    @staticmethod
    def _validate_ledger(records, scope):
        if not records:
            return
        require(VM_RESTORE_ACTIVE_OPERATION in records)
        pointer = records[VM_RESTORE_ACTIVE_OPERATION]
        fields(
            pointer,
            ('schema_version', 'scope', 'operation_id', 'last_operation_id', 'revision', 'operation_count', 'manifest_count'))
        require(type(pointer['schema_version']) is int and pointer['schema_version'] == 1 and pointer['scope'] == scope)
        integer(pointer['revision'], 1)
        integer(pointer['operation_count'], 1)
        integer(pointer['manifest_count'])
        operations, manifests = {}, {}
        for name, record in records.items():
            if name.startswith(MANIFEST_PREFIX):
                validate_manifest(record, scope)
                require(name == MANIFEST_PREFIX + record['snapshot_uid'])
                manifests[record['snapshot_uid']] = record
            elif name.startswith(OPERATION_PREFIX):
                fields(record, ('schema_version', 'scope', 'operation_id', 'request_id', 'kind', 'phase', 'revision',
                                'lease_owner', 'lease_until', 'execution_epoch', 'retry_count', 'retry_at', 'error_code',
                                'snapshot_uid', 'document_hash', 'rollback_config', 'region_intent', 'region_terminal'),
                       ('request', 'observation', 'rpc', 'console_commit'))
                require(type(record['schema_version']) is int and record['schema_version'] == 1 and record['scope'] == scope)
                for key in ('operation_id', 'request_id'):
                    identifier(record[key])
                require(name == OPERATION_PREFIX + record['operation_id'])
                require(
                    type(record['phase']) is str and record['kind'] in ('snapshot', 'restore') and record['phase'] in PHASES)
                require(type(record['snapshot_uid']) is str and type(record['document_hash']) is str)
                for key in ('revision', 'lease_until', 'execution_epoch', 'retry_count', 'retry_at'):
                    integer(record[key], 1 if key == 'revision' else 0)
                require(type(record['lease_owner']) is str)
                if record['lease_owner']:
                    identifier(record['lease_owner'])
                require(bool(record['lease_owner']) == bool(record['execution_epoch']) == bool(record['lease_until']))
                require(record['error_code'] in ('', 'REGION_UNKNOWN', 'DEPENDENCY_PENDING', 'CONFLICT', 'RETRY_EXHAUSTED'))
                if record['kind'] == 'restore':
                    if record['rollback_config'] is None:
                        require('request' in record and isinstance(record.get('rpc'), dict)
                                and record['rpc'].get('observation') is None)
                    else:
                        selected_config(record['rollback_config'])
                    require(bool(record['snapshot_uid']) and bool(record['document_hash']))
                else:
                    require(record['rollback_config'] is None)
                if 'request' in record:
                    require(record['kind'] == 'snapshot' or 'operator' not in record['request'])
                    snapshot_request(record['request'])
                if 'observation' in record:
                    observed_snapshot(record['observation'], record['operation_id'])
                if 'rpc' in record:
                    require(record['kind'] == 'restore')
                    restore_rpc_state(record['rpc'], record)
                operations[record['operation_id']] = record
            else:
                require(name == VM_RESTORE_ACTIVE_OPERATION)
        require(len(operations) == pointer['operation_count'] and len(manifests) == pointer['manifest_count'])
        referenced = set()
        for op in operations.values():
            VMRestoreJournal._validate_region(op, scope)
            if 'console_commit' in op:
                from console.services.vm_restore_config_commit import validate_commit_document
                validate_commit_document(op['console_commit'], op, scope)
            if op['snapshot_uid'] or op['document_hash']:
                identifier(op['snapshot_uid'])
                manifest = manifests.get(op['snapshot_uid'])
                require(manifest is not None and op['document_hash'] == manifest['document_hash'])
                if op['kind'] == 'restore' and 'request' in op:
                    require(op['request']['name'] == manifest['snapshot_name'] and op['request']['description'] == ''
                            and op['request']['power_after'] == op['rpc']['power_after'])
                referenced.add(op['snapshot_uid'])
                if op['region_intent'] is not None:
                    require(op['region_intent']['core_hash'] == manifest['core_hash']
                            and op['region_intent']['namespace'] == manifest['namespace'])
                if 'rpc' in op:
                    rpc = op['rpc']
                    if rpc['observation'] is not None:
                        bind_restore_source_config(rpc['observation'], manifest)
                    if rpc['source'] is not None:
                        require(rpc['source'] == dict(snapshot_name=manifest['snapshot_name'],
                                                      snapshot_uid=manifest['snapshot_uid'],
                                                      content_uid=manifest['content_uid'],
                                                      vm_uid=manifest['source_vm']['uid'],
                                                      core_hash=manifest['core_hash'],
                                                      document_hash=manifest['document_hash']))
                    if rpc['pending'] and rpc['pending']['action'] == 'prepare' and rpc['pending']['request']:
                        require(rpc['pending']['request']['snapshot_name'] == manifest['snapshot_name']
                                and rpc['pending']['request']['power_after'] == rpc['power_after'])
                    for command in rpc['commands']:
                        if command['action'] == 'prepare':
                            require(command['request']['snapshot_name'] == manifest['snapshot_name']
                                    and command['request']['power_after'] == rpc['power_after'])
            if op['operation_id'] != pointer['operation_id']:
                require(op['phase'] in TERMINAL)
                require(op['region_terminal'] is not None if op['region_intent'] is not None else op['phase'] == 'cancelled')
        require(referenced == set(manifests))
        require(type(pointer['operation_id']) is str and type(pointer['last_operation_id']) is str)
        if pointer['operation_id']:
            require(pointer['operation_id'] in operations)
        else:
            require(pointer['last_operation_id'] in operations
                    and operations[pointer['last_operation_id']]['phase'] in TERMINAL)
        if pointer['last_operation_id']:
            require(pointer['last_operation_id'] in operations)

    @staticmethod
    def _write(scope, records, attributes, name, value):
        encoded = canonical(value).decode('utf-8')
        if name in attributes:
            row = attributes[name]
            row.attribute_value = encoded
            row.save(update_fields=['attribute_value'])
        else:
            require(len(records) < MAX_HISTORY_RECORDS)
            attributes[name] = ComponentK8sAttributes.objects.create(tenant_id=scope['tenant_id'],
                                                                     component_id=scope['service_id'],
                                                                     name=name,
                                                                     save_type='json',
                                                                     attribute_value=encoded)
        records[name] = value

    @staticmethod
    def _operation(records, operation_id):
        identifier(operation_id)
        require(OPERATION_PREFIX + operation_id in records)
        return records[OPERATION_PREFIX + operation_id]

    @classmethod
    def _owned(cls, records, operation_id, owner, epoch, revision, now):
        integer(now)
        integer(epoch, 1)
        integer(revision, 1)
        identifier(owner)
        op = cls._operation(records, operation_id)
        require(records[VM_RESTORE_ACTIVE_OPERATION]['operation_id'] == operation_id and op['lease_owner'] == owner
                and op['execution_epoch'] == epoch and op['revision'] == revision and op['lease_until'] > now)
        return op

    def create_operation(self,
                         context,
                         operation_id,
                         request_id,
                         kind,
                         snapshot_uid='',
                         document_hash='',
                         rollback_config=None,
                         request=None):
        identifier(operation_id)
        identifier(request_id)
        if request is not None:
            require(kind == 'snapshot' or 'operator' not in request)
            snapshot_request(request)
            request = json.loads(canonical(request))
        require(kind in ('snapshot', 'restore') and type(snapshot_uid) is str and type(document_hash) is str)
        with self._locked(context) as (scope, records, attrs):
            if kind == 'restore':
                if rollback_config is None:
                    require(request is not None)
                else:
                    selected_config(rollback_config)
                manifest = records.get(MANIFEST_PREFIX + snapshot_uid)
                require(manifest is not None and document_hash == manifest['document_hash'])
                if request is not None:
                    require(request['name'] == manifest['snapshot_name'] and request['description'] == '')
            else:
                require(snapshot_uid == document_hash == '' and rollback_config is None)
            old = records.get(OPERATION_PREFIX + operation_id)
            if old is not None:
                require((old['request_id'], old['kind']) == (request_id, kind))
                require(old['rollback_config'] == rollback_config
                        or (kind == 'restore' and request is not None and rollback_config is None))
                require(old.get('request') == request)
                if kind == 'restore':
                    require((old['snapshot_uid'], old['document_hash']) == (snapshot_uid, document_hash))
                return old
            require(not any(op.get('request_id') == request_id for op in records.values()))
            pointer = records.get(VM_RESTORE_ACTIVE_OPERATION)
            require(pointer is None or pointer['operation_id'] == '')
            op = dict(schema_version=1,
                      scope=scope,
                      operation_id=operation_id,
                      request_id=request_id,
                      kind=kind,
                      phase='pending',
                      revision=1,
                      lease_owner='',
                      lease_until=0,
                      execution_epoch=0,
                      retry_count=0,
                      retry_at=0,
                      error_code='',
                      snapshot_uid=snapshot_uid,
                      document_hash=document_hash,
                      rollback_config=rollback_config,
                      region_intent=None,
                      region_terminal=None)
            if request is not None:
                op['request'] = request
                if kind == 'restore':
                    op['rpc'] = self._new_restore_rpc(request['power_after'])
            pointer = dict(pointer) if pointer else dict(
                schema_version=1, scope=scope, last_operation_id='', revision=0, operation_count=0, manifest_count=0)
            pointer.update(operation_id=operation_id,
                           revision=pointer['revision'] + 1,
                           operation_count=pointer['operation_count'] + 1)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            self._write(scope, records, attrs, VM_RESTORE_ACTIVE_OPERATION, pointer)
            return op

    def active_operation(self, context):
        with self._locked(context) as (_, records, _attrs):
            pointer = records.get(VM_RESTORE_ACTIVE_OPERATION)
            return pointer['operation_id'] if pointer else ''

    def read_operation(self, context, operation_id):
        with self._locked(context) as (_, records, _attrs):
            return self._operation(records, operation_id)

    def public_operation(self, context, operation_id):
        op = self.read_operation(context, operation_id)
        public = {
            key: op[key]
            for key in ('operation_id', 'kind', 'phase', 'revision', 'retry_count', 'retry_at', 'error_code')
        }
        if 'observation' in op:
            public['observation'] = {
                key: op['observation'][key]
                for key in ('snapshot_name', 'phase', 'ready_to_use', 'manifest_acked', 'finalized', 'error_code')
            }
        if 'rpc' in op:
            pending = op['rpc']['pending']
            public['command'] = ({
                key: pending[key]
                for key in ('action', 'state', 'attempts', 'http_status', 'error_code')
            } if pending else {
                'state': 'prepared' if len(op['rpc']['completed']) == 1 else 'awaiting_producer_steps'
            })
        return public

    @staticmethod
    def _planned_restore_command(action):
        return dict(action=action, request=None, state='planned', attempts=0, http_status=0, error_code='')

    @classmethod
    def _new_restore_rpc(cls, power_after):
        return dict(schema_version=1,
                    power_after=power_after,
                    server_epoch='',
                    target_vm_uid='',
                    source=None,
                    pending=cls._planned_restore_command('prepare'),
                    completed=[],
                    commands=[],
                    observation=None)

    def initialize_restore_commands(self, context, operation_id, owner, epoch, revision, power_after, now):
        require(power_after in ('previous', 'stopped') and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', operation_id))
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            require(op['kind'] == 'restore')
            if 'rpc' in op:
                require(op['rpc']['power_after'] == power_after)
                return op
            op['rpc'] = self._new_restore_rpc(power_after)
            op['revision'] += 1
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def plan_next_restore_command(self, context, operation_id, owner, epoch, revision, now):
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            rpc = op.get('rpc')
            require(rpc is not None)
            if rpc['pending'] is None and rpc['completed'] == ['prepare']:
                require(rpc['observation'] is not None and not rpc['observation']['complete']
                        and rpc['observation']['fence_owned'])
                rpc['pending'] = self._planned_restore_command('halt')
                op['revision'] += 1
                self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def issue_restore_command(self, context, operation_id, owner, epoch, revision, request, now):
        from console.utils.vm_restore_rpc import command_body
        from console.exception.main import ServiceHandleException
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            rpc = op.get('rpc')
            require(rpc is not None and rpc['pending'] is not None and rpc['pending']['state'] not in ('rejected', 'conflict'))
            pending = rpc['pending']
            try:
                detached = json.loads(command_body(pending['action'], request))
            except ServiceHandleException:
                raise JournalConflict() from None
            manifest = records[MANIFEST_PREFIX + op['snapshot_uid']]
            if pending['action'] == 'prepare':
                require(detached['snapshot_name'] == manifest['snapshot_name']
                        and detached['power_after'] == rpc['power_after'])
            elif pending['action'] == 'config-ack':
                from console.services.vm_restore_config_commit import RestoreConfigCommitter, validate_commit_document
                require('console_commit' in op)
                validate_commit_document(op['console_commit'], op, scope)
                RestoreConfigCommitter(self)._verify_fields(context, op['console_commit']['config'])
                require(detached['commit_hash'] == op['console_commit']['commit_hash']
                        and detached['document_hash'] == op['console_commit']['document_hash'])
                require(rpc['observation']['fence_owned'] and not rpc['observation']['complete']
                        and rpc['observation']['operation_binding_generation'] == detached['expected_binding_generation']
                        == rpc['observation']['binding_generation'])
            if pending['request'] is not None:
                require(detached == pending['request'])
                require(not detached.get('expected_operation_epoch')
                        or detached['expected_operation_epoch'] == rpc['server_epoch'])
            else:
                require(detached.get('expected_operation_epoch', '') == rpc['server_epoch'])
            op['region_intent'] = op['region_intent'] or dict(operation_id=operation_id,
                                                              core_hash=manifest['core_hash'],
                                                              namespace=manifest['namespace'],
                                                              source_vm_uid=manifest['source_vm']['uid'],
                                                              issued_epoch=epoch)
            pending.update(request=detached, state='issued', attempts=pending['attempts'] + 1, http_status=0, error_code='')
            op.update(revision=revision + 1, error_code='', retry_at=0)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def record_restore_command_error(self, context, operation_id, owner, epoch, revision, status, code, now):
        integer(status, maximum=599)
        require(code in RESTORE_RPC_ERRORS)
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            pending = op.get('rpc', {}).get('pending')
            require(pending is not None)
            state = 'conflict' if status == 409 else 'rejected' if status in (400, 403, 404, 422) else 'pending' if (
                status == 202 and code == 'vm_restore_pending') else 'unknown'
            pending.update(state=state, http_status=status, error_code=code)
            op.update(revision=revision + 1,
                      error_code='CONFLICT' if state == 'conflict' else 'REGION_UNKNOWN',
                      retry_count=op['retry_count'] + 1,
                      retry_at=now + 30)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def plan_restore_ack(self, context, operation_id, owner, epoch, revision, now):
        from console.services.vm_restore_config_commit import RestoreConfigCommitter
        document = RestoreConfigCommitter(self).read_committed(context, operation_id, owner, epoch, revision, now)
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            rpc = op['rpc']
            require(rpc['observation']['config_committed'] and rpc['observation']['fence_owned']
                    and not rpc['observation']['complete'] and op['console_commit'] == document)
            if rpc['pending'] is None:
                require(rpc['completed'] == ['prepare', 'halt'])
                rpc['pending'] = self._planned_restore_command('config-ack')
                op['revision'] += 1
                self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            else:
                require(rpc['pending']['action'] == 'config-ack')
            return op

    def retry_rejected_restore_command(self, context, operation_id, owner, epoch, revision, now):
        """Explicit caller retry; preserve the original task, arguments and seals."""
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            pending = op.get('rpc', {}).get('pending')
            require(pending is not None and pending['state'] == 'rejected')
            pending['state'] = 'unknown'
            op.update(revision=revision + 1, retry_at=0)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def record_restore_status(self, context, operation_id, owner, epoch, revision, value, now, command_applied=False):
        observed = restore_observation(value, operation_id)
        require(type(command_applied) is bool)
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            rpc = op.get('rpc')
            require(rpc is not None)
            manifest = records[MANIFEST_PREFIX + op['snapshot_uid']]
            expected = dict(snapshot_name=manifest['snapshot_name'],
                            snapshot_uid=manifest['snapshot_uid'],
                            content_uid=manifest['content_uid'],
                            vm_uid=manifest['source_vm']['uid'],
                            core_hash=manifest['core_hash'],
                            document_hash=manifest['document_hash'])
            require(observed['source'] == expected)
            bind_restore_source_config(observed, manifest)
            if op['rollback_config'] is None:
                selected_config(observed['config_before']['hardware'])
                op['rollback_config'] = json.loads(canonical(observed['config_before']['hardware']))
            require(not rpc['server_epoch'] or rpc['server_epoch'] == observed['operation_epoch'])
            require(not rpc['target_vm_uid'] or rpc['target_vm_uid'] == observed['target_vm_uid'])
            require(observed['power_after'] == rpc['power_after'])
            if rpc['observation'] is not None:
                for key in ('source_binding_generation', 'was_running', 'power_after', 'resume_required', 'source_config_ready',
                            'config_before_hash', 'config_after_hash'):
                    require(rpc['observation'][key] == observed[key])
                for key in ('control_revision', 'binding_generation', 'operation_binding_generation'):
                    require(observed[key] >= rpc['observation'][key])
            pending = rpc['pending']
            if pending and pending['request']:
                require(observed['control_revision'] >= pending['request']['expected_control_revision']
                        and observed['binding_generation'] >= pending['request']['expected_binding_generation'])
            require(observed['complete'] or observed['fence_owned'])
            # Observing an existing Region receipt also closes the local-only
            # cancellation path, even if this Console process never sent POST.
            op['region_intent'] = op['region_intent'] or dict(operation_id=operation_id,
                                                              core_hash=manifest['core_hash'],
                                                              namespace=manifest['namespace'],
                                                              source_vm_uid=manifest['source_vm']['uid'],
                                                              issued_epoch=epoch)
            rpc.update(server_epoch=observed['operation_epoch'],
                       target_vm_uid=observed['target_vm_uid'],
                       source=observed['source'],
                       observation=observed)
            if 'console_commit' in op:
                # Reject a drifting receipt before it can poison the durable
                # journal that the next process must read to reconcile ACK.
                from console.services.vm_restore_config_commit import validate_commit_document
                validate_commit_document(op['console_commit'], op, scope)
            if command_applied:
                require(observed['applied'] and rpc['pending'] is not None and rpc['pending']['state'] == 'issued')
                if rpc['pending']['action'] == 'config-ack':
                    require(observed['console_acked'] and observed['config_committed'] and 'console_commit' in op)
                    require(not observed['error_code'] and not observed['retryable']
                            and observed['control_revision'] > rpc['pending']['request']['expected_control_revision']
                            and observed['operation_binding_generation'] == observed['binding_generation']
                            == rpc['pending']['request']['expected_binding_generation'])
                if not observed['complete']:
                    rpc['commands'].append(
                        dict(action=rpc['pending']['action'],
                             request=rpc['pending']['request'],
                             attempts=rpc['pending']['attempts'],
                             server_epoch=observed['operation_epoch'],
                             control_revision=observed['control_revision']))
                    rpc['completed'].append(rpc['pending']['action'])
                    rpc['pending'] = None
                    if op['phase'] != 'console_committed':
                        op['phase'] = 'prepared'
            op.update(revision=revision + 1, error_code='', retry_at=0)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def read_manifest(self, context, snapshot_uid, expected_document_hash=None, expected_native_proof_hash=None):
        identifier(snapshot_uid)
        with self._locked(context) as (_, records, _attrs):
            require(MANIFEST_PREFIX + snapshot_uid in records)
            manifest = records[MANIFEST_PREFIX + snapshot_uid]
            for expected, key in ((expected_document_hash, 'document_hash'), (expected_native_proof_hash, 'native_proof_hash')):
                require(expected is None or expected == manifest[key])
            return manifest

    def claim(self, context, operation_id, owner, revision, now, lease_seconds):
        identifier(owner)
        integer(revision, 1)
        integer(now)
        integer(lease_seconds, 1, 300)
        integer(now + lease_seconds)
        with self._locked(context) as (scope, records, attrs):
            op = self._operation(records, operation_id)
            require(records[VM_RESTORE_ACTIVE_OPERATION]['operation_id'] == operation_id and op['revision'] == revision
                    and (op['lease_until'] <= now or op['lease_owner'] == owner))
            expired = op['lease_until'] <= now
            op.update(lease_owner=owner,
                      lease_until=now + lease_seconds,
                      revision=revision + 1,
                      execution_epoch=op['execution_epoch'] + (1 if expired else 0))
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def seal_manifest(self, context, go_context, operation_id, owner, epoch, revision, document, now):
        require(type(go_context) is ServerGoContext)
        for value in (go_context.namespace, go_context.source_vm_name, go_context.source_vm_uid):
            identifier(value)
        fields(document, ('snapshot_name', 'snapshot_uid', 'content_name', 'content_uid', 'core_hash', 'native_proof_hash',
                          'creation_time', 'consistency', 'config', 'disks'), ('startup', ))
        # Canonical round-trip detaches caller-owned nested containers before persistence.
        manifest = json.loads(canonical(document))
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            require(op['kind'] == 'snapshot' and op['phase'] not in TERMINAL and op['region_intent'] is not None)
            intent = op['region_intent']
            for key, value in (('namespace', go_context.namespace), ('source_vm_uid', go_context.source_vm_uid),
                               ('core_hash', manifest['core_hash'])):
                require(not intent[key] or intent[key] == value)
                intent[key] = value
            manifest.update(schema_version=1,
                            scope=scope,
                            namespace=go_context.namespace,
                            source_vm=dict(kind='VirtualMachine',
                                           namespace=go_context.namespace,
                                           name=go_context.source_vm_name,
                                           uid=go_context.source_vm_uid))
            manifest['document_hash'] = digest(manifest)
            validate_manifest(manifest, scope)
            name = MANIFEST_PREFIX + manifest['snapshot_uid']
            if op['snapshot_uid']:
                require(op['snapshot_uid'] == manifest['snapshot_uid'] and records.get(name) == manifest)
            else:
                require(name not in records)
                self._write(scope, records, attrs, name, manifest)
                op.update(snapshot_uid=manifest['snapshot_uid'], document_hash=manifest['document_hash'], revision=revision + 1)
                self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
                pointer = records[VM_RESTORE_ACTIVE_OPERATION]
                pointer.update(manifest_count=pointer['manifest_count'] + 1, revision=pointer['revision'] + 1)
                self._write(scope, records, attrs, VM_RESTORE_ACTIVE_OPERATION, pointer)
            return dict(manifest_id=manifest['snapshot_uid'],
                        snapshot_uid=manifest['snapshot_uid'],
                        core_hash=manifest['core_hash'],
                        native_proof_hash=manifest['native_proof_hash'],
                        manifest_document_hash=manifest['document_hash'])

    @staticmethod
    def _validate_region(op, scope):
        intent, terminal = op['region_intent'], op['region_terminal']
        if intent is None:
            require(terminal is None)
            return
        fields(intent, ('operation_id', 'core_hash', 'namespace', 'source_vm_uid', 'issued_epoch'))
        require(intent['operation_id'] == op['operation_id'])
        integer(intent['issued_epoch'], 1, op['execution_epoch'])
        for key in ('core_hash', 'namespace', 'source_vm_uid'):
            require(type(intent[key]) is str)
        require(not intent['core_hash'] or HASH.fullmatch(intent['core_hash']) is not None)
        if intent['namespace']:
            identifier(intent['namespace'])
            identifier(intent['source_vm_uid'])
        else:
            require(intent['source_vm_uid'] == '')
        if terminal is None:
            return
        required = ('tenant_id', 'service_id', 'region', 'namespace', 'operation_id', 'core_hash', 'execution_epoch',
                    'finalized', 'fence_released', 'outcome')
        history = ('proof_kind', 'finalized_control_revision', 'fence_owned', 'fence_cleared')
        fields(terminal, required, history)
        if any(key in terminal for key in history):
            fields(terminal, required + history)
            require(op['kind'] == 'snapshot' and terminal['proof_kind'] == 'snapshot_operation_history')
            integer(terminal['finalized_control_revision'], 1, 2**64 - 1)
            require(terminal['fence_owned'] is False and type(terminal['fence_cleared']) is bool)
            observed = op.get('observation', {})
            require(observed.get('finalized') is True
                    and observed.get('finalized_control_revision') == terminal['finalized_control_revision']
                    and observed.get('fence_owned') is False
                    and observed.get('fence_cleared') == terminal['fence_cleared']
                    and observed.get('manifest_id') == op['operation_id']
                    and observed.get('manifest_document_hash') == op['document_hash'])
        require(terminal['tenant_id'] == scope['tenant_id'] and terminal['service_id'] == scope['service_id']
                and terminal['region'] == scope['region'])
        require(bool(intent['core_hash']) and bool(intent['namespace']))
        for key in ('namespace', 'operation_id', 'core_hash'):
            require(terminal[key] == intent[key])
        integer(terminal['execution_epoch'], intent['issued_epoch'], op['execution_epoch'])
        require(terminal['finalized'] is True and terminal['fence_released'] is True)
        require(type(terminal['outcome']) is str and terminal['outcome'] in TERMINAL and op['phase'] == terminal['outcome'])
        if terminal['outcome'] == 'runtime_verified':
            require(bool(op['snapshot_uid']) and bool(op['document_hash']))

    def mark_region_issued(self, context, go_context, operation_id, owner, epoch, revision, core_hash, now):
        """Commit before any mutating RPC, including when no response identity is known.

        Empty hash/None Go context pins unknown outcome. A later server response
        may bind these once; an issued intent is never cleared or rebound.
        """
        require(type(core_hash) is str and (not core_hash or HASH.fullmatch(core_hash) is not None))
        require(go_context is None or type(go_context) is ServerGoContext)
        if go_context is not None:
            for value in (go_context.namespace, go_context.source_vm_name, go_context.source_vm_uid):
                identifier(value)
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            require(op['region_terminal'] is None and op['phase'] not in TERMINAL)
            intent = op['region_intent'] or dict(
                operation_id=operation_id, core_hash='', namespace='', source_vm_uid='', issued_epoch=epoch)
            updates = dict(core_hash=core_hash,
                           namespace=go_context.namespace if go_context else '',
                           source_vm_uid=go_context.source_vm_uid if go_context else '')
            for key, value in updates.items():
                require(not intent[key] or intent[key] == value)
                intent[key] = value
            if op['snapshot_uid']:
                manifest = records[MANIFEST_PREFIX + op['snapshot_uid']]
                require(intent['core_hash'] == manifest['core_hash'] and intent['namespace'] == manifest['namespace'])
            op.update(region_intent=intent, revision=revision + 1)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def record_observation(self, context, operation_id, owner, epoch, revision, observation, now):
        observed_snapshot(observation, operation_id)
        observation = json.loads(canonical(observation))
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            require(op['phase'] not in TERMINAL and op['region_intent'] is not None)
            intent = op['region_intent']
            require(not intent['core_hash'] or intent['core_hash'] == observation['core_hash'])
            require(not intent['source_vm_uid'] or intent['source_vm_uid'] == observation['source_vm_uid'])
            if 'request' in op:
                require(op['request']['name'] == observation['snapshot_name'])
            if op['snapshot_uid']:
                manifest = records[MANIFEST_PREFIX + op['snapshot_uid']]
                require(manifest['snapshot_name'] == observation['snapshot_name'])
            op.update(observation=observation, revision=revision + 1)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def record_region_terminal(self, context, operation_id, owner, epoch, revision, evidence, now):
        require(type(evidence) in (RegionTerminalEvidence, SnapshotTerminalEvidence))
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            require(type(evidence) is RegionTerminalEvidence or op['kind'] == 'snapshot')
            require(op['region_intent'] is not None and evidence.execution_epoch == epoch)
            terminal = asdict(evidence)
            require(op['region_terminal'] is None or op['region_terminal'] == terminal)
            op.update(region_terminal=terminal, phase=evidence.outcome, revision=revision + 1, error_code='', retry_at=0)
            self._validate_region(op, scope)
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def advance(self, context, operation_id, owner, epoch, revision, phase, now, retry_at=0, error_code=''):
        require(type(phase) is str and phase in PHASES)
        integer(retry_at)
        integer(now)
        require(error_code in ('', 'REGION_UNKNOWN', 'DEPENDENCY_PENDING', 'CONFLICT', 'RETRY_EXHAUSTED'))
        require(not retry_at or retry_at >= now)
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            require(op['phase'] not in TERMINAL)
            # Issued operations become terminal only through persisted Region evidence.
            require(phase not in TERMINAL
                    or (op['region_intent'] is None and phase == 'cancelled' and not error_code and not retry_at))
            op.update(phase=phase,
                      revision=revision + 1,
                      retry_at=retry_at,
                      error_code=error_code,
                      retry_count=op['retry_count'] + (1 if retry_at else 0))
            self._write(scope, records, attrs, OPERATION_PREFIX + operation_id, op)
            return op

    def release(self, context, operation_id, owner, epoch, revision, now):
        with self._locked(context) as (scope, records, attrs):
            op = self._owned(records, operation_id, owner, epoch, revision, now)
            require(op['phase'] in TERMINAL)
            require(op['region_terminal'] is not None if op['region_intent'] is not None else op['phase'] == 'cancelled')
            pointer = records[VM_RESTORE_ACTIVE_OPERATION]
            pointer.update(operation_id='', last_operation_id=operation_id, revision=pointer['revision'] + 1)
            self._write(scope, records, attrs, VM_RESTORE_ACTIVE_OPERATION, pointer)


vm_restore_journal = VMRestoreJournal()
