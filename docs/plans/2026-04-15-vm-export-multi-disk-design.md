# VM Export Multi-Disk Refactor 设计文档

## 一、项目背景
### 1.1 项目架构
- `rainbond` 负责 VM 导出、导出持久化与运行时组装。
- `rainbond-console` 负责 VM 资产、创建入口、运行时属性编排。
- `rainbond-ui` 负责 VM 详情页、资产目录、创建页面。

### 1.2 现有基础
- 已存在 VM 导出能力：`vm-exports`、对象存储持久化、资产目录。
- 已存在 VM 模板能力：模板保存、模板中心、模板实例化。
- 已存在单镜像创建 VM 能力：上传/URL 资产 -> `build_from_vm` -> 运行时镜像 -> VM 创建。

### 1.3 核心需求
- 永久废弃“导出虚拟机模板”及其下游实现。
- 保留“导出镜像”能力，导出 VM 上所有持久化磁盘数据。
- 导出后的资产必须支持根盘启动和数据盘内容恢复，不再依赖模板体系。

## 二、用户旅程（MUST — 禁止跳过）
### 2.1 用户操作流程
- 用户在 VM 详情页点击“导出镜像”。
- 系统导出 VM 所有持久化磁盘，并生成导出资产。
- 用户在 VM 创建页选择该资产创建新 VM。
- 系统用导出的根盘恢复启动介质，并恢复数据盘内容。
- 用户不再看到“导出虚拟机模板”入口，也不再使用模板中心完成 VM 克隆。

### 2.2 页面原型
- VM 详情页：保留“导出镜像”按钮，删除“保存模板/导出模板”按钮。
- 资产目录：继续展示 VM 导出资产。
- 创建 VM 页面：继续使用资产创建，不再依赖模板中心。
- 模板中心页面：删除路由和页面实现。

### 2.3 外部系统交互
- `rainbond-console` 调 `rainbond` 的 `vm-exports` 相关接口。
- 不再依赖 `vm-assets/restore-plan` 做整机恢复。
- 不涉及 webhook / 第三方通知。

## 三、整体架构设计
### 3.1 系统架构图
```text
VM Detail Export
  -> console start_vm_export
  -> rainbond vm-exports
  -> export root disk only
  -> persist root disk object
  -> console save as normal VM disk asset

VM Create From Asset
  -> choose exported asset
  -> console resolve boot source as single disk asset
  -> build_from_vm / disk import main path
  -> rainbond worker creates VM
```

### 3.2 核心流程
- 导出流程保留“整机多盘 + machine manifest”。
- 创建流程删除模板实例化，但保留导出资产的多盘恢复分支。
- 根盘通过导出 URL 回到 `build_from_vm` 主链，数据盘通过 `restore-plan` 导入。
- worker 需要重新启用非 ISO 根盘路径，确保 qcow2/img 根盘创建可启动。

## 四、数据模型设计
### 4.1 新增数据库表
- 无新增表。

### 4.2 数据关系
- 废弃 `VMTemplate` / `VMTemplateVersion` / `VMTemplateDisk` 代码路径，不再被业务引用。
- `VirtualMachineImage` 继续作为唯一 VM 资产模型。
- `vm_disk_imports` / `vm_disk_layout` 继续承载 VM 导出资产的多盘恢复协议。

## 五、API设计
### 5.1 接口列表
- 保留：`POST /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports`
- 保留：`GET /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports/{export_id}`
- 保留：`POST /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports/{export_id}/persist`
- 保留：`POST /v2/tenants/{tenant}/vm-assets/restore-plan`
- 删除：模板相关 console 接口 `/vm-templates*`

### 5.2 请求/响应结构
- `vm-exports` 继续返回所有持久化磁盘导出状态。
- `persist vm export` 继续返回 `machine_manifest`，供创建 VM 时恢复数据盘。

## 六、核心实现设计
### 6.1 关键逻辑
- `rainbond`
  - 导出继续选择所有持久化磁盘。
  - 导出持久化继续保存 `machine_manifest`。
  - worker 重新按 `vm_boot_source_format` 和 root DataVolume 决定 ISO / imported-root / vmimage-rootdisk 路径，去掉临时强制 ISO。
- `rainbond-console`
  - 删除 VM 模板 service/view/repo/model 使用路径。
  - 删除基于模板的创建分支。
  - 对 VM 导出资产：根盘走 `build_from_vm`，数据盘走 `restore-plan` 导入。
- `rainbond-ui`
  - 删除模板入口、模板中心、模板 API/model/service。
  - 保留导出镜像入口和资产创建入口。

