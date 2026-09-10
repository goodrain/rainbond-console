# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module = ModuleType("openapi_client.configuration")
    configuration_module.Configuration = type("Configuration", (), {})
    rest_module = ModuleType("openapi_client.rest")
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import SimpleTestCase  # noqa: E402

from console.services.application_delete_service import ApplicationDeleteService  # noqa: E402
from console.views.group import TenantGroupHandleView  # noqa: E402


class ApplicationDeleteServiceTests(SimpleTestCase):

    # capability_id: console.app.delete-shared-orchestration

    @mock.patch("console.services.application_delete_service.operation_log_service")
    @mock.patch("console.services.application_delete_service.group_service")
    @mock.patch("console.services.application_delete_service.app_config_group_service")
    @mock.patch("console.services.application_delete_service.k8s_resource_service")
    @mock.patch("console.services.application_delete_service.kubeblocks_service")
    def test_shared_service_runs_the_complete_delete_orchestration(self, kubeblocks, k8s_resources, config_groups, groups,
                                                                   operation_logs):
        user = SimpleNamespace(user_id=1, enterprise_id="eid-1", nick_name="admin")
        tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a")
        app = SimpleNamespace(ID=7, app_id=7, app_name="AI Engine", group_name="AI Engine")
        services = [
            SimpleNamespace(service_id="svc-1", service_cname="backend"),
            SimpleNamespace(service_id="svc-2", service_cname="frontend"),
        ]
        groups.batch_delete_app_services.return_value = services
        k8s_resources.list_by_app_id.return_value = [SimpleNamespace(ID=31), SimpleNamespace(ID=32)]

        result = ApplicationDeleteService().delete_app(user, tenant, "rainbond", app)

        groups.batch_delete_app_services.assert_called_once_with(user, "tenant-1", "rainbond", 7)
        kubeblocks.delete_kubeblocks_cluster.assert_called_once_with(["svc-1", "svc-2"], "rainbond")
        k8s_resources.batch_delete_k8s_resource.assert_called_once_with("eid-1", "team-a", "7", "rainbond", [31, 32])
        config_groups.batch_delete_config_group.assert_called_once_with("rainbond", "team-a", 7)
        groups.delete_app_share_records.assert_called_once_with("team-a", 7)
        groups.delete_app.assert_called_once_with(tenant, "rainbond", app)
        operation_logs.create_app_log.assert_called_once()
        self.assertEqual(["svc-1", "svc-2"], result["service_ids"])

    @mock.patch("console.views.group.application_delete_service")
    def test_ui_view_delegates_to_the_shared_service(self, delete_service):
        view = TenantGroupHandleView()
        view.user = SimpleNamespace(user_id=1, enterprise_id="eid-1")
        view.tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a")
        view.region_name = "rainbond"
        view.app = SimpleNamespace(ID=7)

        response = view.delete(SimpleNamespace(), "7")

        self.assertEqual(200, response.status_code)
        delete_service.delete_app.assert_called_once_with(view.user, view.tenant, "rainbond", view.app, log_context=view)
