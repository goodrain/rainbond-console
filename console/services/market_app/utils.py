# -*- coding: utf8 -*-
import logging
from typing import Any, Dict, List, Optional

from .component import Component
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


def _resolve_none_value(raw_value: str, secret_groups: Dict[str, str]) -> Optional[str]:
    """Resolve a single env value. Returns the generated value, or None if the
    value is not a **None** / **None:group** placeholder.

    - ``**None**``        -> a fresh random value (``make_uuid()[:8]``)
    - ``**None:group**``  -> one shared random value per group (``make_uuid()``)
    """
    if not isinstance(raw_value, str):
        return None
    if raw_value == "**None**":
        return make_uuid()[:8]
    if raw_value.startswith("**None:") and raw_value.endswith("**"):
        group = raw_value[7:-2]
        if group not in secret_groups:
            secret_groups[group] = make_uuid()
        return secret_groups[group]
    return None


def resolve_none_placeholders(apps: List[dict]) -> None:
    """In-place resolve **None** / **None:group** env placeholders across all apps.

    Replaces matching values in each app's ``service_env_map_list`` and
    ``service_connect_info_map_list``. A single ``secret_groups`` cache is shared
    across every app so that all envs referencing the same group (e.g.
    ``**None:db_password**``) end up with the IDENTICAL value, keeping secrets
    consistent across components. Non-placeholder values are left untouched and
    missing/empty env lists are handled safely.
    """
    if not apps:
        return
    secret_groups: Dict[str, str] = {}
    for app in apps:
        if not app:
            continue
        for env_key in ("service_env_map_list", "service_connect_info_map_list"):
            envs = app.get(env_key)
            if not envs:
                continue
            for env in envs:
                if not isinstance(env, dict):
                    continue
                resolved = _resolve_none_value(env.get("attr_value") or "", secret_groups)
                if resolved is not None:
                    env["attr_value"] = resolved


def get_component_template(component: Component, app_template: dict) -> Optional[Any]:
    templates = app_template.get("apps", [])
    for tmpl in templates:
        if is_same_component(component, tmpl):
            return tmpl
    return None


def is_same_component(component: Component, tmpl: Any) -> bool:
    # 1. service_key
    if component.component.service_key == tmpl.get("service_key"):
        return True
    # 2. service_share_uuid
    # NOTE: component_source can be None -> AttributeError (latent, backlog); behavior unchanged.
    component_key = component.component_source.service_share_uuid  # type: ignore[union-attr]
    tmpl_key = tmpl.get("service_share_uuid")
    if component_key == tmpl_key:
        return True
    # 3. service_share_uuid = xxx + service_id
    # NOTE: component_key can be None -> AttributeError (latent, backlog); behavior unchanged.
    component_key_parts = component_key.split("+")  # type: ignore[union-attr]
    if len(component_key_parts) != 2:
        return False
    tmpl_key_parts = tmpl_key.split("+")
    if len(tmpl_key_parts) != 2:
        return False
    return component_key_parts[1] == tmpl_key_parts[1]
