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
    rest_module.ApiException = type("ApiException", (Exception,), {})
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

from django.db.models.query import QuerySet  # noqa: E402
from django.test import RequestFactory  # noqa: E402

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)

from console.views.app_create.app_check import AppCheck  # noqa: E402


# capability_id: console.deploy-diagnostics.source-check


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AppCheckSourceDiagnosticTests(TestCase):
    def test_get_reports_source_check_failure_without_changing_response(self):
        view = AppCheck()
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.service = Obj(
            service_region="rainbond",
            service_id="svc-1",
            service_alias="grsource",
            service_cname="源码组件",
            service_source="source_code",
            code_from="gitlab_manual",
            git_url="https://git.example.com/demo.git",
            code_version="master",
            server_type="git",
            create_status="checking",
        )
        view.app = Obj(ID=12, group_name="demo-app")
        data = {
            "check_status": "failure",
            "error_infos": [{"error_info": "获取代码超时 请确认源码仓库能否正常访问"}],
            "service_info": [],
        }

        request = RequestFactory().get("/console/check", {"check_uuid": "check-1"})
        with mock.patch("console.views.app_create.app_check.app_check_service.get_service_check_info",
                        return_value=(200, "success", data)), \
                mock.patch("console.views.app_create.app_check.app_check_service.wrap_service_check_info",
                           return_value={"check_status": "failure", "error_infos": data["error_infos"], "service_info": []}), \
                mock.patch(
                    "console.views.app_create.app_check.enterprise_first_deploy_service.safe_report_source_check_failure"
                ) as mock_report:
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["check_status"], "failure")
        mock_report.assert_called_once()
        kwargs = mock_report.call_args[1]
        self.assertEqual(kwargs["reason"], "获取代码超时 请确认源码仓库能否正常访问")
        self.assertEqual(kwargs["source_context"]["git_url"], "https://git.example.com/demo.git")
        self.assertEqual(kwargs["source_context"]["check_uuid"], "check-1")
