# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from console.exception.main import ServiceHandleException
from console.models.main import ConsoleSysConfig

logger = logging.getLogger("default")

AI_AGENT_LLM_CONFIG_KEY = "AI_AGENT_LLM_CONFIG"
API_KEY_PREFIX = "fernet:v1:"
DEFAULT_MODEL = "gpt-4o-mini"
ALLOWED_REASONING_EFFORTS = ("", "low", "medium", "high")


class AgentLLMConfigService(object):

    def get_masked_config(self):
        config = self._load_config()
        api_key = self._decrypt_api_key(config.get("OPENAI_API_KEY", ""))
        return self._to_masked_config(config, api_key)

    def update_config(self, data, updated_by=""):
        data = data or {}
        self._validate_update(data)
        raw_api_key = data.get("openai_api_key")

        next_config = {
            "OPENAI_API_KEY": self._encrypt_api_key(str(raw_api_key).strip()),
            "OPENAI_MODEL": self._read_string(data.get("openai_model")),
            "OPENAI_BASE_URL": self._read_string(data.get("openai_base_url")),
            "LLM_THINKING_ENABLED": self._read_bool(data.get("llm_thinking_enabled"),
                                                    False),
            "LLM_REASONING_EFFORT": self._read_string(data.get("llm_reasoning_effort")).lower(),
            "updated_by": updated_by or "",
            "updated_at": timezone.now().isoformat(),
        }
        self._save_config(next_config)
        api_key = self._decrypt_api_key(next_config.get("OPENAI_API_KEY", ""))
        return self._to_masked_config(next_config, api_key)

    def get_runtime_config(self):
        config = self._load_config()
        api_key = self._decrypt_api_key(config.get("OPENAI_API_KEY", ""))
        return {
            "OPENAI_API_KEY": api_key,
            "OPENAI_MODEL": config.get("OPENAI_MODEL") or DEFAULT_MODEL,
            "OPENAI_BASE_URL": config.get("OPENAI_BASE_URL") or "",
            "LLM_THINKING_ENABLED": self._format_bool(config.get("LLM_THINKING_ENABLED")),
            "LLM_REASONING_EFFORT": config.get("LLM_REASONING_EFFORT") or "",
            "updated_at": config.get("updated_at") or "",
        }

    def _load_config(self):
        try:
            obj = ConsoleSysConfig.objects.get(key=AI_AGENT_LLM_CONFIG_KEY)
        except ObjectDoesNotExist:
            return {}
        except Exception as exc:
            logger.warning("failed to load ai agent llm config: %s", exc)
            return {}

        raw = obj.value or "{}"
        try:
            parsed = json.loads(raw)
        except Exception:
            logger.warning("invalid ai agent llm config json")
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _save_config(self, config):
        value = self._serialize_config(config)
        try:
            obj = ConsoleSysConfig.objects.get(key=AI_AGENT_LLM_CONFIG_KEY)
            obj.value = value
            obj.type = "json"
            obj.desc = "AI 助手 LLM 全局配置"
            obj.enable = True
            obj.save(update_fields=["value", "type", "desc", "enable"])
        except ObjectDoesNotExist:
            ConsoleSysConfig.objects.create(
                key=AI_AGENT_LLM_CONFIG_KEY,
                type="json",
                value=value,
                desc="AI 助手 LLM 全局配置",
                enable=True,
                enterprise_id="",
            )

    def _serialize_config(self, config):
        return json.dumps(config or {}, ensure_ascii=False, sort_keys=True)

    def _validate_update(self, data):
        errors = []
        required_fields = (
            ("openai_api_key", "OPENAI_API_KEY"),
            ("openai_model", "OPENAI_MODEL"),
            ("openai_base_url", "OPENAI_BASE_URL"),
            ("llm_reasoning_effort", "LLM_REASONING_EFFORT"),
        )
        for field, label in required_fields:
            if not self._read_string(data.get(field)):
                errors.append("{} 不能为空".format(label))

        if data.get("llm_thinking_enabled") is None:
            errors.append("LLM_THINKING_ENABLED 不能为空")

        base_url = self._read_string(data.get("openai_base_url"), "")
        if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
            errors.append("OPENAI_BASE_URL 必须以 http:// 或 https:// 开头")

        reasoning_effort = self._read_string(data.get("llm_reasoning_effort"), "").lower()
        if reasoning_effort not in ALLOWED_REASONING_EFFORTS:
            errors.append("LLM_REASONING_EFFORT 只能为 low、medium 或 high")

        if errors:
            raise ServiceHandleException(
                msg="invalid ai agent llm config",
                msg_show="；".join(errors),
                status_code=400,
            )

    def _to_masked_config(self, config, api_key):
        return {
            "openai_api_key_set": bool(api_key),
            "openai_api_key_masked": self._mask_api_key(api_key),
            "openai_model": config.get("OPENAI_MODEL") or DEFAULT_MODEL,
            "openai_base_url": config.get("OPENAI_BASE_URL") or "",
            "llm_thinking_enabled": self._read_bool(config.get("LLM_THINKING_ENABLED"), False),
            "llm_reasoning_effort": config.get("LLM_REASONING_EFFORT") or "",
            "updated_at": config.get("updated_at") or "",
            "updated_by": config.get("updated_by") or "",
        }

    def _encrypt_api_key(self, api_key):
        if not api_key:
            return ""
        encrypted = self._fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")
        return API_KEY_PREFIX + encrypted

    def _decrypt_api_key(self, stored):
        if not stored:
            return ""
        if not stored.startswith(API_KEY_PREFIX):
            return stored
        token = stored[len(API_KEY_PREFIX):]
        try:
            return self._fernet().decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError, TypeError) as exc:
            logger.warning("failed to decrypt ai agent api key: %s", exc)
            return ""

    def _fernet(self):
        secret = getattr(settings, "SECRET_KEY", "") or "rainbond-agent"
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _mask_api_key(self, api_key):
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "****"
        return "{}****{}".format(api_key[:3], api_key[-4:])

    def _read_string(self, *values):
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def _read_bool(self, value, default=False):
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

    def _format_bool(self, value):
        return "true" if self._read_bool(value, False) else "false"


agent_llm_config_service = AgentLLMConfigService()
