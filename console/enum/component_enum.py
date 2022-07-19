# -*- coding: utf-8 -*-
from enum import Enum


class ComponentType(Enum):
    stateless_singleton = "stateless_singleton"
    stateless_multiple = "stateless_multiple"
    state_singleton = "state_singleton"
    state_multiple = "state_multiple"
    job = "job"
    cronjob = "cronjob"


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
            or component_type == ComponentType.state_multiple.value \
            or component_type == ComponentType.job.value \
            or component_type == ComponentType.cronjob.value:
        return True

    return False


class ComponentSource(Enum):
    THIRD_PARTY = "third_party"
