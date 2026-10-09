"""Scoped retirement of platform records. This service never deletes image blobs."""
import hashlib
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
import hmac
import json
import re
import time
from typing import Any


class RetirementConflict(Exception):
    pass


def validate_upload_chunk_retirement(expected: dict[str, Any]) -> None:
    if set(expected) != {'session_id', 'event_id', 'state_fingerprint', 'storage_fingerprint', 'idle_days'}:
        raise ValueError()
    for field in ('session_id', 'event_id'):
        value = expected[field]
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value):
            raise ValueError()
    for field in ('state_fingerprint', 'storage_fingerprint'):
        if not isinstance(expected[field], str) or not re.fullmatch(r'[a-f0-9]{64}', expected[field]):
            raise ValueError()
    if type(expected['idle_days']) is not int or not 1 <= expected['idle_days'] <= 365:
        raise ValueError()


def retire_upload_chunks(enterprise: str, region: str, expected: dict[str, Any], operation_id: str) -> dict[str, Any]:
    from console.models.main import PackageUploadRecord
    from www.models.main import Tenants
    from www.apiclient.regionapi import RegionInvokeApi
    validate_upload_chunk_retirement(expected)
    teams = Tenants.objects.filter(enterprise_id=enterprise).values_list('tenant_name', flat=True)
    if not PackageUploadRecord.objects.filter(
            event_id=expected['event_id'], region=region, team_name__in=teams).exists():
        raise RetirementConflict()
    command = dict(expected, operation_id=operation_id)
    status, response = RegionInvokeApi().delete_cleanup_upload_chunks(enterprise, region, command)
    if status == 409:
        raise RetirementConflict()
    if status != 200:
        raise RuntimeError('upload retirement unavailable')
    result = (response or {}).get('bean') or {}
    if (result.get('protocol') != 1 or result.get('operation_id') != operation_id
            or result.get('event_id') != expected['event_id'] or result.get('session_id') != expected['session_id']
            or result.get('state') != 'deleted'):
        raise RetirementConflict()
    return {'record_retired': True, 'image_deleted': False, 'chunks_deleted': True, 'reclaimed_bytes': None}


def inspect_upload_chunks(enterprise: str, region: str, expected: dict[str, Any], operation_id: str) -> str:
    """Read the exact original Core receipt without replaying retirement."""
    from console.models.main import PackageUploadRecord
    from www.models.main import Tenants
    from www.apiclient.regionapi import RegionInvokeApi
    validate_upload_chunk_retirement(expected)
    teams = Tenants.objects.filter(enterprise_id=enterprise).values_list('tenant_name', flat=True)
    if not PackageUploadRecord.objects.filter(
            event_id=expected['event_id'], region=region, team_name__in=teams).exists():
        raise RetirementConflict()
    command = {
        'operation_id': operation_id,
        'session_id': expected['session_id'],
        'event_id': expected['event_id'],
        'state_fingerprint': expected['state_fingerprint'],
        'storage_fingerprint': expected['storage_fingerprint'],
    }
    status, response = RegionInvokeApi().inspect_cleanup_upload_chunks(enterprise, region, command)
    if status != 200:
        raise RuntimeError('upload inspection unavailable')
    result = (response or {}).get('bean') or {}
    state = result.get('state')
    if (result.get('protocol') != 1 or result.get('operation_id') != operation_id
            or result.get('event_id') != expected['event_id'] or result.get('session_id') != expected['session_id']
            or state not in ('deleted', 'present', 'unknown')):
        raise RuntimeError('upload inspection receipt invalid')
    return state


def retirement_payload(method: str, path: str, enterprise: str, region: str, timestamp: str, body: bytes) -> bytes:
    return '\n'.join(['cleanup-retirement-v1', method, path, enterprise, region, timestamp,
                      hashlib.sha256(body).hexdigest()]).encode('utf-8')


