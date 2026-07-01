# -*- coding: utf-8 -*-
import os

import pytest

os.environ.setdefault("DISABLE_FIRST_DEPLOY_SWEEPER", "1")

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
