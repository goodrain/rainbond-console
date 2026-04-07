# 平台资源治理 + 团队资源中心 设计文档

## 一、项目背景

### 1.1 项目架构

| 仓库 | 语言 | 描述 |
|-----|------|------|
| rainbond | Go 1.23 | 核心服务，直接与 Kubernetes 交互 |
| rainbond-console | Python 3.6 / Django 2.2 | Web 后端，代理 Go API 调用 |
| rainbond-ui | React 16.8 / UMI 3.5 | 前端，用户操作界面 |

数据流：`rainbond-ui → console (/console/*) → rainbond (/v2/*) → Kubernetes`

### 1.2 现有基础

- Go 已有 `pkg/helm/helm.go`：Helm v3 SDK，含 `Uninstall`、`PreInstall`、`UpdateRepo`；注意现有 `install()` private helper（line 181）**无条件**将 `ClientOnly` 设为 `true`（hardcoded），`DryRun` 则通过参数传入（非 hardcoded）；`Install` 和 `PreInstall` 均以 `dryRun=true` 调用，两者叠加导致只渲染 manifest，不实际部署
- Console 已有 `HelmRepoInfo` 模型（`www/models/main.py`）、`helm_repo` repository：Helm repo 管理
- Console 已有企业 settings 接口，全局开关字段加到 `TenantEnterprise`（`www/models/main.py`，`db_table='tenant_enterprise'`）
- K8s client-go 已在 Go 中初始化，dynamic client 通过 `k8s.Default().DynamicClient` 获取
- Go 路由中 `/v2/platform` 已被 `platformPluginsRouter()` 占用（插件代理），`/v2/cluster` 已有 `clusterRouter()`（含 `/resource`、`/k8s-resource`、`/namespace`、`/nodes` 等路由），新接口在**现有 `clusterRouter()` 函数内**追加路由，使用 `/platform-resources`、`/storageclasses`、`/persistentvolumes` 子路径（避免与现有 `/resource`、`/k8s-resource` 语义混淆）

### 1.3 核心需求

1. **全局开关**：平台设置中控制团队资源中心入口的显示/隐藏
2. **平台资源**：平台管理员管理所有 cluster-scoped K8s 资源（StorageClass、PV、CRD、RBAC、Namespace 等）
3. **团队资源中心**：团队成员管理当前 team namespace 内所有 namespace-scoped K8s 资源及 Helm 应用

---

## 二、用户旅程

### 2.1 用户操作流程

**平台管理员：**
1. 进入平台管理 → 平台设置 → 基础设置，找到"启用团队资源展示"开关，可开启/关闭
2. 进入平台管理 → 平台资源，查看集群全局资源：
   - 全局存储：查看 StorageClass 列表（名称、Provisioner、默认、回收策略、绑定模式、支持扩容、卷数），创建/删除 StorageClass；查看 PV 列表，创建/删除 PV
   - 权限与访问控制：查看 ClusterRole、ClusterRoleBinding、ServiceAccount（cluster-scoped）
   - 平台扩展：查看 CRD 列表，点击 CRD 查看其 CR 实例
   - 命名空间治理：查看/创建/删除 Namespace

**团队成员（开关开启时）：**
1. 团队侧边栏"资源管理"分组下出现"资源中心"入口
2. 进入资源中心，通过 Tab 查看当前 team namespace 内的各类 K8s 资源
3. 点击"YAML 创建"打开编辑器，填写 YAML 后 apply 到 namespace（自动打 `rainbond.io/source: yaml` 标签）
4. 点击"新建资源"选择 Kind，填写表单（Deployment/Service/ConfigMap 支持结构化表单，其余走 YAML）
5. 点击 Helm 应用 Tab，选已有 Helm repo → 搜索 chart → 填 release name + values → 直接安装到集群
6. 对任意资源可查看详情（含完整 YAML）、编辑 YAML、删除

