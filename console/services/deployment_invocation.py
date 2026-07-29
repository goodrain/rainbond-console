from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class DeploymentInvocation:
    origin: str = "unknown"
    client: str = "unknown"


_DEFAULT_INVOCATION = DeploymentInvocation()
_deployment_invocation: ContextVar[DeploymentInvocation] = ContextVar("deployment_invocation", default=_DEFAULT_INVOCATION)


def get_deployment_invocation() -> DeploymentInvocation:
    return _deployment_invocation.get()


def is_rainskills_invocation() -> bool:
    return get_deployment_invocation().origin == "rainskills"


@contextmanager
def deployment_invocation_context(origin: str = "unknown", client: str = "unknown") -> Iterator[DeploymentInvocation]:
    invocation = DeploymentInvocation(origin=origin, client=client)
    token = _deployment_invocation.set(invocation)
    try:
        yield invocation
    finally:
        _deployment_invocation.reset(token)
