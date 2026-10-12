"""Owned upload chunk projections; observation never grants deletion permission."""
import re
from datetime import datetime, timezone
from typing import Any

from console.services.cleanup_inventory import _base

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')


def upload_resources(records: list[dict[str, Any]], bean: dict[str, Any], region: str,
                     current_events: set[str] | None = None, now: datetime | None = None) -> list[dict[str, Any]]:
    """Accept only sessions belonging to Console-selected upload records."""
    events = {record['event_id'] for record in records if isinstance(record.get('event_id'), str) and record['event_id']}
    if (not isinstance(bean, dict) or bean.get('protocol') != 1 or bean.get('scope') != 'upload_chunks'
            or not isinstance(bean.get('items'), list) or len(bean['items']) > 500):
        raise ValueError('upload inventory unavailable')
    resources: list[dict[str, Any]] = []
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    storage_fingerprint = bean.get('storage_fingerprint')
    retirement_ready = (bean.get('writers_ready') is True and isinstance(storage_fingerprint, str)
                        and re.fullmatch(r'[a-f0-9]{64}', storage_fingerprint) is not None)
    seen: set[str] = set()
    for item in bean['items']:
        if (not isinstance(item, dict) or not isinstance(item.get('id'), str) or not _ID.fullmatch(item['id'])
                or item['id'] in seen or not isinstance(item.get('event_id'), str) or item['event_id'] not in events):
            raise ValueError('invalid upload inventory scope')
        seen.add(item['id'])
        name = item.get('file_name')
        name = name.strip() if isinstance(name, str) and len(name) <= 255 else ''
        resource = _base('upload-chunks:{}:{}'.format(region, item['id']), region, 'uploads', 'upload_chunks',
                         '{} / 上传分片'.format(name) if name else '上传分片', '')
        resource['source'] = 'platform_uploads'
        _apply_size(resource, item)
        expires_at = _timestamp(item.get('expires_at'))
        state_fingerprint = item.get('state_fingerprint')
        size = item.get('bytes')
        objects = item.get('objects')
        idle_days = int((observed_at - expires_at).total_seconds() // 86400) if expires_at else 0
        if (retirement_ready and item.get('status') in ('uploading', 'completed', 'failed')
                and isinstance(state_fingerprint, str) and re.fullmatch(r'[a-f0-9]{64}', state_fingerprint)
                and type(size) is int and size > 0 and type(objects) is int and objects > 0
                and 1 <= idle_days <= 365):
            resource['retirement'] = {
                'protocol': 1, 'kind': 'upload_chunks', 'rank': 1,
                'expected': {
                    'session_id': item['id'], 'event_id': item['event_id'],
                    'state_fingerprint': state_fingerprint,
                    'storage_fingerprint': storage_fingerprint, 'idle_days': idle_days,
                }
            }
        resources.append(resource)
    if 'packages' in bean:
        packages = bean['packages']
        if not isinstance(packages, list) or len(packages) != len(events):
            raise ValueError('incomplete package inventory')
        seen_events: set[str] = set()
        for package in packages:
            if (not isinstance(package, dict) or not isinstance(package.get('event_id'), str)
                    or package['event_id'] not in events or package['event_id'] in seen_events):
                raise ValueError('invalid package inventory scope')
            event_id = package['event_id']
            seen_events.add(event_id)
            names = {item['file_name'].strip() for item in bean['items'] if item.get('event_id') == event_id
                     and isinstance(item.get('file_name'), str) and 0 < len(item['file_name']) <= 255}
            name = next(iter(names)) + ' / 上传包' if len(names) == 1 else '上传包'
            resource = _base('upload-package:{}:{}'.format(region, event_id), region, 'uploads', 'upload_package', name, '')
            resource['source'] = 'platform_uploads'
            _apply_size(resource, package)
            if package.get('referenced') is True or event_id in (current_events or set()):
                resource['protection'] = 'referenced'
                resource['usageStatus'] = 'referenced'
            resources.append(resource)
    return resources


def _apply_size(resource: dict[str, Any], item: dict[str, Any]) -> None:
    if item.get('size_status') == 'measured':
        size, objects = item.get('bytes'), item.get('objects')
        if type(size) is not int or not 0 <= size <= 2**63 - 1 or type(objects) is not int or not 0 <= objects <= 10000:
            raise ValueError('invalid measured upload size')
        resource['sizeBytes'] = size
        resource['sizeKnown'] = True
    elif item.get('size_status') != 'unavailable' or item.get('bytes') is not None or item.get('objects') is not None:
        raise ValueError('invalid unknown upload size')


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def package_reference_events(paths: list[str | None]) -> tuple[set[str], bool]:
    """Parse bounded package-only paths; return positive evidence even if incomplete."""
    events: set[str] = set()
    complete = len(paths) <= 20000
    pattern = re.compile(r'^/grdata/package_build/(?:temp|components/[A-Za-z0-9][A-Za-z0-9_-]{0,63})/events/'
                         r'([A-Za-z0-9][A-Za-z0-9_-]{0,63})$')
    for value in paths[:20000]:
        match = pattern.fullmatch(value) if isinstance(value, str) and len(value) <= 512 else None
        if match:
            events.add(match.group(1))
        else:
            complete = False
    return events, complete


def current_package_reference_events(region: str) -> tuple[set[str], bool]:
    """Cross-team evidence is reduced to event identifiers, never names or config."""
    from www.models.main import TenantServiceInfo
    try:
        paths = list(TenantServiceInfo.objects.filter(
            service_region=region, git_url__startswith='/grdata/package_build/').values_list('git_url', flat=True)[:20001])
        return package_reference_events(paths)
    except Exception:
        return set(), False
