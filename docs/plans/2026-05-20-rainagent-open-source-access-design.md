# RainAgent 开源版访问控制设计文档

## 一、项目背景
### 1.1 项目架构

RainAgent 前端入口位于 `rainbond-ui`，由全局 `AgentRootShell` 挂载抽屉，并在 `GlobalHeader` 中展示“AI助手”入口。当前入口展示逻辑主要依赖登录状态、当前路由是否隐藏、抽屉是否已打开，以及 `teamControl.pluginsList` 中是否已安装 `rainbond-agent` 插件。

Agent 对话请求通过 `rainbond-ui` 的 `/api/v1/copilot` 代理到 Agent 服务。Rainbond 平台侧的企业、用户、插件安装状态、SaaS 标识等信息由 `rainbond-console` 提供。企业管理员身份目前来自 `enterprise_user_perm` 表，当前用户详情接口会返回 `is_enterprise_admin`。

### 1.2 现有基础

- `rainbond-ui/src/components/GlobalHeader/index.js`
  - 读取 `teamControl.pluginsList` 判断 `rainbond-agent` 是否安装
  - 已安装时 dispatch `agent/show` 打开抽屉
  - 未安装时管理员跳转扩展中心，非管理员提示联系管理员
- `rainbond-ui/src/utils/agentContext.js`
  - 定义 Agent 隐藏路由，包括登录、OAuth、shell、webconsole
- `rainbond-console/console/views/logos.py`
  - `USE_SAAS` 开启时返回 `rainbondInfo.is_saas = true`
- `rainbond-ui/src/utils/pulginUtils.js`
  - `rainbond-enterprise-base` 安装状态代表企业基础插件能力
- `rainbond-console/console/models/main.py`
  - `EnterpriseUserPerm` 保存用户在企业内的身份
- `rainbond-console/console/services/user_services.py`
  - 已存在 `get_enterprise_first_user`
  - 已存在旧环境下第一个企业用户自动补管理员权限的兼容逻辑

### 1.3 核心需求

保持现有开源版、企业版、SaaS 的判断条件不变：

- 开源版：非 SaaS，且未安装 `rainbond-enterprise-base`
- 企业版：已安装 `rainbond-enterprise-base`
- SaaS / 企业 + SaaS：`USE_SAAS` 开启

在此基础上新增 RainAgent 访问控制：

- 开源版仅允许第一个注册的企业管理员打开 RainAgent
- 开源版其他用户或其他企业管理员不可打开 RainAgent，需要提示升级企业版
- 企业版、SaaS、企业 + SaaS 保持现有行为：只要 `rainbond-agent` 插件已安装，即可按现有权限打开
- 前端拦截不能作为唯一安全边界，Agent 会话和消息接口必须有后端强校验

## 二、整体架构设计
### 2.1 系统架构图

```text
rainbond-ui GlobalHeader
  -> 读取 rainbond-agent 插件安装状态
  -> 调用 Agent 访问权限接口
      ↓
rainbond-console AgentAccessService
  -> 判断平台形态：SaaS / 企业基础插件 / 开源
  -> 确保首个企业管理员标识存在
  -> 返回 can_open_agent / deny_reason
      ↓
rainbond-ui
  -> can_open_agent=true: dispatch agent/show
  -> can_open_agent=false: 提示升级企业版或联系管理员

Agent API / Copilot API
  -> 后端复用同一访问控制服务
  -> 拒绝绕过前端的非法请求
```

### 2.2 核心流程

1. 用户点击 `GlobalHeader` 的“AI助手”入口。
2. 前端保持现有 `rainbond-agent` 插件安装判断：
   - 未安装：企业管理员跳转扩展中心安装，非管理员提示联系管理员。
   - 已安装：继续调用 Agent 访问权限接口。
3. `rainbond-console` 判断当前企业是否为开源版：
   - `USE_SAAS` 开启时，不按开源版限制。
   - 任一可用集群已安装 `rainbond-enterprise-base` 时，不按开源版限制。
   - 其余情况为开源版。
4. 开源版下，`rainbond-console` 确保首个企业管理员标识存在。
5. 当前用户同时满足以下条件时，允许打开：
   - 当前企业管理员
   - 是该企业的 `is_initial_enterprise_admin`
6. 企业版或 SaaS 下，不做首个管理员限制，保持现有 Agent 打开逻辑。
7. Agent 会话创建和消息发送接口复用同一服务校验，避免绕过 UI。

## 三、数据模型设计
### 3.1 新增数据库表

无新增表。

