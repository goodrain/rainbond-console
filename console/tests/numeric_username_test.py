# -*- coding: utf-8 -*-
"""Account creation and authentication regressions against real ORM queries."""
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.user_identity import (  # noqa: E402
    check_login_identifiers_available, gitlab_username, resolve_login_user, validate_new_username)
from www.models.main import TenantEnterprise, Users  # noqa: E402


# capability_id: console.users.numeric-username
class NumericUsernameTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.created_models = []
        tables = connection.introspection.table_names()
        with connection.schema_editor() as schema:
            for model in (TenantEnterprise, Users):
                if model._meta.db_table not in tables:
                    schema.create_model(model)
                    cls.created_models.append(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema:
            for model in reversed(cls.created_models):
                schema.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        self.addCleanup(lambda: Users.objects.filter(enterprise_id="numeric-test").delete())
        self.addCleanup(lambda: TenantEnterprise.objects.filter(enterprise_id="numeric-test").delete())
        self.enterprise = TenantEnterprise.objects.create(enterprise_id="numeric-test", enterprise_name="Numeric test")

    def user(self, name="00123", **values):
        fields = dict(nick_name=name, email="{}@example.invalid".format(name), enterprise_id="numeric-test", is_active=True)
        fields.update(values)
        user = Users(**fields)
        user.set_password("$TEST_USER_PASSWORD")
        user.save()
        return user

    def test_creation_length_and_type_preserve_leading_zeros(self):
        for value in ("001", "0" * 24, "existing-user", "Existing_User"):
            validate_new_username(value)
        for value in ("12", "0" * 25, 12345, None, " user ", "name@example.invalid", "１２３"):
            with self.subTest(value=value), self.assertRaises(ServiceHandleException):
                validate_new_username(value)

    def test_username_and_phone_cannot_claim_another_users_identifier(self):
        owner = self.user("existing", phone="13800000000")
        for values in ({"nick_name": owner.phone}, {"phone": owner.nick_name}, {"email": owner.email}):
            with self.subTest(fields=tuple(values)), self.assertRaises(ServiceHandleException) as error:
                check_login_identifiers_available(**values)
            self.assertEqual(error.exception.status_code, 409)
        check_login_identifiers_available(nick_name=owner.phone, phone=owner.phone, user_id=owner.pk)

    def test_one_users_matching_fields_resolve_once_and_ambiguity_is_rejected(self):
        user = self.user("13800000000", phone="13800000000")
        self.assertEqual(resolve_login_user(user.nick_name).pk, user.pk)
        self.user("another", phone=user.nick_name)
        self.assertIsNone(resolve_login_user(user.nick_name))
        self.assertIsNone(resolve_login_user("not-registered"))

    def test_password_login_rejects_cross_field_ambiguity_before_authentication(self):
        from console.serializer import CustomJWTSerializer
        self.user("13800000000")
        self.user("another", phone="13800000000")
        serializer = CustomJWTSerializer(data={"nick_name": "13800000000", "password": "$TEST_USER_PASSWORD"})
        with mock.patch("console.serializer.authenticate") as authenticate:
            self.assertFalse(serializer.is_valid())
        authenticate.assert_not_called()

    def test_numeric_and_historical_long_accounts_can_authenticate(self):
        from console.serializer import CustomJWTSerializer
        for name in ("00123", "historical-" + "x" * 25):
            user = self.user(name)
            serializer = CustomJWTSerializer(data={"nick_name": name, "password": "$TEST_USER_PASSWORD"})
            with mock.patch("console.serializer.issue_jwt", return_value="$TEST_JWT"):
                self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["user"].pk, user.pk)

    def test_wrong_password_cannot_fall_through_to_another_authentication_backend(self):
        from console.serializer import CustomJWTSerializer
        self.user()
        serializer = CustomJWTSerializer(data={"nick_name": "00123", "password": "$INCORRECT_TEST_PASSWORD"})
        self.assertFalse(serializer.is_valid())

    def test_admin_creation_checks_length_without_restricting_existing_users(self):
        from console.services.user_services import user_services
        for name in ("12", "x" * 25, 123):
            with self.subTest(value=name), self.assertRaises(ServiceHandleException):
                user_services.check_params(name, "new@example.invalid", "$TEST_PASSWORD", "$TEST_PASSWORD", "numeric-test")

    def test_team_admin_creation_returns_validation_error_for_short_username(self):
        from console.views import team as module
        view = module.AdminAddUserView()
        view.user = SimpleNamespace(enterprise_id="numeric-test")
        request = SimpleNamespace(data={"user_name": "12", "email": "new@example.invalid", "role_ids": "1",
                                        "tenant_name": "existing-team", "password": "$TEST_PASSWORD",
                                        "re_password": "$TEST_PASSWORD"})
        with mock.patch.object(module.team_services, "get_tenant_by_tenant_name", return_value=SimpleNamespace()):
            response = view.post(request)
        self.assertEqual(response.status_code, 400)

    def test_sms_creation_retains_numeric_account_after_verified_phone(self):
        from console.services import user_service as module
        code = SimpleNamespace(code="$TEST_VERIFICATION_CODE", delete=mock.Mock())
        with mock.patch.object(module.sms_repo, "get_valid_code", return_value=code):
            user = module.user_service.register_by_phone("numeric-test", "13800000000", code.code, "00123")
        self.assertEqual(user.nick_name, "00123")
        self.assertEqual(user.phone, "13800000000")

    def test_openapi_requires_string_usernames_with_creation_length_limits(self):
        from openapi.serializer.user_serializer import CreateUserSerializer
        for name in ("12", "x" * 25, 12345):
            serializer = CreateUserSerializer(data={
                "nick_name": name, "password": "$TEST_PASSWORD", "enterprise_id": "numeric-test"})
            self.assertFalse(serializer.is_valid())

    def test_contact_updates_cannot_introduce_a_numeric_username_collision(self):
        from console.services.user_services import user_services
        owner = self.user("13800000000")
        other = self.user("another")
        with self.assertRaises(ServiceHandleException):
            user_services.update(other.pk, {"phone": owner.nick_name})
        other.refresh_from_db()
        self.assertIsNone(other.phone)

    def test_security_policy_and_locking_do_not_choose_a_user_for_ambiguous_input(self):
        from console.services.login_security_service import LoginAttemptService, LoginSecurityConfigService
        self.user("13800000000")
        self.user("another", phone="13800000000")
        self.assertIsNone(LoginSecurityConfigService._resolve_enterprise_id("13800000000"))
        self.assertIsNone(LoginAttemptService._resolve_account_id("13800000000"))

    def test_gitlab_generated_names_are_stable_bounded_and_preserve_short_names(self):
        self.assertEqual(gitlab_username(1, "123"), "gitlab-1-123")
        first = gitlab_username(1, "12345678901234567890")
        validate_new_username(first)
        self.assertEqual(first, gitlab_username(1, "12345678901234567890"))
        self.assertNotEqual(first, gitlab_username(2, "12345678901234567890"))

    def test_saas_registration_preserves_account_and_existing_namespace_rule(self):
        from console.views import user_operation as module
        self.user("existing-admin")
        view = module.TenantServiceView()
        request = view.initialize_request(APIRequestFactory().post("/console/users/register", {
            "user_name": "00123", "email": "new@example.invalid", "password": "$TEST_PASSWORD",
            "password_repeat": "$TEST_PASSWORD"}, format="json"))
        team = SimpleNamespace(tenant_name="random-team", namespace="user-00123")
        with mock.patch.dict(os.environ, {"USE_SAAS": "1"}), \
                mock.patch.object(module.platform_config_service, "get_config_by_key", return_value=None), \
                mock.patch.object(module.enterprise_services, "get_enterprise_first", return_value=self.enterprise), \
                mock.patch.object(module.region_repo, "get_usable_regions",
                                  return_value=[SimpleNamespace(region_name="r", region_id="r")]), \
                mock.patch.object(module.team_services, "create_team", return_value=team) as create_team, \
                mock.patch.object(module.region_services, "create_tenant_on_region"), \
                mock.patch.object(module.team_services, "set_tenant_resource_limit"), \
                mock.patch.object(module, "JwtManager"), mock.patch.object(module, "issue_jwt", return_value="$TEST_JWT"), \
                mock.patch.object(module, "operation_log_service"):
            response = view.post(request)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["bean"]["nick_name"], "00123")
        self.assertTrue(Users.objects.filter(nick_name="00123", enterprise_id="numeric-test").exists())
        self.assertEqual(create_team.call_args.args[4], "user-00123")
