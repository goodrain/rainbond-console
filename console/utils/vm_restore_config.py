"""Canonical safe RestoreConfig bytes matching frozen Go v1.1 structs."""
import hashlib
import json

from console.utils.vm_restore_rpc import restore_config

HARDWARE = ('cpu_milli', 'memory_mib', 'boot_mode', 'disk_layout')
LAYOUT = ('volume_id', 'disk_key', 'canonical_name', 'role', 'device', 'bus', 'boot_order', 'read_only')
VOLUME = ('volume_id', 'disk_key', 'capacity_gib', 'storage_class', 'read_only', 'access_mode')


def canonical_restore_config(value):
    restore_config(value)
    hardware = {key: value['hardware'][key] for key in HARDWARE}
    hardware['disk_layout'] = [{
        key: row[key]
        for key in LAYOUT
    } for row in sorted(hardware['disk_layout'], key=lambda row: row['volume_id'])]
    volumes = [{key: row[key] for key in VOLUME} for row in sorted(value['volumes'], key=lambda row: row['volume_id'])]
    by_id = {row['volume_id']: row for row in volumes}
    if len(by_id) != len(volumes) or any(row['access_mode'] not in ('ReadWriteOnce', 'ReadWriteMany', 'ReadOnlyMany')
                                         for row in volumes):
        raise ValueError('Invalid restore volume configuration')
    if any(row['volume_id'] not in by_id or row['disk_key'] != by_id[row['volume_id']]['disk_key']
           or row['read_only'] != by_id[row['volume_id']]['read_only'] for row in hardware['disk_layout']):
        raise ValueError('Incomplete restore disk configuration')
    return {'hardware': hardware, 'volumes': volumes}


def restore_config_hash(value):
    canonical = canonical_restore_config(value)
    # Go encoding/json uses struct field order and HTML/U+2028/U+2029 escapes.
    data = json.dumps(canonical, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    for character, escaped in (('<', '\\u003c'), ('>', '\\u003e'), ('&', '\\u0026'), ('\u2028', '\\u2028'), ('\u2029',
                                                                                                             '\\u2029')):
        data = data.replace(character, escaped)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
