# -*- coding: utf-8 -*-
from typing import Any, Dict, List

from console.exception.main import ServiceHandleException
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.services.platform_plugin_service import platform_plugin_service


class MCPPlatformPluginTools(object):
    TOOL_NAMES = frozenset({
        "rainbond_list_platform_plugins",
        "rainbond_install_platform_plugin",
    })

    @staticmethod
    def _is_enterprise_admin(user: Any) -> bool:
        explicit = getattr(user, "is_enterprise_admin", None)
        if explicit is not None:
            return bool(explicit)
        enterprise_id = getattr(user, "enterprise_id", None)
        user_id = getattr(user, "user_id", None)
        return bool(enterprise_id and user_id and enterprise_user_perm_repo.is_admin(enterprise_id, user_id))

    @staticmethod
    def _string(max_length: int = 64) -> Dict[str, Any]:
        return {
            "type": "string",
            "minLength": 1,
            "maxLength": max_length,
            "pattern": r"^[^\x00-\x1f\x7f]+$",
        }

    def list_tools(self, user: Any = None) -> List[dict]:
        tools = [{
            "name": "rainbond_list_platform_plugins",
            "description": "List platform plugins and their authoritative whole-application runtime status.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "region_name": self._string(),
                },
                "required": ["region_name"],
            },
        }]
        if self._is_enterprise_admin(user):
            tools.append({
                "name": "rainbond_install_platform_plugin",
                "description": "Install a platform plugin into the server-managed rbd-plugins team.",
                "inputSchema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "region_name": self._string(),
                        "plugin_id": self._string(128),
                    },
                    "required": ["region_name", "plugin_id"],
                },
            })
        return tools

    def handles(self, tool_name: str) -> bool:
        return tool_name in self.TOOL_NAMES

    @staticmethod
    def _required_string(arguments: dict, name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ServiceHandleException(
                msg="invalid {}".format(name),
                msg_show="参数{}无效".format(name),
                status_code=400,
            )
        return value.strip()

    def call_tool(self, user: Any, tool_name: str, arguments: dict) -> Any:
        enterprise_id = getattr(user, "enterprise_id", None)
        if not enterprise_id:
            raise ServiceHandleException(
                msg="enterprise context required",
                msg_show="缺少企业上下文",
                status_code=403,
            )
        region_name = self._required_string(arguments, "region_name")
        if tool_name == "rainbond_list_platform_plugins":
            items = platform_plugin_service.list_platform_plugins_strict(enterprise_id, region_name)
            return {
                "items": items,
                "total": len(items),
            }
        if tool_name == "rainbond_install_platform_plugin":
            if not self._is_enterprise_admin(user):
                raise ServiceHandleException(
                    msg="permission denied",
                    msg_show="只有企业管理员可以安装平台插件",
                    status_code=403,
                )
            plugin_id = self._required_string(arguments, "plugin_id")
            plugins = platform_plugin_service.list_platform_plugins_strict(enterprise_id, region_name)
            installed = next((item for item in plugins if item.get("plugin_id") == plugin_id and item.get("installed")), None)
            if installed:
                result = dict(installed)
                result["already_installed"] = True
                return result
            result = platform_plugin_service.install_platform_plugin(enterprise_id, region_name, plugin_id, user)
            result["already_installed"] = False
            result.setdefault("status", "")
            return result
        raise ServiceHandleException(msg="tool not found", msg_show="工具不存在", status_code=404)


mcp_platform_plugin_tools = MCPPlatformPluginTools()
