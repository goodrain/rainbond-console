"""Owned upload chunk projections; observation never grants deletion permission."""
import re
from typing import Any

from console.services.cleanup_inventory import _base

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')


def upload_resources(records: list[dict[str, Any]], bean: dict[str, Any], region: str) -> list[dict[str, Any]]:
    """Accept only sessions belonging to Console-selected upload records."""
    events = {record['event_id'] for record in records}
    if (not isinstance(bean, dict) or bean.get('protocol') != 1 or bean.get('scope') != 'upload_chunks'
            or not isinstance(bean.get('items'), list) or len(bean['items']) > 500):
        raise ValueError('upload inventory unavailable')
    resources: list[dict[str, Any]] = []
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
        if item.get('size_status') == 'measured':
            size, objects = item.get('bytes'), item.get('objects')
            if type(size) is not int or not 0 <= size <= 2**63 - 1 or type(objects) is not int or not 0 <= objects <= 10000:
                raise ValueError('invalid measured upload size')
            resource['sizeBytes'] = size
            resource['sizeKnown'] = True
        elif item.get('size_status') != 'unavailable' or item.get('bytes') is not None or item.get('objects') is not None:
            raise ValueError('invalid unknown upload size')
        resources.append(resource)
    return resources
