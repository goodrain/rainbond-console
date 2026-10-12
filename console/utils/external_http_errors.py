# -*- coding: utf-8 -*-
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import SSLError, Timeout


def is_retryable_external_http_error(exc):
    return isinstance(exc, (RequestsConnectionError, SSLError, Timeout))


def get_external_http_url(exc):
    request = getattr(exc, "request", None)
    return getattr(request, "url", "") or ""