**团队成员（开关关闭时）：**
- 团队侧边栏不显示"资源中心"入口，仅保留应用视图

### 2.2 页面原型

| 页面 | 路由 | 入口 |
|------|------|------|
| 平台设置（已有，新增开关） | `/enterprise/:eid/setting` | 平台管理 → 平台设置 |
| 平台资源 | `/enterprise/:eid/region/:region_name/platform-resources` | 平台管理侧边栏 → 平台资源 |
| 团队资源中心 | `/team/:teamName/region/:regionName/resource-center` | 团队侧边栏 → 资源中心（受开关控制） |

**平台资源页 Tab 布局：**
```
平台资源
全局资源与集群级公共资源管理
─────────────────────────────────────────────────
[资源总览] [全局存储] [权限与访问控制] [平台扩展] [命名空间治理]
```

**全局存储子 Tab：**
```
[存储概览] [存储类] [存储卷] [存储配置]
存储类表格：名称 | Provisioner | 默认 | 回收策略 | 绑定模式 | 支持扩容 | 卷数 | 操作
```

**团队资源中心 Tab 布局：**
```
资源中心                                    [<> YAML 创建] [+ 新建资源]
当前团队范围内的资源与 Helm 应用管理
─────────────────────────────────────────────────────────────────
[工作负载] [容器组] [网络] [配置] [存储] [Helm 应用]

表格：名称 | Kind | 状态 | 副本/容量 | 来源 | 创建时间 | 操作(详情 YAML)
来源标签：手动创建 / Helm 托管 / YAML 导入
```

### 2.3 外部系统交互

- 直接调用 Kubernetes API（通过 Go dynamic client + Discovery client）
- Helm 操作通过 `pkg/helm/helm.go`（Helm v3 SDK），不调外部服务
- Helm repo 索引文件存储于 `/grdata/helm/repo/`，chart cache 于 `/grdata/helm/cache/`

---

## 三、整体架构设计

### 3.1 系统架构图

```
rainbond-ui (React)
    ↓ HTTP /console/*
rainbond-console (Django)
    ├── platform-settings API    (读写全局开关)
    ├── platform resources API   (代理到 Go，平台管理员)
    └── team resources API       (代理到 Go，团队成员)
         ↓ HTTP /v2/*
rainbond (Go)
    ├── cluster handler          (cluster-scoped CRUD, Discovery) /v2/cluster/platform-resources/*, /v2/cluster/storageclasses/*, /v2/cluster/persistentvolumes/*（追加到现有 clusterRouter）
    ├── namespace resource handler (namespace-scoped CRUD) /v2/tenants/{name}/ns-resources
    └── helm release handler     (扩展 pkg/helm) /v2/tenants/{name}/helm/releases
         ↓
Kubernetes API Server
```

### 3.2 核心流程

**资源来源识别规则（优先级从高到低）：**
```
检查 labels:
  app.kubernetes.io/managed-by == "Helm"  → "Helm 托管"
  rainbond.io/source == "yaml"            → "YAML 导入"
  rainbond.io/source == "manual"          → "手动创建"（表单创建时打此标签）
  无以上标签                              → "外部创建"（不展示操作按钮，只读）
```

注意："手动创建"通过 `rainbond.io/source: manual` 标签明确标记，"外部创建"则是完全没有 Rainbond 标签的资源，两者区分清晰。

**全局开关生效流程：**
```
console 返回 enterprise info（含 enable_team_resource_view）
  → 前端 teamMenu.js 读取该字段
    true  → 渲染"资源中心"菜单项
    false → 跳过，仅渲染应用视图
```

---

## 四、数据模型设计

### 4.1 新增数据库字段

**`TenantEnterprise` 模型（`www/models/main.py`，`db_table='tenant_enterprise'`，已有表，新增字段）：**
```python
enable_team_resource_view = BooleanField(default=True)
```

Migration 需在 `www` app 下执行：`python manage.py makemigrations www`

### 4.2 数据关系

