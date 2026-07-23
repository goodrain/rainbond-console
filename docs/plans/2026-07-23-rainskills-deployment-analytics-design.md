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
2. 记录部署结果、部署方式、首次/后续报告类型、触发动作和失败信息。
3. RainSkills 数据写入 request-server 新表，供后续独立分析。
4. 不修改现有部署统计口径、查询逻辑和日报分母。
5. 统计故障不得影响 Rainbond 的创建、构建或部署业务流程。

本阶段只实现 RainSkills 部署数据。安装漏斗、页面授权点击、资源创建来源以及 RainAgent/平台拆分不在本次代码范围内。

## 二、用户旅程

### 2.1 用户操作流程

1. 用户执行 RainSkills 安装脚本并选择 Codex、Claude Code 或两者。
2. 安装脚本仍通过原 MCP 地址执行兼容性检测，但为不同客户端注册专用地址：
   - Codex：`/console/mcp/rainskills/codex/query`
   - Claude Code：`/console/mcp/rainskills/claude-code/query`
3. 用户在页面完成现有 JWT 授权，不新增页面或额外交互。
4. AI 客户端通过专用 MCP 地址执行部署工具。
5. Console 从路由可信地得到 `deploy_origin=rainskills` 和客户端类型，将其写入部署诊断载荷。
6. request-server 保持旧表写入行为，并对 RainSkills 载荷幂等旁写新表。
7. 对过去未纳入旧诊断的 RainSkills MCP 部署入口，Console 使用 `rainskills_only` 统计范围，只写新表。

用户不需要配置来源字段，也不能通过 MCP 工具参数伪造来源。

### 2.2 页面原型

本阶段不新增 UI 页面、弹窗、标签或筛选项。授权页面沿用现有交互。

### 2.3 外部系统交互

- Console 继续向 `FIRST_DEPLOY_REPORT_URL` 的 `/api/enterprise/first-deploy` 上报。
- 上报新增可选字段 `deploy_origin`、`deploy_client` 和 `statistics_scope`。
- 旧版 Console 不发送这些字段时，request-server 完全按旧逻辑处理。
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
               EnterpriseFirstDeployService
                 | existing tracked path
                 |   scope=legacy (unchanged) + origin
                 ` missing RainSkills-only path
                     scope=rainskills_only
                              |
                              v
             request-server /api/enterprise/first-deploy
                 | scope=legacy -> old table (unchanged)
                 | origin=rainskills -> new table
                 ` scope=rainskills_only -> new table only
