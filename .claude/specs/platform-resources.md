# 平台资源治理 + 团队资源中心 — 实施规范

**设计文档：** `docs/superpowers/specs/2026-03-16-platform-resources-design.md`
**创建时间：** 2026-03-16

---

## 关键约束（执行前必读）

| 约束 | 说明 |
|------|------|
| `clusterRouter()` 已存在 | `v2Routers.go:266` 已有该函数，新路由追加到函数**内部**，禁止新建 `r.Mount("/cluster", ...)` |
| `InstallFromRepo` 禁用 `install()` | `pkg/helm/helm.go:181` 的私有 helper 无条件 `ClientOnly=true`，必须直接用 `action.NewInstall()` |
| migration 在 `www` app | `TenantEnterprise` 属于 `www` app，`makemigrations www` |
| `console/urls.py` 需转包 | 平文件不支持子模块 include，必须先转为 `console/urls/__init__.py` |
| 路由前缀 | `/v2/platform` 被占用，用 `/v2/cluster/platform-resources/*` |
| React 规范 | class component + `@connect`，Ant Design 3.x，`yarn build` 是质量门控 |

---

## Sprint 1 — Go 平台级接口（commit-1）

**Commit message:** `feat: add cluster-scoped platform resource APIs`

### task-1.1：Discovery + 通用 CRUD

**新建文件：**
- `api/handler/cluster_resource.go`
- `api/controller/cluster_resource.go`

**修改文件：**
- `api/api_routers/version2/v2Routers.go`（在 `clusterRouter()` 函数内追加）

**路由追加位置：** `v2Routers.go` 的 `clusterRouter()` 函数，`return r` 之前
```go
r.Get("/platform-resources/types", controller.GetClusterResourceController().ListResourceTypes)
r.Get("/platform-resources", controller.GetClusterResourceController().ListResources)
r.Post("/platform-resources", controller.GetClusterResourceController().CreateResource)
r.Get("/platform-resources/{name}", controller.GetClusterResourceController().GetResource)
r.Delete("/platform-resources/{name}", controller.GetClusterResourceController().DeleteResource)
```

**执行步骤：**
1. 写测试 → `go test ./api/handler/... -run TestValidateGVRParams` → 期望 FAIL
2. 实现 `cluster_resource.go`（Discovery + dynamic client CRUD）
3. 运行测试 → 期望 PASS
4. 实现 controller，追加路由
5. `go build ./... && go vet ./...` → 期望 exit 0

**验收：** `go build ./...` 通过，`TestValidateGVRParams` PASS

---

### task-1.2：StorageClass + PV 专用接口

**新建文件：**
- `api/handler/storage.go`
- `api/controller/storage.go`

**路由追加（同在 `clusterRouter()` 内）：**
```go
r.Get("/storageclasses", controller.GetStorageController().ListStorageClasses)
r.Post("/storageclasses", controller.GetStorageController().CreateStorageClass)
r.Delete("/storageclasses/{name}", controller.GetStorageController().DeleteStorageClass)
r.Get("/persistentvolumes", controller.GetStorageController().ListPersistentVolumes)
r.Post("/persistentvolumes", controller.GetStorageController().CreatePersistentVolume)
r.Delete("/persistentvolumes/{name}", controller.GetStorageController().DeletePersistentVolume)
```

**执行步骤：**
1. 写测试 → `TestStorageHandlerInit` → 期望 FAIL
2. 实现 `storage.go`（StorageClass list 含 PV 统计，create/delete；PV list/create/delete）
3. 测试 PASS → 实现 controller → 追加路由
4. `go build ./...` → exit 0

---

## Sprint 2 — Go 团队级接口（commit-2）

**Commit message:** `feat: add namespace-scoped resource and helm release APIs`

### task-2.1：namespace-scoped 资源接口

**新建文件：**
- `api/handler/ns_resource.go`
- `api/controller/ns_resource.go`

