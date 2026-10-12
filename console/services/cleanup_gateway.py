"""Trusted request context for the disk-cleanup plugin only.

The browser never receives the signing key. Values are read from server context,
not from caller-provided identity headers.
"""
import base64
import hashlib
import hmac
import json
import re
import time
from urllib.parse import quote


class CleanupAccessDenied(Exception):
    pass


class CleanupGatewayUnavailable(Exception):
    pass


def prepare_cleanup_request(request, region_name, file_path, is_admin, region_allowed, key, now=None):
    for name in list(request.META):
        if name.startswith("HTTP_X_CLEANUP_"):
            del request.META[name]
    if not is_admin or not region_allowed:
        raise CleanupAccessDenied()
    if not key or len(key) < 32:
        raise CleanupGatewayUnavailable()
    if not re.fullmatch(r"api/v1/[A-Za-z0-9_.\-/]+", file_path) or any(
            part in ("", ".", "..") for part in file_path.split("/")):
        raise CleanupAccessDenied()
    actor = str(getattr(request.user, "user_id", "") or "")
    enterprise = str(getattr(request.user, "enterprise_id", "") or "")
    if not actor or not enterprise or not region_name:
        raise CleanupAccessDenied()
    length = request.META.get("CONTENT_LENGTH", "")
    if length and (not str(length).isdigit() or len(str(length)) > 10 or int(length) > 1 << 20):
        raise CleanupAccessDenied()
    body = request.body
    if len(body) > 1 << 20:
        raise CleanupAccessDenied()
    path = "/" + quote(file_path, safe="/-._~")
    query = request.META.get("QUERY_STRING", "")
    if query:
        path += "?" + query
    payload = {
        "issuer": "rainbond-console", "actor": actor, "enterprise": enterprise,
        "region": region_name, "permission": "cluster-admin", "method": request.method.upper(),
        "path": path, "bodyHash": hashlib.sha256(body).hexdigest(),
        "requestKey": request.META.get("HTTP_IDEMPOTENCY_KEY", ""),
        "issuedAt": int(time.time() if now is None else now),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=")
    request.META["HTTP_X_CLEANUP_CONTEXT"] = encoded.decode("ascii")
    request.META["HTTP_X_CLEANUP_SIGNATURE"] = hmac.new(key, encoded, hashlib.sha256).hexdigest()
