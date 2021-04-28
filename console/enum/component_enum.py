# -*- coding: utf-8 -*-
from enum import Enum


class ComponentType(Enum):
    stateless_singleton = "stateless_singleton"
    stateless_multiple = "stateless_multiple"
    state_singleton = "state_singleton"
    state_multiple = "state_multiple"


def is_state(component_type):
    if component_type == ComponentType.state_singleton.value or component_type == ComponentType.state_multiple.value:
        return True
    return False


def is_singleton(component_type):
    if component_type == ComponentType.state_singleton.value or component_type == ComponentType.stateless_singleton.value:
        return True
    return False


def is_support(component_type):
    if component_type == ComponentType.state_singleton.value \
            or component_type == ComponentType.stateless_singleton.value \
            or component_type == ComponentType.stateless_multiple.value \
            or component_type == ComponentType.state_multiple.value:
        return True

    return False


class ComponentSource(Enum):
    THIRD_PARTY = "third_party"


def is_third_party(component_source):
    if component_source == ComponentSource.THIRD_PARTY.value:
        return True
    return False
