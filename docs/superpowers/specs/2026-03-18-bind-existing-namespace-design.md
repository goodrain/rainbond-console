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

**已知约束（实施时必须关注）：**
- Console `team_repo.create_tenant`（`console/repositories/team_repo.py:198`）在写 DB 前检查 `Tenants.objects.filter(namespace=...).count() > 0`，若同名 namespace 已在 console DB 存在则抛出 `ServiceHandleException("命名空间已存在")`。绑定新团队时 namespace 尚不在 DB 中，happy path 正常通过；但若该 namespace 曾绑定过已删除的团队（DB 记录残留），该检查会误拦截——此场景需在 `AddTeamView` 加前置说明，当前版本不额外处理，留 TODO。
- Go `CreateTenant` 中 `resources.go` 存在**两个** `CreateTenant` 调用点（line 449 新接口路径、line 473 旧兼容路径），两处均需传递 `bindExisting` 参数。
- Go `CreateTenant` 在 `USE_SAAS=true` 时创建 NetworkPolicy（line 2078），在 `namespace=="rbd-plugins"` 时创建 RBAC（line 2109）。绑定模式下这两段逻辑**跳过**，因为已有 namespace 的 NetworkPolicy/RBAC 由其原有配置负责，Rainbond 不覆盖。

已有过滤能力：
- Go `/v2/cluster/namespace?content=unmanaged` 已按 `app.kubernetes.io/managed-by: rainbond` label 过滤，返回未被 Rainbond 管理的 namespace 列表（`[]string`）
- Console `regionapi.py:1985 list_namespaces(enterprise_id, region, content)` 已有方法代理该接口

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
5. **"确定"按钮在未选中 namespace 时保持 disabled**，防止提交空值
6. 点击"确定"→ 创建团队，同时将该 namespace 纳入 Rainbond 管理（打上 managed-by label）

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
│           [取消]   [确定(disabled)]      │  ← 未选namespace时disabled
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
  GET  /console/enterprise/{eid}/cluster/namespaces?region=xxx
  POST /console/teams/add-teams  {bind_existing_namespace: true}
       ↓
rainbond-console (Django)
  EnterpriseAdminView: list_namespaces(enterprise_id, region, 'unmanaged', format='detail')
  AddTeamView: 透传 bind_existing_namespace=True 给 regionapi
       ↓ Go API
  GET  /v2/cluster/namespace?content=unmanaged&format=detail&eid=xxx
  POST /v2/tenants  {bind_existing_namespace: true, namespace: "xxx"}
       ↓
rainbond (Go)
  GetNamespaceDetail → K8s List Namespaces (过滤 managed-by:rainbond) → [{name, creation_timestamp}]
  CreateTenant(bindExisting=true) → K8s PATCH namespace labels (不创建，不报错)