### 6.2 复用现有代码
- 复用 `build_from_vm` 对 ISO/qcow2/img 的文件类型识别与运行时镜像打包能力。
- 复用现有 VM 资产目录和创建页面。
- 复用 `vm_disk_imports` 的根盘导入能力。

## 七、实施计划
### 跨层覆盖检查（MUST）
- [x] Go (rainbond): 需要 — 保留多盘 VM 导出协议，恢复 qcow2 根盘启动主链
- [x] Python (console): 需要 — 删除模板体系，保留导出资产多盘恢复创建分支
- [x] React (rainbond-ui): 需要 — 删除模板入口、路由、页面、service/model
- [ ] Plugin: 不涉及

### Sprint 1: Baseline 与设计落盘
#### Task 1.1: 记录跨仓库回退锚点
- 仓库：workspace
- 文件：`docs/2026-04-15-vm-export-cross-repo-baseline.md`
- 实现内容：记录三仓库 branch/HEAD/describe/dirty 状态
- 验收标准：后续回退有明确锚点

#### Task 1.2: 写设计与执行规格
- 仓库：rainbond-console / workspace
- 文件：`docs/plans/2026-04-15-vm-export-multi-disk-design.md`、`.claude/specs/vm-export-multi-disk.yaml`
- 实现内容：明确废弃模板与导出主链收敛方案
- 验收标准：后续实现有可执行依据

### Sprint 2: 删除 VM 模板体系
#### Task 2.1: 删除 console 模板服务与视图
- 仓库：rainbond-console
- 文件：`console/services/virtual_machine.py`、`console/views/vm_template.py`、`console/repositories/vm_template.py`、`console/urls/__init__.py`
- 实现内容：移除模板保存、查询、重试、实例化分支
- 验收标准：模板相关 API 与服务引用全部清除

#### Task 2.2: 删除 console 模板测试与模型引用
- 仓库：rainbond-console
- 文件：`console/tests/vm_template_*`、`www/models/main.py`、`test-manifest.json`
- 实现内容：清除模板测试、能力声明与模型代码引用
- 验收标准：模板相关测试文件与 manifest 条目消失

#### Task 2.3: 删除 UI 模板入口与页面
- 仓库：rainbond-ui
- 文件：`src/pages/VMTemplateCenter/*`、`src/services/vmTemplate.js`、`src/models/vmTemplate.js`、`config/router.config.js`、相关调用点
- 实现内容：删除模板中心和模板动作
- 验收标准：前端不再出现模板入口或模板 API 调用

### Sprint 3: 打通导出镜像与基于镜像创建
#### Task 3.1: 保留 rainbond 多盘导出协议
- 仓库：rainbond
- 文件：`api/handler/vm_export.go`、`api/handler/vm_export_persist.go`、`api/api_routers/version2/v2Routers.go`、相关测试
- 实现内容：导出所有持久化盘，保留 `machine_manifest` / `restore-plan`
- 验收标准：导出产物覆盖所有持久化盘

#### Task 3.2: 让 console 导出资产支持多盘恢复创建
- 仓库：rainbond-console
- 文件：`console/services/virtual_machine.py`、`console/views/app_create/vm_run.py`、相关测试
- 实现内容：根盘回到 `build_from_vm` 主链，数据盘通过 `restore-plan` 恢复
- 验收标准：导出后的资产可创建 VM，并恢复数据盘内容

#### Task 3.3: 恢复 rainbond worker 的非 ISO 根盘启动路径
- 仓库：rainbond
- 文件：`worker/appm/conversion/version.go`、相关测试
- 实现内容：取消临时强制 ISO，按 boot source format + imported root 选择真正路径
- 验收标准：qcow2/img 根盘创建可走 imported-root / root-disk 路径

## 八、关键参考代码
| 功能 | 文件 | 说明 |
|------|------|------|
| VM 导出入口 | `rainbond/api/handler/vm_export.go` | 当前导出实现 |
| 导出持久化 | `rainbond/api/handler/vm_export_persist.go` | 当前 machine manifest 持久化 |
| VM 创建入口 | `rainbond-console/console/views/app_create/vm_run.py` | 资产/模板创建 VM 主入口 |
| VM 资产服务 | `rainbond-console/console/services/virtual_machine.py` | 资产、模板、导出逻辑汇总 |
| VM 启动源绑定 | `rainbond-console/console/services/vm_boot_source.py` | build_from_vm 主链入口 |
| VM 运行时组装 | `rainbond/worker/appm/conversion/version.go` | 实际 VM 启动路径选择 |
