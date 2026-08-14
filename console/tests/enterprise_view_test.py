# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

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
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import enterprise as enterprise_views  # noqa: E402
from console.views.enterprise import Enterprises, EnterpriseTeamNames  # noqa: E402


class EnterprisesViewTestCase(TestCase):
    def test_get_includes_team_resource_view_flag_in_enterprise_list(self):
        view = Enterprises()
        request = APIRequestFactory().get("/console/enterprises")
        request.user = mock.Mock(user_id=7)
        enterprise = mock.Mock(
            ID=1,
            enterprise_alias="demo",
            enterprise_name="Demo Enterprise",
            is_active=1,
            enterprise_id="eid-demo",
            enterprise_token="demo-token",
            create_time="2026-04-01 00:00:00",
            enable_team_resource_view=True,
        )

        with mock.patch("console.views.enterprise.enterprise_repo.get_enterprises_by_user_id", return_value=[enterprise]):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"][0]["enable_team_resource_view"], True)


class EnterpriseTeamNamesViewTestCase(TestCase):
    def test_get_preserves_global_namespace_list_with_single_column_query(self):
        tenant_manager = mock.Mock()
        tenant_manager.filter.return_value = [
            mock.Mock(namespace="namespace-a"),
            mock.Mock(namespace="namespace-other-enterprise"),
        ]
        tenant_manager.values_list.return_value = ["namespace-a", "namespace-other-enterprise"]
        request = APIRequestFactory().get("/console/enterprise/eid-a/team-names")

        with mock.patch.object(enterprise_views.Tenants, "objects", tenant_manager):
            response = EnterpriseTeamNames().get(request, "eid-a")

        tenant_manager.values_list.assert_called_once_with("namespace", flat=True)
        tenant_manager.filter.assert_not_called()
        self.assertEqual(
            response.data["data"]["bean"],
            {"tenant_names": ["namespace-a", "namespace-other-enterprise"]})
