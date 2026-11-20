# -*- coding: utf-8 -*-
import io
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import ModuleType, SimpleNamespace
from unittest import mock, skipUnless

import urllib3

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.test import SimpleTestCase, override_settings  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient  # noqa: E402

AI_PREFIX = "/v2/platform/backend/plugins/rainbond-ai-engine/"
SCOPE = {
    "X-AI-Team-Name": "team-a",
    "X-AI-Region-Name": "region-a",
    "X-AI-Team-Namespace": "team-a-ns",
    "X-AI-Actor-ID": "42",
}


@override_settings(MODULES={"RegionToken": True})
class AIEngineTransportTests(SimpleTestCase):
    def setUp(self):
        self.api = RegionApiBaseHttpClient()
        self.region = SimpleNamespace(url="http://region.example", token="region-token")
        self.client = mock.Mock()
        self.upstream = mock.Mock(
            status=429,
            headers={
                "Content-Type": "application/json",
                "Retry-After": "3",
                "X-Request-ID": "request-1"
            },
            data=b'{"error":{"message":"limited"}}',
            url="http://region.example" + AI_PREFIX + "v1/messages",
            chunked=True,
        )
        self.upstream.stream.return_value = iter([b'{"error":{"message":"limited"}}'])
        self.client.request.return_value = self.upstream
        for patcher in (
                mock.patch("www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name", return_value=self.region),
                mock.patch.object(self.api, "get_client", return_value=self.client),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def request():
        return SimpleNamespace(
            method="POST",
            META={
                "HTTP_AUTHORIZATION": "GRJWT login-token",
                "HTTP_X_ORIGINAL_AUTHORIZATION": "Bearer forged-original",
                "HTTP_X_API_KEY": "forged-key",
                "HTTP_COOKIE": "session=browser",
                "HTTP_X_AI_TEAM_NAME": "other-team",
                "HTTP_X_AI_TEAM_NAMESPACE": "other-ns",
                "HTTP_X_AI_ACTOR_ID": "forged-actor",
                "HTTP_X_AI_PERMISSIONS": "all",
                "HTTP_X_AI_PLATFORM_TOKEN": "forged-platform-token",
                "HTTP_X_HIGRESS_CONSUMER": "forged-consumer",
                "HTTP_ACCEPT": "text/event-stream",
                "CONTENT_TYPE": "application/json",
            },
            _request=io.BytesIO(b'{"stream":true}'),
        )

    def headers(self):
        return {key.lower(): value for key, value in self.client.request.call_args.kwargs["headers"].items()}

    # capability_id: console.ai-engine.trusted-transport
    def test_inference_uses_only_explicit_credentials_and_scope(self):
        trusted = dict(SCOPE, **{"X-Original-Authorization": "Bearer real-key", "x-api-key": "real-key"})
        response = self.api.stream_proxy(self.request(),
                                         AI_PREFIX + "v1/messages?trace=1",
                                         "region-a",
                                         requests_args={"headers": trusted})
        self.addCleanup(response.close)
        headers = self.headers()
        self.assertEqual(headers["authorization"], "region-token")
        self.assertEqual(headers["x-original-authorization"], "Bearer real-key")
        self.assertEqual(headers["x-api-key"], "real-key")
        for key, value in SCOPE.items():
            self.assertEqual(headers[key.lower()], value)
        for key in ("cookie", "x-ai-permissions", "x-higress-consumer", "x-ai-platform-token"):
            self.assertNotIn(key, headers)
        self.assertEqual(self.client.request.call_args.kwargs["url"],
                         "http://region.example" + AI_PREFIX + "v1/messages?trace=1")

    @override_settings(MODULES={"RegionToken": False})
    def test_disabled_region_token_still_forwards_only_canonical_original_credential(self):
        response = self.api.stream_proxy(self.request(),
                                         AI_PREFIX + "v1/messages",
                                         "region-a",
                                         requests_args={"headers": {
                                             "X-Original-Authorization": "Bearer real-key"
                                         }})
        self.addCleanup(response.close)
        self.assertNotIn("authorization", self.headers())
        self.assertEqual(self.headers()["x-original-authorization"], "Bearer real-key")
        self.assertNotIn("x-api-key", self.headers())

    def test_management_does_not_forward_login_or_forged_credentials(self):
        response = self.api.stream_proxy(self.request(),
                                         AI_PREFIX + "api/v1/ai-engine/api-keys",
                                         "region-a",
                                         requests_args={"headers": SCOPE})
        self.addCleanup(response.close)
        headers = self.headers()
        self.assertEqual(headers["authorization"], "region-token")
        self.assertEqual(headers["x-ai-actor-id"], "42")
        for key in ("x-original-authorization", "x-api-key", "cookie", "x-higress-consumer", "x-ai-permissions"):
            self.assertNotIn(key, headers)

    def test_buffered_ai_proxy_also_discards_untrusted_identity(self):
        response = self.api.proxy(self.request(),
                                  AI_PREFIX + "api/v1/ai-engine/api-keys",
                                  "region-a",
                                  requests_args={"headers": SCOPE})
        self.assertEqual(response.content, self.upstream.data)
        headers = self.headers()
        self.assertEqual(headers["x-ai-team-name"], "team-a")
        self.assertNotIn("x-original-authorization", headers)
        self.assertNotIn("x-ai-permissions", headers)

    def test_explicit_unapproved_identity_headers_are_rejected(self):
        with self.assertRaises(ServiceHandleException):
            self.api.stream_proxy(self.request(),
                                  AI_PREFIX + "v1/messages",
                                  "region-a",
                                  requests_args={"headers": {
                                      "X-Higress-Consumer": "control"
                                  }})
        self.client.request.assert_not_called()

    def test_console_cannot_supply_region_owned_platform_token(self):
        with self.assertRaises(ServiceHandleException):
            self.api.stream_proxy(self.request(),
                                  AI_PREFIX + "api/v1/ai-engine/model-apis",
                                  "region-a",
                                  requests_args={"headers": {"X-AI-Platform-Token": "forged-platform-token"}})
        self.client.request.assert_not_called()

    def test_management_preserves_opaque_debug_session_without_trusting_identity(self):
        request = self.request()
        request.META["HTTP_X_AI_DEBUG_SESSION"] = "debug-session-proof"
        response = self.api.stream_proxy(request,
                                         AI_PREFIX + "api/v1/ai-engine/instances/1/media",
                                         "region-a",
                                         requests_args={"headers": SCOPE})
        self.addCleanup(response.close)
        self.assertEqual(self.headers()["x-ai-debug-session"], "debug-session-proof")
        self.assertNotIn("x-ai-permissions", self.headers())

    def test_public_inference_strips_debug_session(self):
        request = self.request()
        request.META["HTTP_X_AI_DEBUG_SESSION"] = "debug-session-proof"
        response = self.api.stream_proxy(request, AI_PREFIX + "v1/messages", "region-a")
        self.addCleanup(response.close)
        self.assertNotIn("x-ai-debug-session", self.headers())

    def test_trusted_context_rejects_control_characters(self):
        with self.assertRaises(ServiceHandleException):
            self.api.stream_proxy(self.request(),
                                  AI_PREFIX + "v1/messages",
                                  "region-a",
                                  requests_args={"headers": {
                                      "X-AI-Team-Name": "team-a\r\nX-AI-Actor-ID: forged"
                                  }})
        self.client.request.assert_not_called()

    def test_management_cannot_forward_explicit_inference_credentials(self):
        with self.assertRaises(ServiceHandleException):
            self.api.stream_proxy(self.request(),
                                  AI_PREFIX + "api/v1/ai-engine/api-keys",
                                  "region-a",
                                  requests_args={"headers": {
                                      "X-Original-Authorization": "Bearer real-key"
                                  }})
        self.client.request.assert_not_called()

    def test_ai_inference_cannot_enable_retry_redirect_or_preload(self):
        timeout = urllib3.Timeout(connect=10, read=None)
        response = self.api.stream_proxy(self.request(),
                                         AI_PREFIX + "v1/messages",
                                         "region-a",
                                         requests_args={
                                             "retries": 2,
                                             "redirect": True,
                                             "preload_content": True,
                                             "timeout": timeout
                                         })
        self.addCleanup(response.close)
        options = self.client.request.call_args.kwargs
        self.assertIs(options["retries"], False)
        self.assertIs(options["redirect"], False)
        self.assertIs(options["preload_content"], False)
        self.assertIs(options["timeout"], timeout)

    def test_protocol_status_headers_and_body_are_unchanged(self):
        response = self.api.stream_proxy(self.request(), AI_PREFIX + "v1/messages", "region-a")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Retry-After"], "3")
        self.assertEqual(response["X-Request-ID"], "request-1")
        self.assertEqual(b"".join(response.streaming_content), self.upstream.data)
        response.close()
        self.upstream.close.assert_called_once_with()
        self.upstream.release_conn.assert_called_once_with()

    def test_redirect_status_and_location_are_passed_without_replay(self):
        self.upstream.status = 307
        self.upstream.headers["Location"] = "/v1/messages"
        response = self.api.stream_proxy(self.request(), AI_PREFIX + "v1/messages", "region-a")
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response["Location"], "/v1/messages")
        self.client.request.assert_called_once()
        self.assertIs(self.client.request.call_args.kwargs["redirect"], False)

    def test_real_post_is_sent_once_on_redirect_retryable_status_and_disconnect(self):
        payload = b'{"model":"demo","stream":true}'
        path = AI_PREFIX + "v1/messages?trace=a%2Fb"
        body = b'{"error":{"message":"upstream rejected"}}'
        for upstream_status in (307, 503, None):
            with self.subTest(upstream_status=upstream_status):
                attempts = []

                class Handler(BaseHTTPRequestHandler):
                    protocol_version = "HTTP/1.1"

                    def do_POST(self):
                        request_body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                        attempts.append((self.command, self.path, request_body))
                        if upstream_status is None:
                            self.close_connection = True
                            self.connection.shutdown(socket.SHUT_RDWR)
                            self.connection.close()
                            return
                        self.send_response(upstream_status)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.send_header("Connection", "close")
                        if upstream_status == 307:
                            self.send_header("Location", "/redirected")
                        else:
                            self.send_header("Retry-After", "0")
                        self.end_headers()
                        self.wfile.write(body)
                        self.wfile.flush()

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                pool = urllib3.PoolManager()
                self.region.url = "http://127.0.0.1:{}".format(server.server_port)
                self.client.request.side_effect = lambda **kwargs: pool.request(**kwargs)
                request = self.request()
                request._request = io.BytesIO(payload)
                request.META = {"CONTENT_LENGTH": str(len(payload)), "CONTENT_TYPE": "application/json"}
                response = None
                try:
                    if upstream_status is None:
                        with self.assertRaises(urllib3.exceptions.HTTPError):
                            self.api.stream_proxy(request, path, "region-a")
                    else:
                        response = self.api.stream_proxy(request, path, "region-a")
                        self.assertEqual(response.status_code, upstream_status)
                        self.assertEqual(b"".join(response.streaming_content), body)
                        if upstream_status == 307:
                            self.assertEqual(response["Location"], "/redirected")
                        else:
                            self.assertEqual(response["Retry-After"], "0")
                    self.assertEqual(attempts, [("POST", path, payload)])
                finally:
                    if response is not None:
                        response.close()
                    pool.clear()
                    server.shutdown()
                    server.server_close()
                    thread.join(1)

    # capability_id: console.ai-engine.stream-cleanup
    def test_close_before_streaming_closes_and_releases_upstream(self):
        response = self.api.stream_proxy(self.request(), AI_PREFIX + "v1/messages", "region-a")
        response.close()
        response.close()
        self.upstream.close.assert_called_once_with()
        self.upstream.release_conn.assert_called_once_with()

    def test_disconnect_watch_starts_before_request_and_transfers_to_response(self):
        stop = mock.Mock()
        watch = mock.Mock(return_value=stop)
        request = self.request()
        request.META["rainbond.ai_proxy_watch_disconnect"] = watch

        def upstream_request(**_kwargs):
            watch.assert_called_once_with()
            stop.assert_not_called()
            return self.upstream

        self.client.request.side_effect = upstream_request
        response = self.api.stream_proxy(request, AI_PREFIX + "v1/messages", "region-a")
        b"".join(response.streaming_content)
        response.close()
        watch.assert_called_once_with()
        stop.assert_called_once_with()

    def test_request_failure_stops_disconnect_watch_without_response(self):
        stop = mock.Mock()
        request = self.request()
        request.META["rainbond.ai_proxy_watch_disconnect"] = mock.Mock(return_value=stop)
        self.client.request.side_effect = urllib3.exceptions.ProtocolError("failed before headers")
        with self.assertRaises(urllib3.exceptions.ProtocolError):
            self.api.stream_proxy(request, AI_PREFIX + "v1/messages", "region-a")
        stop.assert_called_once_with()

    def test_cancel_after_first_chunk_closes_and_releases_upstream(self):
        self.upstream.stream.return_value = iter([b"data: first\n\n", b"data: second\n\n"])
        response = self.api.stream_proxy(self.request(), AI_PREFIX + "v1/messages", "region-a")
        self.assertEqual(next(iter(response.streaming_content)), b"data: first\n\n")
        response.close()
        self.upstream.close.assert_called_once_with()
        self.upstream.release_conn.assert_called_once_with()

    def test_interrupted_stream_is_not_replayed_or_reported_as_complete(self):
        def interrupted(*_args, **_kwargs):
            yield b"data: first\n\n"
            raise urllib3.exceptions.ProtocolError("truncated")

        self.upstream.stream.side_effect = interrupted
        response = self.api.stream_proxy(self.request(), AI_PREFIX + "v1/messages", "region-a")
        with self.assertRaises(urllib3.exceptions.ProtocolError):
            b"".join(response.streaming_content)
        response.close()
        self.client.request.assert_called_once()
        self.upstream.close.assert_called_once_with()
        self.upstream.release_conn.assert_called_once_with()

    def test_real_short_content_length_is_a_transport_error(self):
        payload = b"data: partial\n\n"
        content_type = "text/event-stream"
        attempts = []
        upstream_responses = []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                attempts.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", "200")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)
                self.wfile.flush()
                self.close_connection = True

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        self.region.url = "http://127.0.0.1:{}".format(server.server_port)

        def actual_request(**kwargs):
            upstream = pool.request(**kwargs)
            upstream_responses.append(upstream)
            return upstream

        self.client.request.side_effect = actual_request
        try:
            for method in (self.api.stream_proxy, self.api.proxy):
                for content_type in ("text/event-stream", "application/json"):
                    with self.subTest(method=method.__name__, content_type=content_type):
                        request = self.request()
                        request._request = io.BytesIO()
                        request.META = {"CONTENT_LENGTH": "0"}
                        result = None
                        chunks = []
                        try:
                            with self.assertRaises(urllib3.exceptions.ProtocolError):
                                result = method(request, AI_PREFIX + "v1/messages", "region-a")
                                if result.streaming:
                                    for chunk in result.streaming_content:
                                        chunks.append(chunk)
                        finally:
                            if result is not None:
                                result.close()
                        if chunks:
                            self.assertEqual(b"".join(chunks), payload)
                        self.assertTrue(upstream_responses[-1].closed)
            self.assertEqual(attempts, [AI_PREFIX + "v1/messages"] * 4)
            self.assertEqual(self.client.request.call_count, 4)
        finally:
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(1)

    def test_other_plugins_retain_existing_credential_contract_and_defaults(self):
        response = self.api.stream_proxy(self.request(), "/v2/platform/backend/plugins/other/api", "region-a")
        self.addCleanup(response.close)
        headers = self.headers()
        self.assertEqual(headers["x-original-authorization"], "Bearer forged-original")
        self.assertEqual(headers["x-ai-team-name"], "other-team")
        self.assertNotIn("retries", self.client.request.call_args.kwargs)
        self.assertEqual(self.client.request.call_args.kwargs["timeout"].read_timeout, 3600)

    def test_mcp_region_client_accepts_audit_actor(self):
        api = RegionInvokeApi()
        with mock.patch.object(api, "_RegionInvokeApi__get_region_access_info_by_enterprise_id",
                               return_value=(self.region.url, self.region.token)), \
                mock.patch.object(api, "_request", return_value=(200, b'{"code":200,"data":[]}')) as call:
            api.request_plugin_backend("enterprise",
                                       "region-a",
                                       "rainbond-ai-engine",
                                       "GET",
                                       "/api/v1/ai-engine/instances",
                                       headers=SCOPE)
        self.assertEqual(call.call_args.kwargs["headers"]["X-AI-Actor-ID"], "42")

    # capability_id: console.ai-engine.incremental-stream
    def test_nonchunked_small_fragment_arrives_before_response_end(self):
        continue_response = threading.Event()
        received_first = threading.Event()
        failures = []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", "20")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(b"data: first\n\n")
                self.wfile.flush()
                continue_response.wait(3)
                try:
                    self.wfile.write(b"tailend")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        self.region.url = "http://127.0.0.1:{}".format(server.server_port)
        self.client.request.side_effect = lambda **kwargs: pool.request(**kwargs)
        request = self.request()
        request._request = io.BytesIO()
        request.META = {"CONTENT_LENGTH": "0"}
        response = self.api.stream_proxy(request, AI_PREFIX + "v1/messages", "region-a")

        def read_first():
            try:
                first = next(iter(response.streaming_content))
                if first:
                    received_first.set()
            except Exception as err:
                failures.append(err)

        reader = threading.Thread(target=read_first, daemon=True)
        reader.start()
        try:
            self.assertTrue(received_first.wait(1), "first SSE fragment was buffered until EOF")
            self.assertEqual(failures, [])
        finally:
            continue_response.set()
            reader.join(3)
            response.close()
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(1)

    def test_client_cancel_closes_real_upstream_socket(self):
        disconnected = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", "100")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(b"data: first\n\n")
                self.wfile.flush()
                self.connection.settimeout(3)
                try:
                    if not self.connection.recv(1):
                        disconnected.set()
                except ConnectionResetError:
                    disconnected.set()

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        self.region.url = "http://127.0.0.1:{}".format(server.server_port)
        self.client.request.side_effect = lambda **kwargs: pool.request(**kwargs)
        request = self.request()
        request._request = io.BytesIO()
        request.META = {"CONTENT_LENGTH": "0"}
        response = self.api.stream_proxy(request, AI_PREFIX + "v1/messages", "region-a")
        try:
            self.assertTrue(next(iter(response.streaming_content)))
            response.close()
            self.assertTrue(disconnected.wait(2), "Console cancellation kept upstream connection open")
        finally:
            response.close()
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(1)

    @skipUnless(os.environ.get("HIGRESS_LONG_STREAM_TEST") == "1", "run explicitly for 21-second streaming verification")
    def test_stream_remains_open_for_more_than_twenty_seconds(self):
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", "25")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(b"data: first\n\n")
                self.wfile.flush()
                threading.Event().wait(21)
                self.wfile.write(b"data: last\n\n")
                self.wfile.flush()

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        self.region.url = "http://127.0.0.1:{}".format(server.server_port)
        self.client.request.side_effect = lambda **kwargs: pool.request(**kwargs)
        request = self.request()
        request._request = io.BytesIO()
        request.META = {"CONTENT_LENGTH": "0"}
        response = self.api.stream_proxy(request,
                                         AI_PREFIX + "v1/messages",
                                         "region-a",
                                         requests_args={
                                             "timeout": urllib3.Timeout(connect=10, read=None),
                                             "retries": False
                                         })
        started = time.monotonic()
        try:
            self.assertEqual(b"".join(response.streaming_content), b"data: first\n\ndata: last\n\n")
            self.assertGreater(time.monotonic() - started, 20)
            self.client.request.assert_called_once()
        finally:
            response.close()
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(1)
