"""Public projection of Go's complete current-VM snapshot capability result."""
import re

from console.services.vm_snapshot_read import snapshot_error


def _require(condition):
    if not condition:
        raise snapshot_error('vm_snapshot_read_failed')


def _text(value, maximum=1024):
    _require(type(value) is str and len(value) <= maximum and not any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value))
    return value


def _decision(value):
    _require(isinstance(value, dict))
    _require(type(value.get('supported')) is bool and value.get('status') in ('supported', 'unsupported', 'unknown'))
    _require(value['supported'] == (value['status'] == 'supported'))
    code = _text(value.get('reason_code'), 128)
    _require(re.fullmatch(r'[a-z][a-z0-9_]{0,127}', code) is not None)
    return dict(supported=value['supported'], status=value['status'], reason_code=code, message=_text(value.get('message')))


def project_existing_snapshot_capability(value):
    result = _decision(value)
    _require(value.get('operation') == 'create_snapshot' and type(value.get('complete')) is bool)
    result.update(operation='create_snapshot', complete=value['complete'])
    for key in ('control_revision', 'binding_generation'):
        _require(type(value.get(key)) is int and 0 <= value[key] <= 2**64 - 1)
        result[key] = value[key]
    _require(type(value.get('volumes')) is list and type(value.get('excluded_volumes')) is list)
    _require(len(value['volumes']) <= 256 and len(value['excluded_volumes']) <= 256)
    result['volumes'] = []
    for volume in value['volumes']:
        item = _decision(volume)
        item['key'] = _text(volume.get('key'), 253)
        _require(bool(item['key']) and type(volume.get('read_only')) is bool)
        item['read_only'] = volume['read_only']
        for key in ('disk_key', 'role', 'storage_class', 'driver', 'volume_snapshot_class'):
            if key in volume:
                item[key] = _text(volume[key], 253)
        if 'volume_id' in volume:
            _require(type(volume['volume_id']) is int and 1 <= volume['volume_id'] <= 2**64 - 1)
            item['volume_id'] = volume['volume_id']
        result['volumes'].append(item)
    result['excluded_volumes'] = []
    for volume in value['excluded_volumes']:
        _require(isinstance(volume, dict))
        result['excluded_volumes'].append({key: _text(volume.get(key), 253) for key in ('key', 'role', 'reason_code')})
    # Preserve Go's aggregate (e.g. an active fence) even if every row is ready.
    # This consistency guard can only reject a false positive, never invent one.
    if result['supported']:
        _require(result['complete'] and bool(result['volumes']) and all(v['supported'] for v in result['volumes']))
    return result
