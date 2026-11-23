"""Port path input must be rejected before ORM or region operations."""
import os
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()

from django.test import RequestFactory  # noqa: E402
from console.exception.main import AbortRequest  # noqa: E402
from console.views.app_config import app_port as port_module  # noqa: E402
from console.views import base as base_module  # noqa: E402
from www.models.main import TenantServicesPort  # noqa: E402


# capability_id: console.component.port-path-validation
class AppPortPathValidationTests(TestCase):
    def setUp(self):
        self.view = port_module.AppPortManageView()
        self.view.service = SimpleNamespace(service_id="fixture-component", service_source="third_party",
                                            service_alias="fixture", service_cname="Fixture", service_region="region")
        self.view.tenant = SimpleNamespace(tenant_id="fixture-team", tenant_name="fixture-team")
        self.view.user = SimpleNamespace(nick_name="operator", enterprise_id="fixture-enterprise")
        self.view.app = SimpleNamespace(ID=1)
        self.view.response_region = SimpleNamespace(region_id="fixture-region")

    def request(self, method, action="open_outer"):
        request = getattr(RequestFactory(), method)("/ports/fixture")
        request.data = {"action": action}
        return request

    def test_invalid_path_is_400_before_any_port_or_region_work(self):
        for method in ("get", "put", "delete"):
            for value in ("outer", "letters", "80.5", "0", "65536", "-1", True, 80.5):
                with self.subTest(method=method, value=value), \
                        mock.patch.object(port_module, "port_service") as service, \
                        mock.patch.object(port_module, "region_api") as region_api, \
                        mock.patch.object(port_module, "operation_log_service") as operation_log:
                    with self.assertRaises(AbortRequest) as raised:
                        getattr(self.view, method)(self.request(method), port=value)
                    self.assertEqual(raised.exception.status_code, 400)
                    with mock.patch.object(base_module.logger, "exception") as log_exception:
                        response = base_module.custom_exception_handler(raised.exception, {})
                    self.assertEqual(response.status_code, 400)
                    log_exception.assert_not_called()
                    self.assertEqual(service.mock_calls, [])
                    self.assertEqual(region_api.mock_calls, [])
                    self.assertEqual(operation_log.mock_calls, [])

    def test_missing_port_keeps_existing_client_error(self):
        with mock.patch.object(port_module, "port_service") as service:
            response = self.view.get(self.request("get"))
            self.assertEqual(response.status_code, 400)
            for method in ("put", "delete"):
                with self.assertRaises(AbortRequest) as raised:
                    getattr(self.view, method)(self.request(method))
                self.assertEqual(raised.exception.msg, "container_port not specify")
            self.assertEqual(service.mock_calls, [])

    def test_valid_ports_keep_operations_and_normalize_lookup_to_integer(self):
        self.view.service.service_source = "docker_run"
        for method in ("get", "put", "delete"):
            for value in (1, "1", 65535, "65535", 8080, "8080"):
                with self.subTest(method=method, value=value), \
                        mock.patch.object(port_module, "port_service") as service, \
                        mock.patch.object(port_module, "operation_log_service"):
                    port = TenantServicesPort(service_id="fixture-component", container_port=int(value))
                    service.get_service_port_by_port.return_value = port
                    service.get_port_variables.return_value = {"environment": []}
                    service.delete_port_by_container_port.return_value = port
                    service.manage_port.return_value = (200, "success", port)
                    response = getattr(self.view, method)(self.request(method), port=value)
                    self.assertEqual(response.status_code, 200)
                    lookup = service.get_service_port_by_port.call_args.args[1]
                    self.assertEqual(lookup, int(value))
                    self.assertIs(type(lookup), int)
                    if method == "delete":
                        self.assertEqual(service.delete_port_by_container_port.call_args.args[2], int(value))
                    if method == "put":
                        self.assertEqual(service.manage_port.call_args.args[3:5], (int(value), "open_outer"))

    def test_valid_open_and_close_actions_are_forwarded_unchanged(self):
        self.view.service.service_source = "docker_run"
        for action in ("open_outer", "close_outer", "open_inner", "close_inner"):
            with self.subTest(action=action), \
                    mock.patch.object(port_module, "port_service") as service, \
                    mock.patch.object(port_module, "operation_log_service"):
                port = TenantServicesPort(service_id="fixture-component", container_port=8080)
                service.get_service_port_by_port.return_value = port
                service.manage_port.return_value = (200, "success", port)
                response = self.view.put(self.request("put", action=action), port="8080")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(service.manage_port.call_args.args[3:5], (8080, action))

    def test_valid_third_party_outer_actions_preserve_domain_check_and_response(self):
        for action in ("open_outer", "close_outer"):
            with self.subTest(action=action), \
                    mock.patch.object(port_module, "port_service") as service, \
                    mock.patch.object(port_module, "operation_log_service"):
                port = TenantServicesPort(service_id="fixture-component", container_port=8080)
                service.check_domain_thirdpart.return_value = ("success", "成功", 200)
                service.get_service_port_by_port.return_value = port
                service.manage_port.return_value = (200, "success", port)
                response = self.view.put(self.request("put", action=action), port="8080")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["data"]["bean"]["container_port"], 8080)
                service.check_domain_thirdpart.assert_called_once_with(self.view.tenant, self.view.service)
                lookup_port = service.get_service_port_by_port.call_args.args[1]
                self.assertIs(type(lookup_port), int)
                self.assertEqual(lookup_port, 8080)
                self.assertEqual(service.manage_port.call_args.args[3:5], (8080, action))