在 `enterprise_user_perm` 表增加字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `is_initial_enterprise_admin` | bool | false | 是否为该企业首个企业管理员 |

建议增加索引：

```text
idx_enterprise_initial_admin(enterprise_id, is_initial_enterprise_admin)
```

是否增加数据库唯一约束需按 MySQL 版本和现有迁移能力评估。即使不加唯一约束，业务层也必须保证同一企业最终只有一个 `true`。

### 3.2 数据关系

- `Users.enterprise_id`
  - 标识用户所属企业。
- `Users.create_time` / `Users.user_id`
  - 用于判定历史数据中的“第一个注册用户”。
- `EnterpriseUserPerm.enterprise_id + user_id`
  - 标识用户在企业下的权限身份。
- `EnterpriseUserPerm.identity`
  - 包含 `admin` 时代表企业管理员。
- `EnterpriseUserPerm.is_initial_enterprise_admin`
  - 新增标识，代表开源版下可打开 RainAgent 的首个企业管理员。

推荐判定顺序：

1. 优先使用已有 `is_initial_enterprise_admin=true` 记录。
2. 若无标识，按企业管理员中最早注册用户补标识。
3. 若无企业管理员记录，兼容旧逻辑：选择该企业最早注册用户，补管理员权限并补标识。

## 四、API设计
### 4.1 接口列表

新增 console 接口：

```http
GET /console/agent/access
```

用途：返回当前用户是否可打开 RainAgent，以及被拒绝的原因。

可选增强：当前用户详情接口增加字段：

```json
{
  "is_initial_enterprise_admin": true
}
```

该字段用于展示和调试，不作为前端唯一判断依据。

### 4.2 请求/响应结构

请求：

```http
GET /console/agent/access
Authorization: JWT ...
```

响应：

```json
{
  "status_code": 200,
  "msg": "success",
  "bean": {
    "can_open_agent": true,
    "edition": "open_source",
    "is_saas": false,
    "has_enterprise_base": false,
    "is_enterprise_admin": true,
    "is_initial_enterprise_admin": true,
    "deny_reason": ""
  }
}
```

拒绝示例：

```json
{
  "status_code": 200,
  "msg": "success",
  "bean": {
    "can_open_agent": false,
    "edition": "open_source",
    "is_saas": false,
    "has_enterprise_base": false,
    "is_enterprise_admin": true,
    "is_initial_enterprise_admin": false,
    "deny_reason": "open_source_requires_enterprise"
  }
}
```

`deny_reason` 约定：

| 值 | 含义 |
|----|------|
| `""` | 允许打开 |
| `not_authenticated` | 未登录 |
| `not_enterprise_admin` | 开源版下当前用户不是企业管理员 |
| `open_source_requires_enterprise` | 开源版下非首个企业管理员，需要升级企业版 |
| `enterprise_not_found` | 企业信息不存在 |

Agent / Copilot 后端接口被拒绝时应返回 403：

```json
{
  "code": 403,
  "msg": "agent access denied",
  "msg_show": "开源版仅首个企业管理员可使用 AI 助手，请升级企业版后开放给更多成员。",
  "deny_reason": "open_source_requires_enterprise"
}
```

## 五、核心实现设计
### 5.1 关键逻辑

#### 5.1.1 平台形态判断

新增 `edition_service` 或 `agent_access_service` 内部方法：

```python
def get_platform_edition(enterprise_id):
    is_saas = bool(os.getenv("USE_SAAS"))
    has_enterprise_base = has_installed_enterprise_base_plugin(enterprise_id)

    if is_saas and has_enterprise_base:
        return "enterprise_saas"
    if is_saas:
        return "saas"
    if has_enterprise_base:
        return "enterprise"
    return "open_source"
```

`has_installed_enterprise_base_plugin` 保持现有判断条件：从已安装官方插件列表中判断是否存在 `rainbond-enterprise-base`。可遍历企业可用集群，只要任一集群安装即认为企业版能力已启用。

#### 5.1.2 首个企业管理员标识生成

新增服务方法：

```python
def ensure_initial_enterprise_admin_marker(enterprise_id):
    # 1. 已有唯一标识则直接返回
    # 2. 多个标识则保留最早用户，清理其他标识
    # 3. 无标识时进入事务补齐
```

补齐规则：

1. 查询 `enterprise_user_perm` 中该企业所有管理员。
2. 关联 `user_info`，按 `Users.create_time ASC, Users.user_id ASC` 排序。
3. 选择第一位管理员，设置 `is_initial_enterprise_admin=true`。
4. 如果没有管理员权限记录：
   - 查询该企业最早用户。
   - 创建或更新其 `enterprise_user_perm` 为 `admin`。
   - 设置 `is_initial_enterprise_admin=true`。
