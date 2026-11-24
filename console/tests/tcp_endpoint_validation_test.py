# -*- coding: utf-8 -*-
import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.app_config import domain_service as service  # noqa: E402
from console.views.app_config import app_domain as views  # noqa: E402
from console.views.base import RegionTenantHeaderView  # noqa: E402
from www.models.main import ServiceTcpDomain  # noqa: E402

import importlib  # noqa: E402

domain_module = importlib.import_module("console.services.app_config.domain_service")


# capability_id: console.gateway.tcp-endpoint-validation
class TCPEndpointValidationTests(TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tcp-fixture-team", tenant_name="tcp-fixture-team")
        self.user = SimpleNamespace(user_id=1)
        self.component = SimpleNamespace(
            tenant_id=self.tenant.tenant_id, service_id="tcp-fixture-service", service_alias="fixture",
            service_cname="fixture", service_region="fixture-region", service_source="docker_image")
        self.region = SimpleNamespace(region_id="fixture-region-id", region_name="fixture-region")
        self.old_rule = ServiceTcpDomain.objects.create(
            tcp_rule_id="fixture-rule", tenant_id=self.tenant.tenant_id, service_id=self.component.service_id,
            service_name="fixture", service_alias="fixture", region_id=self.region.region_id,
            container_port=8080, protocol="tcp", end_point="0.0.0.0:30000", type=0)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.bind_api = self.stack.enter_context(mock.patch.object(domain_module.region_api, "bindTcpDomain"))
        self.update_api = self.stack.enter_context(mock.patch.object(domain_module.region_api, "updateTcpDomain"))
        self.region_lookup = self.stack.enter_context(mock.patch.object(
            domain_module.region_repo, "get_region_by_region_name", return_value=self.region))
        self.stack.enter_context(mock.patch.object(
            domain_module.port_repo, "get_service_port_by_port", return_value=SimpleNamespace(protocol="tcp")))

    def bind(self, endpoint, default_port=30000):
        return service.bind_tcpdomain(self.tenant, self.user, self.component, endpoint, 8080, default_port, [], None)

    def update(self, endpoint):
        return service.update_tcpdomain(self.tenant, self.user, self.component, endpoint, 8080,
                                        self.old_rule.tcp_rule_id, "tcp", 1, [], None)

    def assert_invalid_without_side_effects(self, operation):
        invalid = [None, True, 30000, [], {}, "", "host", ":30000", "host:", "host:abc", "host:1.5",
                   "host:-1", "host:0", "host:65536", "host:+30000", "host:٣٠٠٠٠", "bad host:30000",
                   "http://host:30000", "host/path:30000", "host:30000?x", "host:30000:1",
                   "999.1.2.3:30000", "-bad.example:30000", "bad..example:30000", "[::1]:30000",
                   "::1:30000", "[not-ipv6]:30000", "host\nname:30000", "host\x00:30000",
                   "a" * 64 + ".example:30000", ".".join(["a" * 63] * 4) + ":30000"]
        for endpoint in invalid:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ServiceHandleException) as raised:
                    operation(endpoint)
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(ServiceTcpDomain.objects.count(), 1)
                self.old_rule.refresh_from_db()
                self.assertEqual(self.old_rule.end_point, "0.0.0.0:30000")
                self.bind_api.assert_not_called()
                self.update_api.assert_not_called()

    def test_invalid_create_endpoint_is_rejected_before_region_or_database_changes(self):
        self.assert_invalid_without_side_effects(self.bind)

    def test_invalid_update_endpoint_is_rejected_before_region_or_database_changes(self):
        self.assert_invalid_without_side_effects(self.update)

    def test_valid_create_forwards_host_and_integer_port_and_persists_canonical_endpoint(self):
        cases = [("127.0.0.1:30001", "127.0.0.1", 30001), ("0.0.0.0:30002", "0.0.0.0", 30002),
                 ("gateway.example:30003", "gateway.example", 30003), ("gateway:30004", "gateway", 30004),
                 (" Gateway.Example. : 030005 ", "Gateway.Example.", 30005), ("host:65535", "host", 65535)]
        for endpoint, host, port in cases:
            with self.subTest(endpoint=endpoint):
                result = self.bind(endpoint)
                body = self.bind_api.call_args.args[2]
                self.assertEqual(body["ip"], host)
                self.assertEqual(body["port"], port)
                self.assertEqual(body["container_port"], 8080)
                self.assertEqual(result["end_point"], "{}:{}".format(host, port))
                self.assertTrue(ServiceTcpDomain.objects.filter(
                    tcp_rule_id=result["tcp_rule_id"], end_point=result["end_point"]).exists())
        self.assertEqual(self.bind_api.call_count, len(cases))

    def test_default_port_classification_stays_unchanged(self):
        default = self.bind("0.0.0.0:30000")
        custom = self.bind("0.0.0.0:30001")
        self.assertEqual(ServiceTcpDomain.objects.get(tcp_rule_id=default["tcp_rule_id"]).type, 0)
        self.assertEqual(ServiceTcpDomain.objects.get(tcp_rule_id=custom["tcp_rule_id"]).type, 1)

    def test_valid_update_keeps_rule_identity_and_replaces_endpoint(self):
        code, message = self.update(" gateway.example : 030001 ")
        self.assertEqual((code, message), (200, "success"))
        body = self.update_api.call_args.args[2]
        self.assertEqual((body["ip"], body["port"]), ("gateway.example", 30001))
        self.assertEqual(body["tcp_rule_id"], "fixture-rule")
        self.assertEqual(ServiceTcpDomain.objects.count(), 1)
        self.assertEqual(ServiceTcpDomain.objects.get(tcp_rule_id="fixture-rule").end_point, "gateway.example:30001")

    def test_create_preserves_external_failure_without_creating_local_rule(self):
        self.bind_api.side_effect = RuntimeError("fixture gateway unavailable")
        with self.assertRaisesRegex(RuntimeError, "fixture gateway unavailable"):
            self.bind("gateway.example:30001")
        self.assertEqual(ServiceTcpDomain.objects.count(), 1)

    def test_update_preserves_external_failure_without_deleting_existing_rule(self):
        self.update_api.side_effect = RuntimeError("fixture gateway unavailable")
        with self.assertRaisesRegex(RuntimeError, "fixture gateway unavailable"):
            self.update("gateway.example:30001")
        self.assertEqual(ServiceTcpDomain.objects.count(), 1)
        self.old_rule.refresh_from_db()
        self.assertEqual(self.old_rule.end_point, "0.0.0.0:30000")

    def test_create_does_not_turn_upstream_404_into_a_saved_rule(self):
        failure = domain_module.region_api.CallApiError(
            "fixture", "/tcp-rule", "POST", SimpleNamespace(status=404), {})
        self.bind_api.side_effect = failure
        with self.assertRaises(domain_module.region_api.CallApiError) as raised:
            self.bind("gateway.example:30001")
        self.assertIs(raised.exception, failure)
        self.assertEqual(ServiceTcpDomain.objects.count(), 1)

    def test_update_does_not_turn_upstream_404_into_a_saved_rule(self):
        failure = domain_module.region_api.CallApiError(
            "fixture", "/tcp-rule", "PUT", SimpleNamespace(status=404), {})
        self.update_api.side_effect = failure
        with self.assertRaises(domain_module.region_api.CallApiError) as raised:
            self.update("gateway.example:30001")
        self.assertIs(raised.exception, failure)
        self.old_rule.refresh_from_db()
        self.assertEqual(self.old_rule.end_point, "0.0.0.0:30000")

    def test_update_missing_rule_returns_404_before_gateway_request(self):
        self.old_rule.delete()
        with self.assertRaises(ServiceHandleException) as raised:
            self.update("gateway.example:30001")
        self.assertEqual(raised.exception.status_code, 404)
        self.update_api.assert_not_called()
        self.assertEqual(ServiceTcpDomain.objects.count(), 0)

    def test_update_foreign_team_rule_returns_404_before_gateway_request(self):
        self.old_rule.tenant_id = "foreign-team"
        self.old_rule.save()
        with self.assertRaises(ServiceHandleException) as raised:
            self.update("gateway.example:30001")
        self.assertEqual(raised.exception.status_code, 404)
        self.update_api.assert_not_called()
        self.old_rule.refresh_from_db()
        self.assertEqual(self.old_rule.tenant_id, "foreign-team")
        self.assertEqual(self.old_rule.end_point, "0.0.0.0:30000")

    def test_update_another_component_rule_returns_404_before_gateway_request(self):
        self.old_rule.service_id = "different-component"
        self.old_rule.save()
        with self.assertRaises(ServiceHandleException) as raised:
            self.update("gateway.example:30001")
        self.assertEqual(raised.exception.status_code, 404)
        self.update_api.assert_not_called()
        self.old_rule.refresh_from_db()
        self.assertEqual(self.old_rule.service_id, "different-component")

    def test_direct_calls_cannot_use_a_component_from_another_team(self):
        self.component.tenant_id = "foreign-team"
        for operation in (self.bind, self.update):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(ServiceHandleException) as raised:
                    operation("gateway.example:30001")
                self.assertEqual(raised.exception.status_code, 404)
                self.bind_api.assert_not_called()
                self.update_api.assert_not_called()
        self.old_rule.refresh_from_db()
        self.assertEqual(self.old_rule.end_point, "0.0.0.0:30000")

    def view_request(self, method, endpoint, whether_open=True):
        payload = {"service_id": self.component.service_id, "container_port": 8080, "end_point": endpoint,
                   "tcp_rule_id": self.old_rule.tcp_rule_id, "whether_open": whether_open, "type": 1}
        request = getattr(APIRequestFactory(), method)("/tcpdomain", payload, format="json")

        def initial(view, request, *args, **kwargs):
            view.tenant = self.tenant
            view.user = self.user

        with mock.patch.object(RegionTenantHeaderView, "initial", initial), \
                mock.patch.object(views.service_repo, "get_service_by_service_id", return_value=self.component), \
                mock.patch.object(views.port_service, "get_service_port_by_port",
                                  return_value=SimpleNamespace(container_port=8080, protocol="tcp", port_alias="",
                                                               is_outer_service=True)), \
                mock.patch.object(views.port_service, "manage_port", return_value=(200, "success", {})) as manage:
            response = views.ServiceTcpDomainView.as_view()(request)
        return response, manage

    def test_create_view_validates_before_whether_open_can_change_region(self):
        response, manage = self.view_request("post", "gateway-without-port")
        self.assertEqual(response.status_code, 400)
        manage.assert_not_called()
        self.bind_api.assert_not_called()
        self.assertEqual(ServiceTcpDomain.objects.count(), 1)

    def test_update_view_rejects_non_string_endpoint_as_400(self):
        response, manage = self.view_request("put", {"host": "gateway", "port": 30000})
        self.assertEqual(response.status_code, 400)
        manage.assert_not_called()
        self.update_api.assert_not_called()
        self.old_rule.refresh_from_db()
        self.assertEqual(self.old_rule.end_point, "0.0.0.0:30000")

    def test_create_view_rejects_foreign_component_before_opening_its_port(self):
        self.component.tenant_id = "foreign-team"
        response, manage = self.view_request("post", "gateway.example:30001")
        self.assertEqual(response.status_code, 404)
        manage.assert_not_called()
        self.bind_api.assert_not_called()

    def test_update_view_rejects_foreign_component_before_gateway_request(self):
        self.component.tenant_id = "foreign-team"
        response, _ = self.view_request("put", "gateway.example:30001")
        self.assertEqual(response.status_code, 404)
        self.update_api.assert_not_called()

    def test_create_view_normalizes_before_duplicate_check(self):
        response, manage = self.view_request("post", " 0.0.0.0 : 030000 ", whether_open=False)
        self.assertEqual(response.data["code"], 400)
        self.assertEqual(response.data["msg_show"], "策略已存在")
        manage.assert_not_called()
        self.bind_api.assert_not_called()

    def test_valid_create_view_still_uses_existing_success_response(self):
        response, manage = self.view_request("post", "gateway.example:30001", whether_open=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["end_point"], "gateway.example:30001")
        manage.assert_not_called()
        self.assertEqual(self.bind_api.call_count, 1)

    def test_valid_update_view_still_uses_existing_success_response(self):
        response, _ = self.view_request("put", "gateway.example:30001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "策略修改成功")
        self.assertEqual(ServiceTcpDomain.objects.get(tcp_rule_id="fixture-rule").end_point, "gateway.example:30001")
