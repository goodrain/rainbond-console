# -*- coding: utf-8 -*-
import sys
from types import ModuleType
from unittest import TestCase, mock

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

from rest_framework.test import APIRequestFactory  # noqa: E402

from console.views.app_config.app_domain import TenantCertificateManageView  # noqa: E402


class TenantCertificateDeleteTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TenantCertificateManageView()

    # capability_id: console.gateway.certificate-delete-idempotent
    def test_delete_missing_certificate_is_idempotent(self):
        request = self.factory.delete("/console/teams/demo-team/certificates/42")

        with (
                mock.patch(
                    "console.views.app_config.app_domain.domain_service.get_certificate_by_pk",
                    return_value=(404, "证书不存在", None),
                ) as get_certificate,
                mock.patch(
                    "console.views.app_config.app_domain.domain_service.delete_certificate_by_pk",
                ) as delete_certificate,
                mock.patch(
                    "console.views.app_config.app_domain.operation_log_service.create_team_log",
                ) as create_team_log,
        ):
            response = self.view.delete(request, certificate_id="42")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "证书删除成功")
        get_certificate.assert_called_once_with("42")
        delete_certificate.assert_not_called()
        create_team_log.assert_not_called()
