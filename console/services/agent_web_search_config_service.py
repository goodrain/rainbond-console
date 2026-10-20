# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import logging
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from console.exception.main import ServiceHandleException
from console.models.main import ConsoleSysConfig

logger = logging.getLogger("default")

AI_AGENT_WEB_SEARCH_CONFIG_KEY = "AI_AGENT_WEB_SEARCH_CONFIG"
API_KEY_PREFIX = "fernet:v1:"
WEB_SEARCH_PROVIDERS = ("exa", "perplexity")
DEFAULT_CONFIG = {
    "enabled": True,
    "provider": "exa",
    "max_results": 5,
    "fetch_timeout_ms": 15000,
}


class AgentWebSearchConfigService(object):

    def get_masked_config(self) -> Dict[str, Any]:
        config = self._load_config()
        api_key = self._decrypt_api_key(config.get("api_key", ""))
        return self._to_masked(config, api_key)

    def get_runtime_config(self) -> Dict[str, Any]:
        config = self._load_config()
        return {
            "enabled": self._read_bool(config.get("enabled"), True),
            "provider": self._read_string(config.get("provider"), DEFAULT_CONFIG["provider"]),
            "api_key": self._decrypt_api_key(config.get("api_key", "")),
            "max_results": self._read_int(config.get("max_results"), DEFAULT_CONFIG["max_results"]),
            "fetch_timeout_ms": self._read_int(
                config.get("fetch_timeout_ms"), DEFAULT_CONFIG["fetch_timeout_ms"]),
            "updated_at": config.get("updated_at") or "",
        }

    def update_config(self, data: Optional[Dict[str, Any]] = None,
                      updated_by: str = "") -> Dict[str, Any]:
        data = data or {}
        existing = self._load_config()
        current_key = existing.get("api_key", "")
        raw_key = self._read_string(data.get("api_key"))
        stored_key = self._encrypt_api_key(raw_key) if raw_key else current_key
        config = {
            "enabled": self._read_bool(data.get("enabled"), True),
            "provider": self._read_string(data.get("provider"), DEFAULT_CONFIG["provider"]),
            "api_key": stored_key,
            "max_results": self._read_int(data.get("max_results"), DEFAULT_CONFIG["max_results"]),
            "fetch_timeout_ms": self._read_int(
                data.get("fetch_timeout_ms"), DEFAULT_CONFIG["fetch_timeout_ms"]),
        }
        self._validate(config, has_api_key=bool(raw_key or self._decrypt_api_key(current_key)))
        self._save_config(config, updated_by)
        return self._to_masked(config, self._decrypt_api_key(stored_key), updated_by)

    def reset_config(self, updated_by: str = "") -> Dict[str, Any]:
        ConsoleSysConfig.objects.filter(key=AI_AGENT_WEB_SEARCH_CONFIG_KEY).delete()
        return self._to_masked(dict(DEFAULT_CONFIG), "", updated_by)

    def _load_config(self) -> Dict[str, Any]:
        try:
            obj = ConsoleSysConfig.objects.get(key=AI_AGENT_WEB_SEARCH_CONFIG_KEY)
        except ObjectDoesNotExist:
            return {}
        except Exception as exc:
            logger.warning("failed to load ai agent web search config: %s", exc)
            return {}
        try:
            parsed = json.loads(obj.value or "{}")
        except (TypeError, ValueError):
            logger.warning("invalid ai agent web search config json")
            return {}
        if not isinstance(parsed, dict):
            return {}
        return parsed.get("config") if isinstance(parsed.get("config"), dict) else parsed

    def _save_config(self, config: Dict[str, Any], updated_by: str) -> None:
        value = json.dumps(
            {
                "config": config,
                "updated_by": updated_by or "",
                "updated_at": timezone.now().isoformat(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        try:
            obj = ConsoleSysConfig.objects.get(key=AI_AGENT_WEB_SEARCH_CONFIG_KEY)
            obj.value = value
            obj.type = "json"
            obj.desc = "AI 助手联网搜索配置"
            obj.enable = True
            obj.save(update_fields=["value", "type", "desc", "enable"])
        except ObjectDoesNotExist:
            ConsoleSysConfig.objects.create(
                key=AI_AGENT_WEB_SEARCH_CONFIG_KEY,
                type="json",
                value=value,
                desc="AI 助手联网搜索配置",
                enable=True,
                enterprise_id="",
            )

    def _validate(self, config: Dict[str, Any], has_api_key: bool) -> None:
        if not has_api_key:
            raise ServiceHandleException(
                msg="web search api key is required",
                msg_show="联网搜索 API Key 不能为空",
                status_code=400,
            )
        if config["provider"] not in WEB_SEARCH_PROVIDERS:
            raise ServiceHandleException(
                msg="invalid web search provider",
                msg_show="联网搜索 provider 必须是 exa 或 perplexity",
                status_code=400,
            )
        if not (1 <= config["max_results"] <= 10):
            raise ServiceHandleException(
                msg="invalid max_results",
                msg_show="联网搜索 max_results 必须在 1..10",
                status_code=400,
            )
        if not (1000 <= config["fetch_timeout_ms"] <= 60000):
            raise ServiceHandleException(
                msg="invalid fetch_timeout_ms",
                msg_show="联网搜索 fetch_timeout_ms 必须在 1000..60000",
                status_code=400,
            )

    def _to_masked(self, config: Dict[str, Any], api_key: str,
                   updated_by: str = "") -> Dict[str, Any]:
        return {
            "enabled": self._read_bool(config.get("enabled"), True),
            "provider": self._read_string(config.get("provider"), DEFAULT_CONFIG["provider"]),
            "max_results": self._read_int(config.get("max_results"), DEFAULT_CONFIG["max_results"]),
            "fetch_timeout_ms": self._read_int(
                config.get("fetch_timeout_ms"), DEFAULT_CONFIG["fetch_timeout_ms"]),
            "api_key_set": bool(api_key),
            "api_key_masked": self._mask_api_key(api_key),
            "updated_by": updated_by or str(config.get("updated_by") or ""),
            "updated_at": config.get("updated_at") or "",
        }

    def _encrypt_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        encrypted = self._fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")
        return API_KEY_PREFIX + encrypted

    def _decrypt_api_key(self, stored: str) -> str:
        if not stored:
            return ""
        if not stored.startswith(API_KEY_PREFIX):
            return stored
        try:
            return self._fernet().decrypt(stored[len(API_KEY_PREFIX):].encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError, TypeError) as exc:
            logger.warning("failed to decrypt ai agent web search key: %s", exc)
            return ""

    def _fernet(self) -> Fernet:
        secret = getattr(settings, "SECRET_KEY", "") or "rainbond-agent"
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _mask_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "****"
        return "{}****{}".format(api_key[:3], api_key[-4:])

    def _read_string(self, *values: Any) -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def _read_bool(self, value: Any, default: bool = False) -> bool:
        if value is None:
            return bool(default)
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
        return bool(default)

    def _read_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)


agent_web_search_config_service = AgentWebSearchConfigService()
