"""Platform-owned coordination identity, independent of plugin installation.

The file is a single atomically projected Secret entry. Only the platform mounts
it; neither the request nor an installed application selects the credential.
It must contain an independently generated key, never the plugin gateway key.
"""
import base64
import json
import os

from console.services.cleanup_gateway import CleanupGatewayUnavailable


def resolve_system_coordination_key(enterprise: str, region: str) -> bytes:
    from console.repositories.region_repo import region_repo

    try:
        if not region_repo.get_enterprise_region_by_region_name(enterprise, region):
            raise CleanupGatewayUnavailable()
        path = os.environ.get('CLEANUP_SYSTEM_COORDINATION_FILE', '')
        if not path or not os.path.isabs(path):
            raise CleanupGatewayUnavailable()
        with open(path, 'rb') as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise CleanupGatewayUnavailable()
        credential = json.loads(raw)
        if (not isinstance(credential, dict) or set(credential) != {'enterprise', 'region', 'key'}
                or credential['enterprise'] != enterprise or credential['region'] != region
                or not isinstance(credential['key'], str) or len(credential['key']) > 8192):
            raise CleanupGatewayUnavailable()
        key = base64.b64decode(credential['key'], validate=True)
        if not 32 <= len(key) <= 4096:
            raise CleanupGatewayUnavailable()
        return key
    except Exception:
        # No secret, filesystem path or upstream database error leaves this boundary.
        raise CleanupGatewayUnavailable() from None
