# 对接已有 Namespace 创建团队 设计文档

## 一、项目背景

### 1.1 项目架构

Rainbond 采用三层架构：
- `rainbond-ui`（React 16.8 + UMI 3.5）：用户界面
- `rainbond-console`（Python/Django）：Web 后端，代理协调 Go API 调用
- `rainbond`（Go）：核心服务，直接与 Kubernetes 交互

### 1.2 现有基础

当前"创建团队"流程：
- React `CreateTeam` 组件（`src/components/CreateTeam/index.js`）支持输入团队名称、团队英文名称（即 namespace）、集群、LOGO
- Console `AddTeamView`（`console/views/team.py:124`）接收并验证参数，调用 `team_services.create_team()`
- Go `AddTenant`（`api/controller/resources.go:396`）创建 DB 记录并在 Kubernetes 创建 namespace
- Go `CreateTenant`（`api/handler/service.go:2041`）执行 K8s namespace 创建，若已存在则返回 `ErrNamespaceExists` 报错

已有过滤能力：
- Go `/v2/cluster/namespace?content=unmanaged` 已按 `app.kubernetes.io/managed-by: rainbond` label 过滤，返回未被 Rainbond 管理的 namespace 列表（`[]string`）
- Console `regionapi.py:1985` 已有 `list_namespaces` 方法代理该接口

### 1.3 核心需求

在"创建团队"弹窗中新增"对接已有 Namespace"Tab，允许用户直接选择集群中已存在且未被 Rainbond 管理的 namespace，将其纳入 Rainbond 管理并绑定到新团队。

---

## 二、用户旅程

### 2.1 用户操作流程

**触发入口：** 平台管理 → 项目/团队 → `+创建 项目/团队` 按钮

**Tab 1（原有）"新建团队"：** 填写团队名称 → 自动生成英文名称 → 选集群 → 确定

**Tab 2（新增）"对接已有 Namespace"：**
1. 填写团队名称
2. 选择集群（单选下拉；若仅一个集群则自动选中）
3. 集群选中后异步加载 namespace 表格（过滤已被 Rainbond 管理的 namespace）
4. 从表格中选择一个 namespace（radio 单选），"团队英文名称"自动填充并锁定为只读
5. 点击"确定"→ 创建团队，同时将该 namespace 纳入 Rainbond 管理（打上 managed-by label）

### 2.2 页面原型

**弹窗结构：**
```
┌─────────────────────────────────────────┐
│              创建团队                    │
├─────────────────────────────────────────┤
│  [ 新建团队 ] [ 对接已有 Namespace ]     │  ← Tab 切换
├─────────────────────────────────────────┤
│  * 团队名称   [________________]        │
│              请输入团队名称，最大长度10位 │
│                                         │
│  * 团队英文名称 [__已选namespace__] 🔒   │  ← 只读，由表格选择填充
│              对应该团队在集群中使用的命名空间│
│                                         │
│  * 集群       [  请选择集群  ▼]          │
│                                         │
│  可用 Namespace（仅展示未被 Rainbond 管理）│
│  ┌────────────────────────────────────┐ │
│  │ ○  Namespace 名称  │  创建时间     │ │
│  │ ●  my-namespace   │  2026-01-15   │ │
│  │ ○  test-ns        │  2026-02-20   │ │
│  └────────────────────────────────────┘ │
│                                         │
│           [取消]        [确 定]          │
└─────────────────────────────────────────┘
```

### 2.3 外部系统交互

- Kubernetes API：查询 namespace 列表（通过 Go 端 K8s client）
- Kubernetes API：PATCH namespace labels（纳入 Rainbond 管理）

---

## 三、整体架构设计

### 3.1 系统架构图

```
rainbond-ui (React)
  GET  /console/namespaces?region=xxx&format=detail
  POST /console/teams/add-teams  {bind_existing_namespace: true}
       ↓
rainbond-console (Django)
  GET  /v2/cluster/namespace?content=unmanaged&format=detail
  POST /v2/tenants  {bind_existing_namespace: true, namespace: "xxx"}
       ↓
rainbond (Go)
  GetNamespace → K8s List Namespaces (过滤 managed-by:rainbond)
  CreateTenant → K8s PATCH namespace labels (bind 模式) 或 Create (普通模式)
```

### 3.2 核心流程

