# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
if "openapi_client" not in sys.modules:
    openapi_client = ModuleType("openapi_client")
    openapi_client.ApiClient = object
    openapi_client.MarketOpenapiApi = object
    configuration = ModuleType("openapi_client.configuration")
    configuration.Configuration = type("Configuration", (), {})
    rest = ModuleType("openapi_client.rest")
    rest.ApiException = type("ApiException", (Exception, ), {})
    sys.modules["openapi_client"] = openapi_client
    sys.modules["openapi_client.configuration"] = configuration
    sys.modules["openapi_client.rest"] = rest

from django.http import StreamingHttpResponse  # noqa: E402
from django.test import RequestFactory, SimpleTestCase  # noqa: E402
from django.urls import resolve  # noqa: E402

from console.utils import perms_route_config as perms  # noqa: E402


class AppEventLogStreamViewTests(SimpleTestCase):
    def test_get_uses_component_region_and_fixed_upstream_path(self):
        from console.views import app_event

        view = app_event.AppEventLogStreamView()
        view.service = SimpleNamespace(service_region="component-region")
        request = RequestFactory().get("/console/ignored?region_name=caller-region&path=/arbitrary")
        upstream_response = StreamingHttpResponse(iter(["data: {}\n\n"]), content_type="text/event-stream")

        with mock.patch.object(app_event.region_api, "sse_proxy", return_value=upstream_response) as sse_proxy:
            response = view.get(request, eventId="event-1")

        sse_proxy.assert_called_once_with("component-region", "/v2/events/event-1/stream")
        self.assertIs(response, upstream_response)

    def test_route_is_component_scoped_and_requires_overview_permission(self):
        from console.views.app_event import AppEventLogStreamView

        match = resolve("/console/teams/demo-team/apps/demo-service/events/event-1/stream")

        self.assertIs(match.func.view_class, AppEventLogStreamView)
        self.assertEqual(match.kwargs["tenantName"], "demo-team")
        self.assertEqual(match.kwargs["serviceAlias"], "demo-service")
        self.assertEqual(match.kwargs["eventId"], "event-1")
        self.assertEqual(match.kwargs["__message"], perms.APP_OVERVIEW_PERMS["__message"])

    def test_route_rejects_unauthenticated_requests(self):
        path = "/console/teams/demo-team/apps/demo-service/events/event-1/stream"
        match = resolve(path)

        response = match.func(RequestFactory().get(path), **match.kwargs)

        self.assertEqual(response.status_code, 401)
