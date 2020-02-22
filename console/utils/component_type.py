# -*- coding: utf8 -*-

stateless_singleton = "stateless_singleton"
stateless_multiple = "stateless_multiple"
state_singleton = "state_singleton"
state_multiple = "state_multiple"


# singleton component or not
def is_singleton(component_type):
    if component_type == stateless_singleton or component_type == state_singleton:
        return True
    return False


# state component or not
def is_state(component_type):
    if component_type == state_singleton or component_type == state_multiple:
        return True
    return False
