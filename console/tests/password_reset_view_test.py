# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    typing.NotRequired = typing.Optional

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration(object):
        def __init__(self):
            self.host = ""
            self.api_key = {}

    configuration_module.Configuration = _Configuration
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
if "rest_framework_simplejwt.tokens" not in sys.modules:
    simplejwt_module = ModuleType("rest_framework_simplejwt")
    tokens_module = ModuleType("rest_framework_simplejwt.tokens")
    tokens_module.AccessToken = object
    simplejwt_module.tokens = tokens_module
    sys.modules["rest_framework_simplejwt"] = simplejwt_module
    sys.modules["rest_framework_simplejwt.tokens"] = tokens_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import RequestFactory  # noqa: E402

from console.views.user_operation import PasswordResetBegin, PasswordResetForm  # noqa: E402
from www.models.main import Users  # noqa: E402


# capability_id: console.user.password-reset-invalid-link
class PasswordResetViewTestCase(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def test_form_initializes_without_optional_crispy_helper(self):
        form = PasswordResetForm()

        self.assertFalse(form.is_bound)

    def test_post_rejects_malformed_reset_tag(self):
        request = self.request_factory.post("/console/users/begin_password_reset?tag=broken", {
            "password": "new-password",
            "password_repeat": "new-password",
        })

        with mock.patch("console.views.user_operation.AuthCode.decode", return_value="broken-payload"):
            response = PasswordResetBegin().post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg"], "invalid password reset link")

    def test_post_rejects_link_for_deleted_user(self):
        request = self.request_factory.post("/console/users/begin_password_reset?tag=valid", {
            "password": "new-password",
            "password_repeat": "new-password",
        })

        with mock.patch("console.views.user_operation.AuthCode.decode", return_value="missing@example.com,1"), \
                mock.patch("console.views.user_operation.time.time", return_value=2), \
                mock.patch.object(Users.objects, "get", side_effect=Users.DoesNotExist):
            response = PasswordResetBegin().post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg"], "invalid password reset link")

    def test_post_rejects_expired_link(self):
        request = self.request_factory.post("/console/users/begin_password_reset?tag=expired", {
            "password": "new-password",
            "password_repeat": "new-password",
        })

        with mock.patch("console.views.user_operation.AuthCode.decode", return_value="user@example.com,1"), \
                mock.patch("console.views.user_operation.time.time", return_value=3602):
            response = PasswordResetBegin().post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "链接已失效")

    def test_post_rejects_password_mismatch(self):
        request = self.request_factory.post("/console/users/begin_password_reset?tag=valid", {
            "password": "new-password",
            "password_repeat": "other-password",
        })
        user = mock.Mock()

        with mock.patch("console.views.user_operation.AuthCode.decode", return_value="user@example.com,1"), \
                mock.patch("console.views.user_operation.time.time", return_value=2), \
                mock.patch.object(Users.objects, "get", return_value=user):
            response = PasswordResetBegin().post(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("两次输入的密码不一致", response.data["msg_show"])
        user.set_password.assert_not_called()

    def test_post_resets_password_for_valid_link(self):
        request = self.request_factory.post("/console/users/begin_password_reset?tag=valid", {
            "password": "new-password",
            "password_repeat": "new-password",
        })
        user = mock.Mock()

        with mock.patch("console.views.user_operation.AuthCode.decode", return_value="user@example.com,1"), \
                mock.patch("console.views.user_operation.time.time", return_value=2), \
                mock.patch.object(Users.objects, "get", return_value=user):
            response = PasswordResetBegin().post(request)

        self.assertEqual(response.status_code, 200)
        user.set_password.assert_called_once_with("new-password")
        user.save.assert_called_once_with()

    def test_post_reports_unexpected_error_without_python2_message_attribute(self):
        request = self.request_factory.post("/console/users/begin_password_reset?tag=valid", {
            "password": "new-password",
            "password_repeat": "new-password",
        })

        with mock.patch("console.views.user_operation.AuthCode.decode", return_value="user@example.com,1"), \
                mock.patch("console.views.user_operation.time.time", return_value=2), \
                mock.patch.object(Users.objects, "get", side_effect=RuntimeError("database unavailable")):
            response = PasswordResetBegin().post(request)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg"], "database unavailable")
