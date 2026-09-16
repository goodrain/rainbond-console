# -*- coding: utf-8 -*-
import sys
import base64
import importlib
from types import ModuleType
from types import SimpleNamespace
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

from console.views.app_config.app_domain import (  # noqa: E402
    TenantCertificateManageView,
    certificate_operation_information,
)
from console.services.app_config.domain_service import DomainService  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402

domain_service_module = importlib.import_module("console.services.app_config.domain_service")
app_config_repository_module = importlib.import_module("console.repositories.app_config")


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


# capability_id: console.gateway.client-ca-management
class GatewayClientCAManagementTests(TestCase):
    def setUp(self):
        self.service = DomainService()
        self.tenant = SimpleNamespace(tenant_id="tenant-id", tenant_name="demo-team", namespace="tenant-ns")
        self.region = SimpleNamespace(region_name="demo-region")

    def test_add_client_ca_syncs_secret_without_private_key(self):
        certificate = "-----BEGIN CERTIFICATE-----\nclient-ca\n-----END CERTIFICATE-----"
        saved = SimpleNamespace(ID=7)

        with (
                mock.patch.object(domain_service_module.domain_repo, "get_certificate_by_alias", return_value=None),
                mock.patch.object(domain_service_module, "validate_ca_certificate") as validate_ca,
                mock.patch.object(domain_service_module.gateway_api, "create_gateway_client_ca") as create_ca,
                mock.patch.object(domain_service_module.domain_repo, "add_certificate", return_value=saved) as add_certificate,
        ):
            result = self.service.add_certificate(
                self.region,
                self.tenant,
                "partner-ca",
                "certificate-id",
                certificate,
                None,
                "client_ca",
            )

        self.assertIs(result, saved)
        validate_ca.assert_called_once_with(certificate)
        create_ca.assert_called_once_with(
            "demo-region",
            "demo-team",
            "rbd-client-ca-certificate-id",
            certificate,
        )
        add_certificate.assert_called_once_with(
            "tenant-id",
            "partner-ca",
            "certificate-id",
            base64.b64encode(certificate.encode("utf-8")).decode("utf-8"),
            "",
            "client_ca",
        )

    def test_list_client_ca_maps_secret_and_bound_domains(self):
        certificate = base64.b64encode(b"certificate").decode("utf-8")
        record = SimpleNamespace(
            alias="partner-ca",
            certificate_type="client_ca",
            certificate_id="certificate-id",
            certificate=certificate,
            ID=7,
        )
        statuses = [{"name": "rbd-client-ca-certificate-id", "bound_domains": ["api.example.com"]}]

        with (
                mock.patch.object(
                    domain_service_module.domain_repo,
                    "get_tenant_certificate_page",
                    return_value=([record], 1),
                ) as get_page,
                mock.patch.object(domain_service_module, "analyze_cert", return_value={"end_data": "2027-01-01"}),
                mock.patch.object(domain_service_module.gateway_api, "list_gateway_client_cas", return_value=statuses),
        ):
            items, total = self.service.get_certificate(
                self.tenant,
                1,
                10,
                certificate_kind="client_ca",
                region_name="demo-region",
            )

        self.assertEqual(total, 1)
        self.assertEqual(items[0]["secret_name"], "rbd-client-ca-certificate-id")
        self.assertEqual(items[0]["bound_domains"], ["api.example.com"])
        get_page.assert_called_once_with("tenant-id", 0, 9, None, "client_ca")

    def test_list_all_certificate_kinds_maps_client_ca_binding(self):
        server = SimpleNamespace(
            alias="api-server",
            certificate_type="gateway",
            certificate_id="server-id",
            certificate=base64.b64encode(b"server-certificate").decode("utf-8"),
            ID=6,
        )
        client_ca = SimpleNamespace(
            alias="partner-ca",
            certificate_type="client_ca",
            certificate_id="certificate-id",
            certificate=base64.b64encode(b"ca-certificate").decode("utf-8"),
            ID=7,
        )
        statuses = [{"name": "rbd-client-ca-certificate-id", "bound_domains": ["api.example.com"]}]

        with (
                mock.patch.object(
                    domain_service_module.domain_repo,
                    "get_tenant_certificate_page",
                    return_value=([server, client_ca], 2),
                ) as get_page,
                mock.patch.object(
                    domain_service_module,
                    "analyze_cert",
                    side_effect=[{"issued_to": ["api.example.com"]}, {"issued_to": ["Partner Root CA"]}],
                ),
                mock.patch.object(
                    domain_service_module.gateway_api,
                    "list_gateway_client_cas",
                    return_value=statuses,
                ) as list_client_cas,
        ):
            items, total = self.service.get_certificate(
                self.tenant,
                1,
                10,
                certificate_kind="all",
                region_name="demo-region",
            )

        self.assertEqual(total, 2)
        self.assertEqual([item["certificate_type"] for item in items], ["gateway", "client_ca"])
        self.assertNotIn("bound_domains", items[0])
        self.assertEqual(items[1]["bound_domains"], ["api.example.com"])
        get_page.assert_called_once_with("tenant-id", 0, 9, None, "all")
        list_client_cas.assert_called_once_with("demo-region", "demo-team")

    def test_repository_all_kind_does_not_filter_certificate_type(self):
        queryset = mock.MagicMock()
        queryset.count.return_value = 2
        queryset.__getitem__.return_value = ["server", "client-ca"]

        with mock.patch.object(app_config_repository_module.ServiceDomainCertificate, "objects") as objects:
            objects.filter.return_value = queryset
            records, total = app_config_repository_module.domain_repo.get_tenant_certificate_page(
                "tenant-id", 0, 9, None, "all")

        objects.filter.assert_called_once_with(tenant_id="tenant-id")
        queryset.filter.assert_not_called()
        queryset.exclude.assert_not_called()
        self.assertEqual(records, ["server", "client-ca"])
        self.assertEqual(total, 2)

    def test_add_client_ca_cleans_up_secret_when_database_save_fails(self):
        with (
                mock.patch.object(domain_service_module.domain_repo, "get_certificate_by_alias", return_value=None),
                mock.patch.object(domain_service_module, "validate_ca_certificate"),
                mock.patch.object(domain_service_module.gateway_api, "create_gateway_client_ca"),
                mock.patch.object(domain_service_module.gateway_api, "delete_gateway_client_ca") as delete_ca,
                mock.patch.object(
                    domain_service_module.domain_repo,
                    "add_certificate",
                    side_effect=RuntimeError("database unavailable"),
                ),
                self.assertRaises(RuntimeError),
        ):
            self.service.add_certificate(
                self.region,
                self.tenant,
                "partner-ca",
                "certificate-id",
                "certificate",
                None,
                "client_ca",
            )

        delete_ca.assert_called_once_with("demo-region", "demo-team", "rbd-client-ca-certificate-id")

    def test_client_ca_operation_log_does_not_include_certificate_material(self):
        information = certificate_operation_information(
            "partner-ca",
            "client_ca",
            "sensitive-certificate-content",
            "unexpected-private-key",
        )

        self.assertNotIn("sensitive-certificate-content", information)
        self.assertNotIn("unexpected-private-key", information)

    def test_delete_bound_client_ca_preserves_database_record(self):
        record = mock.Mock(
            certificate_type="client_ca",
            certificate_id="certificate-id",
            alias="partner-ca",
        )
        with (
                mock.patch.object(domain_service_module.domain_repo, "get_certificate_by_pk", return_value=record),
                mock.patch.object(domain_service_module.domain_repo, "list_service_domains_by_cert_id", return_value=[]),
                mock.patch.object(
                    domain_service_module.gateway_api,
                    "delete_gateway_client_ca",
                    side_effect=ServiceHandleException("client CA is in use", "客户端 CA 正在使用"),
                ),
                self.assertRaises(ServiceHandleException),
        ):
            self.service.delete_certificate_by_pk("demo-region", self.tenant, 7)

        record.delete.assert_not_called()


# capability_id: console.gateway.domain-mtls-proxy
class GatewayMTLSProxyTests(TestCase):
    def test_delete_proxy_accepts_bean_only_response(self):
        client = RegionInvokeApi.__new__(RegionInvokeApi)
        client.default_headers = {}
        with (
                mock.patch.object(
                    client,
                    "_RegionInvokeApi__get_region_access_info",
                    return_value=("https://region.example.com", "token"),
                ),
                mock.patch.object(client, "_set_headers"),
                mock.patch.object(
                    client,
                    "_delete",
                    return_value=(mock.Mock(), {"bean": {"domain": "api.example.com", "enabled": False}}),
                ),
        ):
            result = client.api_gateway_delete_proxy(
                "demo-region",
                "demo-team",
                "/api-gateway/v1/demo-team/routes/http/mtls?domain=api.example.com",
            )

        self.assertEqual(result, {"domain": "api.example.com", "enabled": False})
