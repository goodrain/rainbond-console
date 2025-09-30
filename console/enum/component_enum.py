# -*- coding: utf-8 -*-
from enum import Enum


class ComponentType(Enum):
    stateless_singleton = "stateless_singleton"
    stateless_multiple = "stateless_multiple"
    state_singleton = "state_singleton"
    state_multiple = "state_multiple"
    job = "job"
    cronjob = "cronjob"
    vm = "vm"
    kubeblocks = "kubeblocks_component"

    @staticmethod
    def to_zh(key):
        if key == "stateless_singleton":
            return "无状态单实例"
        if key == "stateless_multiple":
            return "无状态多实例"
        if key == "state_singleton":
            return "有状态单实例"
        if key == "state_multiple":
            return "有状态多实例"
        if key == "kubeblocks_component":
            return "KubeBlocks 组件"


def is_state(component_type):
    if component_type == ComponentType.state_singleton.value or component_type == ComponentType.state_multiple.value:
        return True
    return False


def is_singleton(component_type):
    if component_type == ComponentType.state_singleton.value or component_type == ComponentType.stateless_singleton.value:
        return True
    return False


def is_kubeblocks(component_type):
    return component_type == ComponentType.kubeblocks.value


def is_support(component_type):
    if component_type == ComponentType.state_singleton.value \
            or component_type == ComponentType.stateless_singleton.value \
            or component_type == ComponentType.stateless_multiple.value \
            or component_type == ComponentType.state_multiple.value \
            or component_type == ComponentType.job.value \
            or component_type == ComponentType.cronjob.value \
            or component_type == ComponentType.kubeblocks.value:
        return True

    return False


class ComponentSource(Enum):
    THIRD_PARTY = "third_party"