**获取 namespace 列表：**
1. 前端选集群后，调用 `GET /console/namespaces?region=xxx&format=detail`
2. Console 代理调用 Go `/v2/cluster/namespace?content=unmanaged&format=detail`
3. Go 返回 `[]NamespaceInfo{Name, CreationTimestamp}`（新增 `format=detail` 支持）
4. 前端渲染表格

**创建团队（绑定模式）：**
1. 前端 POST `{..., bind_existing_namespace: true, namespace: "selected-ns"}`
2. Console `AddTeamView` 透传 `bind_existing_namespace=True` 给 regionapi
3. Go `AddTenant` 收到 `BindExistingNamespace=true`，传给 `CreateTenant`
4. `CreateTenant` 改造：当 `bindExisting=true` 时，对已有 namespace 执行 label 更新（而非报错）

---

## 四、数据模型设计

### 4.1 无新增数据库表

`Tenants` 表现有字段已满足需求，`namespace` 字段存储绑定的 K8s namespace 名称，无需新增字段或表。

### 4.2 数据关系

绑定后团队的 `namespace` 字段 = 已有 K8s namespace 名称，与普通创建团队完全一致，无特殊处理。

---

## 五、API 设计

### 5.1 接口列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/console/namespaces` | 获取集群未管理 namespace 列表（新增 Console 视图） |
| GET | `/v2/cluster/namespace` | 已有接口，扩展支持 `format=detail` |
| POST | `/console/teams/add-teams` | 已有接口，新增 `bind_existing_namespace` 字段 |
| POST | `/v2/tenants` | 已有接口，新增 `bind_existing_namespace` 字段 |

### 5.2 请求/响应结构

**GET `/console/namespaces?region=xxx&format=detail`**
```json
// Response
{
  "data": [
    {"name": "my-namespace", "creation_timestamp": "2026-01-15T10:00:00Z"},
    {"name": "test-ns", "creation_timestamp": "2026-02-20T08:30:00Z"}
  ]
}
```

**GET `/v2/cluster/namespace?content=unmanaged&format=detail`**
```json
// Response（format=detail 时）
[
  {"name": "my-namespace", "creation_timestamp": "2026-01-15T10:00:00Z"}
]
// format 不传时保持原有 []string 行为（向后兼容）
```

**POST `/console/teams/add-teams`（新增字段）**
```json
{
  "team_alias": "我的团队",
  "namespace": "my-namespace",
  "useable_regions": "default",
  "bind_existing_namespace": true
}
```

**POST `/v2/tenants`（新增字段）**
```json
{
  "tenant_id": "xxx",
  "tenant_name": "xxx",
  "eid": "xxx",
  "namespace": "my-namespace",
  "bind_existing_namespace": true
}
```

---

## 六、核心实现设计

### 6.1 关键逻辑

**Go `GetNamespace` 扩展（`api/handler/cluster.go:541`）：**
- 新增 `NamespaceInfo` 结构体：`{Name string, CreationTimestamp string}`
- 新增接口方法 `GetNamespaceDetail(ctx, content) ([]NamespaceInfo, error)`
- 原 `GetNamespace` 保持不变（向后兼容）
- Controller 根据 `format=detail` query param 路由到对应方法

**Go `CreateTenant` 改造（`api/handler/service.go:2066`）：**
```
原逻辑（namespace 已存在时）：
  → k8sErrors.IsAlreadyExists → return bcode.ErrNamespaceExists  ❌

新逻辑（bindExisting=true 时）：
  → k8sErrors.IsAlreadyExists
    → Get 该 namespace
    → 添加 app.kubernetes.io/managed-by: rainbond label
    → Update namespace
    → 继续（不报错）  ✅
```

参考 `service.go:2055-2064`（default namespace 的处理模式）实现。

**函数签名变更：**
- `CreateTenant(t *dbmodel.Tenants)` → `CreateTenant(t *dbmodel.Tenants, bindExisting bool)`
- 接口 `ServiceManager` 同步更新

### 6.2 复用现有代码

- `regionapi.py:1985 list_namespaces` — 已有方法，扩展传 `format=detail` 参数
- `regionapi.py:110 create_tenant` — 已有方法，新增 `bind_existing_namespace` 参数
- `console/views/team.py AddTeamView` — 已有视图，新增参数透传
- React `CreateTeam` 组件中已有集群选择（`useable_regions`）— 复用 Select 组件样式