```

### 3.2 核心流程

1. MCP 路由把来源写入 Python `ContextVar`，并在每次 JSON-RPC 调用结束后重置，避免并发请求串值。
2. 部署跟踪创建载荷时读取当前调用上下文；非 MCP 业务默认 `platform`，旧通用 MCP 路由显式使用 `unknown`。
3. request-server 先解析和校验原有部署字段，再根据 `statistics_scope` 决定是否执行原有保存逻辑。
4. `deploy_origin=rainskills` 时按 `deploy_attempt_id` 幂等写新表。
5. 新表写入失败时上报请求返回错误以触发 Console 现有重试；实际 Rainbond 部署已经完成且不回滚。

## 四、数据模型设计

### 4.1 新增数据库表

request-server 新增 `rainskills_deployment`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | uint | 主键 |
| `deploy_attempt_id` | varchar(64) | 部署尝试唯一键，幂等写入 |
| `eid` | varchar(32) | 企业标识 |
| `enterprise_name` | varchar(128) | 企业名称，保持现有上报语义 |
| `deploy_client` | varchar(32) | `codex`、`claude_code` 或 `unknown` |
| `report_type` | varchar(32) | `first_deploy` 或 `deploy_attempt` |
| `deploy_type` | varchar(32) | 原有源码、镜像、市场等部署方式 |
| `trigger` | varchar(64) | 创建部署、直接构建、批量部署等动作 |
| `source_language` | varchar(64) | 源码语言 |
| `is_success` | bool | 最终状态 |
| `deploy_result_at` | datetime | 结果时间 |
| `failure_stage` | varchar(32) | 失败阶段 |
| `failure_category` | varchar(64) | 失败分类 |
| `failure_reason` | varchar(1024) | 脱敏后的失败原因 |
| `deployment_context_json` | longtext | 现有部署上下文，用于后续诊断 |
| `app_context_json` | longtext | 现有应用上下文 |
| `workload_context_json` | longtext | 现有工作负载上下文 |

### 4.2 数据关系

- 新表不与旧表建立数据库外键，避免旧表生命周期和去重策略影响 RainSkills 数据。
- `deploy_attempt_id` 是唯一索引；同一次部署的即时成功回执和后续最终结果使用更新覆盖。
- 旧数据不回填、不推断为 RainSkills。

## 五、API设计

### 5.1 接口列表

| 接口 | 变更 |
|------|------|
| `POST /api/enterprise/first-deploy` | 兼容增加三个可选字段，并条件旁写新表 |
| `POST /console/mcp/rainskills/codex/query` | 新增，复用现有 MCP HTTP 协议 |
| `POST /console/mcp/rainskills/claude-code/query` | 新增，复用现有 MCP HTTP 协议 |
| `POST /console/mcp/query` | 保留，行为不变，来源为 `unknown` |

### 5.2 请求/响应结构

部署上报新增字段：

```json
{
  "deploy_origin": "rainskills",
  "deploy_client": "codex",
  "statistics_scope": "legacy"
}
```

- `statistics_scope=legacy`：保持原有表写入，并在来源为 RainSkills 时旁写新表。
- `statistics_scope=rainskills_only`：不写旧表，只写 RainSkills 新表。
- 缺少新字段：按旧版请求处理。
- 非法来源不会被当作 RainSkills；专用表只接受服务端生成的 `rainskills`。

## 六、核心实现设计

### 6.1 关键逻辑

1. Console 增加部署调用上下文模块，默认平台来源，MCP 视图在调用工具前覆盖并在 `finally` 中恢复。
2. `EnterpriseFirstDeployService` 将来源、客户端和统计范围保存到本地跟踪载荷并上报。
3. 已有部署跟踪入口只增加元数据，原 `report_type`、`deploy_type`、`trigger` 和状态判断不变。
4. 镜像创建、`rainbond_build_component`、`rainbond_operate_app(action=deploy)` 等缺失入口只在
   RainSkills 上下文中创建 `rainskills_only` 的部署尝试跟踪。
5. request-server 将旧保存分支封装为原样调用，再独立执行 RainSkills upsert；`deploy_statistics.go` 不修改。
6. 安装脚本分别生成客户端专用 URL；连通性检测继续使用旧通用地址，兼容尚未升级的 Console，并在专用地址不存在时明确失败而不静默退回通用地址。

### 6.2 复用现有代码

- 复用 `EnterpriseFirstDeployService` 的事件绑定、异步轮询、失败分类、脱敏和重试。
- 复用 request-server 的 JSON 限制、部署类型校验和 GORM 自动迁移。
- 复用 RainSkills 现有 Codex/Claude MCP 配置检测和安装测试框架。

## 七、实施计划

### 跨层覆盖检查

- [ ] Go (rainbond)：不涉及，部署执行接口不变。
- [x] Python (console)：需要，增加可信 MCP 来源上下文、上报字段和 RainSkills-only 跟踪入口。
- [ ] React (rainbond-ui)：不涉及，授权页面交互不变。
- [ ] Plugin frontend (enterprise-base)：不涉及。
- [ ] Plugin backend (plugin-template)：不涉及。
- [x] Go (rainbond-request-server)：需要，增加独立表和条件入库。
- [x] Shell (rainskills)：需要，为 Codex/Claude Code 配置不同专用 MCP 地址。

跨仓库顺序：`rainbond-request-server` -> `rainbond-console` -> `rainskills`。

### Sprint 1: request-server 独立存储

#### Task 1.1: 新增 RainSkills 部署模型和幂等保存

- 仓库：`rainbond-request-server`
- 文件：`first_deploy.go`、`resource.go`、`first_deploy_test.go`
- 实现内容：新增表模型、自动迁移、请求字段、范围路由和 upsert。
- 验收标准：RainSkills 请求写新表；重复 attempt 更新；旧请求只写旧表；only 请求不写旧表。

### Sprint 2: Console 来源传播和部署覆盖

#### Task 2.1: 增加可信 MCP 调用上下文和专用路由

- 仓库：`rainbond-console`
- 文件：`console/services/deployment_invocation.py`、`console/views/mcp_query.py`、`console/urls/__init__.py`、相关测试
- 实现内容：路由固定来源和客户端，通用路由保持 unknown，调用结束重置上下文。
- 验收标准：并发/连续请求不串来源；工具参数无法覆盖来源。

#### Task 2.2: 扩展部署报告并补 RainSkills-only 入口

- 仓库：`rainbond-console`
- 文件：`console/services/enterprise_first_deploy_service.py`、`console/services/mcp_query_service.py`、相关测试
- 实现内容：附加元数据；只对缺失的 RainSkills 部署入口建立 only 跟踪。
- 验收标准：已有路径报告语义不变；新增入口不上报到旧统计范围；失败不阻断业务。

### Sprint 3: RainSkills 客户端标识

#### Task 3.1: 注册客户端专用 MCP 地址

- 仓库：`rainskills`
- 文件：`install.sh`、`tests/install.sh.test`
- 实现内容：Codex 和 Claude Code 使用各自专用 URL，保留通用连通性检测。
- 验收标准：单平台和 all 安装都写入正确 URL，refresh 行为不变。

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| 部署诊断载荷 | `rainbond-console/console/services/enterprise_first_deploy_service.py` | 构造、持久化、轮询和上报 |
| MCP JSON-RPC 调度 | `rainbond-console/console/views/mcp_query.py` | 服务端可信识别入口 |
| MCP 部署工具 | `rainbond-console/console/services/mcp_query_service.py` | 创建、构建、批量部署入口 |
| 旧部署入库 | `rainbond-request-server/first_deploy.go` | 兼容接口和原有去重规则 |
| 旧日报统计 | `rainbond-request-server/deploy_statistics.go` | 必须保持不变 |
| MCP 安装配置 | `rainskills/install.sh` | 为两类客户端注册 URL |
