"""Existing snapshot manifest and ACK signatures; no transport or total workflow."""
import json
import re
from dataclasses import dataclass

from django.db import connections

from console.models.main import ComponentK8sAttributes
from console.services.vm_restore_journal import (ServerGoContext, VMRestoreJournal, canonical, require, selected_config,
                                                 snapshot_request, strict_pairs, validate_manifest)
from console.utils.vm_restore_attributes import GO_WHITESPACE
from www.models.main import TenantServiceInfo, TenantServiceVolume


@dataclass(frozen=True)
class SnapshotCapacityEvidence:
    scope: tuple
    operation_id: str
    core_hash: str
    volumes: tuple

    @classmethod
    def from_region(cls, context, observed, response, body):
        # Called only by the worker's scoped SDK read, outside SQL locks.
        require(observed.get('fence_owned') is True and observed.get('fence_cleared') is False)
        require(
            isinstance(response, dict) and response.get('status') == 200 and isinstance(body, dict)
            and body.get('code', 200) == 200)
        rows = json.loads(canonical(body.get('list')))
        require(type(rows) is list and len(rows) <= 256)
        wanted = {disk['disk_key']: disk for disk in observed['disks']}
        require(len(wanted) == len(observed['disks']) and bool(wanted))
        found = {}
        seen = set()
        for row in rows:
            require(type(row) is dict and row.get('service_id') == context.identity[2])
            key = row.get('volume_name')
            require(type(key) is str and key not in seen)
            seen.add(key)
            if key not in wanted:
                continue
            capacity = row.get('volume_capacity')
            require(type(capacity) is int and 0 < capacity <= 2**30)
            logical_bytes = capacity * (1 << 30)
            disk = wanted[key]
            require(row.get('volume_type') == disk['storage_class'] and logical_bytes <= disk['requested_bytes'])
            found[key] = (key, row['volume_type'], logical_bytes)
        require(set(found) == set(wanted))
        return cls(context.identity, observed['operation_id'], observed['core_hash'],
                   tuple(found[key] for key in sorted(found)))

    def verify_scope(self, context, operation_id, document):
        require(self.scope == context.identity and self.operation_id == operation_id
                and self.core_hash == document['core_hash'])


