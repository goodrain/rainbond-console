# -*- coding: utf-8 -*-
from enum import IntEnum


class ComponentType(IntEnum):
    stateless_singleton = 0
    stateless_multiple = 1
    state_singleton = 2
    state_multiple = 3


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
