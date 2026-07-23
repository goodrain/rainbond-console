# RainSkills 部署数据独立采集设计文档

## 一、项目背景

### 1.1 项目架构

RainSkills 通过安装脚本把 Rainbond MCP 注册到 Codex 或 Claude Code。用户授权后，AI 客户端调用
Rainbond Console MCP 工具创建、构建和部署应用。Console 已经把部分首次部署和后续部署诊断上报到
`rainbond-request-server`，后者使用 `enterprise_first_deploy` 和 `enterprise_deploy_diagnostic` 生成现有部署日报。

### 1.2 现有基础

- Console 的 `EnterpriseFirstDeployService` 已跟踪源码、软件包、市场、Compose 等部署流程。
- request-server 已按 `deploy_type`、`report_type`、成功状态和失败原因统计首次及后续部署。
- RainSkills 当前给 Codex 和 Claude Code 注册同一个 `/console/mcp/query` 地址，服务端无法识别调用方。
- MCP 中镜像创建、直接构建和批量部署等入口没有全部进入现有部署诊断链路。

### 1.3 核心需求

1. 单独收集 RainSkills 发起的部署，识别实际客户端 `codex` 或 `claude_code`。
2. 记录部署结果、部署方式、初次创建/持续部署阶段、触发动作和失败信息。
3. RainSkills 数据通过独立接口写入 request-server 新表，供后续独立分析。
4. 记录 `service_id`、`app_id` 和 `resource_created`，可分析哪些资源 ID 与 RainSkills 部署尝试关联。
5. 不修改现有部署统计接口、存储、查询逻辑和日报分母。
6. 统计故障不得影响 Rainbond 的创建、构建或部署业务流程。

本阶段只实现 RainSkills 部署数据及其资源 ID 映射。安装漏斗、页面授权点击、在 Rainbond 业务表中
持久化资源来源标签，以及 RainAgent/平台拆分不在本次代码范围内。

## 二、用户旅程

### 2.1 用户操作流程

1. 用户执行 RainSkills 安装脚本并选择 Codex、Claude Code 或两者。
2. 安装脚本仍通过原 MCP 地址执行兼容性检测，但为不同客户端注册专用地址：
   - Codex：`/console/mcp/rainskills/codex/query`
   - Claude Code：`/console/mcp/rainskills/claude-code/query`
3. 用户在页面完成现有 JWT 授权，不新增页面或额外交互。
4. AI 客户端通过专用 MCP 地址执行部署工具。
5. Console 从专用路由得到 `deploy_origin=rainskills` 和客户端类型，在 MCP 调度边界识别部署型工具。
6. Console 使用独立的 RainSkills 跟踪键记录分发和最终事件状态，并上报独立接口。
7. request-server 只把独立接口的数据写入 RainSkills 新表，不调用任何旧部署保存逻辑。

用户不需要配置来源字段，MCP 工具参数不能覆盖路由生成的来源。中央统计接口接收互联网部署的
Console 上报，来源属于分析标签而不是安全凭据；数据不可用于计费、授权或其他安全决策。

### 2.2 页面原型

本阶段不新增 UI 页面、弹窗、标签或筛选项。授权页面沿用现有交互。

### 2.3 外部系统交互

- Console 的既有部署链路继续向 `FIRST_DEPLOY_REPORT_URL` 的 `/api/enterprise/first-deploy` 上报，
  请求结构和行为不变。
- RainSkills 跟踪独立向 `RAINSKILLS_DEPLOY_REPORT_URL` 的 `/api/rainskills/deployments` 上报。
- 新接口严格校验客户端、阶段、状态和部署类型枚举，并限制字符串和数组长度。它是低信任度遥测入口，
  不以无法安全分发到社区 Console 的共享密钥伪装成强认证。
- request-server 不接收 JWT、授权回调内容、代码仓库凭据或其他密钥。

## 三、整体架构设计

### 3.1 系统架构图

