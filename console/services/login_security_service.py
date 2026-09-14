# -*- coding: utf-8 -*-
import hashlib
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, Optional

from django.db.models import Q

from console.repositories.region_repo import region_repo
from console.utils.cache import cache
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Users

logger = logging.getLogger("default")

SECURITY_CENTER_PLUGIN_NAME = "rainbond-security-center"
LOGIN_SECURITY_CONFIG_CACHE_TTL_SECONDS = 5
LOGIN_FAILURE_THRESHOLD = 3
LOGIN_FAILURE_WINDOW_SECONDS = 300
LOGIN_LOCK_SECONDS = 300


def _default_login_security_config(plugin_installed: bool = False) -> Dict[str, Any]:
    return {
        "plugin_installed": plugin_installed,
        "login_captcha_enabled": False,
        "login_limit_enabled": False,
        "failure_threshold": LOGIN_FAILURE_THRESHOLD,
        "observation_window_seconds": LOGIN_FAILURE_WINDOW_SECONDS,
        "lock_seconds": LOGIN_LOCK_SECONDS,
        "source_region": "",
    }


def apply_login_security_to_platform_config(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(data)
    captcha = dict(result.get("captcha_code") or {})
    captcha["enable"] = bool(config.get("login_captcha_enabled"))
    captcha["value"] = None
    result["captcha_code"] = captcha
    result["login_security"] = dict(config)
    return result


class LoginSecurityConfigService(object):
    def __init__(self,
                 region_repository: Any = region_repo,
                 region_client: Optional[Any] = None,
                 now: Callable[[], float] = time.time,
                 cache_ttl: int = LOGIN_SECURITY_CONFIG_CACHE_TTL_SECONDS,
                 enterprise_resolver: Optional[Callable[[str], Any]] = None) -> None:
        self.region_repository = region_repository
        self.region_client = region_client or RegionInvokeApi()
        self.now = now
        self.cache_ttl = cache_ttl
        self.enterprise_resolver = enterprise_resolver or self._resolve_enterprise_id
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()

    @staticmethod
    def _resolve_enterprise_id(identifier: str) -> Optional[str]:
        return Users.objects.filter(
            Q(phone=identifier) | Q(email=identifier) | Q(nick_name=identifier)).values_list(
                "enterprise_id", flat=True).first()

    @staticmethod
    def _parse_plugin_config(status: int, envelope: Any, region_name: str) -> Optional[Dict[str, Any]]:
        if status != 200 or not isinstance(envelope, dict):
            return None
        try:
            code = int(envelope.get("code", 0))
        except (TypeError, ValueError):
            return None
        if code != 200:
            return None
        data = envelope.get("data")
        if not isinstance(data, dict):
            return None
        return {
            "plugin_installed": True,
            "login_captcha_enabled": data.get("login_captcha_enabled") is True,
            "login_limit_enabled": data.get("login_limit_enabled") is True,
            "failure_threshold": LOGIN_FAILURE_THRESHOLD,
            "observation_window_seconds": LOGIN_FAILURE_WINDOW_SECONDS,
            "lock_seconds": LOGIN_LOCK_SECONDS,
            "source_region": region_name,
        }

    def get_config(self,
                   enterprise_id: Optional[str] = None,
                   login_identifier: Optional[str] = None) -> Dict[str, Any]:
        if not enterprise_id and login_identifier:
            try:
                enterprise_id = self.enterprise_resolver(login_identifier)
            except Exception as exc:
                logger.warning("failed to resolve enterprise for login security: %s", exc)
        enterprise_id = enterprise_id or os.environ.get("ENTERPRISE_ID", "")
        if not enterprise_id:
            return _default_login_security_config()

        now = self.now()
        with self._cache_lock:
            cached = self._cache.get(enterprise_id)
            if cached and cached["expires_at"] > now:
                return dict(cached["config"])

        config = _default_login_security_config()
        try:
            regions = self.region_repository.get_usable_regions(enterprise_id)
        except Exception as exc:
            logger.warning("failed to list regions for security center detection: %s", exc)
            regions = []
        if hasattr(regions, "order_by"):
            regions = regions.order_by("ID")
        for region in regions or []:
            region_name = region.region_name
            try:
                installed = self.region_client.cluster_plugin_exists(
                    enterprise_id, region_name, SECURITY_CENTER_PLUGIN_NAME)
            except Exception as exc:
                logger.warning("failed to detect security center plugin region=%s: %s", region_name, exc)
                continue
            if not installed:
                continue
            config["plugin_installed"] = True
            try:
                status, envelope = self.region_client.request_plugin_backend(
                    enterprise_id,
                    region_name,
                    SECURITY_CENTER_PLUGIN_NAME,
                    "GET",
                    "/api/v1/config",
                    timeout=3,
                )
            except Exception as exc:
                logger.warning("failed to read security center config region=%s: %s", region_name, exc)
                continue
            parsed = self._parse_plugin_config(status, envelope, region_name)
            if parsed is not None:
                config = parsed
                break

        if self.cache_ttl > 0:
            with self._cache_lock:
                self._cache[enterprise_id] = {
                    "expires_at": now + self.cache_ttl,
                    "config": dict(config),
                }
        return config


class LoginAttemptService(object):
    def __init__(self,
                 cache_backend: Any = cache,
                 now: Callable[[], float] = time.time,
                 account_resolver: Optional[Callable[[str], Any]] = None) -> None:
        self.cache = cache_backend
        self.now = now
        self.account_resolver = account_resolver or self._resolve_account_id

    @staticmethod
    def _resolve_account_id(identifier: str) -> Optional[int]:
        return Users.objects.filter(
            Q(phone=identifier) | Q(email=identifier) | Q(nick_name=identifier)).values_list("user_id", flat=True).first()

    def identity(self, identifier: str) -> str:
        account_id = self.account_resolver(identifier)
        if account_id is not None:
            return "user:{}".format(account_id)
        return "login:{}".format(str(identifier or "").strip().casefold())

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
