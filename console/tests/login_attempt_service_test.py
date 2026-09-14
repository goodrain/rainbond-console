# coding: utf-8
from unittest import TestCase


class FakeCache(object):
    def __init__(self):
        self.values = {}
        self.increment_result = None
        self.deleted = []

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, seconds):
        self.values[key] = value

    def increment(self, key, seconds):
        if self.increment_result is None:
            self.increment_result = 0
        self.increment_result += 1
        return self.increment_result

    def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)


class FailingCache(FakeCache):
    def increment(self, key, seconds):
        return None


class LoginAttemptServiceTests(TestCase):
    # capability_id: console.login-security.failure-lock
    def test_third_failure_locks_account_for_five_minutes(self):
        from console.services.login_security_service import LoginAttemptService

        backend = FakeCache()
        service = LoginAttemptService(cache_backend=backend, now=lambda: 1000)

        self.assertEqual(service.record_failure("Admin"), 1)
        self.assertEqual(service.record_failure("admin"), 2)
        self.assertEqual(service.record_failure("ADMIN"), 3)
        self.assertEqual(service.lock_remaining("admin"), 300)

    # capability_id: console.login-security.failure-lock
    def test_keys_hash_login_identifier_instead_of_exposing_it(self):
        from console.services.login_security_service import LoginAttemptService

        service = LoginAttemptService(cache_backend=FakeCache(), now=lambda: 1000)

        failure_key = service.failure_key("user@example.com")

        self.assertTrue(failure_key.startswith("login-security:failures:"))
        self.assertNotIn("user@example.com", failure_key)

    # capability_id: console.login-security.failure-lock
    def test_success_clears_failure_and_lock_state(self):
        from console.services.login_security_service import LoginAttemptService

        backend = FakeCache()
        service = LoginAttemptService(cache_backend=backend, now=lambda: 1000)
        service.record_failure("admin")
        service.clear("admin")

        self.assertEqual(
            backend.deleted,
            [service.failure_key("admin"), service.lock_key("admin")],
        )

    # capability_id: console.login-security.failure-lock
    def test_cache_failure_does_not_create_a_lock(self):
        from console.services.login_security_service import LoginAttemptService

        service = LoginAttemptService(cache_backend=FailingCache(), now=lambda: 1000)

        self.assertIsNone(service.record_failure("admin"))
        self.assertEqual(service.lock_remaining("admin"), 0)
