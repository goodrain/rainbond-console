"""Durable Region-side protection for Console reference transactions."""
import hashlib
import json
import re
import uuid
from contextlib import contextmanager


class CoordinationUnavailable(Exception):
    pass


_IDENTITY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$')
_REPOSITORY = re.compile(r'^[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*(?:/[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*)*$')


@contextmanager
def protect_region_references(region_name, tenant_name, repositories=None):
    """Protect reference collection through the final Console database commit."""
    from django.db import transaction
    from www.apiclient.regionapi import RegionInvokeApi
    api = RegionInvokeApi()

    def invoke(action, storage, body):
        return api.cleanup_reference_operation(region_name, tenant_name, action, storage, body)

    with transaction.atomic():
        with protect_references(invoke, repositories, transaction.on_commit):
            yield


def template_reference_scopes(raw_templates):
    """Use exact repository scopes only when every component is understood."""
    scopes = set()
    try:
        for raw in raw_templates:
            template = json.loads(raw)
            if not isinstance(template, dict):
                return ['*']
            # Embedded workloads may introduce images outside apps/plugins.
            # Until every manifest type is resolved, do not claim a narrow scope.
            if template.get('k8s_resources'):
                return ['*']
            for section in ('apps', 'plugins'):
                components = template.get(section, [])
                if not isinstance(components, list):
                    return ['*']
                for component in components:
                    if not isinstance(component, dict):
                        return ['*']
                    delivery = component.get('service_image') or {}
                    if not isinstance(delivery, dict):
                        return ['*']
                    images = [component.get('share_image'), component.get('image'), delivery.get('image_url')]
                    if not any(images):
                        return ['*']
                    for image in filter(None, images):
                        if not isinstance(image, str) or '/' not in image:
                            return ['*']
                        host, target = image.split('/', 1)
                        if not re.fullmatch(r'[A-Za-z0-9.-]+(?::[0-9]+)?', host) or ('.' not in host and ':' not in host
                                                                                     and host != 'localhost'):
                            return ['*']
                        if '@' in target:
                            target, digest = target.split('@', 1)
                            if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
                                return ['*']
                        if ':' in target:
                            target, tag = target.rsplit(':', 1)
                            if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', tag):
                                return ['*']
                        if len(target) > 255 or not _REPOSITORY.fullmatch(target):
                            return ['*']
                        scopes.add(target)
    except (ValueError, TypeError):
        return ['*']
    return sorted(scopes) if scopes and len(scopes) <= 256 else ['*']


def _response(value):
    bean = value.get('bean') if isinstance(value, dict) else None
    if not isinstance(bean, dict) or type(bean.get('protocol')) is not int or bean['protocol'] != 1:
        raise CoordinationUnavailable('cleanup coordination response is invalid')
    return bean


@contextmanager
def protect_references(api, repositories, on_commit):
    """Keep admission until the outermost database transaction commits.

    There is no TTL or retry of ambiguous admission. If commit never happens,
    the durable Region operation remains protective for later reconciliation.
    """
    scopes = repositories or ['*']
    if not isinstance(scopes, (list, tuple)) or len(scopes) > 256:
        raise CoordinationUnavailable('cleanup reference scope is invalid')
    for scope in scopes:
        if not isinstance(scope, str) or len(scope) > 255 or (scope != '*' and not _REPOSITORY.fullmatch(scope)):
            raise CoordinationUnavailable('cleanup reference scope is invalid')
    scopes = sorted(set(scopes))

    def invoke(action, storage, body):
        try:
            return _response(api(action, storage, body))
        except Exception:
            raise CoordinationUnavailable('cleanup coordination request was not acknowledged') from None

    stores = invoke('discover', '', {}).get('stores')
    if not isinstance(stores, list) or len(stores) > 64:
        raise CoordinationUnavailable('cleanup storage discovery is incomplete')
    seen = set()
    for store in stores:
        if not isinstance(store, dict) or any(not isinstance(store.get(k), str) or not _IDENTITY.fullmatch(store[k])
                                              for k in ('storage_id', 'generation')):
            raise CoordinationUnavailable('cleanup storage identity is invalid')
        if store['storage_id'] in seen:
            raise CoordinationUnavailable('cleanup storage identity is duplicated')
        seen.add(store['storage_id'])
    owner = 'console-reference:' + uuid.uuid4().hex
    leases = []

    def finish(confirmed):
        failed = False
        for storage, request in leases:
            try:
                bean = invoke('finish', storage, dict(request, confirmed=confirmed))
                if bean.get('recorded') is not True:
                    failed = True
            except Exception:
                failed = True
        if failed:
            raise CoordinationUnavailable('cleanup reference completion was not acknowledged')

    try:
        for store in sorted(stores, key=lambda item: item['storage_id']):
            for scope in scopes:
                request = dict(generation=store['generation'],
                               owner=owner,
                               operation_id=uuid.uuid4().hex,
                               kind='producer',
                               scope=scope)
                request['fingerprint'] = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
                # Register the original identity before transport: a lost response
                # may still mean that Region durably admitted this operation.
                leases.append((store['storage_id'], request))
                if invoke('acquire', store['storage_id'], request).get('newly_admitted') is not True:
                    raise CoordinationUnavailable('cleanup reference admission was not confirmed')
        yield
    except BaseException:
        try:
            finish(False)
        except CoordinationUnavailable:
            pass  # Never replace the primary failure or claim a successful release.
        raise
    else:
        on_commit(lambda: finish(True))