```text
RainSkills install.sh
  |-- Codex ------> /console/mcp/rainskills/codex/query
  `-- Claude Code -> /console/mcp/rainskills/claude-code/query
                              |
                              v
                 Console MCP invocation context
                 origin=rainskills, client=...
                              |
                              v
               RainSkillsDeploymentService
                 | classify MCP tool + arguments
                 | persist RAINSKILLS_DEPLOY_* tracker
                 ` poll bounded deployment event ids
                              |
                              v
             request-server /api/rainskills/deployments
                              |
                              v
                    rainskills_deployment

Existing EnterpriseFirstDeployService
  -> /api/enterprise/first-deploy -> old tables/report (unchanged)
```

### 3.2 核心流程

1. MCP 路由把来源写入 Python `ContextVar`，并在每次 JSON-RPC 调用结束后重置，避免并发请求串值。
2. MCP 调度器只在 RainSkills 专用路由下调用独立跟踪服务；普通平台请求和旧通用 MCP 路由不创建新记录。
3. 跟踪服务使用 `RAINSKILLS_DEPLOY_*` 独立键，不读写 `FIRST_DEPLOY_*` 或 `DEPLOY_DIAG_*`。
4. 工具调用失败时上报最终失败；调用成功后先上报 `dispatch`，有事件 ID 时异步轮询并上报 `final`。
5. request-server 按 `deploy_attempt_id` 和阶段序号幂等 upsert；`final` 不可被迟到的 `dispatch` 覆盖。
6. 新接口或新表失败只触发 RainSkills 上报重试；旧统计请求和实际 Rainbond 部署均不重放、不回滚。

## 四、数据模型设计

### 4.1 新增数据库表

request-server 新增 `rainskills_deployment`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | uint | 主键 |
| `deploy_attempt_id` | varchar(64) | 部署尝试唯一键，幂等写入 |
| `eid` | varchar(64) | 企业标识或 Console 稳定生成的匿名标识 |
| `deploy_client` | varchar(32) | `codex`、`claude_code` 或 `unknown` |
| `tool_name` | varchar(96) | 实际触发部署的 MCP 工具 |
| `deploy_type` | varchar(32) | 源码、镜像、软件包、市场或混合部署方式 |
| `deploy_stage` | varchar(32) | `initial`、`continuous` 或 `rollback` |
| `trigger` | varchar(64) | 创建部署、直接构建、批量部署、升级或回滚 |
| `source_language` | varchar(64) | 源码语言 |
| `resource_created` | bool | 本次工具调用是否创建资源 |
| `app_id` | int | Rainbond 应用 ID |
| `service_ids_json` | text | 白名单投影后的组件 ID 数组，最多 50 项 |
| `event_ids_json` | text | 白名单投影后的事件 ID 数组，最多 50 项 |
| `service_count` | int | 截断前组件 ID 去重计数 |
| `event_count` | int | 截断前事件 ID 去重计数 |
| `service_ids_truncated` | bool | 组件 ID 是否被截断 |
| `event_ids_truncated` | bool | 事件 ID 是否被截断 |
| `report_phase` | varchar(16) | `dispatch` 或 `final` |
| `phase_sequence` | tinyint | `dispatch=1`、`final=2`，用于防止状态降级 |
| `status` | varchar(16) | `accepted`、`success`、`failure` 或 `timeout` |
| `deploy_result_at` | datetime | 结果时间 |
| `failure_stage` | varchar(32) | 失败阶段 |
| `failure_category` | varchar(64) | 失败分类 |
| `failure_reason` | varchar(1024) | 脱敏后的失败原因 |

### 4.2 数据关系

- 新表不与旧表建立数据库外键，旧接口也不会触达新表。
- `deploy_attempt_id` 是唯一索引；upsert 只接受阶段序号不小于当前值的更新，最终结果不会被迟到回执降级。
- 不保存企业名称、完整参数、应用上下文、环境上下文、工作负载上下文或日志；失败原因沿用脱敏并限制长度。
- 自动保留策略不在本次代码范围，记录遵循 request-server 日志数据库现有运维保留策略。
- 旧数据不回填、不推断为 RainSkills。

## 五、API设计

### 5.1 接口列表

