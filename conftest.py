# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse

import pytest
import requests

os.environ["DISABLE_FIRST_DEPLOY_SWEEPER"] = "1"
os.environ["RAINBOND_TELEMETRY_DISABLED"] = "1"
os.environ["RAINBOND_ERROR_REPORTING_DISABLED"] = "1"

_LOCAL_TEST_HOSTS = {"127.0.0.1", "localhost"}
_ORIGINAL_SESSION_SEND = requests.sessions.Session.send


def _block_external_http_requests(session, request, **kwargs):
    hostname = urlparse(request.url).hostname
    if hostname not in _LOCAL_TEST_HOSTS:
        raise RuntimeError("external HTTP requests are disabled during tests")
    return _ORIGINAL_SESSION_SEND(session, request, **kwargs)


requests.sessions.Session.send = _block_external_http_requests

OPENAPI_CLIENT_TEST_DIRS = (
    os.path.join("src", "openapi-client", "test"),
    os.path.join("src", "openapi-client", "client", "python", "v1", "test"),
)


def pytest_collection_modifyitems(config, items):
    repo_root = os.path.dirname(os.path.abspath(__file__))
    marker = pytest.mark.xfail(
        reason="generated OpenAPI client test stubs are not executable",
        strict=False,
    )
    for item in items:
        relpath = os.path.relpath(str(item.fspath), repo_root)
        if relpath.startswith(OPENAPI_CLIENT_TEST_DIRS):
            item.add_marker(marker)