```

### 3.2 核心流程

**获取 namespace 列表：**
1. 前端选集群后，调用 `GET /console/enterprise/{eid}/cluster/namespaces?region=xxx`
2. Console `ClusterNamespacesView`（继承 `EnterpriseAdminView`，自动注入 `self.enterprise`）调用 `regionapi.list_namespaces(self.enterprise.enterprise_id, region, 'unmanaged', format='detail')`
3. Go handler 按 `format=detail` 返回 `[]NamespaceInfo{Name, CreationTimestamp}`
4. Console view 解包 Go 响应的 body，以 `general_message(200, ..., bean=body)` 格式返回
5. 前端渲染表格

**创建团队（绑定模式）：**
1. 前端 POST `{..., bind_existing_namespace: true, namespace: "selected-ns"}`
2. Console `AddTeamView` 读取 `bind_existing_namespace`，透传给 `regionapi.create_tenant(..., bind_existing=True)`
3. Go `AddTenant` 收到 `BindExistingNamespace=true`，两个调用点（line 449、line 473）均传 `bindExisting=true` 给 `CreateTenant`
4. `CreateTenant`：`k8sErrors.IsAlreadyExists + bindExisting=true` → Get namespace → 追加 managed-by label → Update → 继续（不报错）；NetworkPolicy/RBAC 块在绑定模式下跳过

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
| GET | `/console/enterprise/{eid}/cluster/namespaces` | 新增：获取集群未管理 namespace 列表（含时间） |
| GET | `/v2/cluster/namespace` | 已有，扩展支持 `format=detail` 返回对象数组 |
| POST | `/console/teams/add-teams` | 已有，新增 `bind_existing_namespace` 字段 |
| POST | `/v2/tenants` | 已有，新增 `bind_existing_namespace` 字段 |

### 5.2 请求/响应结构

**GET `/console/enterprise/{eid}/cluster/namespaces?region=xxx`**
```json
// Response（console 标准 general_message 格式）
{
  "code": 200,
  "msg": "success",
  "bean": [
    {"name": "my-namespace", "creation_timestamp": "2026-01-15T10:00:00Z"},
    {"name": "test-ns", "creation_timestamp": "2026-02-20T08:30:00Z"}
  ]
}
```

**GET `/v2/cluster/namespace?content=unmanaged&format=detail&eid=xxx`**
```json
// format=detail 时返回对象数组
[{"name": "my-namespace", "creation_timestamp": "2026-01-15T10:00:00Z"}]
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
- `ClusterHandler` 接口（`cluster.go:71`）新增方法 `GetNamespaceDetail(ctx context.Context, content string) ([]NamespaceInfo, *util.APIHandleError)`
- `clusterAction` 实现 `GetNamespaceDetail`，逻辑与 `GetNamespace` 相同但返回对象
- Controller（`api/controller/cluster.go:135`）按 `format=detail` query param 分支：`format=detail` → `GetNamespaceDetail`，否则 → `GetNamespace`（原有行为）

**Go `CreateTenant` 改造（`api/handler/service.go:2041`）：**

```
改造后逻辑（namespace Create 分支）：

if k8sErrors.IsAlreadyExists(err) {
    if bindExisting {
        // 绑定模式：追加 label，不报错
        ns, getErr := s.kubeClient.CoreV1().Namespaces().Get(ctx, t.Namespace, metav1.GetOptions{})
        if getErr != nil { return getErr }
        if ns.Labels == nil { ns.Labels = make(map[string]string) }
        ns.Labels[constants.ResourceManagedByLabel] = constants.Rainbond
        _, updateErr := s.kubeClient.CoreV1().Namespaces().Update(ctx, ns, metav1.UpdateOptions{})
        if updateErr != nil { return updateErr }
        // 继续执行，跳过 NetworkPolicy/RBAC 块
        return nil  ← 在 NetworkPolicy/RBAC 判断之前提前 return
    }
    return bcode.ErrNamespaceExists  // 普通模式保持原有行为
}
```

注意：绑定模式提前 `return nil`，**有意跳过** NetworkPolicy（line 2078）和 rbd-plugins RBAC（line 2109）块。理由：已有 namespace 的网络策略和 RBAC 由其原有配置负责，Rainbond 绑定时不覆盖。

**函数签名变更：**
- `CreateTenant(t *dbmodel.Tenants)` → `CreateTenant(t *dbmodel.Tenants, bindExisting bool)`
- 接口 `ServiceManager`（`api/handler/service_handler.go:69`）同步更新
- `resources.go` **两处**调用点均需更新：
  - line 449（新接口 eid 路径）：`handler.GetServiceManager().CreateTenant(&dbts, ts.Body.BindExistingNamespace)`
  - line 473（旧兼容路径）：`handler.GetServiceManager().CreateTenant(&dbts, ts.Body.BindExistingNamespace)`

**Console `AddTeamView` 改造（`console/views/team.py:124`）：**
- 读取请求参数 `bind_existing_namespace`（bool，默认 False）
- 通过 `region_api.create_tenant(..., bind_existing=bind_existing_namespace)` 透传给 Go
- 前置检查：若 `bind_existing_namespace=True`，在调用 `team_services.create_team` 前校验 namespace 参数非空，否则返回 `ErrQualifiedName`

**Console `regionapi.create_tenant` 改造（`regionapi.py:110`）：**
- 新增 `bind_existing=False` 参数
- 请求 body 新增 `"bind_existing_namespace": bind_existing`