| 接口 | 变更 |
|------|------|
| `POST /api/enterprise/first-deploy` | 不修改 |
| `POST /api/rainskills/deployments` | 新增，只写 RainSkills 新表 |
| `POST /console/mcp/rainskills/codex/query` | 新增，复用现有 MCP HTTP 协议 |
| `POST /console/mcp/rainskills/claude-code/query` | 新增，复用现有 MCP HTTP 协议 |
| `POST /console/mcp/query` | 保留，行为不变，来源为 `unknown` |

### 5.2 请求/响应结构

RainSkills 独立部署上报：

```json
{
  "deploy_attempt_id": "4f8f...",
  "eid": "stable-enterprise-id",
  "deploy_client": "codex",
  "tool_name": "rainbond_build_component",
  "deploy_type": "source_code",
  "deploy_stage": "continuous",
  "trigger": "build_component",
  "resource_created": false,
  "app_id": 12,
  "service_ids": ["svc-1"],
  "event_ids": ["event-1"],
  "service_count": 1,
  "event_count": 1,
  "service_ids_truncated": false,
  "event_ids_truncated": false,
  "report_phase": "dispatch",
  "status": "accepted"
}
```

- `eid` 必填且最长 64 字符；Console 优先使用企业 ID，缺失时以 `tenant_name|region_name` 计算稳定 UUIDv5，
  不发送原始租户名。
- request-server 使用 64 KiB HTTP body 硬上限；新接口只接收固定白名单字段，未知字段不会持久化。
- 枚举非法、attempt ID 缺失、数组超限或字段超长返回 `400`。
- `phase_sequence` 不由客户端提交，由 request-server 按 `report_phase` 派生；只允许
  `dispatch + accepted` 和 `final + success/failure/timeout`。
- 处理器执行可配置的进程内全局及 EID 固定窗口限流，超限返回 `429`；生产入口仍可叠加网关限流。
- Console 对 ID 去重、排序后确定性保留前 50 项，同时发送截断前计数和 truncated 标记；request-server
  校验 count 不小于数组长度，合法大批次不会因数组超限进入永久重试。
- 相同 attempt 的重复请求返回成功；阶段序号较小的迟到请求不更新已存最终结果。
- 旧接口不解析这些字段，保证旧版与新版请求的旧统计行为一致。

## 六、核心实现设计

### 6.1 关键逻辑

1. Console 增加部署调用上下文模块，默认来源不是 RainSkills；MCP 视图在专用路由调用工具前覆盖并在
   `finally` 中恢复。
2. `RainSkillsDeploymentService` 在 MCP JSON-RPC 调度边界按固定矩阵识别部署工具，使用独立仓储和
   `RAINSKILLS_DEPLOY_*` 键持久化，绝不调用 `begin_deploy_tracking()`。
3. 工具成功返回后从白名单结果字段提取事件 ID 和资源 ID；有事件时异步轮询 Region 事件状态，
   无事件时只记录 `accepted`，不把“接口调用成功”伪装成“部署最终成功”。
4. 工具调用异常转换为脱敏、限长的最终失败统计，然后原异常继续按现有 MCP 协议返回。
5. request-server 新处理器只调用 RainSkills 仓储；`AddEnterpriseFirstDeploy`、旧模型和
   `deploy_statistics.go` 不修改。
6. 安装脚本在写配置前分别向目标专用 URL 发起 `initialize` 校验，失败不写配置且不退回通用路由。
7. `refresh` 仅迁移由脚本管理且仍精确指向 `/console/mcp/query` 的旧配置；自定义地址保持不变并提示。

独立 tracker 状态机：

1. 创建 `RAINSKILLS_DEPLOY_*` 记录后调用工具；调用异常写 `final/failure`。
2. 工具成功且没有事件 ID：上报 `dispatch/accepted`，中央接受后删除本地记录。
3. 工具成功且有事件 ID：上报 dispatch 后保留记录并轮询；最终成功、失败或超时上报被中央接受后删除。
4. dispatch/final 上报失败时保留记录，独立 sweeper 在重启后继续上报或轮询；进程内 running-key 集合防止重复 worker。
5. 轮询达到 20 分钟写 `final/timeout`；中央持续不可用超过 7 天时删除本地记录并记录限量警告，
   避免 `ConsoleSysConfig` 无界增长。

