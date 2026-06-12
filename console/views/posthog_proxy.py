# -*- coding: utf-8 -*-
import os
from urllib.parse import urlsplit, urlunsplit

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt


DEFAULT_POSTHOG_API_PROXY_TARGET = "https://posthog.goodrain.com"
DEFAULT_POSTHOG_ASSET_PROXY_TARGET = "https://posthog.goodrain.com"
REQUEST_TIMEOUT = (3, 10)

REQUEST_HEADER_MAP = {
    "CONTENT_TYPE": "Content-Type",
    "HTTP_ACCEPT": "Accept",
    "HTTP_CONTENT_ENCODING": "Content-Encoding",
    "HTTP_USER_AGENT": "User-Agent",
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


class PostHogProxyRequestError(Exception):
    pass


def _get_api_proxy_target():
    return (
        os.environ.get("RAINBOND_POSTHOG_PROXY_TARGET")
        or os.environ.get("POSTHOG_PROXY_TARGET")
        or DEFAULT_POSTHOG_API_PROXY_TARGET
    ).rstrip("/")


def _get_asset_proxy_target(api_target):
    return (
        os.environ.get("RAINBOND_POSTHOG_ASSET_PROXY_TARGET")
        or os.environ.get("POSTHOG_ASSET_PROXY_TARGET")
        or api_target
        or DEFAULT_POSTHOG_ASSET_PROXY_TARGET
    ).rstrip("/")


def _is_asset_path(path):
    request_path = (path or "").lstrip("/")
    return request_path.startswith("static/") or request_path.startswith("array/")


def _get_proxy_target(path):
    api_target = _get_api_proxy_target()
    if _is_asset_path(path):
        return _get_asset_proxy_target(api_target)
    return api_target


def _build_target_url(path, query_string):
    target = urlsplit(_get_proxy_target(path))
    if not target.scheme or not target.netloc:
        raise ValueError("invalid posthog proxy target")
    base_path = target.path.rstrip("/")
    request_path = (path or "").lstrip("/")
    merged_path = "/".join(part for part in (base_path, request_path) if part)
    target_path = "/" + merged_path if merged_path else "/"
    return urlunsplit((target.scheme, target.netloc, target_path, query_string, ""))


def _build_upstream_headers(request):
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


def _send_upstream_request(**kwargs):
    import requests
    try:
        return requests.request(**kwargs)
    except requests.RequestException as exc:
        raise PostHogProxyRequestError(str(exc))


def _add_cors_headers(response, request):
    origin = request.META.get("HTTP_ORIGIN")
    response["Access-Control-Allow-Origin"] = origin or "*"
    response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = request.META.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS") or "Content-Type"
    response["Access-Control-Max-Age"] = "3600"
    if origin:
        response["Vary"] = "Origin"
    return response


@method_decorator(csrf_exempt, name="dispatch")
class PostHogProxyView(View):
    http_method_names = ["get", "post", "options", "head"]

    def options(self, request, path=""):
        return _add_cors_headers(HttpResponse(status=204), request)

    def get(self, request, path=""):
        return self._proxy(request, path)

    def post(self, request, path=""):
        return self._proxy(request, path)

    def _proxy(self, request, path):
        try:
            target_url = _build_target_url(path, request.META.get("QUERY_STRING", ""))
        except ValueError:
            return _add_cors_headers(HttpResponse("PostHog proxy target is invalid", status=502), request)

        try:
            upstream_response = _send_upstream_request(
                method=request.method,
                url=target_url,
                headers=_build_upstream_headers(request),
                data=request.body if request.method in ("POST", "PUT", "PATCH") else None,
                timeout=REQUEST_TIMEOUT,
            )
        except PostHogProxyRequestError:
            return _add_cors_headers(HttpResponse("PostHog proxy request failed", status=502), request)

        response = HttpResponse(
            content=upstream_response.content,
            status=upstream_response.status_code,
            content_type=upstream_response.headers.get("Content-Type", ""),
        )
        for key, value in upstream_response.headers.items():
            if key.lower() not in HOP_BY_HOP_RESPONSE_HEADERS:
                response[key] = value
        return _add_cors_headers(response, request)
