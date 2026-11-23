# -*- coding: utf-8 -*-
import os
from types import SimpleNamespace
from unittest import TestCase, mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
django.setup()

from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import AbortRequest  # noqa: E402
from console.views.app_config import app_domain as app_domain_module  # noqa: E402
from console.views.base import custom_exception_handler  # noqa: E402


# capability_id: console.gateway.domain-query-port-validation
class ServiceDomainPortValidationTests(TestCase):
    def setUp(self):
        self.view = app_domain_module.ServiceDomainView()
        self.view.service = SimpleNamespace(service_id="component-1")
        self.domain_call = mock.patch.object(app_domain_module.domain_service, "get_port_bind_domains")
        self.get_domains = self.domain_call.start()
        self.addCleanup(self.domain_call.stop)

    def query(self, value=None, present=True):
        data = {"container_port": value} if present else {}
        request = self.view.initialize_request(
            APIRequestFactory().get("/console/teams/team-1/apps/component-1/domain", data)
        )
        return self.view.get(request)

    def assert_invalid(self, query):
        with self.assertRaises(AbortRequest) as error:
            query()
        response = custom_exception_handler(error.exception, {"view": self.view})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 400)
        self.get_domains.assert_not_called()

    def test_missing_port_returns_native_400_before_domain_query(self):
        self.assert_invalid(lambda: self.query(present=False))

    def test_invalid_query_string_ports_return_native_400(self):
        for value in ("", "outer", "8080.5", "0", "-1", "65536", "999999999999999999999999"):
            with self.subTest(value=value):
                self.assert_invalid(lambda: self.query(value))

    def test_non_scalar_query_values_are_rejected_without_coercion(self):
        for value in (None, True, 80.5, [], {}):
            with self.subTest(value=value):
                request = self.view.initialize_request(APIRequestFactory().get("/"))
                with mock.patch.object(request._request, "GET", {"container_port": value}):
                    self.assert_invalid(lambda: self.view.get(request))

    def test_valid_ports_are_passed_as_integers_with_success_contract_preserved(self):
        expected = [{"domain_name": "first.example.test"}, {"domain_name": "second.example.test"}]
        self.get_domains.return_value = [SimpleNamespace(to_dict=lambda value=item: value) for item in expected]
        for value in ("1", "80", "8080", "65535"):
            with self.subTest(value=value):
                response = self.query(value)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["code"], 200)
                self.assertEqual(response.data["data"]["list"], expected)
                self.get_domains.assert_called_with(self.view.service, int(value))

    def test_empty_domain_list_keeps_success_response(self):
        self.get_domains.return_value = []

        response = self.query("8080")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], [])
