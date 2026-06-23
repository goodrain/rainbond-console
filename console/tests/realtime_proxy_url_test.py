# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _DummyConfiguration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _DummyApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test import RequestFactory, SimpleTestCase  # noqa: E402

django.setup()

from console.services.app_actions.app_log import AppWebSocketService  # noqa: E402
from console.services.app_import_and_export_service import import_service  # noqa: E402
from console.utils.realtime_proxy import (  # noqa: E402
    DockerConsoleActivityTracker,
    WEBSOCKET_PROXY_READ_TIMEOUT_SECONDS,
    _backend_websocket_subprotocols,
    build_multipart_payload,
    build_console_realtime_proxy_url,
    build_region_realtime_proxy_url,
    open_backend_websocket,
    proxy_http_request,
)


class RealtimeProxyUrlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory(HTTP_HOST="console.example.com:7070")

    # capability_id: console.realtime-proxy.websocket-url
    def test_websocket_service_returns_console_proxy_url_without_6060(self):
        request = self.factory.get("/console/teams/demo/apps/app/events")

        ws_url = AppWebSocketService().get_event_log_ws(request, "rainbond")

        self.assertEqual(ws_url, "ws://console.example.com:7070/console/regions/rainbond/websocket/event_log")
        self.assertNotIn(":6060", ws_url)

    # capability_id: console.realtime-proxy.secure-websocket-url
    def test_console_proxy_url_uses_wss_when_request_is_https(self):
        request = self.factory.get(
            "/console/teams/demo/apps/app/events",
            HTTP_X_FORWARDED_PROTO="https",
        )

        ws_url = build_console_realtime_proxy_url(request, "rainbond", "event_log", scheme_type="ws")

        self.assertEqual(ws_url, "wss://console.example.com:7070/console/regions/rainbond/websocket/event_log")

    # capability_id: console.realtime-proxy.upload-url
    def test_upload_package_url_returns_console_proxy_path(self):
        with mock.patch(
            "console.services.app_import_and_export_service.region_repo.get_region_by_region_name",
            return_value=mock.Mock(wsurl="ws://region.example.com:6060"),
        ):
            upload_url = import_service.get_upload_package_url("rainbond", "evt-1")

        self.assertEqual(upload_url, "/console/regions/rainbond/websocket/package_build/component/events/evt-1")
        self.assertNotIn(":6060", upload_url)

    # capability_id: console.realtime-proxy.region-target-url
    def test_region_proxy_target_keeps_region_websocket_host_for_http(self):
        with mock.patch(
            "console.utils.realtime_proxy.region_repo.get_region_by_region_name",
            return_value=mock.Mock(wsurl="wss://region.example.com:6060"),
        ):
            target_url = build_region_realtime_proxy_url(
                "rainbond",
                "/package_build/component/events/evt-1",
                "chunk=1",
                scheme_type="http",
            )

        self.assertEqual(target_url, "https://region.example.com:6060/package_build/component/events/evt-1?chunk=1")

    # capability_id: console.realtime-proxy.internal-target-override
    def test_region_proxy_target_prefers_internal_override_for_builtin_region(self):
        with mock.patch.dict(
            os.environ,
            {"REGION_WS_PROXY_TARGET": "ws://127.0.0.1:6060"},
        ), mock.patch(
            "console.utils.realtime_proxy.region_repo.get_region_by_region_name",
            return_value=mock.Mock(wsurl="ws://public.example.com:6060"),
        ):
            target_url = build_region_realtime_proxy_url(
                "rainbond",
                "/event_log",
                scheme_type="ws",
            )

        self.assertEqual(target_url, "ws://127.0.0.1:6060/event_log")

    # capability_id: console.realtime-proxy.http-forward
    def test_http_proxy_forwards_upload_request_to_region_websocket_service(self):
        request = self.factory.post(
            "/console/regions/rainbond/websocket/package_build/component/events/evt-1?chunk=1",
            data=b"demo-body",
            content_type="application/octet-stream",
            HTTP_AUTHORIZATION="JWT token",
        )
        backend_response = mock.Mock()
        backend_response.status_code = 201
        backend_response.headers = {"Content-Type": "application/json"}
        backend_response.iter_content.return_value = iter([b'{"ok":true}'])

        with mock.patch(
            "console.utils.realtime_proxy.region_repo.get_region_by_region_name",
            return_value=mock.Mock(wsurl="ws://region.example.com:6060"),
        ), mock.patch("console.utils.realtime_proxy.requests.request", return_value=backend_response) as request_mock:
            response = proxy_http_request(request, "rainbond", "package_build/component/events/evt-1")

        _, kwargs = request_mock.call_args
        self.assertEqual(request_mock.call_args[0][0], "POST")
        self.assertEqual(
            request_mock.call_args[0][1],
            "http://region.example.com:6060/package_build/component/events/evt-1?chunk=1",
        )
        self.assertEqual(kwargs["headers"]["Authorization"], "JWT token")
        self.assertIsNotNone(kwargs["data"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(b"".join(response.streaming_content), b'{"ok":true}')

    # capability_id: console.realtime-proxy.multipart-upload-forward
    def test_http_proxy_rebuilds_multipart_upload_for_app_import(self):
        upload_file = SimpleUploadedFile(
            "app.tar.gz",
            b"app package content",
            content_type="application/gzip",
        )
        request = self.factory.post(
            "/console/regions/rainbond/websocket/app/upload/evt-1",
            data={"appTarFile": upload_file},
            HTTP_AUTHORIZATION="JWT token",
        )
        backend_response = mock.Mock()
        backend_response.status_code = 200
        backend_response.headers = {"Content-Type": "application/json"}
        backend_response.iter_content.return_value = iter([b'{"ok":true}'])

        with mock.patch(
            "console.utils.realtime_proxy.region_repo.get_region_by_region_name",
            return_value=mock.Mock(wsurl="ws://region.example.com:6060"),
        ), mock.patch("console.utils.realtime_proxy.requests.request", return_value=backend_response) as request_mock:
            response = proxy_http_request(request, "rainbond", "app/upload/evt-1")

        _, kwargs = request_mock.call_args
        self.assertEqual(request_mock.call_args[0][1], "http://region.example.com:6060/app/upload/evt-1")
        self.assertEqual(kwargs["headers"]["Authorization"], "JWT token")
        self.assertNotIn("Content-Type", kwargs["headers"])
        self.assertNotIn("Content-Length", kwargs["headers"])
        self.assertIn("appTarFile", kwargs["files"])
        file_name, file_obj, content_type = kwargs["files"]["appTarFile"]
        self.assertEqual(file_name, "app.tar.gz")
        self.assertEqual(file_obj.read(), b"app package content")
        self.assertEqual(content_type, "application/gzip")
        self.assertEqual(kwargs["data"], {})
        self.assertEqual(response.status_code, 200)

    # capability_id: console.realtime-proxy.multipart-folder-upload-forward
    def test_multipart_folder_upload_encodes_repeated_file_field(self):
        upload_files = [
            SimpleUploadedFile(
                "file-{0}.txt".format(index),
                "content-{0}".format(index).encode("utf-8"),
                content_type="text/plain",
            )
            for index in range(5)
        ]
        request = self.factory.post(
            "/console/regions/rainbond/websocket/v2/file-operate/upload",
            data={"path": "/data", "files": upload_files},
        )

        data, files = build_multipart_payload(request)

        from requests.models import RequestEncodingMixin  # noqa: WPS433
        body, content_type = RequestEncodingMixin._encode_files(files, data)
        self.assertTrue(content_type.startswith("multipart/form-data"))
        self.assertIn(b"file-0.txt", body)
        self.assertIn(b"file-4.txt", body)

    # capability_id: console.realtime-proxy.docker-console-subprotocol
    def test_docker_console_backend_uses_webtty_subprotocol(self):
        request = self.factory.get("/console/regions/rainbond/websocket/docker_console")

        protocols = _backend_websocket_subprotocols(request, "docker_console")

        self.assertEqual(protocols, ["webtty"])

    # capability_id: console.realtime-proxy.forward-client-subprotocols
    def test_websocket_proxy_keeps_client_requested_subprotocols(self):
        request = self.factory.get(
            "/console/regions/rainbond/websocket/docker_console",
            HTTP_SEC_WEBSOCKET_PROTOCOL="webtty, other",
        )

        protocols = _backend_websocket_subprotocols(request, "docker_console")

        self.assertEqual(protocols, ["webtty", "other"])

    # capability_id: console.realtime-proxy.websocket-idle-timeout
    def test_backend_websocket_uses_short_read_timeout_for_idle_checks(self):
        request = self.factory.get("/console/regions/rainbond/websocket/docker_console")
        backend_ws = mock.Mock()
        create_connection = mock.Mock(return_value=backend_ws)

        result = open_backend_websocket(create_connection, "ws://127.0.0.1:6060/docker_console", request, "docker_console")

        self.assertIs(result, backend_ws)
        _, kwargs = create_connection.call_args
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["subprotocols"], ["webtty"])
        backend_ws.settimeout.assert_called_once_with(WEBSOCKET_PROXY_READ_TIMEOUT_SECONDS)

    # capability_id: console.realtime-proxy.docker-console-user-idle-timeout
    def test_docker_console_activity_tracker_ignores_webtty_ping(self):
        tracker = DockerConsoleActivityTracker("docker_console", idle_timeout_seconds=1800, now=lambda: 1000)

        tracker.mark_client_message("2")

        self.assertFalse(tracker.is_idle_expired(now=2799))
        self.assertTrue(tracker.is_idle_expired(now=2801))

    # capability_id: console.realtime-proxy.docker-console-user-activity
    def test_docker_console_activity_tracker_refreshes_on_user_input(self):
        current_time = [1000]
        tracker = DockerConsoleActivityTracker("docker_console", idle_timeout_seconds=1800, now=lambda: current_time[0])

        current_time[0] = 2700
        tracker.mark_client_message("1ls")

        self.assertFalse(tracker.is_idle_expired(now=4400))
        self.assertTrue(tracker.is_idle_expired(now=4501))

    # capability_id: console.realtime-proxy.non-terminal-no-user-idle-timeout
    def test_non_docker_console_activity_tracker_never_user_idle_expires(self):
        tracker = DockerConsoleActivityTracker("event_log", idle_timeout_seconds=1800, now=lambda: 1000)

        self.assertFalse(tracker.is_idle_expired(now=999999))
