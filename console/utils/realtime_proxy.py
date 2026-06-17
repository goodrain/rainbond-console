# -*- coding: utf-8 -*-
import logging
import os

import requests
from django.http import HttpResponse, HttpResponseBadRequest, StreamingHttpResponse

from console.repositories.region_repo import region_repo

logger = logging.getLogger("default")

REALTIME_PROXY_PATH = "/console/regions/{region_name}/websocket"

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _strip_slashes(value):
    return (value or "").strip("/")


def normalize_proxy_path(proxy_path):
    proxy_path = _strip_slashes(proxy_path)
    if not proxy_path:
        return ""
    return "/" + proxy_path


def build_console_realtime_proxy_path(region_name, proxy_path=""):
    return REALTIME_PROXY_PATH.format(region_name=region_name) + normalize_proxy_path(proxy_path)


def _request_is_secure(request):
    forwarded_proto = request.META.get("HTTP_X_FORWARDED_PROTO", "")
    if forwarded_proto:
        return forwarded_proto.split(",", 1)[0].strip().lower() == "https"
    return request.is_secure()


def build_console_realtime_proxy_url(request, region_name, proxy_path="", scheme_type="http"):
    secure = _request_is_secure(request)
    if scheme_type == "ws":
        scheme = "wss" if secure else "ws"
    else:
        scheme = "https" if secure else "http"
    return "{scheme}://{host}{path}".format(
        scheme=scheme,
        host=request.get_host(),
        path=build_console_realtime_proxy_path(region_name, proxy_path),
    )


def _auto_region_wsurl(request):
    if request is None:
        raise ValueError("request is required when region websocket url is auto")
    host = request.get_host().split(":", 1)[0]
    return "ws://{0}:6060".format(host)


def get_region_wsurl(region_name, request=None):
    region = region_repo.get_region_by_region_name(region_name)
    proxy_target = os.environ.get("REGION_WS_PROXY_TARGET")
    proxy_region = os.environ.get("REGION_WS_PROXY_REGION", "rainbond")
    if proxy_target and region_name == proxy_region:
        return proxy_target.rstrip("/")
    if not region or not getattr(region, "wsurl", None) or region.wsurl == "auto":
        return _auto_region_wsurl(request)
    return region.wsurl.rstrip("/")


def _convert_scheme(url, scheme_type):
    if scheme_type == "ws":
        if url.startswith("https://"):
            return "wss://" + url[len("https://"):]
        if url.startswith("http://"):
            return "ws://" + url[len("http://"):]
        return url
    if url.startswith("wss://"):
        return "https://" + url[len("wss://"):]
    if url.startswith("ws://"):
        return "http://" + url[len("ws://"):]
    return url


def build_region_realtime_proxy_url(region_name, proxy_path="", query_string="", request=None, scheme_type="http"):
    base_url = _convert_scheme(get_region_wsurl(region_name, request=request), scheme_type).rstrip("/")
    target_url = base_url + normalize_proxy_path(proxy_path)
    if query_string:
        target_url = target_url + "?" + query_string
    return target_url


def build_region_status_probe_url(api_host, token):
    return "http://{0}:6060/helm_install/region_status/{1}".format(api_host, token)


def _header_name(meta_key):
    return "-".join([part.capitalize() for part in meta_key.split("_")])


def build_forward_headers(request):
    headers = {}
    for key, value in request.META.items():
        if key.startswith("HTTP_"):
            header = _header_name(key[5:])
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            header = _header_name(key)
        else:
            continue
        if header.lower() in HOP_BY_HOP_HEADERS or header.lower() == "host":
            continue
        headers[header] = value
    return headers


def _is_multipart_request(request):
    return request.META.get("CONTENT_TYPE", "").lower().startswith("multipart/form-data")


def build_multipart_payload(request):
    data = {}
    files = {}
    for key, values in request.POST.lists():
        data[key] = values if len(values) > 1 else values[0]
    for key, uploaded_files in request.FILES.lists():
        file_items = []
        for uploaded_file in uploaded_files:
            file_items.append((
                uploaded_file.name,
                uploaded_file,
                uploaded_file.content_type or "application/octet-stream",
            ))
        files[key] = file_items if len(file_items) > 1 else file_items[0]
    return data, files


def _request_body_stream(request):
    content_length = request.META.get("CONTENT_LENGTH")
    if request.method in ("GET", "HEAD", "OPTIONS") or content_length in (None, "", "0"):
        return None
    return request.META.get("wsgi.input")


