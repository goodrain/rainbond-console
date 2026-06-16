# -*- coding: utf-8 -*-
import os
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt


DEFAULT_SENTRY_PROXY_TARGET = "https://sentry.goodrain.com"
REQUEST_TIMEOUT = (3, 10)
ENVELOPE_PATH_RE = re.compile(r"(^|.*/)api/\d+/envelope/?$")

REQUEST_HEADER_MAP = {
    "CONTENT_TYPE": "Content-Type",
    "HTTP_ACCEPT": "Accept",
    "HTTP_CONTENT_ENCODING": "Content-Encoding",
    "HTTP_USER_AGENT": "User-Agent",
    "HTTP_X_SENTRY_AUTH": "X-Sentry-Auth",
}

HOP_BY_HOP_RESPONSE_HEADERS = (
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
)


class SentryProxyRequestError(Exception):
    pass


def _get_proxy_target() -> str:
    return (
        os.environ.get("RAINBOND_SENTRY_PROXY_TARGET")
        or os.environ.get("RAINBOND_ERROR_REPORTING_PROXY_TARGET")
        or os.environ.get("SENTRY_PROXY_TARGET")
        or DEFAULT_SENTRY_PROXY_TARGET
    ).rstrip("/")


def _validate_envelope_path(path: str) -> str:
    request_path = (path or "").lstrip("/")
    if not ENVELOPE_PATH_RE.match(request_path):
        raise ValueError("invalid sentry envelope path")
    return request_path


def _build_target_url(path: str, query_string: str) -> str:
    request_path = _validate_envelope_path(path)
    target = urlsplit(_get_proxy_target())
    if not target.scheme or not target.netloc:
        raise ValueError("invalid sentry proxy target")
    base_path = target.path.strip("/")
    merged_path = "/".join(part for part in (base_path, request_path) if part)
    target_path = "/" + merged_path if merged_path else "/"
    return urlunsplit((target.scheme, target.netloc, target_path, query_string, ""))


def _build_upstream_headers(request: Any) -> dict:
    headers = {}
    for meta_key, header_name in REQUEST_HEADER_MAP.items():
        value = request.META.get(meta_key)
        if value:
            headers[header_name] = value
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    headers["X-Forwarded-Proto"] = request.scheme
    return headers


def _send_upstream_request(**kwargs: Any) -> Any:
    import requests
    try:
        return requests.request(**kwargs)
    except requests.RequestException as exc:
        raise SentryProxyRequestError(str(exc))


def _add_cors_headers(response: HttpResponse, request: Any) -> HttpResponse:
    origin = request.META.get("HTTP_ORIGIN")
    response["Access-Control-Allow-Origin"] = origin or "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = request.META.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS") or "Content-Type"
    response["Access-Control-Max-Age"] = "3600"
    if origin:
        response["Vary"] = "Origin"
    return response


@method_decorator(csrf_exempt, name="dispatch")
class SentryProxyView(View):
    http_method_names = ["post", "options"]

    def options(self, request: Any, path: str = "") -> HttpResponse:
        return _add_cors_headers(HttpResponse(status=204), request)

    def post(self, request: Any, path: str = "") -> HttpResponse:
        try:
            target_url = _build_target_url(path, request.META.get("QUERY_STRING", ""))
        except ValueError:
            return _add_cors_headers(HttpResponse("Sentry proxy target is invalid", status=502), request)

        try:
            upstream_response = _send_upstream_request(
                method=request.method,
                url=target_url,
                headers=_build_upstream_headers(request),
                data=request.body,
                timeout=REQUEST_TIMEOUT,
            )
        except SentryProxyRequestError:
            return _add_cors_headers(HttpResponse("Sentry proxy request failed", status=502), request)

        response = HttpResponse(
            content=upstream_response.content,
            status=upstream_response.status_code,
            content_type=upstream_response.headers.get("Content-Type", ""),
        )
        for key, value in upstream_response.headers.items():
            if key.lower() not in HOP_BY_HOP_RESPONSE_HEADERS:
                response[key] = value
        return _add_cors_headers(response, request)
