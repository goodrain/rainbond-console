"""Existing snapshot manifest and ACK signatures; no transport or total workflow."""
import json
import re

from django.db import connections

from console.models.main import ComponentK8sAttributes
from console.services.vm_restore_journal import (ServerGoContext, VMRestoreJournal, canonical, require, selected_config,
                                                 snapshot_request, strict_pairs, validate_manifest)
from console.utils.vm_restore_attributes import GO_WHITESPACE
from www.models.main import TenantServiceInfo, TenantServiceVolume


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
    def _verify_console(context, document):
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
        require(set(found) == {'vm_boot_mode', 'vm_disk_layout'})
        require(found['vm_boot_mode'].save_type == 'string' and found['vm_boot_mode'].attribute_value == config['boot_mode']
                and found['vm_disk_layout'].save_type == 'json')
        try:
            layout = json.loads(found['vm_disk_layout'].attribute_value, object_pairs_hook=strict_pairs)
        except (ValueError, TypeError):
            require(False)
        require(
            type(layout) is list and len(layout) == len(config['disk_layout']) and all(type(item) is dict for item in layout))
        actual = {item.get('disk_key'): item for item in layout}
        require(len(actual) == len(layout) and set(actual) == {row['disk_key'] for row in config['disk_layout']})
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
        for disk in disks:
            row = volumes.get(disk['disk_key'])
            require(row is not None and row.volume_type == disk['storage_class']
                    and row.volume_capacity * (1 << 30) == disk['requested_bytes'])

    def commit(self, context, go_context, operation_id, owner, epoch, revision, observed, now):
        require(not connections[context.identity[4]].in_atomic_block)
        with self.journal._locked(context) as (_scope, records, _attrs):
            operation = self.journal._owned(records, operation_id, owner, epoch, revision, now)
            document = self._document(operation, go_context, observed)
            self._verify_console(context, document)
            self.journal.seal_manifest(context, go_context, operation_id, owner, epoch, revision, document, now)
        operation = self.journal.read_operation(context, operation_id)
        return self.journal.read_manifest(context, operation['snapshot_uid'], operation['document_hash'])

    def ready_request(self, context, operation_id, owner, epoch, revision, observed, now):
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
            self._verify_console(context, document)
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
