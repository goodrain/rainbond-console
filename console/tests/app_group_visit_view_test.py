# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    typing.NotRequired = typing.Optional

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration(object):
        def __init__(self):
            self.host = ""
            self.api_key = {}

    configuration_module.Configuration = _Configuration
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
if "rest_framework_simplejwt.tokens" not in sys.modules:
    simplejwt_module = ModuleType("rest_framework_simplejwt")
    tokens_module = ModuleType("rest_framework_simplejwt.tokens")
    tokens_module.AccessToken = object
    simplejwt_module.tokens = tokens_module
    sys.modules["rest_framework_simplejwt"] = simplejwt_module
    sys.modules["rest_framework_simplejwt.tokens"] = tokens_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import RequestFactory  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.views.app_overview import AppGroupVisitView  # noqa: E402


# capability_id: console.app-overview.group-visit-resilience
class AppGroupVisitViewTestCase(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.view = AppGroupVisitView()
        self.team = mock.Mock(tenant_name="demo")

    def test_get_skips_components_deleted_after_topology_load(self):
        request = self.request_factory.get("/console/teams/demo/group/service/visit", {"service_alias": "missing-active"})
        active_service = mock.Mock(service_id="service-active")

        def get_access_info(team, service):
            if service is None:
                raise AttributeError("'NoneType' object has no attribute 'service_id'")
            return "http", [{"url": "https://example.com"}]

        with mock.patch("console.views.app_overview.team_services.get_tenant_by_tenant_name",
                        return_value=self.team), \
                mock.patch("console.views.app_overview.service_repo.get_service_by_service_alias",
                           side_effect=[None, active_service]), \
                mock.patch("console.views.app_overview.port_service.get_access_info",
                           side_effect=get_access_info) as access_info:
            response = self.view.get(request, "demo")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]["list"]), 1)
        access_info.assert_called_once_with(self.team, active_service)

    def test_get_preserves_service_handle_exception(self):
        request = self.request_factory.get("/console/teams/demo/group/service/visit", {"service_alias": "active"})
        service = mock.Mock(service_id="service-active")
        error = ServiceHandleException(msg="region unavailable", msg_show="数据中心不可用", status_code=503)

        with mock.patch("console.views.app_overview.team_services.get_tenant_by_tenant_name",
                        return_value=self.team), \
                mock.patch("console.views.app_overview.service_repo.get_service_by_service_alias",
                           return_value=service), \
                mock.patch("console.views.app_overview.port_service.get_access_info", side_effect=error):
            with self.assertRaises(ServiceHandleException) as raised:
                self.view.get(request, "demo")

        self.assertIs(raised.exception, error)

    def test_get_reports_regular_exception_without_python2_message_attribute(self):
        request = self.request_factory.get("/console/teams/demo/group/service/visit", {"service_alias": "active"})
        service = mock.Mock(service_id="service-active")

        with mock.patch("console.views.app_overview.team_services.get_tenant_by_tenant_name",
                        return_value=self.team), \
                mock.patch("console.views.app_overview.service_repo.get_service_by_service_alias",
                           return_value=service), \
                mock.patch("console.views.app_overview.port_service.get_access_info",
                           side_effect=ValueError("invalid access data")):
            response = self.view.get(request, "demo")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg"], "invalid access data")
