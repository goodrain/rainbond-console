# -*- coding: utf-8 -*-
import json
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _OpenAPIConfiguration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _OpenAPIApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    configuration_module.Configuration = _OpenAPIConfiguration
    rest_module.ApiException = _OpenAPIApiException
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

try:
    import requests as _requests  # noqa: F401
except ImportError:
    requests = ModuleType("requests")

    def _missing_requests_get(*args, **kwargs):
        return None

    requests.get = _missing_requests_get
    sys.modules["requests"] = requests

try:
    import django  # noqa: E402
except ImportError:
    django = None

if django is not None:
    django.setup()
else:
    django_http = ModuleType("django.http")

    class JsonResponse(object):
        def __init__(self, data=None, status=200, safe=True, **kwargs):
            self.data = data
            self.status_code = status
            self.safe = safe

    django_http.JsonResponse = JsonResponse

    django_cache = ModuleType("django.views.decorators.cache")

    def _never_cache(func):
        return func

    django_cache.never_cache = _never_cache

    views_base = ModuleType("console.views.base")
    views_base.JWTAuthApiView = object

    region_api = ModuleType("www.apiclient.regionapi")

    class RegionInvokeApiStub(object):
        pass

    region_api.RegionInvokeApi = RegionInvokeApiStub

    region_repo = ModuleType("console.repositories.region_repo")
    region_repo.region_repo = object()

    return_message = ModuleType("www.utils.return_message")

    def _general_message(*args, **kwargs):
        return {}

    return_message.general_message = _general_message

    rest_response = ModuleType("rest_framework.response")
    rest_response.Response = object

    sys.modules.setdefault("django", ModuleType("django"))
    sys.modules["django.http"] = django_http
    sys.modules.setdefault("django.views", ModuleType("django.views"))
    sys.modules.setdefault("django.views.decorators", ModuleType("django.views.decorators"))
    sys.modules["django.views.decorators.cache"] = django_cache
    sys.modules["console.views.base"] = views_base
    sys.modules["www.apiclient.regionapi"] = region_api
    sys.modules["console.repositories.region_repo"] = region_repo
    sys.modules["www.utils.return_message"] = return_message
    sys.modules.setdefault("rest_framework", ModuleType("rest_framework"))
    sys.modules["rest_framework.response"] = rest_response

from console.views import upgrade as upgrade_view  # noqa: E402


def _json_response_data(response):
    if hasattr(response, "data"):
        return response.data
    return json.loads(response.content.decode("utf-8"))


class UpgradeVersionViewTests(TestCase):
    def test_fetch_json_data_skips_external_request_when_default_market_disabled(self):
        with mock.patch.dict(os.environ, {
            "DISABLE_DEFAULT_APP_MARKET": "true",
            "DISABLE_CLOUD_MARKET": "",
        }, clear=False), \
                mock.patch("console.views.upgrade.requests.get") as requests_get:
            data = upgrade_view.fetch_json_data()

        self.assertIsNone(data)
        requests_get.assert_not_called()

    def test_fetch_json_data_uses_short_timeout(self):
        response = mock.Mock()
        response.json.return_value = [{"version": "v1"}]

        with mock.patch.dict(os.environ, {
            "DISABLE_DEFAULT_APP_MARKET": "",
            "DISABLE_CLOUD_MARKET": "",
            "VERSION_INFO_URL": "https://example.com/upgrade-versions.json",
        }, clear=False), \
                mock.patch("console.views.upgrade.requests.get", return_value=response) as requests_get:
            data = upgrade_view.fetch_json_data()

        self.assertEqual([{"version": "v1"}], data)
        response.raise_for_status.assert_called_once_with()
        requests_get.assert_called_once_with("https://example.com/upgrade-versions.json", timeout=2)

    def test_upgrade_versions_are_sorted_by_semantic_version_desc(self):
        data = [
            {
                "version": "v6.9.2-release"
            },
            {
                "version": "v6.9.1-release"
            },
            {
                "version": "v6.2.0-release"
            },
            {
                "version": "v6.10.0-release"
            },
            {
                "version": "v6.1.3-release"
            },
        ]

        with mock.patch("console.views.upgrade.fetch_json_data", return_value=data):
            response = upgrade_view.UpgradeVersionLView().get(mock.Mock())

        self.assertEqual([
            "v6.10.0-release",
            "v6.9.2-release",
            "v6.9.1-release",
            "v6.2.0-release",
            "v6.1.3-release",
        ], _json_response_data(response))
