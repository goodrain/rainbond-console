"""Commit selected Console configuration and prove a post-commit read before ACK."""
import json

from django.db import connections

from console.models.main import ComponentK8sAttributes
from console.services.vm_restore_journal import (VMRestoreJournal, canonical, digest, fields, require)
from console.utils.vm_restore_attributes import GO_WHITESPACE
from console.utils.vm_restore_config import canonical_restore_config, restore_config_hash
from www.models.main import TenantServiceInfo, TenantServiceVolume

ACCESS_MODE = {'ReadWriteOnce': 'RWO', 'ReadWriteMany': 'RWX', 'ReadOnlyMany': 'ROX'}


def restored_layout(config):
    disks = sorted(config['hardware']['disk_layout'],
                   key=lambda row: (row['boot_order'] == 0, row['boot_order'], row['volume_id']))
    return [
        dict(disk_key=row['disk_key'],
             disk_name=row['canonical_name'],
             disk_role=row['role'],
             device_type=row['device'],
             source_kind='volume',
             order_index=index,
             boot=row['boot_order'] > 0,
             bus=row['bus'],
             boot_order=row['boot_order'],
             read_only=row['read_only']) for index, row in enumerate(disks)
    ]


def validate_commit_document(value, op, scope):
    fields(value, ('schema_version', 'scope', 'operation_id', 'server_epoch', 'snapshot_uid', 'source_document_hash',
                   'commit_hash', 'config_hash', 'config', 'document_hash'))
    observed = op['rpc']['observation']
    require(observed is not None and observed['source_config_ready'] and observed['config_committed'])
    require(value['schema_version'] == 1 and value['scope'] == scope and value['operation_id'] == op['operation_id'])
    require(value['server_epoch'] == op['rpc']['server_epoch'] and value['snapshot_uid'] == op['snapshot_uid']
            and value['source_document_hash'] == op['document_hash'])
    require(value['config'] == observed['config_after'] and value['config_hash'] == observed['config_after_hash']
            and value['commit_hash'] == observed['config_commit_hash'])
    require(restore_config_hash(value['config']) == value['config_hash'])
    material = dict(value)
    material.pop('document_hash')
    require(digest(material) == value['document_hash'])


