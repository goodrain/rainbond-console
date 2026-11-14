"""Closed bounded-command inputs for the frozen Region restore RPC v1."""
import json
import re

from console.exception.main import ServiceHandleException

ACTION_FIELDS = {
    'prepare': ('snapshot_name', 'power_after'),
    'halt': (),
    'sync-halted': (),
    'resume': (),
    'rollback-halt': (),
    'rollback': (),
    'rollback-sync-halted': (),
    'rollback-resume': (),
    'cancel': (),
    'ensure-rox': ('volume_id', ),
    'pin-rox': ('volume_id', ),
    'ensure-target': ('volume_id', ),
    'pin-target': ('volume_id', ),
    'stage-plan': ('mode', ),
    'stage-job': ('mode', ),
    'stage-pod': ('mode', ),
    'stage-capture': ('mode', ),
    'cleanup': ('resource_key', ),
    'commit': ('config', ),
    'config-ack': ('commit_hash', 'document_hash'),
    'rollback-ack': ('commit_hash', 'document_hash'),
    'finalize': ()
}


def check(condition):
    if not condition:
        raise ServiceHandleException('vm_restore_invalid_request', '恢复请求参数无效', status_code=400)


def uint(value, minimum=0):
    check(type(value) is int and minimum <= value <= 2**64 - 1)


def hash_value(value):
    check(type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value) is not None)


def operation_id(value):
    check(type(value) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', value) is not None)


def restore_config(config):
    check(type(config) is dict and set(config) == {'hardware', 'volumes'})
    hardware = config['hardware']
    check(type(hardware) is dict and set(hardware) == {'cpu_milli', 'memory_mib', 'boot_mode', 'disk_layout'})
    uint(hardware['cpu_milli'], 1)
    uint(hardware['memory_mib'], 1)
    check(hardware['boot_mode'] in ('bios', 'uefi'))
    check(type(hardware['disk_layout']) is list and 1 <= len(hardware['disk_layout']) <= 16)
    for disk in hardware['disk_layout']:
        check(
            type(disk) is dict
            and set(disk) == {'volume_id', 'disk_key', 'canonical_name', 'role', 'device', 'bus', 'boot_order', 'read_only'})
        uint(disk['volume_id'], 1)
        uint(disk['boot_order'])
        check(type(disk['read_only']) is bool and disk['canonical_name'] == 'manual' + str(disk['volume_id']))
        check(disk['role'] in ('root', 'data') and disk['device'] in ('disk', 'lun', 'cdrom'))
        check(disk['bus'] in ('virtio', 'sata', 'scsi', 'usb'))
        check(type(disk['disk_key']) is str and re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,127}', disk['disk_key']) is not None)
    check(type(config['volumes']) is list and 1 <= len(config['volumes']) <= 16)
    for disk in config['volumes']:
        check(
            type(disk) is dict
            and set(disk) == {'volume_id', 'disk_key', 'capacity_gib', 'storage_class', 'read_only', 'access_mode'})
        uint(disk['volume_id'], 1)
        uint(disk['capacity_gib'], 1)
        check(type(disk['read_only']) is bool)
        for key in ('disk_key', 'storage_class', 'access_mode'):
            check(type(disk[key]) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,252}', disk[key]) is not None)


def command_body(action, body):
    check(type(action) is str and action in ACTION_FIELDS and type(body) is dict)
    common = {'expected_control_revision', 'expected_binding_generation'}
    required = common | set(ACTION_FIELDS[action])
    optional = {'expected_operation_epoch'
                } | ({'rollback', 'cancelled'} if action == 'finalize' else {'cancelled'} if action == 'cleanup' else set())
    check(required <= set(body) <= required | optional)
    for key in common:
        uint(body[key])
    if action != 'prepare' or 'expected_operation_epoch' in body:
        hash_value(body.get('expected_operation_epoch'))
    if action == 'prepare':
        name = body['snapshot_name']
        check(
            type(name) is str and 1 <= len(name) <= 253
            and re.fullmatch(r'[a-z0-9](?:[-a-z0-9]*[a-z0-9])?(?:\.[a-z0-9](?:[-a-z0-9]*[a-z0-9])?)*', name) is not None)
        check(body['power_after'] in ('previous', 'stopped'))
    if 'volume_id' in body:
        uint(body['volume_id'], 1)
    if 'mode' in body:
        check(body['mode'] in ('inspect', 'copy', 'verify'))
    if 'resource_key' in body:
        check(
            type(body['resource_key']) is str and re.fullmatch(
                r'(?:(?:rox|target)[1-9][0-9]*|(?:plan|job|pod)-(?:inspect|copy|verify))', body['resource_key']) is not None)
    for key in ('commit_hash', 'document_hash'):
        if key in body:
            hash_value(body[key])
    for key in ('rollback', 'cancelled'):
        if key in body:
            check(type(body[key]) is bool)
    check(not (body.get('rollback') and body.get('cancelled')))
    if 'config' in body:
        restore_config(body['config'])
    try:
        encoded = json.dumps(body, ensure_ascii=False, allow_nan=False, separators=(',', ':'), sort_keys=True)
    except (TypeError, ValueError):
        check(False)
    check(len(encoded.encode('utf-8')) <= 16384)
    return encoded