def proxy_http_request(request, region_name, proxy_path):
    target_url = build_region_realtime_proxy_url(
        region_name,
        proxy_path,
        request.META.get("QUERY_STRING", ""),
        request=request,
        scheme_type="http",
    )
    headers = build_forward_headers(request)
    data = _request_body_stream(request)
    files = None
    if request.method in ("POST", "PUT", "PATCH") and _is_multipart_request(request):
        headers.pop("Content-Type", None)
        headers.pop("Content-Length", None)
        data, files = build_multipart_payload(request)

    response = requests.request(
        request.method,
        target_url,
        headers=headers,
        data=data,
        files=files,
        stream=True,
        timeout=(10, 3600),
        allow_redirects=False,
    )

    excluded_headers = HOP_BY_HOP_HEADERS | {"content-encoding"}
    response_headers = {
        key: value for key, value in response.headers.items()
        if key.lower() not in excluded_headers
    }

    if request.method == "HEAD":
        proxy_response = HttpResponse(status=response.status_code)
    else:
        proxy_response = StreamingHttpResponse(
            _iter_response_content(response),
            status=response.status_code,
        )
    for key, value in response_headers.items():
        proxy_response[key] = value
    return proxy_response


def _iter_response_content(response):
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if chunk:
                yield chunk
    finally:
        response.close()


def _websocket_subprotocols(request):
    protocols = request.META.get("HTTP_SEC_WEBSOCKET_PROTOCOL", "")
    return [item.strip() for item in protocols.split(",") if item.strip()]


def _backend_websocket_subprotocols(request, proxy_path):
    protocols = _websocket_subprotocols(request)
    if protocols:
        return protocols
    if normalize_proxy_path(proxy_path) == "/docker_console":
        return ["webtty"]
    return []


def _websocket_headers(request):
    headers = []
    for header in ("Origin", "Cookie", "Authorization", "X-Forwarded-For"):
        meta_key = "HTTP_" + header.upper().replace("-", "_")
        value = request.META.get(meta_key)
        if value:
            headers.append("{0}: {1}".format(header, value))
    return headers


def proxy_websocket_request(request, region_name, proxy_path):
    client_ws = getattr(request, "environ", {}).get("wsgi.websocket")
    if client_ws is None:
        client_ws = request.META.get("wsgi.websocket")
    if client_ws is None:
        return HttpResponseBadRequest("websocket upgrade required")

    try:
        import gevent
        from geventwebsocket.exceptions import WebSocketError
        from websocket import ABNF, WebSocketConnectionClosedException, create_connection
    except ImportError:
        logger.exception("websocket proxy dependencies are missing")
        return HttpResponse("websocket proxy dependencies are missing", status=500)

    target_url = build_region_realtime_proxy_url(
        region_name,
        proxy_path,
        request.META.get("QUERY_STRING", ""),
        request=request,
        scheme_type="ws",
    )
    backend_ws = create_connection(
        target_url,
        timeout=10,
        header=_websocket_headers(request),
        subprotocols=_backend_websocket_subprotocols(request, proxy_path),
    )

    def client_to_backend():
        while True:
            try:
                message = client_ws.receive()
                if message is None:
                    break
                if isinstance(message, bytes):
                    backend_ws.send_binary(message)
                else:
                    backend_ws.send(message)
            except (WebSocketError, WebSocketConnectionClosedException):
                break
            except Exception:
                logger.exception("websocket proxy client->backend failed")
                break

    def backend_to_client():
        while True:
            try:
                opcode, data = backend_ws.recv_data()
                if opcode == ABNF.OPCODE_CLOSE:
                    break
                if opcode == ABNF.OPCODE_BINARY:
                    client_ws.send(data, binary=True)
                elif opcode == ABNF.OPCODE_TEXT:
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    client_ws.send(data)
                elif opcode == ABNF.OPCODE_PING:
                    backend_ws.pong(data)
            except (WebSocketError, WebSocketConnectionClosedException):
                break
            except Exception:
                logger.exception("websocket proxy backend->client failed")
                break

    jobs = [gevent.spawn(client_to_backend), gevent.spawn(backend_to_client)]
    try:
        gevent.joinall(jobs, count=1)
    finally:
        for job in jobs:
            job.kill()
        try:
            backend_ws.close()
        except Exception:
            logger.debug("close backend websocket failed", exc_info=True)
        try:
            client_ws.close()
        except Exception:
            logger.debug("close client websocket failed", exc_info=True)
    return HttpResponse(status=204)
