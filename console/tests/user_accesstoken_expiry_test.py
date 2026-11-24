"""Expiry validation never generates real access keys or touches credentials."""
import os
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services import user_accesstoken_services as service_module  # noqa: E402
from console.views import base as base_module, user_accesstoken as view_module  # noqa: E402


# capability_id: console.user.access-key-expiry-bounds
class UserAccessTokenExpiryTests(TestCase):
    def setUp(self):
        self.service = service_module.user_access_services
        generator = mock.patch.object(self.service, "generate_key", return_value=mock.sentinel.generated_key)
        repository = mock.patch.object(service_module.user_access_repo, "create_user_access_key")
        self.generate = generator.start()
        self.create = repository.start()
        self.addCleanup(generator.stop)
        self.addCleanup(repository.stop)
        clock = mock.patch.object(service_module.time, "time", return_value=1800000000.75)
        clock.start()
        self.addCleanup(clock.stop)

    def test_invalid_age_is_rejected_before_generation_or_persistence(self):
        for age in (True, False, -1, 1.5, "1", "0", "invalid", float("nan"), float("inf"), [], {}, 10 ** 30):
            with self.subTest(age=age):
                with self.assertRaises(ServiceHandleException) as raised:
                    self.service.create_user_access_key("fixture", "fixture-user", age)
                self.assertEqual(raised.exception.status_code, 400)
                self.generate.assert_not_called()
                self.create.assert_not_called()

    def test_existing_permanent_values_remain_unbounded(self):
        for age in (None, "", 0):
            with self.subTest(age=age):
                result = self.service.create_user_access_key("fixture", "fixture-user", age)
                self.assertIs(result, self.create.return_value)
                self.assertIsNone(self.create.call_args.kwargs["expire_time"])
                self.assertIs(self.create.call_args.kwargs["access_key"], mock.sentinel.generated_key)

    def test_exact_int32_deadline_is_allowed_and_fractional_clock_is_normalized(self):
        result = self.service.create_user_access_key("fixture", "fixture-user", 2147483647 - 1800000000)
        self.assertIs(result, self.create.return_value)
        self.assertEqual(self.create.call_args.kwargs["expire_time"], 2147483647)
        self.assertIs(type(self.create.call_args.kwargs["expire_time"]), int)

    def test_one_second_after_deadline_is_rejected_before_generation(self):
        with self.assertRaises(ServiceHandleException):
            self.service.create_user_access_key("fixture", "fixture-user", 2147483648 - 1800000000)
        self.generate.assert_not_called()
        self.create.assert_not_called()

    def test_normal_expiry_keeps_post_response_and_operation_log(self):
        self.create.return_value.to_dict.return_value = {"note": "fixture", "expire_time": 1800000060}
        view = view_module.UserAccessTokenCLView()
        view.user = SimpleNamespace(enterprise_id="fixture-enterprise")
        request = SimpleNamespace(data={"note": "fixture", "age": 60},
                                  user=SimpleNamespace(user_id="fixture-user"))
        with mock.patch.object(view_module, "operation_log_service") as operations:
            response = view.post(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], {"note": "fixture", "expire_time": 1800000060})
        self.assertEqual(self.create.call_args.kwargs["expire_time"], 1800000060)
        operations.create_enterprise_log.assert_called_once()

    def test_positive_age_after_absolute_deadline_is_rejected(self):
        with mock.patch.object(service_module.time, "time", return_value=2147483648):
            with self.assertRaises(ServiceHandleException):
                self.service.create_user_access_key("fixture", "fixture-user", 1)
        self.generate.assert_not_called()
        self.create.assert_not_called()

    def test_post_uses_native_400_without_logging_or_creating_operation_record(self):
        view = view_module.UserAccessTokenCLView()
        view.user = SimpleNamespace(enterprise_id="fixture-enterprise")
        request = SimpleNamespace(data={"note": "fixture", "age": 10 ** 30},
                                  user=SimpleNamespace(user_id="fixture-user"))
        with mock.patch.object(view_module, "operation_log_service") as operations, \
                mock.patch.object(view_module.logger, "exception") as view_exception, \
                mock.patch.object(base_module.logger, "exception") as handler_exception:
            with self.assertRaises(ServiceHandleException) as raised:
                view.post(request)
            response = base_module.custom_exception_handler(raised.exception, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(operations.mock_calls, [])
        view_exception.assert_not_called()
        handler_exception.assert_not_called()
        self.generate.assert_not_called()
        self.create.assert_not_called()
