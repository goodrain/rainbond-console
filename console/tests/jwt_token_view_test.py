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

from rest_framework.test import APIRequestFactory  # noqa: E402

from console.captcha.captcha_code import CaptchaView  # noqa: E402
from console.views.jwt_token_view import JWTTokenView  # noqa: E402


class FakeSession(dict):
    def save(self):
        return None


class FakeSerializer(object):
    def __init__(self, valid, user=None):
        self.valid = valid
        self.validated_data = {
            "user": user,
            "token": "jwt-token",
        } if valid else {}
        self.errors = {"non_field_errors": ["internal credential detail"]}

    def is_valid(self):
        return self.valid


class JWTTokenViewSecurityTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def request(self, data, captcha=None):
        request = self.factory.post("/console/users/login", data=data, format="multipart")
        request.session = FakeSession()
        request.data = request.POST
        if captcha is not None:
            request.session["captcha_code"] = captcha
        return request

    def service_patches(self, config, attempt_service):
        return (
            mock.patch(
                "console.views.jwt_token_view.login_security_config_service.get_config",
                return_value=config,
            ),
            mock.patch("console.views.jwt_token_view.login_attempt_service", attempt_service),
        )

    # capability_id: console.login-security.login-enforcement
    def test_enabled_captcha_cannot_be_bypassed_by_omitting_client_flag(self):
        attempt_service = mock.Mock()
        attempt_service.identity.return_value = "user:1"
        patches = self.service_patches(
            {
                "login_captcha_enabled": True,
                "login_limit_enabled": False
            },
            attempt_service,
        )
        with patches[0], patches[1]:
            response = JWTTokenView().post(self.request({"nick_name": "admin", "password": "wrong"}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "验证码错误")
        attempt_service.record_failure.assert_not_called()

    # capability_id: console.login-security.login-enforcement
    def test_wrong_captcha_is_consumed_without_counting_password_failure(self):
        attempt_service = mock.Mock()
        attempt_service.identity.return_value = "user:1"
        patches = self.service_patches(
            {
                "login_captcha_enabled": True,
                "login_limit_enabled": True
            },
            attempt_service,
        )
        request = self.request(
            {
                "nick_name": "admin",
                "password": "wrong",
                "captcha_code": "zzzz"
            },
            captcha="abcd",
        )
        attempt_service.lock_remaining.return_value = 0
        with patches[0], patches[1]:
            response = JWTTokenView().post(request)

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("captcha_code", request.session)
        attempt_service.record_failure.assert_not_called()

    # capability_id: console.login-security.login-enforcement
    def test_third_password_failure_returns_429_and_retry_after(self):
        attempt_service = mock.Mock()
        attempt_service.identity.return_value = "login:missing"
        attempt_service.lock_remaining.return_value = 0
        attempt_service.record_failure.return_value = 3
        patches = self.service_patches(
            {
                "login_captcha_enabled": False,
                "login_limit_enabled": True
            },
            attempt_service,
        )
        view = JWTTokenView()
        view.get_serializer = mock.Mock(return_value=FakeSerializer(False))
        with patches[0], patches[1]:
            response = view.post(self.request({"nick_name": "missing", "password": "wrong"}))

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "300")
        self.assertEqual(response.data["data"]["bean"]["retry_after"], 300)

    # capability_id: console.login-security.login-enforcement
    def test_first_password_failure_uses_generic_message(self):
        attempt_service = mock.Mock()
        attempt_service.identity.return_value = "login:missing"
        attempt_service.lock_remaining.return_value = 0
        attempt_service.record_failure.return_value = 1
        patches = self.service_patches(
            {
                "login_captcha_enabled": False,
                "login_limit_enabled": True
            },
            attempt_service,
        )
        view = JWTTokenView()
        view.get_serializer = mock.Mock(return_value=FakeSerializer(False))
        with patches[0], patches[1]:
            response = view.post(self.request({"nick_name": "missing", "password": "wrong"}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "用户名或密码错误")

    # capability_id: console.login-security.login-enforcement
    def test_existing_lock_is_checked_before_captcha_and_password(self):
        attempt_service = mock.Mock()
        attempt_service.identity.return_value = "user:1"
        attempt_service.lock_remaining.return_value = 120
        patches = self.service_patches(
            {
                "login_captcha_enabled": True,
                "login_limit_enabled": True
            },
            attempt_service,
        )
        request = self.request(
            {
                "nick_name": "admin",
                "password": "correct",
                "captcha_code": "abcd"
            },
            captcha="abcd",
        )
        view = JWTTokenView()
        view.get_serializer = mock.Mock()
        with patches[0], patches[1]:
            response = view.post(request)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "120")
        self.assertIn("captcha_code", request.session)
        view.get_serializer.assert_not_called()

    # capability_id: console.login-security.login-enforcement
    @mock.patch("console.views.jwt_token_view.operation_log_service")
    @mock.patch("console.views.jwt_token_view.LoginEvent")
    @mock.patch("console.views.jwt_token_view.JwtManager")
    @mock.patch("console.views.jwt_token_view.jwt_issuer.jwt_response_payload")
    def test_success_clears_failure_state(self, jwt_payload, jwt_manager, login_event, operation_log):
        user = SimpleNamespace(user_id=1, enterprise_id="eid-1", username="admin")
        jwt_payload.return_value = {"token": "jwt-token"}
        operation_log.generate_generic_comment.return_value = "login"
        attempt_service = mock.Mock()
        attempt_service.identity.return_value = "user:1"
        attempt_service.lock_remaining.return_value = 0
        patches = self.service_patches(
            {
                "login_captcha_enabled": False,
                "login_limit_enabled": True
            },
            attempt_service,
        )
        view = JWTTokenView()
        view.get_serializer = mock.Mock(return_value=FakeSerializer(True, user=user))
        with patches[0], patches[1]:
            response = view.post(self.request({"nick_name": "Admin", "password": "correct"}))

        self.assertEqual(response.status_code, 200)
        attempt_service.clear.assert_called_once_with("user:1")


class CaptchaViewSecurityTests(TestCase):
    # capability_id: console.login-security.login-enforcement
    def test_captcha_is_stored_in_session_and_never_cached(self):
        request = APIRequestFactory().get("/console/captcha")
        request.session = FakeSession()

        response = CaptchaView().get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(request.session["captcha_code"]), 4)
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertIn("no-store", response["Cache-Control"])
