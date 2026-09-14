# -*- coding: utf-8 -*-
import hashlib
import logging
import time
from typing import Any, Callable, Dict, Optional

from django.db import transaction

from console.models.main import ConsoleSysConfig
from console.utils.cache import cache

logger = logging.getLogger("default")

LOGIN_CAPTCHA_CONFIG_KEY = "CAPTCHA_CODE"
LOGIN_FAILURE_LOCK_CONFIG_KEY = "LOGIN_FAILURE_LOCK"
LOGIN_FAILURE_THRESHOLD = 3
LOGIN_FAILURE_WINDOW_SECONDS = 300
LOGIN_LOCK_SECONDS = 300

_CONFIG_DESCRIPTIONS = {
    LOGIN_CAPTCHA_CONFIG_KEY: "开启/关闭登录验证码",
    LOGIN_FAILURE_LOCK_CONFIG_KEY: "开启/关闭登录失败锁定",
}


class LoginSecurityConfigService(object):
    @staticmethod
    def _config(key: str) -> ConsoleSysConfig:
        config, _ = ConsoleSysConfig.objects.get_or_create(
            key=key,
            defaults={
                "type": "string",
                "value": None,
                "desc": _CONFIG_DESCRIPTIONS[key],
                "enable": False,
                "enterprise_id": "",
            },
        )
        return config

    def get_config(self) -> Dict[str, Any]:
        return {
            "login_captcha_enabled": bool(self._config(LOGIN_CAPTCHA_CONFIG_KEY).enable),
            "login_limit_enabled": bool(self._config(LOGIN_FAILURE_LOCK_CONFIG_KEY).enable),
            "failure_threshold": LOGIN_FAILURE_THRESHOLD,
            "observation_window_seconds": LOGIN_FAILURE_WINDOW_SECONDS,
            "lock_seconds": LOGIN_LOCK_SECONDS,
        }

    @transaction.atomic
    def update_config(self, login_captcha_enabled: bool, login_limit_enabled: bool) -> Dict[str, Any]:
        values = {
            LOGIN_CAPTCHA_CONFIG_KEY: login_captcha_enabled,
            LOGIN_FAILURE_LOCK_CONFIG_KEY: login_limit_enabled,
        }
        for key, enabled in values.items():
            ConsoleSysConfig.objects.update_or_create(
                key=key,
                defaults={
                    "type": "string",
                    "value": None,
                    "desc": _CONFIG_DESCRIPTIONS[key],
                    "enable": enabled,
                    "enterprise_id": "",
                },
            )
        return self.get_config()


class LoginAttemptService(object):
    def __init__(self, cache_backend: Any = cache, now: Callable[[], float] = time.time) -> None:
        self.cache = cache_backend
        self.now = now

    @staticmethod
    def _digest(identifier: str) -> str:
        normalized = str(identifier or "").strip().casefold()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def failure_key(self, identifier: str) -> str:
        return "login-security:failures:{}".format(self._digest(identifier))

    def lock_key(self, identifier: str) -> str:
        return "login-security:locked:{}".format(self._digest(identifier))

    def record_failure(self, identifier: str) -> Optional[int]:
        count = self.cache.increment(self.failure_key(identifier), LOGIN_FAILURE_WINDOW_SECONDS)
        if count is None:
            logger.warning("failed to update login failure counter")
            return None
        count = int(count)
        if count >= LOGIN_FAILURE_THRESHOLD:
            self.cache.set(self.lock_key(identifier), int(self.now()) + LOGIN_LOCK_SECONDS, LOGIN_LOCK_SECONDS)
        return count

    def lock_remaining(self, identifier: str) -> int:
        locked_until = self.cache.get(self.lock_key(identifier))
        if locked_until is None:
            return 0
        try:
            if isinstance(locked_until, bytes):
                locked_until = locked_until.decode("utf-8")
            remaining = int(locked_until) - int(self.now())
        except (TypeError, ValueError):
            logger.warning("invalid login lock state")
            self.cache.delete(self.lock_key(identifier))
            return 0
        if remaining <= 0:
            self.cache.delete(self.lock_key(identifier))
            return 0
        return remaining

    def clear(self, identifier: str) -> None:
        self.cache.delete(self.failure_key(identifier))
        self.cache.delete(self.lock_key(identifier))


login_security_config_service = LoginSecurityConfigService()
login_attempt_service = LoginAttemptService()
