# -*- coding: utf8 -*-
import logging
from typing import Any, Optional

from .component import Component

logger = logging.getLogger("default")


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