def snapshot_prepare_body(operation):
    require(operation['kind'] == 'snapshot' and 'request' in operation)
    operation_id = operation['operation_id']
    require(type(operation_id) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', operation_id) is not None)
    snapshot_request(operation['request'])
    # Region RequestID is its operation ID. ManifestID must be fixed before POST.
    return dict(operation['request'], request_id=operation_id, manifest_id=operation_id)


def ready_action(operation, observed):
    """Select an existing action only after ready_request verified this observation."""
    request = snapshot_prepare_body(operation)
    require(bool(operation['snapshot_uid']) and bool(operation['document_hash']))
    require(observed['operation_id'] == operation['operation_id'] and observed['snapshot_name'] == request['name']
            and observed['power_after'] == request['power_after'])
    for key in ('was_running', 'source_stopped', 'source_running', 'source_lock_clear', 'ready_to_use', 'finalized',
                'cancelled', 'deleted'):
        require(type(observed.get(key)) is bool)
    require(not (observed['source_stopped'] and observed['source_running']))
    if (observed.get('error_code') or observed.get('coverage', {}).get('complete') is not True
            or not observed['source_lock_clear'] or not observed['ready_to_use'] or observed['finalized']
            or observed['cancelled'] or observed['deleted']):
        return None
    want_running = observed['was_running'] and request['power_after'] == 'previous'
    if want_running:
        return 'finalize' if observed['source_running'] else 'resume' if observed['source_stopped'] else None
    return 'finalize' if observed['source_stopped'] else None


class SnapshotManifestService:
    def __init__(self, journal=None):
        self.journal = journal or VMRestoreJournal()

    @staticmethod
    def _document(operation, go_context, observed):
        require(type(go_context) is ServerGoContext)
        request = snapshot_prepare_body(operation)
        intent = operation['region_intent']
        require(intent is not None and intent['operation_id'] == observed['operation_id'] == operation['operation_id']
                and intent['core_hash'] == observed['core_hash'] and bool(intent['core_hash'])
                and intent['source_vm_uid'] == go_context.source_vm_uid == observed['source_vm_uid']
                and intent['namespace'] == go_context.namespace)
        require(observed['snapshot_name'] == request['name'] and observed['description'] == request['description']
                and observed['power_after'] == request['power_after'])
        for key in ('ready_to_use', 'finalized', 'cancelled', 'deleted', 'was_running'):
            require(type(observed.get(key)) is bool)
        require(observed['ready_to_use'] and not observed['cancelled'] and not observed['deleted'] and not observed['finalized']
                and observed.get('error_code') == '')
        selected_config(observed['config'])
        writable = [row for row in observed['config']['disk_layout'] if not row['read_only']]
        excluded = sorted(row['disk_key'] for row in observed['config']['disk_layout'] if row['read_only'])
        coverage = observed['coverage']
        require(coverage['complete'] is True and type(coverage['expected_writable_disks']) is int
                and type(coverage['included_disks']) is int
                and coverage['expected_writable_disks'] == coverage['included_disks'] == len(writable)
                and coverage['missing_disk_keys'] == [] and coverage['excluded_read_only'] == excluded)
        document = {
            key: observed[key]
            for key in ('snapshot_name', 'snapshot_uid', 'content_name', 'content_uid', 'core_hash', 'native_proof_hash',
                        'creation_time', 'consistency', 'config', 'disks')
        }
        document['startup'] = dict(was_running=observed['was_running'], power_after=observed['power_after'])
        return json.loads(canonical(document))

    @staticmethod
    def _verify_console(context, document, capacities=None):
        alias = context.identity[4]
        live = TenantServiceInfo.objects.using(alias).get(pk=context.identity[0])
        config = document['config']
        require((live.tenant_id, live.service_id, live.service_region) == context.identity[1:4] and live.extend_method == 'vm')
        require(live.min_cpu == config['cpu_milli'] and live.min_memory == config['memory_mib'])
        found = {}
        for row in ComponentK8sAttributes.objects.using(alias).select_for_update().filter(component_id=live.service_id):
            name = row.name.strip(GO_WHITESPACE).lower()
            if name in ('vm_boot_mode', 'vm_disk_layout'):
                require(row.tenant_id == live.tenant_id and row.name == name and name not in found)
                found[name] = row
        require('vm_disk_layout' in found and found['vm_disk_layout'].save_type == 'json')
        boot = found.get('vm_boot_mode')
        # ISO-created BIOS guests historically omit this optional attribute.
        # An explicit boot mode still has to match the observed native config.
        require((boot is None and config['boot_mode'] == 'bios')
                or (boot is not None and boot.save_type == 'string' and boot.attribute_value == config['boot_mode']))
        try:
            layout = json.loads(found['vm_disk_layout'].attribute_value, object_pairs_hook=strict_pairs)
        except (ValueError, TypeError):
            require(False)
        require(type(layout) is list and all(type(item) is dict for item in layout))
        require(all(type(item.get('disk_key')) is str and item['disk_key'] for item in layout))
        require(len({item['disk_key'] for item in layout}) == len(layout))
        actual = {}
        for item in layout:
            if item.get('source_kind') == 'volume':
                actual[item['disk_key']] = item
            else:
                # This is the same read-only optical-media exclusion as Region.
                # Unknown or writable sources must never disappear from coverage.
                require(
                    item.get('source_kind') in ('installer_media', 'container_disk') and item.get('device_type') == 'cdrom'
                    and item.get('read_only', True) is True)
        require(set(actual) == {row['disk_key'] for row in config['disk_layout']})
        for disk in config['disk_layout']:
            item = actual[disk['disk_key']]
            # Display disk_name and Console PK are not Region manual<volume_id>.
            require(
                item.get('source_kind') == 'volume' and item.get('disk_role') == disk['role']
                and item.get('device_type') == disk['device'])
            for optional in ('bus', 'boot_order', 'read_only'):
                require(optional not in item
                        or (type(item[optional]) is type(disk[optional]) and item[optional] == disk[optional]))
        # Native historical config/proof supply bus/order/read-only when Console
        # never persisted them. They are never filled with guessed defaults.
        disks = document['disks']
        rows = list(
            TenantServiceVolume.objects.using(alias).select_for_update().filter(
                service_id=live.service_id, volume_name__in=[disk['disk_key'] for disk in disks]))
        volumes = {row.volume_name: row for row in rows}
        require(len(rows) == len(volumes) == len(disks))
        logical = None
        if capacities is not None:
            require(
                type(capacities) is SnapshotCapacityEvidence and capacities.scope == context.identity
                and capacities.core_hash == document['core_hash'])
            logical = {key: (storage, amount) for key, storage, amount in capacities.volumes}
            require(set(logical) == {disk['disk_key'] for disk in disks})
        for disk in disks:
            row = volumes.get(disk['disk_key'])
            # CDI's PVC request includes filesystem overhead; it is not the
            # configured guest capacity. Preserve the physical bytes in the
            # manifest and compare logical capacity against Region metadata.
            expected = disk['requested_bytes']
            if logical is not None:
                storage, expected = logical[disk['disk_key']]
                require(storage == disk['storage_class'] and 0 < expected <= disk['requested_bytes'])
            require(row is not None and row.volume_type == disk['storage_class']
                    and row.volume_capacity * (1 << 30) == expected)

    def commit(self, context, go_context, operation_id, owner, epoch, revision, observed, now, capacities=None):
        require(not connections[context.identity[4]].in_atomic_block)
        with self.journal._locked(context) as (_scope, records, _attrs):
            operation = self.journal._owned(records, operation_id, owner, epoch, revision, now)
            document = self._document(operation, go_context, observed)
            if capacities is not None:
                require(type(capacities) is SnapshotCapacityEvidence)
                capacities.verify_scope(context, operation_id, document)
            self._verify_console(context, document, capacities)
            self.journal.seal_manifest(context, go_context, operation_id, owner, epoch, revision, document, now)
        operation = self.journal.read_operation(context, operation_id)
        return self.journal.read_manifest(context, operation['snapshot_uid'], operation['document_hash'])

    def ready_request(self, context, operation_id, owner, epoch, revision, observed, now, capacities=None):
        require(not connections[context.identity[4]].in_atomic_block)
        with self.journal._locked(context) as (scope, records, _attrs):
            operation = self.journal._owned(records, operation_id, owner, epoch, revision, now)
            require(bool(operation['snapshot_uid']))
            manifest = self.journal.read_manifest(context, operation['snapshot_uid'], operation['document_hash'])
            validate_manifest(manifest, scope)
            source = manifest['source_vm']
            go_context = ServerGoContext(source['namespace'], source['name'], source['uid'])
            document = self._document(operation, go_context, observed)
            require(all(manifest[key] == value for key, value in document.items()))
            if capacities is not None:
                require(type(capacities) is SnapshotCapacityEvidence)
                capacities.verify_scope(context, operation_id, document)
            self._verify_console(context, document, capacities)
            # The convenience seal return uses snapshot_uid as manifest_id;
            # Region expects the original Prepare ManifestID instead.
            return dict(operation_id=operation_id,
                        request_id=operation_id,
                        core_hash=manifest['core_hash'],
                        snapshot_uid=manifest['snapshot_uid'],
                        content_uid=manifest['content_uid'],
                        native_proof_hash=manifest['native_proof_hash'],
                        manifest_id=snapshot_prepare_body(operation)['manifest_id'],
                        manifest_document_hash=manifest['document_hash'],
                        ack_kind='ready')
