# -*- coding: utf-8 -*-
import http.client
import os
from urllib.parse import urlparse

import pytest
import urllib3

os.environ["DISABLE_FIRST_DEPLOY_SWEEPER"] = "1"
os.environ["RAINBOND_TELEMETRY_DISABLED"] = "1"
os.environ["RAINBOND_ERROR_REPORTING_DISABLED"] = "1"

_LOCAL_TEST_HOSTS = {"127.0.0.1", "localhost", "::1"}
_BLOCKED_EXTERNAL_HTTP_REQUESTS = []
_ORIGINAL_HTTP_CONNECTION_CONNECT = http.client.HTTPConnection.connect
_ORIGINAL_HTTP_CONNECTION_PUTREQUEST = http.client.HTTPConnection.putrequest
_ORIGINAL_URLLIB3_HTTP_CONNECTION_CONNECT = urllib3.connection.HTTPConnection.connect
_ORIGINAL_URLLIB3_HTTPS_CONNECTION_CONNECT = urllib3.connection.HTTPSConnection.connect
_ORIGINAL_URLLIB3_HTTP_CONNECTION_POOL_URLOPEN = urllib3.connectionpool.HTTPConnectionPool.urlopen


def _assert_local_test_host(connection):
    _assert_local_test_hostname(connection.host)


def _assert_local_test_hostname(hostname):
    hostname = hostname.strip("[]").lower()
    if hostname not in _LOCAL_TEST_HOSTS:
        _BLOCKED_EXTERNAL_HTTP_REQUESTS.append(None)
        raise RuntimeError("external HTTP requests are disabled during tests")


def _block_external_http_requests(connection):
    _assert_local_test_host(connection)
    return _ORIGINAL_HTTP_CONNECTION_CONNECT(connection)


def _block_external_http_request_target(connection, method, url, *args, **kwargs):
    hostname = urlparse(url).hostname
    if hostname:
        _assert_local_test_hostname(hostname)
    return _ORIGINAL_HTTP_CONNECTION_PUTREQUEST(connection, method, url, *args, **kwargs)


def _block_external_urllib3_http_requests(connection):
    _assert_local_test_host(connection)
    return _ORIGINAL_URLLIB3_HTTP_CONNECTION_CONNECT(connection)


def _block_external_urllib3_https_requests(connection):
    _assert_local_test_host(connection)
    return _ORIGINAL_URLLIB3_HTTPS_CONNECTION_CONNECT(connection)


def _block_external_urllib3_http_requests_through_proxy(pool, method, url, *args, **kwargs):
    hostname = urlparse(url).hostname or pool.host
    _assert_local_test_hostname(hostname)
    return _ORIGINAL_URLLIB3_HTTP_CONNECTION_POOL_URLOPEN(pool, method, url, *args, **kwargs)


def blocked_external_http_request_count():
    return len(_BLOCKED_EXTERNAL_HTTP_REQUESTS)


def fail_for_blocked_external_http_requests_since(start_count):
    blocked_count = len(_BLOCKED_EXTERNAL_HTTP_REQUESTS) - start_count
    if blocked_count <= 0:
        return
    del _BLOCKED_EXTERNAL_HTTP_REQUESTS[start_count:]
    pytest.fail("{} external HTTP request(s) blocked during test".format(blocked_count))


@pytest.fixture(autouse=True)
def fail_for_blocked_external_http_requests():
    start_count = blocked_external_http_request_count()
    yield
    fail_for_blocked_external_http_requests_since(start_count)


def pytest_sessionfinish(session, exitstatus):
    if not _BLOCKED_EXTERNAL_HTTP_REQUESTS:
        return
    session.exitstatus = pytest.ExitCode.TESTS_FAILED


http.client.HTTPConnection.connect = _block_external_http_requests
http.client.HTTPConnection.putrequest = _block_external_http_request_target
urllib3.connection.HTTPConnection.connect = _block_external_urllib3_http_requests
urllib3.connection.HTTPSConnection.connect = _block_external_urllib3_https_requests
urllib3.connectionpool.HTTPConnectionPool.urlopen = _block_external_urllib3_http_requests_through_proxy

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
