#!/usr/bin/env python
"""导出 MCP 工具清单，供跨仓契约测试对账。

背景：2026-10-27 的事故暴露「Skill 写了工具、平台没实现」无人发现
（rainbond_probe_delivery_url 长期缺失）。这里把 console 侧暴露的工具名
固化成快照，rainbond-agent 的契约测试拿它做集合校验。

说明：不启动 Django，从 list_tools 实际引用的工具描述中读取 name 字面量。
函数名不是工具名；未加入公开列表的历史描述函数不会进入快照。
快照记录完整工具集，运行时仍可按身份和客户端过滤。
"""
from __future__ import annotations

import json
import re
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES = REPO_ROOT / "console" / "services"
OUTPUT = REPO_ROOT / "contracts" / "mcp-tools.json"

TOOL_NAME_PATTERN = re.compile(r"rainbond_[a-z0-9_]+\Z")


def literal_tool_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and TOOL_NAME_PATTERN.fullmatch(node.value):
        return node.value
    return None


def descriptor_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if not isinstance(item, ast.Dict):
            continue
        for key, value in zip(item.keys, item.values):
            if isinstance(key, ast.Constant) and key.value == "name":
                name = literal_tool_name(value)
                if name:
                    names.add(name)
    return names


def collect_tools() -> list[str]:
    names: set[str] = set()
    for filename in ("mcp_query_service.py", "mcp_ai_engine_tools.py", "mcp_platform_plugin_tools.py"):
        tree = ast.parse((SERVICES / filename).read_text(encoding="utf-8"))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
            listing = methods.get("list_tools")
            if listing is None:
                continue
            names.update(descriptor_names(listing))
            referenced = {node.func.attr for node in ast.walk(listing)
                          if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                          and isinstance(node.func.value, ast.Name) and node.func.value.id == "self"
                          and node.func.attr.startswith("_tool_")}
            for method in referenced:
                descriptors = descriptor_names(methods[method])
                if len(descriptors) != 1:
                    raise ValueError(f"Expected one literal tool name in {filename}:{method}")
                names.update(descriptors)
            # AI Engine declares schema entries keyed by public tool name.
            for node in ast.walk(listing):
                if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
                        and any(isinstance(target, ast.Name) and target.id == "definitions" for target in node.targets)):
                    names.update(name for key in node.value.keys if (name := literal_tool_name(key)))
    return sorted(names)


def main() -> None:
    tools = collect_tools()
    payload = {
        "version": 1,
        "note": "MCP 工具快照。由 console/scripts/export_mcp_tools.py 生成，请勿手工编辑。",
        "generated_from": "rainbond-console::console/services/mcp_*.py",
        "tools": [{"name": name} for name in tools],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(tools)} tools)")


if __name__ == "__main__":
    main()
