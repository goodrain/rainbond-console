# coding: utf-8
from django.test import TestCase

from console.models.main import ConsoleSysConfig


class LoginSecurityConfigServiceTests(TestCase):
    def setUp(self):
        ConsoleSysConfig.objects.filter(key__in=("CAPTCHA_CODE", "LOGIN_FAILURE_LOCK")).delete()

    # capability_id: console.login-security.configuration
    def test_defaults_are_disabled_and_policy_is_fixed(self):
        from console.services.login_security_service import LoginSecurityConfigService

        config = LoginSecurityConfigService().get_config()

        self.assertEqual(
            config,
            {
                "login_captcha_enabled": False,
                "login_limit_enabled": False,
                "failure_threshold": 3,
                "observation_window_seconds": 300,
                "lock_seconds": 300,
            },
        )

    # capability_id: console.login-security.configuration
    def test_update_persists_only_the_two_switches(self):
        from console.services.login_security_service import LoginSecurityConfigService

        service = LoginSecurityConfigService()
        updated = service.update_config(login_captcha_enabled=True, login_limit_enabled=True)

        self.assertTrue(updated["login_captcha_enabled"])
        self.assertTrue(updated["login_limit_enabled"])
        self.assertTrue(ConsoleSysConfig.objects.get(key="CAPTCHA_CODE").enable)
        self.assertTrue(ConsoleSysConfig.objects.get(key="LOGIN_FAILURE_LOCK").enable)
