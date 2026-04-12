import collections
import os
from types import ModuleType, SimpleNamespace
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys  # noqa: E402

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

openapi_client_module = ModuleType("openapi_client")
openapi_client_module.ApiClient = lambda configuration=None: SimpleNamespace(configuration=configuration)
openapi_client_module.MarketOpenapiApi = lambda client=None: SimpleNamespace(client=client)

openapi_client_configuration = ModuleType("openapi_client.configuration")


class _OpenAPIConfiguration(object):
    def __init__(self):
        self.client_side_validation = False
        self.host = ""
        self.api_key = {}


openapi_client_configuration.Configuration = _OpenAPIConfiguration

openapi_client_rest = ModuleType("openapi_client.rest")


class _ApiException(Exception):
    def __init__(self, status=400, body=""):
        super().__init__(body)
        self.status = status
        self.body = body


openapi_client_rest.ApiException = _ApiException

sys.modules.setdefault("openapi_client", openapi_client_module)
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.views.app_manage import PauseAppView, UNPauseAppView  # noqa: E402


class VMManageViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_pause_view_returns_service_failure_code(self):
        view = PauseAppView()
        view.tenant = SimpleNamespace(tenant_name="demo-team")
        view.service = SimpleNamespace(service_alias="demo-vm", service_region="demo-region")
        view.user = SimpleNamespace(nick_name="tester")

        request = view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/pause", {}, format="json")
        )

        with mock.patch("console.views.app_manage.app_manage_service.pause", return_value=(507, "组件异常")):
            response = view.post(request)

        self.assertEqual(response.status_code, 507)
        self.assertEqual("组件异常", response.data["msg_show"])

    def test_unpause_view_returns_service_failure_code(self):
        view = UNPauseAppView()
        view.tenant = SimpleNamespace(tenant_name="demo-team")
        view.service = SimpleNamespace(service_alias="demo-vm", service_region="demo-region")
        view.user = SimpleNamespace(nick_name="tester")

        request = view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/unpause", {}, format="json")
        )

        with mock.patch("console.views.app_manage.app_manage_service.un_pause", return_value=(409, "操作过于频繁，请稍后再试")):
            response = view.post(request)

        self.assertEqual(response.status_code, 409)
        self.assertEqual("操作过于频繁，请稍后再试", response.data["msg_show"])