5. 如果企业没有任何用户，返回 `None`。

并发控制：

- 使用数据库事务。
- 事务内重新查询标识记录。
- 写入前将该企业其他记录统一置为 `false`，再设置目标记录为 `true`。
- 这样即使并发请求同时触发懒修复，最终也能收敛到一个标识用户。

#### 5.1.3 当前用户访问判断

```python
def get_agent_access(user):
    edition = get_platform_edition(user.enterprise_id)

    if edition != "open_source":
        return allow()

    marker = ensure_initial_enterprise_admin_marker(user.enterprise_id)
    is_admin = enterprise_user_perm_repo.is_admin(user.enterprise_id, user.user_id)
    is_initial = marker and marker.user_id == user.user_id

    if is_admin and is_initial:
        return allow()

    if not is_admin:
        return deny("not_enterprise_admin")

    return deny("open_source_requires_enterprise")
```

#### 5.1.4 历史数据处理

升级平台时，历史数据库中不会有 `is_initial_enterprise_admin`。需要两层处理：

- 数据迁移 / 管理命令回填
  - 遍历所有企业，执行 `ensure_initial_enterprise_admin_marker(enterprise_id)`。
  - 记录无用户、无企业、修复多个标识等异常日志。
- 运行时懒修复
  - Agent 权限接口调用时执行。
  - 当前用户详情接口可选执行。
  - Copilot API 后端强校验执行。

懒修复是必须的。仅靠迁移无法覆盖恢复旧备份、跳过迁移、手动导入数据等情况。

#### 5.1.5 前端打开逻辑

保留 `GlobalHeader` 现有 `rainbond-agent` 插件判断：

1. `agentPluginStatus === "missing"`：
   - 企业管理员：提示去扩展中心安装。
   - 非管理员：提示联系管理员。
2. `agentPluginStatus === "installed"`：
   - 调用 `/console/agent/access`。
   - `can_open_agent=true`：dispatch `agent/show`。
   - `can_open_agent=false`：展示升级企业版提示。

提示文案：

```text
开源版仅首个企业管理员可使用 AI 助手。
如需为更多成员开放 AI 助手，请升级企业版。
```

#### 5.1.6 后端强校验

以下接口必须复用 `agent_access_service`：

- 创建 Agent 会话
- 发送 Agent 消息
- 审批 Agent 动作
- 恢复或订阅 Agent run 事件

如果 Agent 服务独立于 `rainbond-console`，则需要在网关层或 Agent 服务中通过当前登录凭证调用 console 权限接口，或者复用同一套权限判断依赖。不能只依赖前端判断。

### 5.2 复用现有代码

- 复用 `enterprise_user_perm_repo.is_admin`
- 复用 `user_services.get_enterprise_first_user`
- 复用 `user_services.make_user_as_admin_for_enterprise`
- 复用 `region_api.list_plugins` 或 `rbd_plugin_service.list_plugins` 获取已安装插件
- 复用 `rainbond-ui` 现有 `GlobalHeader.openAgentDrawer`
- 复用 `AgentRootShell` 当前挂载、隐藏路由、抽屉展示逻辑

## 六、实施计划
### Sprint 1: 后端数据标识与访问服务
#### Task 1.1: 增加首个企业管理员标识字段
- 文件：`console/models/main.py`
- 实现内容：
  - 为 `EnterpriseUserPerm` 增加 `is_initial_enterprise_admin`
  - 增加数据库迁移
  - 增加索引
- 验收标准：
  - 新老数据迁移后字段默认值为 false
  - 不影响现有企业管理员判断

#### Task 1.2: 实现首个管理员懒修复服务
- 文件：`console/services/agent_access_service.py`
- 实现内容：
  - 新增 `ensure_initial_enterprise_admin_marker`
  - 处理无标识、多个标识、无管理员权限记录、无用户等场景
  - 使用事务保证并发收敛
- 验收标准：
  - 每个有用户的企业最终只有一个首个管理员标识
  - 历史无标识数据可自动修复

#### Task 1.3: 实现平台形态与 Agent 权限判断
- 文件：`console/services/agent_access_service.py`
- 实现内容：
  - 保持现有版本判断条件不变
  - 返回 `can_open_agent`、`edition`、`deny_reason`
- 验收标准：
  - 开源版仅首个企业管理员允许
  - 企业版和 SaaS 不受首个管理员限制

