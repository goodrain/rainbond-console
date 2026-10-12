# coding: utf-8
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.app_config import app_domain as app_domain_module  # noqa: E402


class ServiceDomainViewTests(TestCase):
    # capability_id: console.gateway.domain-port-required
    def test_post_rejects_missing_component_port_before_binding_domain(self):
        view = app_domain_module.ServiceDomainView()
        view.tenant = SimpleNamespace(tenant_id="team-1", tenant_name="demo-team")
        view.user = SimpleNamespace(enterprise_id="eid-1")
        view.service = SimpleNamespace(
            service_id="service-1",
            service_alias="demo",
            service_cname="Demo",
            service_region="rainbond",
        )
        view.app = SimpleNamespace(ID=42, app_id=42)
        view.region = SimpleNamespace(region_name="rainbond")
        request = view.initialize_request(
            APIRequestFactory().post(
                "/console/teams/demo-team/apps/demo/domain",
                {
                    "domain_name": "demo.example.com",
                    "container_port": 8080,
                    "protocol": "http",
                },
                format="json",
            )
        )

        with mock.patch.object(
                app_domain_module.port_repo,
                "get_service_port_by_port",
                return_value=None,
        ), mock.patch.object(
            app_domain_module.domain_repo,
            "get_domain_by_name_and_port_and_protocol",
            return_value=None,
        ), mock.patch.object(app_domain_module.domain_service, "bind_domain") as bind_domain, mock.patch.object(
            app_domain_module.region_api,
            "api_gateway_bind_http_domain",
        ) as bind_gateway, mock.patch.object(
            app_domain_module.operation_log_service,
            "create_component_log",
        ):
            response = view.post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "组件端口不存在")
        bind_domain.assert_not_called()
        bind_gateway.assert_not_called()