def verify_retirement_request(method: str, path: str, enterprise: str, region: str, timestamp: Any,
                              signature: Any, body: bytes, key: bytes, now: float | None = None) -> bool:
    if method != 'POST' or len(key) < 32 or len(body) > 65536:
        return False
    if not isinstance(timestamp, str) or not re.fullmatch(r'[0-9]{1,12}', timestamp):
        return False
    if not isinstance(signature, str) or not re.fullmatch(r'[a-f0-9]{64}', signature):
        return False
    if abs(int(time.time() if now is None else now) - int(timestamp)) > 120:
        return False
    expected = hmac.new(key, retirement_payload(method, path, enterprise, region, timestamp, body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def inspection_payload(method: str, path: str, enterprise: str, region: str, timestamp: str, body: bytes) -> bytes:
    return '\n'.join(['cleanup-retirement-inspect-v1', method, path, enterprise, region, timestamp,
                      hashlib.sha256(body).hexdigest()]).encode('utf-8')


def verify_inspection_request(method: str, path: str, enterprise: str, region: str, timestamp: Any,
                              signature: Any, body: bytes, key: bytes, now: float | None = None) -> bool:
    if method != 'POST' or len(key) < 32 or len(body) > 65536:
        return False
    if not isinstance(timestamp, str) or not re.fullmatch(r'[0-9]{1,12}', timestamp):
        return False
    if not isinstance(signature, str) or not re.fullmatch(r'[a-f0-9]{64}', signature):
        return False
    if abs(int(time.time() if now is None else now) - int(timestamp)) > 120:
        return False
    expected = hmac.new(key, inspection_payload(method, path, enterprise, region, timestamp, body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def validate_template_retirement(current: dict, expected: dict) -> None:
    if any(not expected.get(key) or current.get(key) != expected[key] for key in ('id', 'app_id', 'version', 'content_hash')):
        raise RetirementConflict()
    if current.get('activation_revision', '') != expected.get('activation_revision', ''):
        raise RetirementConflict()
    protected = any(current.get(key) is not False for key in ('current', 'referenced', 'active_operation'))
    if current.get('managed') is not True or protected:
        raise RetirementConflict()


def template_fingerprint(raw: str, key: bytes) -> str:
    if len(key) < 32:
        raise RetirementConflict()
    return hmac.new(key, b'cleanup-template-v1\n' + raw.encode('utf-8'), hashlib.sha256).hexdigest()


def inspect_template_identity(current: dict[str, Any] | None, expected: dict[str, Any]) -> str:
    if current is None:
        return 'absent'
    for field in ('id', 'app_id', 'version', 'content_hash', 'activation_revision'):
        if current.get(field) != expected.get(field):
            raise RetirementConflict()
    return 'present'


def inspect_template_record(enterprise: str, region: str, expected: dict[str, Any], key: bytes) -> str:
    from console.models.main import RainbondCenterApp, RainbondCenterAppVersion
    parent = RainbondCenterApp.objects.filter(app_id=expected['app_id'], enterprise_id=enterprise).first()
    if parent is None:
        return 'absent'
    version = RainbondCenterAppVersion.objects.filter(ID=expected['id'], app_id=parent.app_id).first()
    if version is None:
        return 'absent'
    current = {
        'id': version.ID,
        'app_id': version.app_id,
        'version': version.version,
        'content_hash': template_fingerprint(version.app_template, key),
        'activation_revision': version.cleanup_activation_revision,
    }
    if version.enterprise_id != enterprise or version.region_name != region:
        raise RetirementConflict()
    return inspect_template_identity(current, expected)


def inspect_build_version_record(enterprise: str, region: str, expected: dict[str, Any]) -> str:
    from www.models.main import Tenants, TenantServiceInfo
    from www.apiclient.regionapi import RegionInvokeApi
    component = TenantServiceInfo.objects.get(service_id=expected['service_id'], service_region=region)
    tenant = Tenants.objects.get(tenant_id=component.tenant_id, enterprise_id=enterprise)
    response = RegionInvokeApi().inspect_service_build_version(
        region, tenant.tenant_name, component.service_alias, expected['version'], expected)
    result = (response or {}).get('bean') or {}
    state = result.get('record_state')
    if state not in ('present', 'absent'):
        raise RetirementConflict()
    return state


def retire_template(enterprise: str, region: str, expected: dict, key: bytes) -> dict:
    from django.db import transaction
    from django.db.models import Q
    from console.models.main import RainbondCenterApp, RainbondCenterAppVersion, AppUpgradeRecord, AppVersionTemplateRelation
    from www.models.main import TenantServiceGroup

    with transaction.atomic():
        # Parent lock also fences new market installations of this model/version.
        parent = RainbondCenterApp.objects.select_for_update().get(app_id=expected['app_id'], enterprise_id=enterprise)
        version = RainbondCenterAppVersion.objects.select_for_update().get(ID=expected['id'], app_id=parent.app_id)
        latest = RainbondCenterAppVersion.objects.filter(app_id=parent.app_id).order_by('-ID').first()
        state = {
            'id': version.ID, 'app_id': version.app_id, 'version': version.version,
            'content_hash': template_fingerprint(version.app_template, key),
            'activation_revision': version.cleanup_activation_revision,
            'managed': (version.enterprise_id == enterprise and version.region_name == region
                        and version.source == 'local' and version.is_complete),
            'current': latest is None or latest.ID == version.ID,
            'referenced': (TenantServiceGroup.objects.filter(group_key=version.app_id, group_version=version.version).exists()
                           or (version.app_id, version.version) in snapshot_template_bindings(enterprise)),
            'active_operation': AppUpgradeRecord.objects.filter(group_key=version.app_id).filter(
                Q(version=version.version) | Q(old_version=version.version)).filter(status__in=[0, 1, 2, 4]).exists(),
        }
        if AppVersionTemplateRelation.objects.filter(app_model_id=parent.app_id).exists():
            state['managed'] = False
        validate_template_retirement(state, expected)
        version.delete()
    return {'record_retired': True, 'image_deleted': False, 'reclaimed_bytes': None}


def retire_build_version(enterprise: str, region: str, expected: dict, actor: str, operation_id: str) -> dict:
    from django.db import transaction
    from console.models.main import ServiceUpgradeRecord
    from www.models.main import Tenants, TenantServiceInfo
    from www.apiclient.regionapi import RegionInvokeApi

    with transaction.atomic():
        component = TenantServiceInfo.objects.select_for_update().get(
            service_id=expected['service_id'], service_region=region)
        tenant = Tenants.objects.get(tenant_id=component.tenant_id, enterprise_id=enterprise)
        if (ServiceUpgradeRecord.objects.filter(service=component, status__in=[1, 2, 4]).exists()
                or component.service_id in snapshot_protected_components(enterprise)):
            raise RetirementConflict()
        api = RegionInvokeApi()
        command = dict(expected, operator='cleanup:' + actor, operation_id=operation_id)
        response = api.retire_service_build_version(
            region, tenant.tenant_name, component.service_alias, expected['version'], command)
        result = (response or {}).get('bean') or {}
        if result.get('record_retired') is not True or result.get('image_deleted') is not False:
            raise RetirementConflict()
        return {'record_retired': True, 'image_deleted': False, 'reclaimed_bytes': None}


@contextmanager
def lock_template_use(app_id: str, version: str, region_name: str, tenant_name: str,
                      external_template: dict[str, Any] | None = None) -> Iterator[None]:
    """Fence template retirement against a new installation reference."""
    from django.db import transaction
    from www.apiclient.regionapi import RegionInvokeApi
    from console.services.cleanup_coordination import protect_references, template_reference_scopes
    from console.models.main import RainbondCenterApp, RainbondCenterAppVersion
    with transaction.atomic():
        versions = []
        if external_template is None:
            parents = list(RainbondCenterApp.objects.select_for_update().filter(app_id=app_id).order_by('ID'))
            if not parents:
                raise RetirementConflict()
            versions = list(RainbondCenterAppVersion.objects.select_for_update().filter(
                app_id=app_id, version=version).order_by('ID'))
            if not versions:
                raise RetirementConflict()
            raw_templates = [item.app_template for item in versions]
        else:
            # Cloud-market models are transient Django objects and are intentionally
            # not stored in the local template tables. Protect their image references
            # without treating the missing local rows as retirement.
            raw_templates = [json.dumps(external_template, default=str)]
        api = RegionInvokeApi()
        scopes = template_reference_scopes(raw_templates)

        def invoke(action, storage, body):
            return api.cleanup_reference_operation(region_name, tenant_name, action, storage, body)
        with protect_references(invoke, scopes, transaction.on_commit):
            if versions:
                RainbondCenterAppVersion.objects.filter(ID__in=[item.ID for item in versions]).update(
                    cleanup_activation_revision=uuid.uuid4().hex)
            yield


def template_retirement_targets(enterprise: str, region: str, rows: list[dict], key: bytes) -> dict[int, dict]:
    """Return record-only targets, never infer that underlying images are unused."""
    from console.models.main import RainbondCenterApp, RainbondCenterAppVersion, AppVersionTemplateRelation, AppUpgradeRecord
    from www.models.main import TenantServiceGroup
    app_ids = {row['app_id'] for row in rows}
    owned = set(RainbondCenterApp.objects.filter(app_id__in=app_ids, enterprise_id=enterprise).values_list('app_id', flat=True))
    hidden = set(AppVersionTemplateRelation.objects.filter(app_model_id__in=app_ids).values_list('app_model_id', flat=True))
    bindings = set(TenantServiceGroup.objects.filter(group_key__in=app_ids).values_list('group_key', 'group_version'))
    bindings.update(snapshot_template_bindings(enterprise))
    active = set()
    for app_key, version, old in AppUpgradeRecord.objects.filter(group_key__in=app_ids, status__in=[0, 1, 2, 4]).values_list(
            'group_key', 'version', 'old_version'):
        active.update([(app_key, version), (app_key, old)])
    ranks: dict[int, int] = {}
    counters: dict[str, int] = {}
    versions = RainbondCenterAppVersion.objects.filter(app_id__in=app_ids).order_by('-ID').values_list('ID', 'app_id')
    for identifier, app_id in versions:
        counters[app_id] = counters.get(app_id, 0) + 1
        ranks[identifier] = counters[app_id]
    result = {}
    for row in rows:
        app_id, version = row['app_id'], row['version']
        if (app_id not in owned or app_id in hidden or row.get('enterprise_id') != enterprise
                or row.get('region_name') != region or row.get('source') != 'local' or not row.get('is_complete')
                or ranks.get(row['ID'], 0) <= 1 or (app_id, version) in bindings or (app_id, version) in active):
            continue
        result[row['ID']] = {'protocol': 1, 'kind': 'template_version', 'rank': ranks[row['ID']], 'expected': {
            'id': row['ID'], 'app_id': app_id, 'version': version,
            'content_hash': template_fingerprint(row.get('app_template') or '', key),
            'activation_revision': row.get('cleanup_activation_revision') or '',
        }}
    return result


def snapshot_component_ids(raw: str) -> set[str]:
    """Legacy snapshots do not always record an authoritative runtime version.

    Protect all build records of their components rather than guessing which
    historical build is needed to restore a retained snapshot.
    """
    import json
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        raise RetirementConflict() from None
    if not isinstance(data, dict) or not isinstance(data.get('components'), list):
        raise RetirementConflict()
    identifiers = set()
    for component in data['components']:
        if not isinstance(component, dict) or not isinstance(component.get('service_base'), dict):
            raise RetirementConflict()
        identifier = component['service_base'].get('service_id')
        if not isinstance(identifier, str) or not identifier:
            raise RetirementConflict()
        identifiers.add(identifier)
    return identifiers


def snapshot_protected_components(enterprise: str) -> set[str]:
    from console.models.main import AppUpgradeSnapshot
    from www.models.main import Tenants
    teams = Tenants.objects.filter(enterprise_id=enterprise).values_list('tenant_id', flat=True)
    protected: set[str] = set()
    for raw in AppUpgradeSnapshot.objects.filter(tenant_id__in=teams).values_list('snapshot', flat=True).iterator(chunk_size=20):
        protected.update(snapshot_component_ids(raw))
    return protected


def snapshot_template_bindings(enterprise: str) -> set[tuple[str, str]]:
    import json
    from console.models.main import AppUpgradeSnapshot
    from www.models.main import Tenants
    teams = Tenants.objects.filter(enterprise_id=enterprise).values_list('tenant_id', flat=True)
    bindings: set[tuple[str, str]] = set()
    for raw, group_id in AppUpgradeSnapshot.objects.filter(tenant_id__in=teams).values_list(
            'snapshot', 'upgrade_group_id').iterator(chunk_size=20):
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            raise RetirementConflict() from None
        if not isinstance(data, dict) or not isinstance(data.get('component_group'), dict):
            raise RetirementConflict()
        group = data['component_group']
        if not group_id:
            continue  # Hidden application snapshots are protected separately.
        if not isinstance(group.get('group_key'), str) or not isinstance(group.get('group_version'), str):
            raise RetirementConflict()
        bindings.add((group['group_key'], group['group_version']))
    return bindings
