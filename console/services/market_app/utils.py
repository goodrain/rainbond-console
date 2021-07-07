# -*- coding: utf8 -*-
from .component import Component


def get_component_template(component: Component, app_template):
    templates = app_template.get("apps", [])
    for tmpl in templates:
        if is_same_component(component, tmpl):
            return tmpl
    return None


def is_same_component(component: Component, tmpl):
    # 1. service_key
    if component.component.service_key == tmpl.get("service_key"):
        return True
    # 2. service_share_uuid
    component_key = component.component_source.service_share_uuid
    tmpl_key = tmpl.get("service_share_uuid")
    if component_key == tmpl_key:
        return True
    # 3. service_share_uuid = xxx + service_id
    component_key = component_key.split("+")
    if len(component_key) != 2:
        return False
    tmpl_key = tmpl_key.split("+")
    if len(tmpl_key) != 2:
        return False
    return component_key[1] == tmpl_key[1]
