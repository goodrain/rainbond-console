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
from django.test import RequestFactory, SimpleTestCase  # noqa: E402

django.setup()

from console.services.app_actions.app_log import AppWebSocketService  # noqa: E402
from console.services.app_import_and_export_service import import_service  # noqa: E402
from console.utils.realtime_proxy import (  # noqa: E402
    build_console_realtime_proxy_url,
    build_region_realtime_proxy_url,
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
