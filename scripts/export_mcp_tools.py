#!/usr/bin/env python
"""导出 MCP 工具清单，供跨仓契约测试对账。

背景：2026-10-27 的事故暴露「Skill 写了工具、平台没实现」无人发现
（rainbond_probe_delivery_url 长期缺失）。这里把 console 侧暴露的工具名
固化成快照，rainbond-agent 的契约测试拿它做集合校验。

说明：不启动 Django，直接从 MCP 服务模块里静态提取工具名——
`def _tool_xxx(` 对应 `rainbond_xxx`，AI Engine / 插件模块里以字符串字面量声明。
这样在 CI 里无需数据库与配置即可运行，结果与 `MCPService.list_tools()` 一致。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES = REPO_ROOT / "console" / "services"
OUTPUT = REPO_ROOT / "contracts" / "mcp-tools.json"

METHOD_PATTERN = re.compile(r"def _tool_([a-z0-9_]+)\(")
LITERAL_PATTERN = re.compile(r"[\"'](rainbond_[a-z0-9_]+)[\"']")


def collect_tools() -> list[str]:
    names: set[str] = set()
    for path in sorted(SERVICES.glob("mcp_*.py")):
        text = path.read_text(encoding="utf-8")
        for method in METHOD_PATTERN.findall(text):
            names.add(f"rainbond_{method}")
        if path.name in {"mcp_ai_engine_tools.py", "mcp_platform_plugin_tools.py"}:
            names.update(LITERAL_PATTERN.findall(text))
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