**React `CreateTeam` 改造：**
- Tab2 "确定"按钮：`disabled={!selectedNamespace}`，防止未选 namespace 时提交
- Tab 切换时重置 namespace 选中状态和 namespace 字段值

### 6.2 复用现有代码

- `regionapi.py:1985 list_namespaces(enterprise_id, region, content)` — 扩展增加 `format` 参数（`format=''` 时不传，保持向后兼容）
- `regionapi.py:110 create_tenant` — 新增 `bind_existing` 参数
- `console/views/team.py AddTeamView` — 新增参数读取和透传
- React `CreateTeam` 中已有集群选择（`useable_regions` Select）— 复用 Select 组件样式，改为单选

---

## 七、实施计划

### 跨层覆盖检查

- [x] Go (rainbond): **需要** — 扩展 `GetNamespace`/`ClusterHandler` 接口；改造 `CreateTenant`（签名 + 两处调用点 + 绑定逻辑）
- [x] Python (console): **需要** — 新增 `ClusterNamespacesView`；`AddTeamView` 透传参数；`regionapi` 扩展两个方法
- [x] React (rainbond-ui): **需要** — `CreateTeam` 增加 Tab + 集群单选 + namespace 表格 + disabled 逻辑
- [ ] Plugin: **不涉及**

### Sprint 1: Go 后端改造

#### Task 1.1: 扩展 ClusterHandler 接口和 GetNamespaceDetail 实现
- 仓库：rainbond
- 文件：`api/handler/cluster.go:71`（接口）、`api/handler/cluster.go:541`（实现）、`api/controller/cluster.go:135`（controller）
- 实现：
  - `NamespaceInfo` 结构体（`api/model/` 或 `api/handler/cluster.go` 文件内）
  - `ClusterHandler` 接口新增 `GetNamespaceDetail` 方法
  - `clusterAction` 实现 `GetNamespaceDetail`
  - Controller 按 `format=detail` 分支调用
- 验收：`GET /v2/cluster/namespace?content=unmanaged&format=detail` 返回 `[{name, creation_timestamp}]`；不传 `format` 时行为与原来完全一致

#### Task 1.2: 改造 CreateTenant 支持绑定已有 namespace
- 仓库：rainbond
- 文件：`api/handler/service_handler.go:69`（接口）、`api/handler/service.go:2041`（实现）、`api/model/`（请求结构体）、`api/controller/resources.go:449+473`（两处调用点）
- 实现：
  - `AddTenantStruct.Body` 新增 `BindExistingNamespace bool`
  - `ServiceManager` 接口和 `CreateTenant` 签名增加 `bindExisting bool`
  - 绑定模式：IsAlreadyExists + bindExisting=true → Get → 追加 label → Update → return nil（提前 return，跳过 NetworkPolicy/RBAC 块）
  - 普通模式（bindExisting=false）：保持原有行为不变
  - `resources.go` line 449 和 line 473 两处调用均传 `ts.Body.BindExistingNamespace`
- 验收：`bind_existing_namespace=true` + 已有 namespace → 团队创建成功，K8s namespace 被打上 managed-by label；`bind_existing_namespace=false` + 新 namespace → 行为与原来一致

### Sprint 2: Console 改造

#### Task 2.1: 新增 ClusterNamespacesView
- 仓库：rainbond-console
- 文件：`console/views/team.py`（追加视图类）、`console/urls/__init__.py`（追加路由）
- 实现：
  - `ClusterNamespacesView(EnterpriseAdminView)` — 使用 `EnterpriseAdminView` 基类，自动注入 `self.enterprise`
  - GET 方法：读取 `region` query param，调用 `region_api.list_namespaces(self.enterprise.enterprise_id, region, 'unmanaged', format='detail')`；解包 Go 响应 body，以 `general_message(200, "success", "OK", bean=body)` 返回
  - URL 注册：在 `console/urls/__init__.py` 企业相关路由区域新增 `url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cluster/namespaces$', ClusterNamespacesView.as_view())`
- 验收：`GET /console/enterprise/{eid}/cluster/namespaces?region=xxx` 返回 namespace 对象列表含创建时间