**路由追加位置：** `tenantNameRouter()` 函数内，`return r` 之前
```go
r.Get("/ns-resource-types", controller.GetNsResourceController().ListNsResourceTypes)
r.Get("/ns-resources", controller.GetNsResourceController().ListNsResources)
r.Post("/ns-resources", controller.GetNsResourceController().CreateNsResource)
r.Get("/ns-resources/{name}", controller.GetNsResourceController().GetNsResource)
r.Delete("/ns-resources/{name}", controller.GetNsResourceController().DeleteNsResource)
```

**关键实现细节：**
- `tenant_name` → `tenant_id`（namespace）通过 `db.GetManager().TenantDao().GetTenantByName()` 查询
- POST 创建时注入 `rainbond.io/source` 标签（`yaml` 或 `manual`，由 query param `source` 决定）
- 来源识别：`app.kubernetes.io/managed-by=Helm` → helm；`rainbond.io/source` → yaml/manual；无标签 → external

---

### task-2.2：Helm Release 接口

**修改文件：** `pkg/helm/helm.go`（末尾追加两个方法）
**新建文件：** `api/handler/helm_release.go`，`api/controller/helm_release.go`

**⚠️ 关键约束：** `InstallFromRepo` 必须直接调用 `action.NewInstall(h.cfg)`，**禁止调用** 私有 `install()` helper（`helm.go:181` 该 helper `client.ClientOnly = true` 是 hardcoded）

```go
// 正确实现：
func (h *Helm) InstallFromRepo(repoName, chart, version, releaseName, valuesYAML string) (*release.Release, error) {
    client := action.NewInstall(h.cfg)
    client.DryRun = false      // 必须显式设置
    client.ClientOnly = false  // 必须显式设置
    // ... 其余实现
}
```

**`repoFile`/`repoCache`：** `helm_release.go` 与 `helm.go` 同包，直接用包级变量（`api/handler/helm.go:60-64`）

**路由追加（`tenantNameRouter()` 内）：**
```go
r.Get("/helm/releases", controller.GetHelmReleaseController().ListReleases)
r.Post("/helm/releases", controller.GetHelmReleaseController().InstallRelease)
r.Delete("/helm/releases/{release_name}", controller.GetHelmReleaseController().UninstallRelease)
```

**验收：** `go build ./...` 通过，`go test ./pkg/helm/...` PASS

---

## Sprint 3 — Console 接口（commit-3 + commit-4）

### commit-3：`chore: convert console/urls.py to package structure`

#### task-3.0：urls.py 转包（**最先执行，其他 console task 依赖此步骤**）

```bash
cd /Users/zhangqihang/MyWork/workrc/rainbond-console
mkdir -p console/urls
cp console/urls.py console/urls/__init__.py
rm console/urls.py
python manage.py check  # 期望：System check identified no issues
```

---

### commit-4：`feat: add global switch and platform/team resource proxy APIs`

#### task-3.1：全局开关

**修改 `www/models/main.py:816`**（TenantEnterprise 类末尾追加）：
```python
enable_team_resource_view = models.BooleanField(default=True, help_text="是否启用团队资源展示")
```

```bash
python manage.py makemigrations www  # 期望：Migrations for 'www'
python manage.py migrate
```

**新建 `console/views/platform_settings.py`：**
- `PlatformSettingsView(JWTAuthApiView)` — GET `/console/enterprise/{eid}/platform-settings`
- `PlatformSettingsUpdateView(EnterpriseAdminView)` — PUT 同路径

**在 `console/urls/__init__.py` 追加路由：**
```python
url(r'^enterprise/(?P<eid>[^/]+)/platform-settings$', PlatformSettingsView.as_view()),
url(r'^enterprise/(?P<eid>[^/]+)/platform-settings/update$', PlatformSettingsUpdateView.as_view()),
```

---

#### task-3.2：平台资源代理

**新建：**
- `console/views/platform_resources/__init__.py`（空文件）
- `console/views/platform_resources/cluster.py`（7 个视图类，均继承 `EnterpriseAdminView`）
- `console/urls/platform_resources.py`（urlpatterns）