- 全局开关属于 enterprise 级别，不属于具体 region
- Helm repo 记录复用现有 `HelmRepoInfo`（`helm_repo` 表），不新建
- K8s 资源不落 MySQL，直接从 Kubernetes API 实时查询
- Helm release 状态从 Kubernetes secrets 读取（Helm 原生存储机制），不落 MySQL

---

## 五、API 设计

### 5.1 Go (rainbond) 新增接口

**路由前缀说明：**
- `/v2/platform` 已被插件代理占用，不可使用
- `/v2/cluster` 已有 `clusterRouter()`，新接口**追加到现有 `clusterRouter()` 函数内**（`v2Routers.go` line 266），不新建 `r.Mount("/cluster", ...)`
- 新路径使用 `/platform-resources`、`/storageclasses`、`/persistentvolumes` 前缀，避免与现有 `/resource`（GetNamespaceResource）和 `/k8s-resource`（应用内 K8s 资源管理）语义混淆

**平台级（cluster-scoped）：**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/v2/cluster/platform-resources/types` | Discovery API，返回所有 cluster-scoped 资源类型 |
| GET | `/v2/cluster/platform-resources` | 通用列表（`?group=&version=&resource=`，均必填） |
| GET | `/v2/cluster/platform-resources/{name}` | 获取单个资源详情/YAML（`?group=&version=&resource=`，均必填） |
| POST | `/v2/cluster/platform-resources` | 通用创建（YAML body，`?group=&version=&resource=`） |
| DELETE | `/v2/cluster/platform-resources/{name}` | 通用删除（`?group=&version=&resource=`，均必填） |
| GET | `/v2/cluster/storageclasses` | 存储类列表（含 PV 统计） |
| POST | `/v2/cluster/storageclasses` | 创建存储类（YAML body） |
| DELETE | `/v2/cluster/storageclasses/{name}` | 删除存储类 |
| GET | `/v2/cluster/persistentvolumes` | 存储卷列表 |
| POST | `/v2/cluster/persistentvolumes` | 创建存储卷（YAML body） |
| DELETE | `/v2/cluster/persistentvolumes/{name}` | 删除存储卷 |

**团队级（namespace-scoped）：**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/v2/tenants/{tenant_name}/ns-resource-types` | Discovery，namespace-scoped 类型 |
| GET | `/v2/tenants/{tenant_name}/ns-resources` | 通用列表（`?group=&version=&resource=`，均必填） |
| GET | `/v2/tenants/{tenant_name}/ns-resources/{name}` | 获取单个资源详情/YAML（`?group=&version=&resource=`，均必填） |
| POST | `/v2/tenants/{tenant_name}/ns-resources` | 创建（YAML body，自动注入来源标签） |
| DELETE | `/v2/tenants/{tenant_name}/ns-resources/{name}` | 删除（`?group=&version=&resource=`，均必填） |

