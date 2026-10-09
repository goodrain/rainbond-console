# coding: utf-8
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import user_operation as user_operation_module  # noqa: E402


class TenantServiceRegistrationViewTests(TestCase):
    # capability_id: console.user-registration.required-username
    def test_post_returns_form_error_when_username_is_missing(self):
        view = user_operation_module.TenantServiceView()
        request = view.initialize_request(
            APIRequestFactory().post(
                "/console/users/register",
                {"email": "demo@example.com", "password": "password", "password_repeat": "password"},
                format="json",
            )
        )
        register_form = mock.Mock()
        register_form.is_valid.return_value = False
        register_form.errors.as_json.return_value = '{"user_name":[{"message":"用户名不能为空"}]}'

        with mock.patch.object(
                user_operation_module.platform_config_service,
                "get_config_by_key",
                return_value=None,
        ), mock.patch.object(
            user_operation_module,
            "RegisterForm",
            return_value=register_form,
        ) as form_class, mock.patch.object(user_operation_module.logger, "exception") as log_exception:
            response = view.post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "用户名不能为空")
        form_class.assert_called_once()
        log_exception.assert_not_called()

    # capability_id: console.user-registration.required-username
    def test_post_normalizes_provided_username_before_form_validation(self):
        view = user_operation_module.TenantServiceView()
        request = view.initialize_request(
            APIRequestFactory().post(
                "/console/users/register",
                {
                    "user_name": "Demo User",
                    "email": "demo@example.com",
                    "password": "password",
                    "password_repeat": "password",
                },
                format="json",
            )
        )
        register_form = mock.Mock()
        register_form.is_valid.return_value = False
        register_form.errors.as_json.return_value = '{"email":[{"message":"邮箱错误"}]}'

        with mock.patch.object(
                user_operation_module.platform_config_service,
                "get_config_by_key",
                return_value=None,
        ), mock.patch.object(
            user_operation_module,
            "normalize_name_for_k8s_namespace",
            return_value="demo-user",
        ) as normalize_name, mock.patch.object(
            user_operation_module,
            "RegisterForm",
            return_value=register_form,
        ) as form_class:
            response = view.post(request)

        self.assertEqual(response.status_code, 400)
        normalize_name.assert_called_once_with("Demo User")
        self.assertEqual(form_class.call_args[0][0]["user_name"], "demo-user")
