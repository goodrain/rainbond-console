# -*- coding: utf-8 -*-
import json
import logging
from typing import Any, Dict, Optional, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from console.exception.main import ServiceHandleException
from console.models.main import ConsoleSysConfig

logger = logging.getLogger("default")

AI_AGENT_PERMISSION_CONFIG_KEY = "AI_AGENT_PERMISSION_CONFIG"

PERMISSION_ROLES = ("enterprise_admin", "team_admin", "member", "viewer")
TOOL_CLASSES = ("read", "write", "destructive", "exec", "web")
POLICY_DECISIONS = ("allow", "deny", "ask")
TOOL_SCOPES = ("enterprise", "team", "app", "component")

DEFAULT_PERMISSION_CONFIG = {
    "version": 1,
    "defaultByRole": {
        "enterprise_admin": {"read": "allow", "write": "allow", "destructive": "ask", "exec": "ask", "web": "allow"},
        "team_admin": {"read": "allow", "write": "allow", "destructive": "ask", "exec": "deny", "web": "allow"},
        "member": {"read": "allow", "write": "ask", "destructive": "deny", "exec": "deny", "web": "allow"},
        "viewer": {"read": "allow", "write": "deny", "destructive": "deny", "exec": "deny", "web": "deny"},
    },
    "tools": [],
}


class AgentPermissionConfigService(object):

    def get_config(self) -> Dict[str, Any]:
        return self._load_config()

    def get_runtime_config(self) -> Dict[str, Any]:
        return self._load_config()

    def update_config(self, data: Optional[Dict[str, Any]] = None,
                      updated_by: str = "") -> Dict[str, Any]:
        raw = data or {}
        candidate = raw.get("config") if isinstance(raw.get("config"), dict) else raw
        config = self._validate_config(candidate)
        self._save_config(config, updated_by)
        return self._to_response(config, updated_by, timezone.now().isoformat())

    def reset_config(self, updated_by: str = "") -> Dict[str, Any]:
        ConsoleSysConfig.objects.filter(key=AI_AGENT_PERMISSION_CONFIG_KEY).delete()
        return self._to_response(DEFAULT_PERMISSION_CONFIG, updated_by, timezone.now().isoformat())

    def _load_config(self) -> Dict[str, Any]:
        try:
            obj = ConsoleSysConfig.objects.get(key=AI_AGENT_PERMISSION_CONFIG_KEY)
        except ObjectDoesNotExist:
            return self._to_response(DEFAULT_PERMISSION_CONFIG, "", "")
        except Exception as exc:
            logger.warning("failed to load ai agent permission config: %s", exc)
            return self._to_response(DEFAULT_PERMISSION_CONFIG, "", "")

        try:
            stored = json.loads(obj.value or "{}")
        except (TypeError, ValueError):
            logger.warning("invalid ai agent permission config json")
            return self._to_response(DEFAULT_PERMISSION_CONFIG, "", "")

        if not isinstance(stored, dict):
            return self._to_response(DEFAULT_PERMISSION_CONFIG, "", "")
        config = stored.get("config") if isinstance(stored.get("config"), dict) else stored
        try:
            normalized = self._validate_config(config)
        except ServiceHandleException as exc:
            logger.warning("invalid stored ai agent permission config: %s", exc.msg_show)
            return self._to_response(DEFAULT_PERMISSION_CONFIG, "", "")
        return self._to_response(
            normalized,
            str(stored.get("updated_by") or ""),
            str(stored.get("updated_at") or ""),
        )

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
            obj = ConsoleSysConfig.objects.get(key=AI_AGENT_PERMISSION_CONFIG_KEY)
            obj.value = value
            obj.type = "json"
            obj.desc = "AI 助手权限全局配置"
            obj.enable = True
            obj.save(update_fields=["value", "type", "desc", "enable"])
        except ObjectDoesNotExist:
            ConsoleSysConfig.objects.create(
                key=AI_AGENT_PERMISSION_CONFIG_KEY,
                type="json",
                value=value,
                desc="AI 助手权限全局配置",
                enable=True,
                enterprise_id="",
            )

    def _validate_config(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            self._fail("权限配置必须是对象")
        if value.get("version") != 1:
            self._fail("权限配置 version 必须为 1")

        default_by_role = value.get("defaultByRole")
        if not isinstance(default_by_role, dict):
            self._fail("defaultByRole 不能为空")
        normalized_defaults: Dict[str, Dict[str, str]] = {}
        for role in PERMISSION_ROLES:
            by_class = default_by_role.get(role)
            if not isinstance(by_class, dict):
                self._fail("defaultByRole.{} 不能为空".format(role))
            normalized_defaults[role] = {}
            for tool_class in TOOL_CLASSES:
                decision = by_class.get(tool_class)
                if decision not in POLICY_DECISIONS:
                    self._fail("defaultByRole.{}.{} 必须为 allow/deny/ask".format(role, tool_class))
                normalized_defaults[role][tool_class] = decision

        tools = value.get("tools")
        if not isinstance(tools, list):
            self._fail("tools 必须是数组")
        normalized_tools = []
        seen = set()
        for index, item in enumerate(tools):
            if not isinstance(item, dict):
                self._fail("tools[{}] 必须是对象".format(index))
            tool = str(item.get("tool") or "").strip()
            if not tool:
                self._fail("tools[{}].tool 不能为空".format(index))
            if tool in seen:
                self._fail("重复的工具策略：{}".format(tool))
            seen.add(tool)
            tool_class = item.get("class")
            if tool_class not in TOOL_CLASSES:
                self._fail("tools[{}].class 无效".format(index))
            scope = item.get("scope")
            if scope not in TOOL_SCOPES:
                self._fail("tools[{}].scope 无效".format(index))
            roles = item.get("roles")
            if not isinstance(roles, dict):
                self._fail("tools[{}].roles 不能为空".format(index))
            normalized_roles = {}
            for role in PERMISSION_ROLES:
                decision = roles.get(role)
                if decision not in POLICY_DECISIONS:
                    self._fail("tools[{}].roles.{} 必须为 allow/deny/ask".format(index, role))
                normalized_roles[role] = decision
            normalized_tools.append({
                "tool": tool,
                "class": tool_class,
                "scope": scope,
                "roles": normalized_roles,
            })

        return {
            "version": 1,
            "defaultByRole": normalized_defaults,
            "tools": normalized_tools,
        }

    def _to_response(self, config: Dict[str, Any], updated_by: str,
                     updated_at: str) -> Dict[str, Any]:
        return {
            "config": config,
            "updated_by": updated_by,
            "updated_at": updated_at,
        }

    def _fail(self, message: str) -> None:
        raise ServiceHandleException(
            msg="invalid ai agent permission config",
            msg_show=message,
            status_code=400,
        )


agent_permission_config_service = AgentPermissionConfigService()
