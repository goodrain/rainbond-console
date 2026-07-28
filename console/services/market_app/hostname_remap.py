# -*- coding: utf8 -*-
"""Shared hostname remap helpers.

When a component's port k8s_service_name collides with an existing service
name in the target namespace, the platform suffixes the conflicting name
(e.g. api -> api-2311). Env values and config-file content referencing the
original hostname must then be rewritten to the suffixed name. These helpers
implement the URL/DSN-aware rewrite used by both the market-install path
(console.services.market_app.new_components) and the app copy/migrate path
(console.services.groupapp_recovery.groupapps_migrate).
"""
from typing import Optional, overload


def is_host_env_name(attr_name: Optional[str]) -> bool:
    """Whether an env holds a bare hostname (``*_HOST`` / ``*_HOSTNAME`` / ``HOST``).

    Only these may have their whole value exact-matched against a colliding
    service name during hostname remap. Other envs whose value happens to
    equal a service name (e.g. Harbor's ``POSTGRESQL_DATABASE=registry``,
    which collides with the ``registry`` component) must NOT be rewritten.
    """
    if not attr_name:
        return False
    return attr_name == "HOST" or attr_name.endswith("_HOST") or attr_name.endswith("_HOSTNAME")


@overload
def apply_hostname_remap(value: str, remap: Optional[dict], is_host_env: bool = ...) -> str:
    ...


@overload
def apply_hostname_remap(value: None, remap: Optional[dict], is_host_env: bool = ...) -> None:
    ...


def apply_hostname_remap(value: Optional[str], remap: Optional[dict], is_host_env: bool = False) -> Optional[str]:
    if not value or not remap:
        return value
    for old, new in remap.items():
        # Exact whole-value match is only safe for hostname-valued envs; a
        # database name / username that merely equals a service name must be
        # left alone. URL and host:port rewrites below are unambiguous.
        if is_host_env and value == old:
            value = new
            continue
        value = value.replace("://" + old + ":", "://" + new + ":")
        value = value.replace("://" + old + "/", "://" + new + "/")
        # DSNs with userinfo credentials keep the host after an "@",
        # e.g. mongodb://user:pass@mongo:27017/db or redis://default:pass@redis:6379.
        value = value.replace("@" + old + ":", "@" + new + ":")
        value = value.replace("@" + old + "/", "@" + new + "/")
        if "://" in value and value.endswith("@" + old):
            value = value[:-len(old)] + new
        if value.startswith(old + ":") and "://" not in value:
            value = new + value[len(old):]
    return value
