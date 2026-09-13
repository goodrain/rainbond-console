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

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.application_delete_service import ApplicationDeleteService  # noqa: E402
from console.views.group import TenantGroupHandleView  # noqa: E402


class ApplicationDeleteServiceTests(SimpleTestCase):

    # capability_id: console.app.delete-shared-orchestration

    @mock.patch("console.services.application_delete_service.operation_log_service")
    @mock.patch("console.services.application_delete_service.group_service")
    @mock.patch("console.services.application_delete_service.k8s_resource_service")
    def test_shared_service_runs_the_complete_delete_orchestration(self, k8s_resources, groups, operation_logs):
        user = SimpleNamespace(user_id=1, enterprise_id="eid-1", nick_name="admin")
        tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a")
        app = SimpleNamespace(ID=7, app_id=7, app_name="AI Engine", group_name="AI Engine")
        services = [
            SimpleNamespace(service_id="svc-1", service_cname="backend"),
            SimpleNamespace(service_id="svc-2", service_cname="frontend"),
        ]
        groups.delete_app_with_resources.return_value = services
        k8s_resources.list_by_app_id.return_value = [SimpleNamespace(ID=31), SimpleNamespace(ID=32)]

        result = ApplicationDeleteService().delete_app(user, tenant, "rainbond", app)

        groups.delete_app_with_resources.assert_called_once_with(user,
                                                                 tenant,
                                                                 "rainbond",
                                                                 app,
                                                                 cascade_crd=False,
                                                                 is_enterprise_admin=False)
        operation_logs.create_app_log.assert_called_once()
        log = operation_logs.create_app_log.call_args.kwargs
        self.assertIs(log["ctx"].user, user)
        self.assertEqual(log["ctx"].tenant_name, "team-a")
        self.assertIn("backend", log["old_information"])
        self.assertEqual({"app_id": 7, "service_ids": ["svc-1", "svc-2"], "resource_ids": [31, 32]}, result)

    @mock.patch("console.services.application_delete_service.operation_log_service")
    @mock.patch("console.services.application_delete_service.group_service")
    @mock.patch("console.services.application_delete_service.k8s_resource_service")
    def test_shared_service_forwards_crd_confirmation_and_authenticated_admin(self, resources, groups, operation_logs):
        user = SimpleNamespace(enterprise_id="eid-1")
        tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a")
        app = SimpleNamespace(ID=7, app_id=7)
        context = SimpleNamespace(user=user)
        resources.list_by_app_id.return_value = []
        groups.delete_app_with_resources.return_value = []

        ApplicationDeleteService().delete_app(user,
                                              tenant,
                                              "rainbond",
                                              app,
                                              log_context=context,
                                              cascade_crd=True,
                                              is_enterprise_admin=True)

        groups.delete_app_with_resources.assert_called_once_with(user,
                                                                 tenant,
                                                                 "rainbond",
                                                                 app,
                                                                 cascade_crd=True,
                                                                 is_enterprise_admin=True)
        self.assertIs(operation_logs.create_app_log.call_args.kwargs["ctx"], context)

    def test_crd_preflight_failure_prevents_component_deletion_and_success_audit(self):
        user = SimpleNamespace(enterprise_id="eid-1")
        tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a", enterprise_id="eid-1")
        app = SimpleNamespace(ID=7, app_id=7)
        impact = {"requires_cascade": True, "crds": [{"name": "widgets.example.com"}]}
        with mock.patch("console.services.k8s_resource.k8s_resource_service.list_by_app_id",
                        return_value=[SimpleNamespace(ID=31)]), \
                mock.patch("console.services.group_service.group_service._preview_app_k8s_deletion", return_value=impact), \
                mock.patch("console.services.group_service.group_service.batch_delete_app_services",
                           return_value=[]) as delete_components, \
                mock.patch("console.services.k8s_resource.k8s_resource_service.batch_delete_k8s_resource") as delete_resources, \
                mock.patch("console.services.kubeblocks_service.kubeblocks_service.delete_kubeblocks_cluster"), \
                mock.patch("console.services.group_service.app_config_group_service.batch_delete_config_group"), \
                mock.patch("console.services.group_service.group_service.delete_app_share_records"), \
                mock.patch("console.services.group_service.group_service.delete_app"), \
                mock.patch("console.services.application_delete_service.operation_log_service.create_app_log") as audit:
            with self.assertRaises(ServiceHandleException) as raised:
                ApplicationDeleteService().delete_app(user, tenant, "rainbond", app)

        self.assertEqual(403, raised.exception.status_code)
        delete_components.assert_not_called()
        delete_resources.assert_not_called()
        audit.assert_not_called()

    @mock.patch("console.views.group.application_delete_service")
    def test_ui_view_delegates_to_the_shared_service(self, delete_service):
        view = TenantGroupHandleView()
        view.user = SimpleNamespace(user_id=1, enterprise_id="eid-1")
        view.tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a")
        view.region_name = "rainbond"
        view.app = SimpleNamespace(ID=7)
        view.is_enterprise_admin = True

        response = view.delete(SimpleNamespace(data={"cascade_crd": True}), "7")

        self.assertEqual(200, response.status_code)
        delete_service.delete_app.assert_called_once_with(view.user,
                                                          view.tenant,
                                                          "rainbond",
                                                          view.app,
                                                          log_context=view,
                                                          cascade_crd=True,
                                                          is_enterprise_admin=True)