#### Task 2.2: AddTeamView 透传 bind_existing_namespace + regionapi 扩展
- 仓库：rainbond-console
- 文件：`console/views/team.py:124`、`www/apiclient/regionapi.py:110` 和 `regionapi.py:1985`
- 实现：
  - `regionapi.list_namespaces` 增加可选 `format=''` 参数，非空时附加到 URL query string
  - `regionapi.create_tenant(region, tenant_name, tenant_id, enterprise_id, namespace, bind_existing=False)` 新增参数，body 中追加 `"bind_existing_namespace": bind_existing`
  - `AddTeamView.post`：读取 `bind_existing_namespace = request.data.get("bind_existing_namespace", False)`；若为 True 且 namespace 为空则返回参数错误；透传到 `region_api.create_tenant(..., bind_existing=bind_existing_namespace)`
- 验收：`POST /console/teams/add-teams` 传 `bind_existing_namespace=true` 时 Go 正确收到该标志；`bind_existing_namespace=false` 时行为与原来完全一致

### Sprint 3: React 前端改造

#### Task 3.1: CreateTeam 组件增加 Tab 和 namespace 选择
- 仓库：rainbond-ui
- 文件：`src/services/team.js`、`src/models/teamControl.js`、`src/components/CreateTeam/index.js`
- 实现：
  - `team.js` 新增 `listClusterNamespaces(enterpriseId, region)` 服务函数，调用 `GET /console/enterprise/{enterpriseId}/cluster/namespaces?region={region}`
  - `teamControl.js` 新增 `getClusterNamespaces` effect（与 createTeam effect 并列，不影响其他 effect）
  - `CreateTeam` 组件：
    - 新增 `activeTab`（`'new'|'bind'`）state，默认 `'new'`
    - Tab 切换时重置 `selectedNamespace` 和 namespace 表单字段
    - Tab2 `bind` 模式：集群 Select（单选，`onChange` 触发 `dispatch getClusterNamespaces`）；namespace Table（`rowSelection: {type:'radio'}`，选中后 `form.setFieldsValue({namespace: record.name})` 并设 `namespaceReadonly=true`）
    - "确定"按钮：Tab2 模式下追加 `disabled={!selectedNamespace}` 条件
    - createTeam payload：Tab2 模式追加 `bind_existing_namespace: true`；Tab1 模式不变
- 验收：`yarn build` 通过；Tab2 集群选择后加载 namespace 表格；选中 namespace 后团队英文名称只读并填充；未选 namespace 时确定按钮 disabled；提交后团队创建成功

---

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| GetNamespace 过滤逻辑 | `rainbond/api/handler/cluster.go:541` | 按 label 过滤，`content=unmanaged` |
| ClusterHandler 接口 | `rainbond/api/handler/cluster.go:71` | 需新增 `GetNamespaceDetail` 方法 |
| CreateTenant K8s 操作 | `rainbond/api/handler/service.go:2041` | 两段需关注：IsAlreadyExists(line 2072) 和 NetworkPolicy(line 2078) |
| ServiceManager 接口 | `rainbond/api/handler/service_handler.go:69` | CreateTenant 签名需同步更新 |
| AddTenant 控制器两处调用 | `rainbond/api/controller/resources.go:449+473` | 两处 CreateTenant 均需传 bindExisting |
| Console team_repo 命名空间唯一检查 | `rainbond-console/console/repositories/team_repo.py:198` | 绑定新团队时 happy path 正常；已删团队遗留记录场景留 TODO |
| Console 团队创建视图 | `rainbond-console/console/views/team.py:124` | AddTeamView，新增参数透传 |
| Console region API 客户端 | `rainbond-console/www/apiclient/regionapi.py:110+1985` | create_tenant 和 list_namespaces 均需扩展 |
| EnterpriseAdminView 基类 | `rainbond-console/console/views/base.py` | ClusterNamespacesView 的基类，提供 self.enterprise |
| React CreateTeam 组件 | `rainbond-ui/src/components/CreateTeam/index.js` | 现有表单结构，Tab/state 新增于此 |
| React team 服务 | `rainbond-ui/src/services/team.js:145` | 新增 listClusterNamespaces 于此 |
| React DVA model | `rainbond-ui/src/models/teamControl.js:199` | 新增 getClusterNamespaces effect 于此，与 createTeam 并列 |