---

## 七、实施计划

### 跨层覆盖检查

- [x] Go (rainbond): **需要** — 扩展 `GetNamespace` 返回详情；改造 `CreateTenant` 支持绑定模式
- [x] Python (console): **需要** — 新增 `/console/namespaces` 视图；`AddTeamView` 透传 `bind_existing_namespace`
- [x] React (rainbond-ui): **需要** — `CreateTeam` 组件新增 Tab + 集群选择 + namespace 表格
- [ ] Plugin: **不涉及**

### Sprint 1: Go 后端改造

#### Task 1.1: 扩展 GetNamespace 支持 detail 格式
- 仓库：rainbond
- 文件：`api/handler/cluster.go:541`，`api/controller/cluster.go:135`
- 实现：新增 `NamespaceInfo` 结构体，新增 `GetNamespaceDetail` handler 方法，controller 按 `format` 参数分支
- 验收：`GET /v2/cluster/namespace?content=unmanaged&format=detail` 返回 `[{name, creation_timestamp}]`

#### Task 1.2: 改造 CreateTenant 支持绑定已有 namespace
- 仓库：rainbond
- 文件：`api/handler/service.go:2041`，`api/controller/resources.go:396`，`api/model/`
- 实现：`AddTenantStruct.Body` 新增 `BindExistingNamespace bool`；`CreateTenant` 增加 `bindExisting bool` 参数；已有 namespace + bindExisting=true 时 Update labels
- 验收：传 `bind_existing_namespace=true` + 已有 namespace 时团队创建成功，namespace 被打上 managed-by label

### Sprint 2: Console 改造

#### Task 2.1: 新增 namespace 列表视图
- 仓库：rainbond-console
- 文件：`console/views/team.py`，`console/urls/__init__.py`
- 实现：新增 `ClusterNamespacesView`，调用 `regionapi.list_namespaces(region, 'unmanaged', format='detail')`；注册路由 `GET /console/namespaces`
- 验收：`GET /console/namespaces?region=xxx` 返回 namespace 列表含创建时间

#### Task 2.2: AddTeamView 透传 bind_existing_namespace
- 仓库：rainbond-console
- 文件：`console/views/team.py:124`，`www/apiclient/regionapi.py:110`
- 实现：`AddTeamView` 读取 `bind_existing_namespace` 参数；`regionapi.create_tenant` 新增 `bind_existing` 参数并传给 Go
- 验收：`POST /console/teams/add-teams` 传 `bind_existing_namespace=true` 时 Go 收到正确标志

### Sprint 3: React 前端改造

#### Task 3.1: CreateTeam 组件增加 Tab 和 namespace 选择
- 仓库：rainbond-ui
- 文件：`src/components/CreateTeam/index.js`，`src/services/team.js`，`src/models/teamControl.js`
- 实现：
  - `team.js` 新增 `listClusterNamespaces(region, format)` 服务函数
  - `teamControl.js` 新增 `getClusterNamespaces` effect
  - `CreateTeam` 增加 Tab 切换（Ant Design Tabs）；Tab2 包含集群 Select（单选）+ namespace Table（radio + 名称/时间列）；选中后填充并锁定 namespace 字段；createTeam payload 增加 `bind_existing_namespace`
- 验收：`yarn build` 通过；Tab2 可正常选择 namespace 并提交

---

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| GetNamespace 过滤逻辑 | `rainbond/api/handler/cluster.go:541` | 按 label 过滤，`content=unmanaged` |
| CreateTenant K8s 操作 | `rainbond/api/handler/service.go:2041` | namespace 创建，default namespace 更新模式可参考 |
| AddTenant 控制器 | `rainbond/api/controller/resources.go:396` | 请求解析，namespace 字段透传 |
| Console 团队创建视图 | `rainbond-console/console/views/team.py:124` | AddTeamView，namespace 参数处理 |
| Console region API 客户端 | `rainbond-console/www/apiclient/regionapi.py:110` | create_tenant, list_namespaces |
| React CreateTeam 组件 | `rainbond-ui/src/components/CreateTeam/index.js` | 现有表单结构 |
| React team 服务 | `rainbond-ui/src/services/team.js:145` | createTeam 服务函数 |
| React DVA model | `rainbond-ui/src/models/teamControl.js:199` | createTeam effect |