**⚠️ 注意：** `RegionInvokeApi` 需要新增 `get_cluster_resource`/`post_cluster_resource`/`delete_cluster_resource` 方法（参考 `www/apiclient/regionapi.py` 中现有方法的模式）

**在 `console/urls/__init__.py` 末尾 include：**
```python
url(r'^', include('console.urls.platform_resources')),
```

---

#### task-3.3：团队资源代理

**新建：**
- `console/views/team_resources.py`（5 个视图类，均继承 `TenantHeaderView`）
- `console/urls/team_resources.py`（urlpatterns）

**⚠️ 注意：** `RegionInvokeApi` 需新增 `get_tenant_ns_resource_types`、`get_tenant_ns_resources`、`post_tenant_ns_resource`、`delete_tenant_ns_resource`、`get_tenant_helm_releases`、`install_tenant_helm_release`、`uninstall_tenant_helm_release` 方法

**在 `console/urls/__init__.py` 末尾 include：**
```python
url(r'^', include('console.urls.team_resources')),
```

**验收：** `python manage.py check` 无报错

---

## Sprint 4 — 前端（commit-5 + commit-6 + commit-7）

### commit-5：`feat: add global switch UI and menu entries`（task-4.1 + task-4.2）

**task-4.1：全局开关 UI**
- 新建 `src/services/platformSettings.js`（getPlatformSettings / updatePlatformSettings）
- 在平台设置页现有表单中追加 Switch 组件，调用 `enterprise/updatePlatformSettings` effect

**task-4.2：菜单 + 路由**
- `src/common/getMenuSvg.js`：添加 `resource` SVG 图标
- `src/common/enterpriseMenu.js`：追加"平台资源"菜单项（需有集群）
- `src/common/teamMenu.js`：当 `enable_team_resource_view=true` 时追加"资源中心"菜单项
- `src/locales/zh-CN/menu.js`：`'menu.enterprise.platform_resources': '平台资源'`, `'menu.team.resource_center': '资源中心'`
- `src/locales/en-US/menu.js`：相应英文翻译
- `config/router.config.js`：注册 `/enterprise/:eid/region/:regionName/platform-resources` 和 `/team/:teamName/region/:regionName/resource-center`

---

### commit-6：`feat: add platform resources page`（task-4.3）

**新建：**
- `src/services/platformResource.js`（listStorageClasses / createStorageClass / deleteStorageClass / listPersistentVolumes / listPlatformResources / deletePlatformResource）
- `src/models/platformResources.js`（namespace: 'platformResources'）
- `src/pages/PlatformResources/index.js`（5 Tab 页面，StorageClass 表格含创建/删除）

**API 路径前缀：** `/console/enterprise/{eid}/platform/regions/{region}/...`

---

### commit-7：`feat: add team resource center page`（task-4.4）

**新建：**
- `src/services/teamResource.js`（listNsResources / createNsResource / deleteNsResource / listHelmReleases / installHelmRelease / uninstallHelmRelease）
- `src/models/teamResources.js`（namespace: 'teamResources'）
- `src/pages/ResourceCenter/index.js`（6 Tab，来源标签四色，YAML 创建弹窗，Helm 安装弹窗）

**来源标签颜色：**
- `helm` → purple（Helm 托管）
- `yaml` → blue（YAML 导入）
- `manual` → green（手动创建）
- `external` → default（外部创建，只读）

**API 路径前缀：** `/console/teams/{team}/regions/{region}/...`

**验收：** `yarn build` 通过（无 error）

---

## 完整验收清单

| 仓库 | 命令 | 期望 |
|------|------|------|
| rainbond | `go build ./...` | exit 0 |
| rainbond | `go vet ./api/handler/... ./api/controller/... ./pkg/helm/...` | exit 0 |
| rainbond | `go test ./api/handler/... -run TestValidateGVRParams` | PASS |
| rainbond | `go test ./pkg/helm/... -v` | PASS |
| rainbond-console | `python manage.py check` | no issues |
| rainbond-console | `python manage.py migrate` | OK |
| rainbond-ui | `yarn build` | Built successfully |