**Helm（直装集群）：**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/v2/tenants/{tenant_name}/helm/releases` | 列出当前 namespace 的 helm release |
| POST | `/v2/tenants/{tenant_name}/helm/releases` | install chart（body: repo_name, chart, version, release_name, values） |
| DELETE | `/v2/tenants/{tenant_name}/helm/releases/{release_name}` | uninstall release |

### 5.2 Console (Python) 新增接口

**全局开关（写操作用 `EnterpriseAdminView`，读操作用 `JWTAuthApiView`）：**

| Method | Path | 权限基类 | 说明 |
|--------|------|---------|------|
| GET | `/console/enterprise/{eid}/platform-settings` | `JWTAuthApiView` | 获取平台设置（含 `enable_team_resource_view`） |
| PUT | `/console/enterprise/{eid}/platform-settings` | `EnterpriseAdminView` | 更新平台设置（仅企业管理员） |

**平台资源（platform admin only，代理到 Go `/v2/cluster/*`）：**

| Method | Path |
|--------|------|
| GET | `/console/platform/regions/{region}/platform-resources/types` |
| GET/POST | `/console/platform/regions/{region}/platform-resources` |
| GET/DELETE | `/console/platform/regions/{region}/platform-resources/{name}` |
| GET/POST | `/console/platform/regions/{region}/storageclasses` |
| DELETE | `/console/platform/regions/{region}/storageclasses/{name}` |
| GET/POST | `/console/platform/regions/{region}/persistentvolumes` |
| DELETE | `/console/platform/regions/{region}/persistentvolumes/{name}` |

**团队资源（team-scoped，代理到 Go `/v2/tenants/*`）：**

| Method | Path |
|--------|------|
| GET | `/console/teams/{team}/regions/{region}/ns-resource-types` |
| GET/POST | `/console/teams/{team}/regions/{region}/ns-resources` |
| GET/DELETE | `/console/teams/{team}/regions/{region}/ns-resources/{name}` |
| GET/POST | `/console/teams/{team}/regions/{region}/helm/releases` |
| DELETE | `/console/teams/{team}/regions/{region}/helm/releases/{release_name}` |

### 5.3 请求/响应结构示例

**GET /v2/cluster/storageclasses 响应：**
```json
{
  "bean": {
    "list": [
      {
        "name": "rainbondslsc",
        "provisioner": "rainbond.io/local",
        "is_default": true,
        "reclaim_policy": "Delete",
        "volume_binding_mode": "WaitForFirstConsumer",
        "allow_volume_expansion": true,
        "pv_count": 32
      }
    ],
    "total": 2
  }
}
```

**POST /v2/tenants/{tenant_name}/helm/releases 请求：**
```json
{
  "repo_name": "bitnami",
  "chart": "nginx",
  "version": "1.2.3",
  "release_name": "my-nginx",
  "values": "replicaCount: 2\nservice:\n  type: ClusterIP"
}
```

**GET /v2/tenants/{tenant_name}/ns-resources 响应：**
```json
{
  "bean": {
    "list": [
      {
        "name": "nginx-deployment",
        "kind": "Deployment",
        "api_version": "apps/v1",
        "status": "running",
        "replicas": "3/3",
        "source": "manual",
        "created_at": "2025-01-15T00:00:00Z"
      }
    ],
    "total": 6
  }
}
```

---

## 六、核心实现设计

### 6.1 关键逻辑

**Discovery API（cluster-scoped 资源类型枚举）：**
```go
// 使用 k8s.io/client-go/discovery 的 ServerGroupsAndResources
// 过滤条件：resource.Namespaced == false && !strings.Contains(resource.Name, "/")
// 返回 group, version, kind, name, verbs
// 注意：ServerGroupsAndResources 在部分 API group 不可用时返回 partial error，
// 使用 discovery.IsGroupDiscoveryFailedError 判断，partial error 可忽略继续处理
```

**Dynamic Client（通用 CRUD）：**
```go
// 使用 k8s.io/client-go/dynamic，从 k8s.Default().DynamicClient 获取
// group/version/resource 三个参数在 list/create/delete 中均为必填，服务端校验缺失时返回 400
// List(cluster): dynamicClient.Resource(gvr).List(ctx, metav1.ListOptions{})
// Get(cluster):  dynamicClient.Resource(gvr).Get(ctx, name, metav1.GetOptions{})
// Create(cluster): 解析 YAML → unstructured → dynamicClient.Resource(gvr).Create()
// Delete(cluster): dynamicClient.Resource(gvr).Delete(ctx, name, metav1.DeleteOptions{})
// namespace-scoped 加 .Namespace(tenantID)：dynamicClient.Resource(gvr).Namespace(ns).List/Get/Create/Delete
// tenantID（K8s namespace）通过 tenant_name 从数据库查 tenant.tenant_id 获取
```

**来源标签注入（创建时）：**
```go
// 通过 YAML 创建时注入（创建方式由请求参数 source 字段指定）
labels["rainbond.io/source"] = "yaml"   // YAML 创建
labels["rainbond.io/source"] = "manual" // 表单创建
// Helm 安装的资源由 Helm SDK 自动打 app.kubernetes.io/managed-by: Helm
```

**Helm 扩展（`pkg/helm/helm.go`）：**
```go
// 新增方法（注意：Helm struct 在构造时绑定 namespace，需每次请求按 tenantID 实例化）
// handler 中调用：h := helm.NewHelm(tenantID, repoFile, repoCache)

func (h *Helm) ListReleases() ([]*release.Release, error)
// 实现：action.NewList(h.cfg).Run()

func (h *Helm) InstallFromRepo(repoName, chart, version, releaseName, valuesYAML string) (*release.Release, error)
// 实现：必须直接调用 action.NewInstall(h.cfg)，禁止委托给私有 install() helper
// 原因：私有 install() helper（helm.go:181）无条件设置 client.ClientOnly = true，
// 即使传入 DryRun=false 也会导致 Helm 只渲染 manifest 而不实际部署到集群
// 正确做法：client := action.NewInstall(h.cfg); client.DryRun = false; client.ClientOnly = false
// values 通过 yaml.Unmarshal 解析后传入，先验证 YAML 合法性再调用

// 复用已有 Uninstall(name string) error 方法，不新增 UninstallRelease
```

**资源状态计算：**
```go
// Deployment: availableReplicas == replicas → "running"，否则 "warning"
// StatefulSet: readyReplicas == replicas → "running"
// Pod: phase == Running → "running"，否则对应 phase 字符串
// PVC: phase == Bound → "bound"，否则 phase 字符串
// 其他: 统一返回 "active"
```

### 6.2 复用现有代码

| 复用内容 | 文件位置 | 用途 |
|---------|---------|------|
| `HelmRepoInfo` 模型 | `www/models/main.py` | Helm repo 存储，直接复用 |
| `helm_repo` repository | `console/repositories/helm.py` | repo CRUD，直接复用 |
| `pkg/helm/helm.go: Uninstall` | `rainbond/pkg/helm/helm.go` | 直接复用，不新增 UninstallRelease |
| `k8s.Default().DynamicClient` | `pkg/component/k8s/k8sComponent.go` | 获取 dynamic client |
| `EnterpriseAdminView` | `console/views/base.py` | 平台管理员写操作权限基类 |
| `JWTAuthApiView` | `console/views/base.py` | 通用认证基类（读操作） |
| `TenantHeaderView` | `console/views/base.py` | 团队接口鉴权基类 |
| 企业 settings 接口 | `console/views/enterprise.py` | 参考 settings 接口模式 |
| 现有 helm 视图 | `console/views/helm_app.py` | 参考 repo list/add 模式（不修改） |

---

## 七、实施计划

### 跨层覆盖检查

- [x] Go (rainbond): 需要 — 新增 cluster handler（/v2/cluster/*）、ns_resource handler、helm release handler（扩展 pkg/helm）
- [x] Python (console): 需要 — `TenantEnterprise` 加字段 + www migration、平台/团队资源代理接口、console/urls 改包结构
- [x] React (rainbond-ui): 需要 — 平台设置加开关、平台资源新页面、团队资源中心新页面、菜单入口
- [ ] Plugin: 不涉及

### Sprint 1：Go 平台级接口

#### Task 1.0：console/urls.py 改包结构（前置）
- 仓库：rainbond-console
- 文件：
  - `console/urls.py` → 重命名为 `console/urls/__init__.py`
  - `goodrain_web/urls.py`：确认 include 路径（`'console.urls'` 无需改，Python 会自动识别包）
- 实现：将 `console/urls.py` 移入 `console/urls/__init__.py`，后续子模块（`platform_resources.py`、`team_resources.py`）在此目录新建并在 `__init__.py` 中 include
- 验收：`python manage.py check` 无报错

#### Task 1.1：Go 平台级 Discovery + 通用 CRUD
- 仓库：rainbond
- 文件：`api/handler/cluster_resource.go`（新建），`api/controller/cluster_resource.go`（新建），`api/api_routers/version2/v2Routers.go`（在**现有 `clusterRouter()` 函数内**追加路由，不新建 `r.Mount`）
- 实现：Discovery API 枚举 cluster-scoped 类型（路由：`/platform-resources/types`、`/platform-resources`、`/platform-resources/{name}`）；dynamic client 通用 list/get/create/delete；group/version/resource 参数缺失返回 400
- 验收：`go test ./api/handler/... -run TestClusterResource`，`go build ./...`

#### Task 1.2：Go StorageClass + PV 专用接口
- 仓库：rainbond
- 文件：`api/handler/storage.go`（新建），`api/controller/storage.go`（新建）
- 实现：StorageClass list/create/delete（含 PV 统计）；PV list/create/delete；挂载到 `/v2/cluster` 路由组
- 验收：`go test ./api/handler/... -run TestStorage`，`go build ./...`

### Sprint 2：Go 团队级接口

#### Task 2.1：Go namespace-scoped 资源接口
- 仓库：rainbond
- 文件：`api/handler/ns_resource.go`（新建），`api/controller/ns_resource.go`（新建）
- 实现：namespace-scoped Discovery；dynamic client list/get/create（注入 source 标签）/delete；namespace 从 tenant_name 查 tenant_id 获取
- 验收：`go test ./api/handler/... -run TestNsResource`，`go build ./...`

#### Task 2.2：Go Helm Release 接口
- 仓库：rainbond
- 文件：`pkg/helm/helm.go`（新增 `ListReleases`、`InstallFromRepo`），`api/handler/helm_release.go`（新建），`api/controller/helm_release.go`（新建）
- 实现：`InstallFromRepo` 必须直接调用 `action.NewInstall(h.cfg)` 并设置 `DryRun=false, ClientOnly=false`；禁止委托给私有 `install()` helper（该 helper 在 helm.go:181 无条件设置 `ClientOnly=true`，导致不实际部署）；values YAML 先 `yaml.Unmarshal` 验证；Uninstall 复用现有方法；handler 每次请求按 tenantID 实例化 `NewHelm()`
- `repoFile`/`repoCache` 路径：新建的 `api/handler/helmrelease.go`（与 `api/handler/helm.go` 同包）直接复用同包的包级变量 `repoFile`/`repoCache`（`api/handler/helm.go:62–63`）；`pkg/helm/helm.go` 中的新方法通过 struct 字段 `h.repoFile`/`h.repoCache` 访问，无需额外传参
- 验收：`go test ./pkg/helm/... -run TestHelmRelease`，`go build ./...`

### Sprint 3：Console 接口

#### Task 3.1：全局开关
- 仓库：rainbond-console
- 文件：`www/models/main.py`（`TenantEnterprise` 加 `enable_team_resource_view` 字段），`console/views/platform_settings.py`（新建），`console/urls/__init__.py`（追加路由）
- 实现：`python manage.py makemigrations www`；GET 用 `JWTAuthApiView`，PUT 用 `EnterpriseAdminView`；GET 同时在 enterprise info 响应中附带此字段（复用已有接口）
- 验收：migration 执行成功；GET 返回正确字段；非管理员 PUT 返回 403

#### Task 3.2：平台资源代理接口
- 仓库：rainbond-console
- 文件：`console/views/platform_resources/`（新建目录），`console/urls/platform_resources.py`（新建）
- 实现：StorageClass、PV、通用资源 GET/POST/DELETE，代理到 Go `/v2/cluster/*`；权限基类用 `EnterpriseAdminView`；在 `console/urls/__init__.py` 中 `include('console.urls.platform_resources')`
- 验收：`python manage.py check`；curl 接口返回预期 JSON

#### Task 3.3：团队资源代理接口
- 仓库：rainbond-console
- 文件：`console/views/team_resources.py`（新建），`console/urls/team_resources.py`（新建）
- 实现：namespace-scoped 资源 + Helm releases GET/POST/DELETE，代理到 Go `/v2/tenants/*`；权限基类用 `TenantHeaderView`；在 `console/urls/__init__.py` 中 include
- 验收：`python manage.py check`；curl 接口返回预期 JSON

### Sprint 4：前端

#### Task 4.1：全局开关 UI
- 仓库：rainbond-ui
- 文件：平台设置页（已有，加 Switch 组件）；`src/services/` 加 platform-settings 调用
- 实现：在基础设置 section 加"启用团队资源展示"Switch，调用 platform-settings PUT 接口；读取 enterprise info 中的 `enable_team_resource_view` 字段回显
- 验收：`yarn build` 通过

#### Task 4.2：菜单入口受开关控制 + 路由注册
- 仓库：rainbond-ui
- 文件：`src/common/teamMenu.js`，`src/common/enterpriseMenu.js`，`src/common/getMenuSvg.js`，`config/router.config.js`，`src/locales/zh-CN/menu.js`，`src/locales/en-US/menu.js`
- 实现：teamMenu 读 `enable_team_resource_view`，true 时加"资源中心"入口；enterprise menu 加"平台资源"入口（需有集群时才显示）；加 resource 图标；注册两条路由
- 验收：`yarn build` 通过

#### Task 4.3：平台资源页面
- 仓库：rainbond-ui
- 文件：`src/pages/PlatformResources/index.js`（新建），`src/services/platformResource.js`（新建），`src/models/platformResources.js`（新建）
- 实现：5 Tab 页面；全局存储含 4 子 Tab；StorageClass 表格含创建（YAML 编辑器弹窗）/删除；所有 API 路径对应 console `/console/platform/regions/{region}/...`
- 验收：`yarn build` 通过

#### Task 4.4：团队资源中心
- 仓库：rainbond-ui
- 文件：`src/pages/ResourceCenter/index.js`（新建），`src/services/teamResource.js`（新建），`src/models/teamResources.js`（新建）
- 实现：6 Tab 页面；来源标签四色（manual/yaml/helm/external）；YAML 创建弹窗（注入 source=yaml）；新建资源表单（Deployment/Service/ConfigMap 结构化，其余 YAML）；Helm 安装弹窗（选 repo → 填 chart/version/release_name/values）；详情页展示完整 YAML；所有 API 路径对应 console `/console/teams/{team}/regions/{region}/...`
- 验收：`yarn build` 通过

---

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| Helm v3 客户端 | `rainbond/pkg/helm/helm.go` | 扩展基础；`Uninstall` 直接复用；新增 `ListReleases`、`InstallFromRepo`（DryRun=false） |
| Helm repo 模型 | `www/models/main.py: HelmRepoInfo` | 复用 repo 管理 |
| Helm repo repository | `console/repositories/helm.py` | 复用 CRUD |
| 企业管理员权限基类 | `console/views/base.py: EnterpriseAdminView` | 平台写操作（PUT settings、平台资源创建删除） |
| 团队权限基类 | `console/views/base.py: TenantHeaderView` | 团队资源接口 |
| dynamic client 初始化 | `rainbond/pkg/component/k8s/k8sComponent.go` | `k8s.Default().DynamicClient` |
| 企业 settings 接口 | `console/views/enterprise.py` | 参考接口模式和 EnterpriseAdminView 用法 |
| 全局开关模型字段 | `www/models/main.py: TenantEnterprise` | `db_table='tenant_enterprise'`，在此加 `enable_team_resource_view` |
| 现有 helm 视图 | `console/views/helm_app.py` | 参考 repo list/add 模式（不修改） |
| 已有路由冲突说明 | `rainbond/api/api_routers/version2/v2Routers.go:80` | `/v2/platform` 已被 platformPluginsRouter 占用，新接口用 `/v2/cluster` |