### Sprint 2: Console API 与历史数据回填
#### Task 2.1: 新增 Agent 权限接口
- 文件：`console/views/agent_access.py`、`console/urls/__init__.py`
- 实现内容：
  - 新增 `GET /console/agent/access`
  - 返回当前用户 Agent 访问权限
- 验收标准：
  - 前端可在打开 Agent 前获取明确权限结论

#### Task 2.2: 当前用户详情补充调试字段
- 文件：`console/views/user_operation.py`
- 实现内容：
  - 可选返回 `is_initial_enterprise_admin`
  - 不改变现有 `is_enterprise_admin` 语义
- 验收标准：
  - 前端或排障时可观察当前用户是否为首个企业管理员

#### Task 2.3: 历史数据回填命令或迁移
- 文件：`console/migrations/*` 或 `console/management/commands/*`
- 实现内容：
  - 遍历企业执行首个管理员标识补齐
  - 输出修复数量与异常日志
- 验收标准：
  - 升级后已有企业可获得稳定标识
  - 回填过程可重复执行，幂等

### Sprint 3: 前端打开链路接入
#### Task 3.1: 新增前端服务调用
- 仓库：`rainbond-ui`
- 文件：`src/services/agentAccess.js` 或现有 service 文件
- 实现内容：
  - 调用 `/console/agent/access`
- 验收标准：
  - 可获取 `can_open_agent` 与 `deny_reason`

#### Task 3.2: 修改 RainAgent 打开逻辑
- 仓库：`rainbond-ui`
- 文件：`src/components/GlobalHeader/index.js`
- 实现内容：
  - 在 `rainbond-agent` 已安装后、`agent/show` 前调用权限接口
  - 拒绝时展示升级企业版提示
- 验收标准：
  - 开源版非首个管理员无法打开抽屉
  - 企业版与 SaaS 行为不变

### Sprint 4: Agent API 强校验
#### Task 4.1: 会话与消息接口增加访问校验
- 文件：Agent/Copilot 服务入口或 console 代理层
- 实现内容：
  - 创建会话、发送消息、审批动作、订阅 run 事件前校验 Agent 访问权限
- 验收标准：
  - 手动请求接口也无法绕过开源版限制

### Sprint 5: 测试与验证
#### Task 5.1: 后端单元测试
- 文件：`console/tests/test_agent_access_service.py`
- 实现内容：
  - 开源版首个管理员允许
  - 开源版非首个管理员拒绝
  - 企业版允许
  - SaaS 允许
  - 历史无标识自动补齐
  - 多个标识自动收敛
- 验收标准：
  - Agent 权限核心规则均有测试覆盖

#### Task 5.2: 前端行为测试
- 仓库：`rainbond-ui`
- 文件：`src/components/GlobalHeader/*`
- 实现内容：
  - 插件未安装保持原逻辑
  - 权限允许时打开
  - 权限拒绝时展示升级提示
- 验收标准：
  - 不破坏现有 `rainbond-agent` 安装引导逻辑

## 七、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| Agent 全局挂载 | `rainbond-ui/src/app.js:39` | 使用 `AgentRootShell` 包裹应用 |
| Agent 入口展示 | `rainbond-ui/src/components/GlobalHeader/index.js:833` | `showAgentLauncher` 判断 |
| Agent 插件判断 | `rainbond-ui/src/components/GlobalHeader/index.js:283` | 判断 `rainbond-agent` 是否安装 |
| Agent 打开逻辑 | `rainbond-ui/src/components/GlobalHeader/index.js:532` | 当前 `openAgentDrawer` |
| Agent 隐藏路由 | `rainbond-ui/src/utils/agentContext.js:108` | 登录、OAuth、shell、webconsole 不展示 |
| SaaS 标识来源 | `rainbond-console/console/views/logos.py:92` | `USE_SAAS` 返回 `is_saas` |
| 企业插件判断 | `rainbond-ui/src/utils/pulginUtils.js:26` | 判断 `rainbond-enterprise-base` |
| 企业用户权限模型 | `rainbond-console/console/models/main.py:497` | `EnterpriseUserPerm` |
| 企业管理员判断 | `rainbond-console/console/repositories/enterprise_repo.py:327` | `enterprise_user_perm_repo.is_admin` |
| 历史首用户兼容 | `rainbond-console/console/services/user_services.py:246` | 第一个企业用户补 admin 权限 |
| 获取企业首用户 | `rainbond-console/console/services/user_services.py:289` | `get_enterprise_first_user` |
