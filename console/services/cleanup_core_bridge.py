"""Signed, bounded access to an explicit set of cleanup coordination operations."""
import hashlib
import hmac
import json
import re
import time

_ID = r'[A-Za-z0-9_.:-]{1,64}'
_EXACT = frozenset(('/v2/cleanup/stores/discover', '/v2/cleanup/registry/prepare', '/v2/cleanup/managed-cache/prepare',
                    '/v2/cleanup/managed-cache/inventory', '/v2/cleanup/managed-packages/prepare'))
_STORE_ACTIONS = frozenset(
    ('operations', 'status', 'observation-permit', 'reference-inventory', 'participants/registry', 'uploads/lookup'))
_OPERATION_ACTIONS = frozenset(
    ('registry-permit', 'registry-references', 'attempt', 'attempt/complete', 'upload', 'upload/requests',
     'upload/requests/finish', 'finish', 'inspect', 'maintenance/request', 'maintenance/enter', 'maintenance/enter-job',
     'maintenance/job', 'maintenance/job/start', 'maintenance/job/restore', 'maintenance/job/status',
     'maintenance/job/cancel-failed', 'maintenance/cancel', 'maintenance/complete', 'maintenance/measurement',
     'maintenance/restore', 'maintenance/restored', 'node/cancel-before-grant', 'node/submit-job', 'node/start-job',
     'node/enter-job', 'node/result', 'node/finish', 'node/status', 'node/recover'))


def allowed_core_path(path: str) -> bool:
    if not isinstance(path, str) or len(path) > 512 or any(part in ('.', '..', '') for part in path[1:].split('/')):
        return False
    if path in _EXACT:
        return True
    match = re.fullmatch(r'/v2/cleanup/stores/(' + _ID + r')/(.+)', path)
    if not match:
        return False
    suffix = match.group(2)
    if suffix in _STORE_ACTIONS:
        return True
    operation = re.fullmatch(r'operations/(' + _ID + r')/(.+)', suffix)
    return bool(operation and operation.group(2) in _OPERATION_ACTIONS)


def decode_core_request(raw: bytes) -> tuple[str, bytes]:
    if not isinstance(raw, bytes) or len(raw) > 65536:
        raise ValueError('invalid coordination envelope')
    try:
        envelope = json.loads(raw)
        if (not isinstance(envelope, dict) or set(envelope) != {'path', 'body'} or not allowed_core_path(envelope['path'])
                or not isinstance(envelope['body'], str)):
            raise ValueError()
        body = envelope['body'].encode('utf-8')
        if len(body) > 16384 or not isinstance(json.loads(body), dict):
            raise ValueError()
        return envelope['path'], body
    except (ValueError, TypeError, KeyError):
        raise ValueError('invalid coordination envelope') from None


def verify_core_request(path: str,
                        enterprise: str,
                        region: str,
                        issued_at: str,
                        signature: str,
                        body: bytes,
                        key: bytes,
                        now: float | None = None) -> bool:
    if (not key or not 32 <= len(key) <= 4096 or len(body) > 65536 or not re.fullmatch(r'[0-9]{1,12}', str(issued_at or ''))
            or not re.fullmatch(r'[a-f0-9]{64}', str(signature or ''))):
        return False
    current = time.time() if now is None else now
    issued = int(issued_at)
    if issued > current + 5 or current - issued > 60:
        return False
    message = '\n'.join(('cleanup-coordination-v1', 'POST', path, enterprise, region, issued_at,
                         hashlib.sha256(body).hexdigest())).encode('utf-8')
    expected = hmac.new(key, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