class RestoreConfigCommitter:
    def __init__(self, journal=None):
        self.journal = journal or VMRestoreJournal()

    @staticmethod
    def _attributes(context):
        rows = ComponentK8sAttributes.objects.using(
            context.identity[4]).select_for_update().filter(component_id=context.identity[2]).order_by('pk')
        found = {}
        for row in rows:
            key = row.name.strip(GO_WHITESPACE).lower()
            if key not in ('vm_boot_mode', 'vm_disk_layout'):
                continue
            require(row.name == key and row.tenant_id == context.identity[1] and key not in found)
            found[key] = row
        return found

    @staticmethod
    def _volumes(context, config):
        keys = [row['disk_key'] for row in config['volumes']]
        rows = list(
            TenantServiceVolume.objects.using(context.identity[4]).select_for_update().filter(
                service_id=context.identity[2], volume_name__in=keys).order_by('pk'))
        require(len(rows) == len(keys) and len(set(row.volume_name for row in rows)) == len(keys))
        return {row.volume_name: row for row in rows}

    def _verify_fields(self, context, config):
        live = TenantServiceInfo.objects.using(context.identity[4]).get(pk=context.identity[0])
        require((live.tenant_id, live.service_id, live.service_region) == context.identity[1:4])
        require(live.min_cpu == config['hardware']['cpu_milli'] and live.min_memory == config['hardware']['memory_mib'])
        attributes = self._attributes(context)
        require(set(attributes) == {'vm_boot_mode', 'vm_disk_layout'})
        require(attributes['vm_boot_mode'].save_type == 'string'
                and attributes['vm_boot_mode'].attribute_value == config['hardware']['boot_mode'])
        require(attributes['vm_disk_layout'].save_type == 'json'
                and json.loads(attributes['vm_disk_layout'].attribute_value) == restored_layout(config))
        rows = self._volumes(context, config)
        for disk in config['volumes']:
            row = rows[disk['disk_key']]
            require(row.volume_capacity == disk['capacity_gib'] and row.volume_type == disk['storage_class']
                    and row.access_mode == ACCESS_MODE[disk['access_mode']])

    def commit(self, context, operation_id, owner, epoch, revision, now):
        # An inner atomic block is not a durable commit. Never ACK from one.
        require(not connections[context.identity[4]].in_atomic_block)
        with self.journal._locked(context) as (scope, records, attrs):
            op = self.journal._owned(records, operation_id, owner, epoch, revision, now)
            observed = op['rpc']['observation']
            require(observed is not None and observed['source_config_ready'] and observed['config_committed']
                    and observed['fence_owned'] and not observed['complete'] and bool(observed['config_commit_hash'])
                    and observed['operation_binding_generation'] == observed['binding_generation'])
            config = canonical_restore_config(observed['config_after'])
            if 'console_commit' in op:
                validate_commit_document(op['console_commit'], op, scope)
                self._verify_fields(context, config)
                return op
            rows = self._volumes(context, config)
            attributes = self._attributes(context)
            live = TenantServiceInfo.objects.using(context.identity[4]).get(pk=context.identity[0])
            live.min_cpu, live.min_memory = config['hardware']['cpu_milli'], config['hardware']['memory_mib']
            live.save(update_fields=['min_cpu', 'min_memory'])
            for key, kind, value in [('vm_boot_mode', 'string', config['hardware']['boot_mode']),
                                     ('vm_disk_layout', 'json', canonical(restored_layout(config)).decode())]:
                if key in attributes:
                    row = attributes[key]
                    row.save_type, row.attribute_value = kind, value
                    row.save(update_fields=['save_type', 'attribute_value'])
                else:
                    ComponentK8sAttributes.objects.using(context.identity[4]).create(tenant_id=context.identity[1],
                                                                                     component_id=context.identity[2],
                                                                                     name=key,
                                                                                     save_type=kind,
                                                                                     attribute_value=value)
            for disk in config['volumes']:
                row = rows[disk['disk_key']]
                # The VM path already passes GiB through to Region unchanged;
                # Console PK and Region logical volume_id need not be equal.
                row.volume_capacity, row.volume_type = disk['capacity_gib'], disk['storage_class']
                row.access_mode = ACCESS_MODE[disk['access_mode']]
                row.save(update_fields=['volume_capacity', 'volume_type', 'access_mode'])
            document = dict(schema_version=1,
                            scope=scope,
                            operation_id=operation_id,
                            server_epoch=op['rpc']['server_epoch'],
                            snapshot_uid=op['snapshot_uid'],
                            source_document_hash=op['document_hash'],
                            commit_hash=observed['config_commit_hash'],
                            config_hash=observed['config_after_hash'],
                            config=config)
            document['document_hash'] = digest(document)
            op.update(console_commit=document, phase='console_committed', revision=revision + 1)
            self.journal._write(scope, records, attrs, 'vm_restore_operation_' + operation_id, op)
        return self.journal.read_operation(context, operation_id)

    def read_committed(self, context, operation_id, owner, epoch, revision, now):
        require(not connections[context.identity[4]].in_atomic_block)
        with self.journal._locked(context) as (scope, records, _attrs):
            op = self.journal._owned(records, operation_id, owner, epoch, revision, now)
            require('console_commit' in op)
            document = op['console_commit']
            validate_commit_document(document, op, scope)
            observed = op['rpc']['observation']
            require(observed['fence_owned'] and not observed['complete']
                    and observed['operation_binding_generation'] == observed['binding_generation'])
            self._verify_fields(context, document['config'])
            return json.loads(canonical(document))
