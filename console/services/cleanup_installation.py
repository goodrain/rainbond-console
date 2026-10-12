"""Resolve plugin-owned authentication through the existing authenticated Region API.

Secret values stay server-side; never return them from an installation response.
"""
import base64
import copy
import binascii
import os
from typing import Any

from console.services.cleanup_gateway import CleanupGatewayUnavailable


def gateway_secret_name() -> str:
    return "rainbond-disk-gateway"


def decode_gateway_secret(secret: dict, namespace: str, enterprise: str, region: str) -> bytes:
    metadata = secret.get("metadata") or {}
    annotations = metadata.get("annotations") or {}
    if (metadata.get("name") != gateway_secret_name() or metadata.get("namespace") != namespace
            or annotations.get("cleanup.rainbond.io/enterprise") != enterprise
            or annotations.get("cleanup.rainbond.io/region") != region):
        raise CleanupGatewayUnavailable()
    try:
        encoded = (secret.get("data") or {}).get("key", "")
        if not isinstance(encoded, str) or len(encoded) > 8192:
            raise ValueError()
        key = base64.b64decode(encoded, validate=True).strip()
    except (ValueError, TypeError, binascii.Error):
        raise CleanupGatewayUnavailable() from None
    if not 32 <= len(key) <= 4096:
        raise CleanupGatewayUnavailable()
    return key


def resolve_gateway_key(enterprise: str, region: str) -> bytes:
    """An installed app owned by this enterprise is required, even for legacy keys."""
    from console.repositories.region_repo import region_repo
    from console.repositories.region_app import region_app_repo
    from www.apiclient.regionapi import RegionInvokeApi
    from www.models.main import ServiceGroup, Tenants

    try:
        if not region_repo.get_enterprise_region_by_region_name(enterprise, region):
            raise CleanupGatewayUnavailable()
        api = RegionInvokeApi()
        _, body = api.list_plugins(enterprise, region, False)
        plugins = [p for p in (body or {}).get("list", []) if p.get("name") == "rainbond-disk"]
        if len(plugins) != 1 or not plugins[0].get("region_app_id"):
            raise CleanupGatewayUnavailable()
        app_id = region_app_repo.get_app_id(region, plugins[0]["region_app_id"])
        app = ServiceGroup.objects.get(ID=app_id, region_name=region)
        tenant = Tenants.objects.get(tenant_id=app.tenant_id, enterprise_id=enterprise)
        # Explicit legacy deployments continue to work; automatic installations need no Console env.
        key_path = os.environ.get("CLEANUP_GATEWAY_KEY_FILE", "")
        if key_path:
            with open(key_path, "rb") as stream:
                key = stream.read(4097).strip()
            if not 32 <= len(key) <= 4096:
                raise CleanupGatewayUnavailable()
            return key
        _, response = api.get_tenant_ns_resource(region, tenant.tenant_name, gateway_secret_name(),
                                                 {"group": "", "version": "v1", "resource": "secrets"})
        return decode_gateway_secret((response or {}).get("bean") or {}, tenant.namespace, enterprise, region)
    except Exception:
        # Region exceptions may contain upstream response bodies; never expose them.
        raise CleanupGatewayUnavailable() from None


def configure_installation(tenant: Any, region: Any, backend: Any) -> None:
    """Inject only non-secret scope/defaults; the plugin creates its own key."""
    from console.services.app_config import env_var_service

    import yaml
    from console.services.k8s_attribute import k8s_attribute_service

    attributes = k8s_attribute_service.get_by_component_ids_and_name(backend.service_id, "volumes")
    if attributes:
        attribute = attributes[0]
        raw = attribute.attribute_value
        volumes = yaml.safe_load(raw) if isinstance(raw, str) else raw
        if not isinstance(volumes, list):
            raise CleanupGatewayUnavailable()
        updated = bootstrap_volumes(volumes)
        if updated != volumes:
            k8s_attribute_service.update_k8s_attribute(tenant, backend, region.region_name, {
                "name": "volumes", "save_type": "yaml", "attribute_value": yaml.safe_dump(updated),
                "operator": "plugin-install"})

    defaults = {
        "REGION_NAME": region.region_name,
        "CLEANUP_SOURCE_ENTERPRISE_ID": tenant.enterprise_id,
        "CLEANUP_AUTO_BOOTSTRAP": "true",
        "CLEANUP_CONSOLE_URL": "http://rbd-app-ui.rbd-system.svc.cluster.local:7070",
        "CLEANUP_CONSOLE_ALLOW_HTTP": "true",
    }
    for name, value in defaults.items():
        existing = env_var_service.get_env_by_attr_name(tenant, backend, name)
        if existing and name in ("CLEANUP_CONSOLE_URL", "CLEANUP_CONSOLE_ALLOW_HTTP"):
            continue  # Keep explicitly configured remote Console addresses.
        if existing and existing.attr_value == value:
            continue
        if existing:
            code, _, _ = env_var_service.update_env_by_env_id(tenant, backend, str(existing.ID), name, value, "plugin-install")
        else:
            code, _, _ = env_var_service.add_service_env_var(
                tenant=tenant, service=backend, container_port=0, name=name, attr_name=name,
                attr_value=value, is_change=True, scope="inner", user_name="plugin-install")
        if code != 200:
            raise CleanupGatewayUnavailable()


def bootstrap_volumes(volumes: list[dict]) -> list[dict]:
    """Only defer the gateway mount; other credentials must still fail closed."""
    result = copy.deepcopy(volumes)
    for volume in result:
        secret = volume.get("secret") or {}
        if secret.get("secretName") in (gateway_secret_name(), "rainbond-disk-cleanup-gateway"):
            secret["optional"] = True
    return result
