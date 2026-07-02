# -*- coding: utf-8 -*-
import collections
import collections.abc
import importlib
import os
import sys
import typing
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

from typing_extensions import NotRequired

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

if not hasattr(typing, "NotRequired"):
    typing.NotRequired = NotRequired

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
    openapi_client_module.V1AppModelCreateRequest = dict
    openapi_client_module.V1CreateAppPaaSVersionRequest = dict
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
openssl_module = ModuleType("OpenSSL")
openssl_crypto_module = ModuleType("OpenSSL.crypto")
openssl_module.crypto = openssl_crypto_module
sys.modules.setdefault("OpenSSL", openssl_module)
sys.modules.setdefault("OpenSSL.crypto", openssl_crypto_module)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from console.services.app_config.env_service import AppEnvVarService  # noqa: E402
from console.services.app_config.port_service import AppPortService  # noqa: E402
from console.views.base import custom_exception_handler  # noqa: E402
from openapi.serializer.app_serializer import ComponentPortReqSerializers  # noqa: E402
from openapi.serializer.gateway_serializer import HTTPConfiguration  # noqa: E402
from rest_framework.exceptions import ValidationError  # noqa: E402


class OpenAPIServiceConfigValidationTest(TestCase):

    # capability_id: openapi.service-config.env-note-optional
    @mock.patch("console.services.app_config.env_service.env_var_repo")
    def test_update_or_create_envs_defaults_missing_note(self, mock_env_repo):
        existing_env = SimpleNamespace(attr_name="FOO", ID=7)
        mock_env_repo.get_service_env.side_effect = [[existing_env], []]
        service = SimpleNamespace(tenant_id="tenant-id", service_id="service-id")
        team = SimpleNamespace(tenant_name="team-name")
        app_env_service = AppEnvVarService()

        with mock.patch.object(app_env_service, "update_env_by_env_id", return_value=(200, "success", None)) as mock_update:
            app_env_service.update_or_create_envs(team, service, [{
                "name": "FOO",
                "value": "bar",
                "is_change": True,
                "scope": "inner",
            }])

        mock_update.assert_called_once_with(team, service, "7", "", "bar")

    # capability_id: openapi.service-config.port-alias-blank
    def test_component_port_serializer_allows_blank_alias_for_auto_generation(self):
        serializer = ComponentPortReqSerializers(data={
            "port": 8080,
            "protocol": "http",
            "port_alias": "",
            "is_inner_service": False,
        })

        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data["port_alias"], "")

    # capability_id: openapi.service-config.validation-error-shape
    def test_validation_error_response_does_not_expose_traceback(self):
        serializer = ComponentPortReqSerializers(data={
            "protocol": "http",
            "is_inner_service": False,
        })

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        response = custom_exception_handler(context.exception, {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "参数错误")
        self.assertIn("port", response.data["err"])
        self.assertNotIn("error_trace", response.data)

    # capability_id: openapi.service-config.http-set-headers-optional
    def test_http_configuration_defaults_missing_set_headers(self):
        serializer = HTTPConfiguration(data={})

        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data["set_headers"], [])

    # capability_id: openapi.service-config.domain-set-headers-service-default
    def test_http_rule_config_defaults_missing_set_headers_in_service(self):
        domain_service_module = importlib.import_module("console.services.app_config.domain_service")
        service_domain = SimpleNamespace(service_id="service-id")
        component = SimpleNamespace(service_alias="component-a")

        with mock.patch.object(domain_service_module, "get_object_or_404") as mock_get_object, \
                mock.patch.object(domain_service_module, "configuration_repo") as mock_configuration_repo, \
                mock.patch.object(domain_service_module, "region_api") as mock_region_api:
            mock_get_object.side_effect = [service_domain, component]
            mock_configuration_repo.get_configuration_by_rule_id.return_value = None
            mock_region_api.upgrade_configuration.return_value = (SimpleNamespace(status=200), {})
            domain_service = domain_service_module.DomainService()

            domain_service.update_http_rule_config(SimpleNamespace(tenant_name="team-a"), "region-a", "rule-id", {})

            body = mock_region_api.upgrade_configuration.call_args[0][3]["body"]
            self.assertEqual(body["set_headers"], [])
            mock_configuration_repo.add_configuration.assert_called_once()

    # capability_id: openapi.service-config.port-open-outer-app-context
    def test_manage_port_resolves_app_when_opening_outer_port(self):
        port_service_module = importlib.import_module("console.services.app_config.port_service")
        app = SimpleNamespace(app_id=123)
        tenant = SimpleNamespace(tenant_id="tenant-id", tenant_name="team-name")
        service = SimpleNamespace(service_id="service-id", service_region="region-a")
        deal_port = SimpleNamespace(container_port=8080, is_inner_service=True)

        with mock.patch.object(port_service_module, "group_repo") as mock_group_repo, \
                mock.patch.object(port_service_module, "region_repo") as mock_region_repo, \
                mock.patch.object(port_service_module, "port_repo") as mock_port_repo:
            port_service = AppPortService()
            mock_region_repo.get_region_by_region_name.return_value = SimpleNamespace(region_name="region-a")
            mock_group_repo.get_by_service_id.return_value = app
            mock_port_repo.get_service_port_by_port.side_effect = [deal_port, deal_port]
            with mock.patch.object(port_service, "_AppPortService__check_params", return_value=(200, "success")), \
                    mock.patch.object(port_service, "_AppPortService__open_outer", return_value=(200, "success")) as mock_open:
                code, _, _ = port_service.manage_port(
                    tenant, service, "region-a", 8080, "open_outer", "http", "WEB8080", "", "tester")

            self.assertEqual(code, 200)
            mock_group_repo.get_by_service_id.assert_called_once_with("tenant-id", "service-id")
            mock_open.assert_called_once_with(
                tenant, service, mock_region_repo.get_region_by_region_name.return_value, deal_port, app, "tester")
