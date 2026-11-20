# -*- coding: utf-8 -*-
"""Standalone gevent probe; imported only in a fresh interpreter."""
from gevent import monkey

monkey.patch_all()

import io  # noqa: E402
from http.client import HTTPResponse  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402
import socket  # noqa: E402
import sys  # noqa: E402
from types import ModuleType, SimpleNamespace  # noqa: E402
from unittest import mock  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

import gevent  # noqa: E402
from gevent.event import Event  # noqa: E402
from gevent.pywsgi import WSGIServer  # noqa: E402
from gevent.server import StreamServer  # noqa: E402
from django.core.handlers.wsgi import WSGIRequest  # noqa: E402
import urllib3  # noqa: E402

from goodrain_web.ai_proxy_worker import AIProxyWebSocketHandler, AIProxyWorker  # noqa: E402
from www.apiclient import regionapibaseclient  # noqa: E402

PATH = "/openapi/v1/ai-engine/team-a/regions/region-a/v1/messages"
TARGET = "/v2/platform/backend/plugins/rainbond-ai-engine/v1/messages"


def check_cancel(path=PATH, cancel=True, pause=0):
    upstream_closed = Event()
    responses = []
    sockets = []
    attempts = []

    def backend(conn, _address):
        sockets.append(conn)
        data = b""
        while b"\r\n\r\n" not in data:
            data += conn.recv(8192)
        headers, body = data.split(b"\r\n\r\n", 1)
        length = int(
            next(line.split(b":", 1)[1] for line in headers.split(b"\r\n") if line.lower().startswith(b"content-length:")))
        while len(body) < length:
            body += conn.recv(8192)
        assert body == b'{"stream":true}', body
        attempts.append(data)
        fragment = b"data: first\n\n"
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
                     b"Transfer-Encoding: chunked\r\n\r\n" + format(len(fragment), "x").encode() + b"\r\n" + fragment + b"\r\n")
        try:
            if not cancel:
                gevent.sleep(pause)
                tail = b"data: last\n\n"
                conn.sendall(format(len(tail), "x").encode() + b"\r\n" + tail + b"\r\n0\r\n\r\n")
                return
            if not conn.recv(1):
                upstream_closed.set()
        except OSError:
            upstream_closed.set()
        finally:
            conn.close()

    upstream = StreamServer(("127.0.0.1", 0), backend)
    upstream.start()
    region = SimpleNamespace(url="http://127.0.0.1:%d" % upstream.server_port, token="")
    pool = urllib3.PoolManager()
    api = regionapibaseclient.RegionApiBaseHttpClient()

    def app(environ, start_response):
        request = WSGIRequest(environ)
        response = api.stream_proxy(request, TARGET, "region-a", timeout=urllib3.Timeout(connect=1, read=None))
        responses.append(response)
        start_response("200 OK", list(response.items()))
        return response

    assert AIProxyWorker.wsgi_handler is AIProxyWebSocketHandler
    server = WSGIServer(("127.0.0.1", 0), app, handler_class=AIProxyWebSocketHandler, log=None)
    server.start()
    client = socket.create_connection(("127.0.0.1", server.server_port))
    try:
        with mock.patch.object(regionapibaseclient.region_repo, "get_region_by_region_name", return_value=region), \
                mock.patch.object(api, "get_client", return_value=pool):
            body = b'{"stream":true}'
            client.sendall(("POST " + path + " HTTP/1.1\r\nHost: localhost\r\nContent-Length: " + str(len(body)) +
                            "\r\n\r\n").encode() + body)
            data = b""
            with gevent.Timeout(3):
                while b"data: first\n\n" not in data:
                    part = client.recv(8192)
                    assert part, data
                    data += part
            # Upstream remains silent. Only the real downstream TCP close may
            # initiate cleanup; this fixture never calls response.close().
            if cancel:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
                assert upstream_closed.wait(2), "downstream cancel left the silent upstream open"
            else:
                with gevent.Timeout(pause + 3):
                    while b"0\r\n\r\n" not in data:
                        part = client.recv(8192)
                        assert part, data
                        data += part
                assert b"data: last\n\n" in data, data
            gevent.sleep(0)
            assert responses[0].closed, "WSGI did not close its response"
            assert len(attempts) == 1, attempts
    finally:
        client.close()
        for conn in sockets:
            conn.close()
        server.stop(timeout=0)
        upstream.stop(timeout=0)
        pool.clear()


def check_normal_completion():
    """A completed AI response must not leave a watcher on a reused connection."""
    completed = Event()
    api = regionapibaseclient.RegionApiBaseHttpClient()
    observed_hooks = []

    def app(environ, start_response):
        request = WSGIRequest(environ)
        observed_hooks.append(callable(environ.get("rainbond.ai_proxy_watch_disconnect")))
        if environ["PATH_INFO"] == PATH:
            upstream = urllib3.response.HTTPResponse(body=io.BytesIO(b"ok"), preload_content=False)
            stream, close = api._ai_response_stream(upstream, request=request)
            from django.http import StreamingHttpResponse
            response = StreamingHttpResponse(stream)
            response._resource_closers.append(close)
            start_response("200 OK", list(response.items()))
            return response
        gevent.sleep(0.2)
        completed.set()
        start_response("200 OK", [("Content-Length", "2")])
        return [b"ok"]

    server = WSGIServer(("127.0.0.1", 0), app, handler_class=AIProxyWebSocketHandler, log=None)
    server.start()
    client = socket.create_connection(("127.0.0.1", server.server_port))
    try:
        client.sendall(("GET " + PATH + " HTTP/1.1\r\nHost: localhost\r\n\r\n").encode())
        data = b""
        with gevent.Timeout(3):
            while b"0\r\n\r\n" not in data:
                part = client.recv(8192)
                assert part, data
                data += part
        client.sendall(b"GET /console/regions/r/backend/plugins/other/api HTTP/1.1\r\nHost: localhost\r\n\r\n")
        gevent.sleep(0.05)
        client.shutdown(socket.SHUT_RDWR)
        client.close()
        assert completed.wait(2), "stale AI watcher killed a subsequent non-AI request"
        assert observed_hooks == [True, False], observed_hooks
    finally:
        client.close()
        server.stop(timeout=0)