部署入口验收矩阵：

| MCP 工具/条件 | 新跟踪 | 现有 legacy 跟踪 | stage / trigger / type | 标准化事件来源 |
|------|------|------|------|------|
| `rainbond_create_component`、`rainbond_create_component_from_image`，`is_deploy=true` | 是 | 无 | initial / image_create / image | 结果 `event_id`；资源 created |
| `rainbond_create_component_from_source`，`is_deploy=true` | 是 | 有，保持原样 | initial / source_create / source_code | 结果 `event_id/event_ids`；资源 created |
| `rainbond_create_component_from_package`、`rainbond_create_component_from_local_package`，`is_deploy=true` | 是 | 有，保持原样 | initial / package_create / package | 结果 `event_id/event_ids`；资源 created |
| `rainbond_install_app_model`、`rainbond_install_app_by_market`，`is_deploy=true` | 是 | 有，保持原样 | initial / market_install / app_market | 下层 install 返回 events，MCP 结果新增标准 `event_ids/service_ids`；资源 created |
| `rainbond_create_app_from_snapshot_version`，`is_deploy=true` | 是 | 有，保持原样 | initial / snapshot_create / app_market | 透传内部 install 的标准事件字段；资源 created |
| `rainbond_build_helm_app` | 否 | 无 | - | 只生成本地模板；后续 install 才计部署 |
| YAML 创建/检查但尚未 build | 否 | 无 | - | 不发生部署 |
| `rainbond_build_component`，最终 `is_deploy=true` | 是 | 无 | continuous / build_component / 按组件来源映射 | 结果 `event_id` |
| `rainbond_operate_app`，`action=deploy/upgrade` | 是 | 无 | continuous / `operate_app_<action>` / `source_code`、`image`、`package` 或 `mixed` | 现有批量结果标准 `event_ids`；按 service 来源归类，批次含多类即 mixed |
| `rainbond_operate_app`，`action=start/stop/restart` | 否 | 无 | - | 运行操作不计部署 |
| `rainbond_execute_app_upgrade_record` | 是 | 无 | continuous / execute_upgrade_record / app_market | 下层无稳定事件契约时只记录 accepted |
| `rainbond_deploy_app_upgrade_record` | 是 | 无 | continuous / deploy_upgrade_record / app_market | 透传 `upgrade_service.deploy()` events 为标准字段 |
| `rainbond_upgrade_app` | 是 | 无 | continuous / upgrade_app / app_market | 现有升级记录标准化 `event_ids/service_ids` |
| `rainbond_rollback_app_upgrade_record`、`rainbond_rollback_app_version_snapshot` | 是 | 无 | rollback / 对应工具动作 / app_market | 能从记录取得事件则标准化，否则只记录 accepted |

已有 legacy tracking 与新跟踪并行：专用路由不会抑制源码、软件包、市场等下层旧跟踪；原本没有旧跟踪的
镜像创建、直接构建等只产生新记录。若工具返回结构不含事件 ID，必须通过测试明确其状态停留在
`accepted`，不得猜测最终结果。

### 6.2 复用现有代码

- 复用 `EnterpriseFirstDeployService` 已有的事件规范化、失败分类和脱敏纯逻辑，不复用其仓储键或旧上报入口。
- 复用 request-server 的 JSON 限制、部署类型校验和 GORM 自动迁移。
- 复用 RainSkills 现有 Codex/Claude MCP 配置检测和安装测试框架。

## 七、实施计划

### 跨层覆盖检查

- [ ] Go (rainbond)：不涉及，部署执行接口不变。
- [x] Python (console)：需要，增加路由派生的 MCP 来源上下文和独立 RainSkills 跟踪入口。
- [ ] React (rainbond-ui)：不涉及，授权页面交互不变。
- [ ] Plugin frontend (enterprise-base)：不涉及。
- [ ] Plugin backend (plugin-template)：不涉及。
- [x] Go (rainbond-request-server)：需要，增加独立表和条件入库。
- [x] Shell (rainskills)：需要，为 Codex/Claude Code 配置不同专用 MCP 地址。

跨仓库顺序：`rainbond-request-server` -> `rainbond-console` -> `rainskills`。

