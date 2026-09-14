# coding: utf-8
import sys
from types import SimpleNamespace
from types import ModuleType
from unittest import TestCase, mock

openapi_client = ModuleType("openapi_client")
openapi_client.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
openapi_client.ApiClient = type("ApiClient", (), {"__init__": lambda self, configuration=None: None})
sys.modules.setdefault("openapi_client", openapi_client)
openapi_client_configuration = ModuleType("openapi_client.configuration")
openapi_client_configuration.Configuration = type(
    "Configuration",
    (),
    {"__init__": lambda self: setattr(self, "api_key", {})},
)
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
openapi_client_rest = ModuleType("openapi_client.rest")
openapi_client_rest.ApiException = type("ApiException", (Exception, ), {})
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)

from rest_framework.exceptions import ValidationError  # noqa: E402

from console.exception.main import NoPermissionsError  # noqa: E402
from console.views.login_security import LoginSecurityConfigView  # noqa: E402


class LoginSecurityConfigViewTests(TestCase):
    def make_view(self, enterprise_id="eid-1", is_admin=True):
        view = LoginSecurityConfigView()
        view.user = SimpleNamespace(enterprise_id=enterprise_id)
        view.is_enterprise_admin = is_admin
        return view

    # capability_id: console.login-security.admin-api
    @mock.patch("console.views.login_security.login_security_config_service")
    def test_admin_can_read_and_update_two_switches(self, config_service):
        config_service.get_config.return_value = {
            "login_captcha_enabled": False,
            "login_limit_enabled": False,
        }
        config_service.update_config.return_value = {
            "login_captcha_enabled": True,
            "login_limit_enabled": True,
        }
        view = self.make_view()

        get_response = view.get(SimpleNamespace(), "eid-1")
        put_response = view.put(
            SimpleNamespace(data={
                "login_captcha_enabled": True,
                "login_limit_enabled": True
            }),
            "eid-1",
        )

        self.assertEqual(get_response.data["data"]["bean"]["login_captcha_enabled"], False)
        self.assertEqual(put_response.data["data"]["bean"]["login_limit_enabled"], True)
        config_service.update_config.assert_called_once_with(
            login_captcha_enabled=True,
            login_limit_enabled=True,
        )

    # capability_id: console.login-security.admin-api
    def test_non_admin_and_cross_enterprise_requests_are_forbidden(self):
        with self.assertRaises(NoPermissionsError):
            self.make_view(is_admin=False).get(SimpleNamespace(), "eid-1")
        with self.assertRaises(NoPermissionsError):
            self.make_view(enterprise_id="eid-2").get(SimpleNamespace(), "eid-1")

    # capability_id: console.login-security.admin-api
    def test_string_booleans_and_unknown_fields_are_rejected(self):
        view = self.make_view()
        with self.assertRaises(ValidationError):
            view.put(
                SimpleNamespace(data={
                    "login_captcha_enabled": "true",
                    "login_limit_enabled": True
                }),
                "eid-1",
            )
        with self.assertRaises(ValidationError):
            view.put(
                SimpleNamespace(data={
                    "login_captcha_enabled": True,
                    "login_limit_enabled": True,
                    "lock_seconds": 1,
                }),
                "eid-1",
            )