def check_before_headers(proxy_style, cancel=True, delay=0):
    request_received = Event()
    upstream_closed = Event()
    request_done = Event()
    responses = []
    sockets = []
    attempts = []

    def backend(conn, _address):
        sockets.append(conn)
        data = b""
        while b"\r\n\r\n" not in data:
            data += conn.recv(8192)
        headers, body = data.split(b"\r\n\r\n", 1)
        length = int(
            next(line.split(b":", 1)[1] for line in headers.split(b"\r\n") if line.lower().startswith(b"content-length:")))
        while len(body) < length:
            body += conn.recv(8192)
        assert body == b'{"stream":true}', body
        attempts.append(data)
        request_received.set()
        try:
            if cancel:
                # Deliberately send no HTTP status/headers or body.
                if not conn.recv(1):
                    upstream_closed.set()
            else:
                gevent.sleep(delay)
                fragment = b"data: first\n\n"
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: " +
                             str(len(fragment)).encode() + b"\r\nConnection: close\r\n\r\n" + fragment)
        except OSError:
            upstream_closed.set()
        finally:
            conn.close()

    upstream = StreamServer(("127.0.0.1", 0), backend)
    upstream.start()
    region = SimpleNamespace(url="http://127.0.0.1:%d" % upstream.server_port, token="")
    api = regionapibaseclient.RegionApiBaseHttpClient()
    pool = urllib3.PoolManager()

    def app(environ, start_response):
        try:
            response = getattr(api, proxy_style)(WSGIRequest(environ),
                                                 TARGET,
                                                 "region-a",
                                                 timeout=urllib3.Timeout(connect=1, read=None))
            responses.append(response)
            start_response("200 OK", list(response.items()))
            return response
        finally:
            request_done.set()

    server = WSGIServer(("127.0.0.1", 0), app, handler_class=AIProxyWebSocketHandler, log=None)
    server.start()
    client = socket.create_connection(("127.0.0.1", server.server_port))
    try:
        with mock.patch.object(regionapibaseclient.region_repo, "get_region_by_region_name", return_value=region), \
                mock.patch.object(api, "get_client", return_value=pool):
            body = b'{"stream":true}'
            client.sendall(
                ("POST " + PATH + " HTTP/1.1\r\nHost: localhost\r\nContent-Length: " + str(len(body)) + "\r\n\r\n").encode())
            # Split the upload across reads; an early watcher must not consume
            # request bytes or compete with WSGI's request-body read watcher.
            for part in (body[:4], body[4:]):
                gevent.sleep(0.03)
                client.sendall(part)
            assert request_received.wait(2), "POST body was not forwarded intact"
            if cancel:
                assert not responses, "upstream unexpectedly produced response headers"
                client.shutdown(socket.SHUT_RDWR)
                client.close()
                assert upstream_closed.wait(2), "pre-header cancel kept upstream connection open"
                assert request_done.wait(2), "serving greenlet remained blocked before headers"
                assert not responses
            else:
                with gevent.Timeout(delay + 3):
                    protocol_response = HTTPResponse(client)
                    protocol_response.begin()
                    assert protocol_response.status == 200
                    assert protocol_response.read(len(b"data: first\n\n")) == b"data: first\n\n"
                    protocol_response.close()
            assert len(attempts) == 1, attempts
    finally:
        client.close()
        for conn in sockets:
            conn.close()
        server.stop(timeout=0)
        upstream.stop(timeout=0)
        pool.clear()


if __name__ == "__main__" and sys.argv[1:] == ["preheaders"]:
    for style in ("stream_proxy", "proxy"):
        check_before_headers(style)
    check_before_headers("stream_proxy", cancel=False, delay=21 if os.environ.get("HIGRESS_LONG_STREAM_TEST") == "1" else 0.05)
    print("all pre-header lifecycle checks passed; urllib3=" + urllib3.__version__)

elif __name__ == "__main__":
    for path in (PATH, "/openapi/v1/ai-engine/team-a/v1/messages",
                 "/console/regions/r/backend/plugins/rainbond-ai-engine/api/v1/ai-engine/instances/i/chat",
                 "/console/regions/r/proxy/plugins/rainbond-ai-engine/api/v1/ai-engine/instances/i/chat"):
        check_cancel(path)
    check_normal_completion()
    check_cancel(cancel=False, pause=21 if os.environ.get("HIGRESS_LONG_STREAM_TEST") == "1" else 0.05)
    print("all downstream lifecycle checks passed; urllib3=" + urllib3.__version__)
