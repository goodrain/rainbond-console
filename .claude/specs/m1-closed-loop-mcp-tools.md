# M1 自动排障 loop 内核 — 3 个闭环信号 MCP 工具 规范

- 仓库：`rainbond-console` · 分支：`feat/app-to-template`
- 设计文档：`docs/plans/2026-06-25-opensource-app-to-template-design.md`（第五章 API 设计 + 第九章 M0 实证）
- 机器可解析版：`.claude/specs/m1-closed-loop-mcp-tools.yaml`
- 全部实现在 `console/services/mcp_query_service.py`，复用既有 region API 客户端与 helper，零新增数据表。

## 范围裁剪（brainstorming 已确认）

- **`get_config_file_content` 不重复实现** —— 已被现有 `rainbond_get_config_file`（PR #1930）完全覆盖（读 config-file 卷内容、宕机也能读）。M1 工具 #3 只做 `analyze_env_conflicts`。

## 三工具（按 M0 实测痛感排序）

| # | 工具 | 复用引擎 | 输出 |
|---|------|----------|------|
| 1（最痛）| `get_app_health_overview(team,region,app_id)` | `group_service.get_group_services` + 一次批量 `base_service.status_multi_service`；仅对 `status != running` 组件 `_collect_pod_warnings` + `classify_failure` | `{app_status, components:[{service_id,name,status,critical_blocker}], total}` |
| 2 | `wait_for_build_completion(team,region,app_id,service_id,event_id,timeout)` | `region_api.get_target_events_list` 定位事件；终态判定；`_read_failure_event_log_tail`(脱敏)+`classify_failure` | `{status: success/failure/running, event_id, error_summary, classified_reason, timeout}` |
| 3 | `analyze_env_conflicts(team,region,app_id,service_id)` | `env_var_service.get_all_envs_incloud_depend_env` 合并自身+依赖注入 env，按 `attr_name` 分组 | `{conflicts:[{attr_name, sources:[{origin,value,scope,service_id}]}], total}` |

## 关键实现决策

- **健康总览成本**：状态走一次批量调用（便宜）；只对非 running 组件深挖 pod 告警 → 成本随**故障数**增长而非组件总数。全绿时近乎零额外 region 调用。
- **构建等待轮询**：**有界阻塞** —— 服务端 `time.sleep(5)` 循环直到终态或上限；`default timeout=60s`、`硬上限 120s`（clamp）。终态(success/failure/timeout)立即返回；超上限未终态返回 `status=running`+`event_id` 供续等。消除 M0 的 `for+sleep+curl` 自旋，又把 gunicorn worker 占用上限封在 120s。失败摘要复用已脱敏的 `_read_failure_event_log_tail`，**不返回原始日志**。
- **env 冲突**：同名同值不算冲突；同名多值 / 自身 vs 依赖注入跨源不一致才判冲突。覆盖 M0 的 `<ALIAS>_PORT` 412 同名碰撞类。

## 接入方式（每工具一致，沿用既有模式）

1. 实现方法 `def xxx(self, user, arguments) -> dict`
2. `call_tool` 内加 `if name == "rainbond_xxx": return self.xxx(...)`
3. `list_tools` 列表加 `self._tool_xxx()`
4. 新增 `_tool_xxx()` 返回 `{name, description, inputSchema}`
5. `test-manifest.json` 登记能力条目（`console.mcp.*`）—— CI 门控要求

## Commit 分组（垂直切片，按痛感顺序）

- **commit-1**：`feat(mcp): add get_app_health_overview tool...`（task-1.1 TDD + 1.2 注册）
- **commit-2**：`feat(mcp): add wait_for_build_completion tool...`（task-2.1 + 2.2）
- **commit-3**：`feat(mcp): add analyze_env_conflicts tool...`（task-3.1 + 3.2）+ 回灌文档进度行

## 质量门控

- TDD：每工具先写失败测试（`SimpleTestCase` + mock region_api/repo，不依赖活集群）
- `make check`（flake8 max-line 129）
- 测试用现有 harness（Docker py3.6 + openapi-client tarball，见记忆 `local-test-harness` / `mypy-typecheck-harness`）
- 每工具新增能力 `capability_id` 标记 + `test-manifest.json` 条目（避免 CI drift）

## 活体验证靶子

`dify-poc`（team `tynwrm27`, region `rainbond`, app_id `3141`, 9 组件 running）—— 单元测试绿后用它打真实数据验证 3 工具。**勿删该应用。**