### Sprint 1: request-server 独立存储

#### Task 1.1: 新增 RainSkills 部署模型、独立接口和有序幂等保存

- 仓库：`rainbond-request-server`
- 文件：`rainskills_deployment.go`、`resource.go`、`router.go`、`rainskills_deployment_test.go`
- 实现内容：新增表模型、自动迁移、body/速率限制、严格请求 DTO、独立路由和带阶段优先级的 upsert。
- 验收标准：独立请求只写新表；重复 attempt 幂等；final 不被迟到 dispatch 覆盖；旧接口与日报回归不变。

### Sprint 2: Console 来源传播和部署覆盖

#### Task 2.1: 增加路由派生的 MCP 调用上下文和专用路由

- 仓库：`rainbond-console`
- 文件：`console/services/deployment_invocation.py`、`console/views/mcp_query.py`、`console/urls/__init__.py`、相关测试
- 实现内容：路由固定来源和客户端，通用路由保持 unknown，调用结束重置上下文。
- 验收标准：并发/连续请求不串来源；工具参数无法覆盖来源。

#### Task 2.2: 增加独立 RainSkills 部署跟踪服务

- 仓库：`rainbond-console`
- 文件：`console/repositories/rainskills_deployment_repo.py`、`console/services/rainskills_deployment_service.py`、
  `console/views/mcp_query.py`、`console/services/mcp_query_service.py`、`console/services/market_app_service.py`、
  `console/services/upgrade_services.py`、相关测试
- 实现内容：按部署矩阵建立独立 tracker；补齐所需的标准事件返回契约；实现恢复、重试、超时和清理。
- 验收标准：矩阵逐项测试；只使用独立键和接口；原本无 legacy tracking 的镜像创建、直接构建不占用
  `FIRST_DEPLOY_*`，随后平台首次部署仍写旧首次部署记录；已有 legacy tracking 的源码、软件包和市场路径
  保持旧行为；重启恢复和上报故障不阻断工具调用。

### Sprint 3: RainSkills 客户端标识

#### Task 3.1: 注册客户端专用 MCP 地址

- 仓库：`rainskills`
- 文件：`install.sh`、`tests/install.sh.test`、`README.md`
- 实现内容：Codex 和 Claude Code 使用各自专用 URL，写入前校验；refresh 先备份再迁移脚本管理的旧通用配置。
- 验收标准：单平台和 all 安装都写入正确 URL；专用路由校验失败保持原配置；自定义配置不被 refresh 覆盖；
  README 与迁移行为一致。

### 质量门槛

- `rainbond-request-server`：`go test ./...`、`go vet ./...`、`go build ./...`。
- `rainbond-console`：RainSkills/旧首次部署定向 pytest、完整 `make check`。
- `rainskills`：`bash -n install.sh`、`bash tests/install.sh.test`。
- 通过数据库计数和旧日报接口回归测试证明：新接口请求不会写入
  `enterprise_first_deploy`、`enterprise_deploy_diagnostic`，旧日报输出不变。
- Console 测试覆盖独立 tracker 的重启恢复、重复 worker、中央不可用重试、无事件清理和超时清理。
- Console 和 request-server 测试覆盖超过 50 个组件/事件的确定性截断、原始计数及合法入库。

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| 旧部署诊断载荷 | `rainbond-console/console/services/enterprise_first_deploy_service.py` | 仅复用纯逻辑，旧行为必须保持 |
| 旧跟踪键 | `rainbond-console/console/repositories/first_deploy_repo.py` | 新服务禁止读写这些前缀 |
| MCP JSON-RPC 调度 | `rainbond-console/console/views/mcp_query.py` | 从专用路由派生分析来源 |
| MCP 部署工具 | `rainbond-console/console/services/mcp_query_service.py` | 创建、构建、批量部署入口 |
| 旧部署入库 | `rainbond-request-server/first_deploy.go` | 兼容接口和原有去重规则 |
| 旧日报统计 | `rainbond-request-server/deploy_statistics.go` | 必须保持不变 |
| MCP 安装配置 | `rainskills/install.sh` | 为两类客户端注册 URL |
