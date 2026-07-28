# 部署预检权限范围修复设计文档

## 一、项目背景

### 1.1 项目架构

`rainbond-ui` 在用户确认创建组件前调用 `rainbond-console` 的
`POST /console/teams/{tenantName}/apps/deploy_preflight`。Console 通过
`RegionTenantHeaderView` 完成团队上下文和角色权限校验，再执行只读的部署条件检测。

### 1.2 现有基础

- 组件创建权限为 `300013`，可以配置为团队全局权限或指定应用权限。
- 新建应用权限为团队级 `300001`。
- `TenantHeaderView` 只从请求顶层读取 `group_id` 或 `app_id`，以加载指定应用权限。
- 部署预检请求当前只在嵌套的 `payload.group_id` 中携带应用 ID。

### 1.3 核心需求

修复部署预检对权限范围的错误判断：已有应用创建组件时使用该应用的 `300013`；新建应用且尚无
`group_id` 时使用团队级 `300001`。不得扩大用户在其他应用中的权限，也不得改变预检结果结构。

## 二、用户旅程

### 2.1 用户操作流程

- 已有应用：用户进入应用拓扑，点击新增组件，填写源码、镜像或软件包信息并确认创建。预检应识别目标
  应用，拥有该应用 `300013` 的用户可以继续。
- 新建应用：用户从团队入口新建应用并填写首个组件信息。由于预检时应用尚未创建，没有 `group_id`，
  拥有团队级 `300001` 的用户可以继续。
- 用户通过预检后仍按原流程创建应用或组件；预检警告和阻断弹窗保持不变。
- 管理员仍在团队角色页面配置团队级或指定应用权限，无新增配置入口。

### 2.2 页面原型

- 团队角色权限页面：不改页面，仅复用现有“新建应用”和指定应用下“组件创建”权限。
- 组件创建弹窗：不改视觉和交互，仅修正确认创建时发送的权限上下文。
- 部署预检结果弹窗：不改视觉和交互。

### 2.3 外部系统交互

不新增 webhook、回调、通知或第三方集成。现有集群资源和镜像仓库只读检测保持不变。

## 三、整体架构设计

### 3.1 系统架构图

```text
组件创建弹窗
  -> preflightDeploy(group_id 顶层 + 原 payload)
  -> DeployPreflightView.initial()
       -> 有 group_id：指定应用权限 300013
       -> 无 group_id：团队新建应用权限 300001
  -> DeployPreflightService.run()
  -> pass / warning / block
```

### 3.2 核心流程

1. UI 从已有预检 payload 中提取 `group_id`，同时放入 HTTP 请求顶层。
2. Console 优先读取顶层 `group_id`，并兼容旧 UI 的 `payload.group_id`。
3. 有有效目标应用时设置 `perm_app_id`，沿用路由的 `APP_OVERVIEW_CREATE` 权限校验。
4. 没有目标应用时，将本次请求的权限配置切换为 `APP_CREATE_PERMS`。
5. 权限通过后执行原有预检服务；权限失败仍返回 `403 / 10402`。

## 四、数据模型设计

### 4.1 新增数据库表

不涉及。

### 4.2 数据关系

不修改 `role_perms`。继续使用 `app_id = -1` 表示团队全局权限，具体应用 ID 表示应用范围权限。

## 五、API设计

### 5.1 接口列表

| 方法 | 路径 | 变更 |
|------|------|------|
| POST | `/console/teams/{tenantName}/apps/deploy_preflight` | 新增可选顶层 `group_id`，兼容嵌套值 |

### 5.2 请求/响应结构

已有应用请求：

```json
{
  "deploy_type": "source_code",
  "group_id": 7,
  "payload": {
    "group_id": 7
  }
}
```

新建应用请求不携带 `group_id`。响应结构、状态码和预检内容均不变。

## 六、核心实现设计

### 6.1 关键逻辑

- 在 `DeployPreflightView.initial()` 内解析目标应用，保持权限选择只影响该端点。
- 顶层与嵌套 `group_id` 都存在时以顶层为准。
- 非法但非空的 `group_id` 不得降级为新建应用权限，应保持组件创建校验并使应用范围无法匹配。
- UI 请求显式携带顶层 `group_id`，避免依赖后端兼容逻辑。

### 6.2 复用现有代码

- 复用 `RegionTenantHeaderView` 的 `perm_app_id` 和应用权限加载逻辑。
- 复用 `perms.APP_OVERVIEW_CREATE` 与 `perms.APP_CREATE_PERMS`。
- 复用现有部署预检 payload 与结果弹窗，不新增状态或组件。

## 七、实施计划

### 跨层覆盖检查

- [x] Go (rainbond): 不涉及 - 不新增 Region API 或数据模型。
- [x] Python (console): 需要 - 动态选择预检权限范围，增加回归测试和测试清单条目。
- [x] React (rainbond-ui): 需要 - 在预检 HTTP 请求顶层传递 `group_id`，增加请求契约测试。
- [x] Plugin frontend (enterprise-base): 不涉及 - 未调用该接口。
- [x] Plugin backend (plugin-template): 不涉及 - 未代理该接口。

跨仓库实现顺序：先修改并验证 `rainbond-console`，再修改并构建 `rainbond-ui`，最后检查 API 契约。

### Sprint 1: Console 权限范围修复

#### Task 1.1: 增加权限范围回归测试

- 仓库：rainbond-console
- 文件：`console/tests/deploy_preflight_service_test.py:247`
- 实现内容：覆盖已有应用、旧 UI 嵌套应用 ID、新建应用和非法应用 ID。
- 验收标准：测试在实现前失败，实现后通过。

#### Task 1.2: 动态选择权限范围

- 仓库：rainbond-console
- 文件：`console/views/app_create/deploy_preflight.py:12`
- 实现内容：端点内解析 `group_id` 并选择 `300013` 或 `300001`。
- 验收标准：指定应用权限和新建应用权限分别按用户旅程生效。

### Sprint 2: UI 请求契约修复

#### Task 2.1: 提升 group_id 到请求顶层

- 仓库：rainbond-ui
- 文件：`src/services/createApp.js:519`
- 实现内容：预检请求顶层增加 `group_id`，保留原 payload。
- 验收标准：已有应用发送顶层 ID，新建应用发送空值且不改变业务 payload。

#### Task 2.2: 验证前端契约和构建

- 仓库：rainbond-ui
- 文件：`src/components/CreateComponentModal/deployPreflightPayload.node.test.js:1`
- 实现内容：增加可独立执行的请求数据契约测试并运行生产构建。
- 验收标准：Node 测试和 `yarn build` 通过。

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| 预检路由权限 | `console/urls/__init__.py:505` | 当前静态使用组件创建权限 |
| 团队权限加载 | `console/views/base.py:238` | 合并全局和指定应用权限 |
| 权限数据分组 | `console/repositories/perm_repo.py:242` | 按 `app_id` 区分全局和应用权限 |
| 预检视图 | `console/views/app_create/deploy_preflight.py:12` | 本次动态权限入口 |
| UI API 请求 | `src/services/createApp.js:519` | 构造部署预检 HTTP 请求 |
| UI payload | `src/components/CreateComponentModal/deployPreflightPayload.js:1` | 已包含嵌套 `group_id` |
