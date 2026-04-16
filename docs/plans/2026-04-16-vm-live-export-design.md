# 虚拟机实时导出替代持久化设计文档

## 一、项目背景
### 1.1 项目架构

当前 VM 导出链路分布在三个仓库：

```text
rainbond-ui
  -> VM 详情页点击“导出到镜像组”
  -> 创建 VM 页面读取 /console/teams/{team}/vm/assets

rainbond-console
  -> 创建 virtual_machine_image 导出资产记录
  -> 查询 region vm-export 状态
  -> 在资产列表查询中触发 persist_vm_export

rainbond
  -> 创建 KubeVirt VirtualMachineExport
  -> 等待导出 ready
  -> 下载导出盘并上传到 S3/MinIO
  -> 删除 VirtualMachineExport
```

当前实现的问题不是“能不能导出”，而是“导出结果如何保存和何时清理”：

- `vm/assets` 读接口会触发 `persist_vm_export`，导致列表请求阻塞
- 持久化到 MinIO/S3 对大盘 VM 很慢，用户感知差
- `VirtualMachineExport` 是中间态资源，保留太久会影响后续导出和 PVC 使用
- 资产目录当前混合了“长期资产”和“当前导出引用”两种语义，边界不清晰

### 1.2 现有基础

- `rainbond-console` 已有 VM 资产模型 `virtual_machine_image`
- `rainbond-console` 已有 VM 导出入口和导出状态同步逻辑
- `rainbond` 已有 `POST /vm-exports`、`GET /vm-exports/{export_id}` 导出链路
- `rainbond` 已能从 `VirtualMachineExport` 中解析每块磁盘的 `download_url`
- `rainbond-ui` 已有 VM 详情页导出入口、导出状态轮询、资产目录和创建 VM 页面

### 1.3 核心需求

- 取消“导出后落 MinIO/S3”这条持久化路径
- VM 导出改为“当前最新一份 live export”，每个 VM 只保留一份
- 导出内部标识固定使用 `service_id`，用户不再填写导出名
- 若当前团队下该 VM 已有旧导出，重新导出前必须明确提示会删除旧记录和底层 `VirtualMachineExport`
- 资产展示名使用 `service_cname`，不直接向用户暴露 `service_id`
- 资产删除时，需要同步删除底层 `VirtualMachineExport`
- 从资产创建 VM 时，继续使用当前 `VirtualMachineExport` 的原始下载地址，不再改写成 S3 地址

## 二、用户旅程（MUST — 禁止跳过）
### 2.1 用户操作流程

#### 场景 A：首次导出
- 用户在 VM 详情页点击“导出到镜像组”
- 系统按当前团队和当前 VM 查询是否已有 live export 记录
- 若没有旧记录，直接发起导出
- UI 轮询导出状态，导出完成后资产状态变为 `ready`
- 用户在资产目录中看到一条名称为组件中文名/组件名的 VM 导出资产

#### 场景 B：重新导出
- 用户再次点击导出
- 系统先查数据库，发现该 VM 已有旧导出资产
- UI 明确提示：
  - 会删除旧资产记录
  - 会删除底层旧 `VirtualMachineExport`
  - 确认后将重新导出
- 用户确认后，系统先清理旧记录和旧导出资源，再创建新的导出

#### 场景 C：删除资产
- 用户在“虚拟机镜像资产目录”里删除某条 VM 导出资产
- 系统除了删除数据库记录，还要同步删除底层 `VirtualMachineExport`
- 若底层资源已经不存在，允许忽略并继续删除数据库记录

#### 场景 D：从资产创建 VM
- 用户在创建 VM 页面选择该导出资产
- console 不再使用 S3 持久化对象地址
- console 在使用前刷新一次 live export 状态，拿到当前有效的磁盘 `download_url`
- 根盘和数据盘都直接使用当前 live export 的 URL 导入

### 2.2 页面原型

- VM 详情页：
  - 保留“导出到镜像组”按钮
  - 移除用户自定义导出名输入框
  - 若已存在旧导出，弹出覆盖确认提示
- VM 资产目录：
  - 展示名为 `service_cname`
  - 可删除
  - 删除时弹出“同时删除底层导出资源”的确认
- 创建 VM 页面：
  - 继续从资产目录选择
  - 不增加新入口，不引入模板中心

### 2.3 外部系统交互

- `rainbond-console` 调 `rainbond`：
  - 创建 VM 导出
  - 查询 VM 导出状态
  - 删除 VM 导出
- 不再调用：
  - `persist vm export`
  - `vm-assets/restore-plan` 的 S3 manifest 恢复链路

## 三、整体架构设计
### 3.1 系统架构图

```text
VM Detail Export
  -> console checks existing live export record by source_service_id
  -> if exists: prompt confirm -> delete old VMExport + delete old DB record
  -> start new VMExport with export_id = service_id
  -> save VM export asset record (name = service_id, display_name = service_cname)
  -> UI polls export status

Asset List / Asset Detail
  -> console reads DB assets
  -> lightweight sync only
  -> query current VMExport status
  -> refresh disk urls/status in DB
  -> NEVER persist to MinIO/S3

Create VM From Asset
  -> console refreshes live VMExport status
  -> root disk import uses current download_url
  -> data disks import uses current download_url
  -> worker creates VM from direct export URLs

Delete Asset
  -> console delete VMExport by export_id = service_id
  -> ignore missing region export
  -> delete DB asset record
```

### 3.2 核心流程

#### 1. Live export 语义
- `VirtualMachineExport` 不再被视为“导出中间态，最终要转成 S3 资产”
- 它本身就是当前资产的真实来源
- `virtual_machine_image` 仅保存一条“当前 live export 引用记录”

#### 2. 单槽语义
- 每个 VM 只有一个固定导出槽位
- `export_id = service_id`
- 资产记录按 `source_service_id` 或 `source_uri=service://{service_id}` 唯一识别
- 重新导出即覆盖旧导出

#### 3. 读接口轻量化
- `/console/teams/{team}/vm/assets`
- `/console/teams/{team}/vm/assets/{asset_id}`
- `/console/teams/{team}/apps/{serviceAlias}/vm-export`

这些接口只允许：
- 查 DB
- 查当前 live export 状态
- 刷新 `status / disks / image_url / latest_export_error`

这些接口禁止：
- 调 `persist_vm_export`
- 下载磁盘文件
- 上传 MinIO/S3
- 删除导出资源

#### 4. 删除和覆盖
- 删除资产时，必须先删底层 `VirtualMachineExport`
- 重新导出前，必须先删旧 `VirtualMachineExport`
- 若删除底层资源时返回“not found”，应视为幂等成功

## 四、数据模型设计
### 4.1 新增数据库表

- 无新增表

### 4.2 数据关系

继续复用 `virtual_machine_image`，但语义调整为“live export 引用记录”。

建议字段语义：

- `name`
  - 固定保存 `service_id`
  - 作为技术标识，不直接展示给用户
- `source_type`
  - 继续使用 `vm_export`
- `source_uri`
  - 继续使用 `service://{service_id}`
- `build_event_id`
  - 固定保存当前 `export_id`，即 `service_id`
- `extra_json`
  - 保存：
    - `source_service_id`
    - `source_service_alias`
    - `source_service_cname`
    - `display_name`
    - `disks`
    - `latest_export_status`
    - `latest_export_error`
    - `runtime_snapshot`

序列化时新增：

- `display_name`
  - 优先取 `extra.display_name`
  - 为空时回退 `source_service_cname`
  - 再为空时回退 `service_alias`
  - 最后才回退 `name`

说明：
- 不新增表字段，避免迁移成本
- 展示名是用户态信息，放入 `extra_json` 即可满足需求

## 五、API设计
### 5.1 接口列表

#### rainbond-console

- `POST /console/teams/{tenantName}/apps/{serviceAlias}/vm-export`
  - 新增 `force_replace` 控制覆盖确认后的真正执行
- `GET /console/teams/{tenantName}/apps/{serviceAlias}/vm-export`
  - 查询最近一次 live export 状态
- `DELETE /console/teams/{tenantName}/vm/assets/{asset_id}`
  - 删除数据库资产时同步删除底层 `VMExport`

#### rainbond

- 保留：`POST /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports`
- 保留：`GET /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports/{export_id}`
- 新增：`DELETE /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports/{export_id}`
- 废弃调用路径：`POST /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports/{export_id}/persist`

### 5.2 请求/响应结构

#### console 发起导出

请求：

```json
{
  "force_replace": false
}
```

若发现旧导出记录，返回覆盖确认信息：

```json
{
  "requires_confirmation": true,
  "existing_asset": {
    "id": 27,
    "display_name": "Windows 测试机",
    "status": "ready"
  },
  "msg_show": "当前组件已有旧导出，确认后将删除旧导出记录和底层导出资源，并重新导出。"
}
```

用户确认后再次请求：

```json
{
  "force_replace": true
}
```

#### console 资产序列化

新增字段：

```json
{
  "id": 27,
  "name": "53657ddc3c651678c247fc551cddef77",
  "display_name": "Windows 测试机",
  "source_type": "vm_export",
  "status": "ready",
  "disks": [
    {
      "disk_key": "manual30",
      "disk_role": "root",
      "download_url": "https://..."
    }
  ]
}
```

#### rainbond 删除导出

语义：
- 根据 `service_id + export_id` 删除对应的 `VirtualMachineExport`
- 如果不存在，返回成功或可被 console 识别为幂等成功

## 六、核心实现设计
### 6.1 关键逻辑

#### A. 导出启动
- console 不再接收用户输入导出名
- `export_id` 固定为 `service_id`
- 资产记录 `name` 固定为 `service_id`
- `display_name` 固定保存 `service_cname`
- 导出前先查是否已有旧记录：
  - 若没有：直接开始
  - 若有且 `force_replace=false`：返回确认信息
  - 若有且 `force_replace=true`：删除旧 VMExport + 删除旧 DB 记录后再开始

#### B. 状态同步
- `sync_vm_export_status` 保留，但完全移除持久化分支
- 只更新：
  - `asset.status`
  - `asset.image_url`（根盘当前 URL）
  - `extra.disks`
  - `extra.latest_export_status`
  - `extra.latest_export_error`
- 若底层导出不存在：
  - 记录 missing 信息
  - 将资产置为 `failed` 或标记为失效

#### C. 删除资产
- `delete_vm_image` 在删除 `vm_export` 资产时：
  - 先调用 region 删除 live export
  - 删除成功或底层不存在时，再删 DB
  - 其他错误向上抛出

#### D. 从资产创建 VM
- 不再依赖 `machine_manifest`
- 不再依赖 `persist_vm_export` 的 S3 对象路径
- 创建前刷新当前 live export 状态
- 从 `extra.disks` 中直接构造：
  - 根盘 `vm_url`
  - 数据盘 `vm_disk_imports`
  - `vm_disk_layout`

#### E. 展示名
- 资产目录、VM 详情最新导出、创建页列表都展示 `display_name`
- 技术字段 `name=service_id` 不直接给用户看

### 6.2 复用现有代码

- 复用现有 `vm-exports` 启动和状态查询逻辑
- 复用 `virtual_machine_image` 模型和资产目录页
- 复用 VM 导出状态轮询入口
- 复用创建 VM 时的 `vm_disk_imports / vm_disk_layout` 运行时协议

需要删除/绕开的现有代码：

- region `persist vm export` 调用路径
- console 在 `/vm/assets` 里的持久化触发逻辑
- console 对 `machine_manifest` / `restore-plan` 的依赖

## 七、实施计划
### 跨层覆盖检查（MUST）
- [x] Go (rainbond): 需要 — 新增删除 VMExport 接口，保留 live export 状态查询，废弃 persist 调用路径
- [x] Python (console): 需要 — 覆盖确认、删除级联、轻量同步、展示名序列化、创建 VM 改走 live export URL
- [x] React (rainbond-ui): 需要 — 导出确认弹窗、移除自定义命名、资产展示名改为 `service_cname`
- [ ] Plugin: 不涉及

### Sprint 1: region 导出资源生命周期
#### Task 1.1: 新增删除 VMExport API
- 仓库：rainbond
- 文件：`api/handler/vm_export.go`、`api/controller/vm_export.go`、`api/api_routers/version2/v2Routers.go`
- 实现内容：
  - 新增 `DELETE /vm-exports/{export_id}`
  - 按 `service_id + export_id` 删除相关 `VirtualMachineExport`
  - 允许资源缺失时幂等成功
- 验收标准：
  - console 可显式删除旧导出
  - 删除后不会残留旧导出 CR

#### Task 1.2: 覆盖测试 region 删除链路
- 仓库：rainbond
- 文件：`api/controller/vm_export_test.go`、`api/handler/vm_export_test.go`
- 实现内容：
  - 删除成功
  - 删除资源不存在
  - 只删除指定 `export_id`
- 验收标准：
  - 删除接口行为稳定且幂等

### Sprint 2: console live export 语义改造
#### Task 2.1: 导出前覆盖确认
- 仓库：rainbond-console
- 文件：`console/services/virtual_machine.py`、`console/views/app_overview.py`、相关测试
- 实现内容：
  - 固定 `export_id/name=service_id`
  - 查旧导出记录
  - 支持 `force_replace`
  - 删除旧 DB 记录和旧 VMExport
- 验收标准：
  - 用户确认前不会直接覆盖
  - 确认后旧导出被清理再重建

#### Task 2.2: 去掉 MinIO/S3 持久化依赖
- 仓库：rainbond-console
- 文件：`console/services/virtual_machine.py`、`console/views/app_create/vm_run.py`、相关测试
- 实现内容：
  - `sync_vm_export_status` 不再触发 persist
  - 创建 VM 改用 live export URLs 直接构造根盘和数据盘导入
- 验收标准：
  - `/vm/assets` 不再阻塞于持久化
  - 创建 VM 不再依赖 S3 object uri

#### Task 2.3: 删除资产级联删除底层导出
- 仓库：rainbond-console
- 文件：`console/services/virtual_machine.py`、`console/views/app_config/app_domain.py`、相关测试
- 实现内容：
  - 删除 `vm_export` 资产时联动删 region `VMExport`
- 验收标准：
  - 资产目录删除后不残留旧导出资源

### Sprint 3: UI 交互与展示
#### Task 3.1: 调整导出确认交互
- 仓库：rainbond-ui
- 文件：`src/pages/Component/index.js`、`src/components/SlidePanel/components/components.js`、相关 service/model
- 实现内容：
  - 删除导出名输入
  - 有旧导出时展示覆盖确认
  - 确认后携带 `force_replace=true`
- 验收标准：
  - 导出动作符合覆盖确认语义

#### Task 3.2: 展示 `service_cname`
- 仓库：rainbond-ui
- 文件：`src/components/VMAssetCatalogModal/index.js`、`src/components/ImageVirtualMachineForm/index.js`、`src/pages/Component/component/Basic/VMProfilePanel.js`
- 实现内容：
  - 展示名改读 `display_name`
  - 不直接展示 `service_id`
- 验收标准：
  - 用户在资产目录和创建页看到的是组件名

## 八、关键参考代码
| 功能 | 文件 | 说明 |
|------|------|------|
| VM 导出状态同步 | `rainbond-console/console/services/virtual_machine.py` | 当前阻塞点和资产同步逻辑 |
| VM 导出入口 | `rainbond-console/console/views/app_overview.py` | 导出按钮后的 console 入口 |
| VM 资产目录接口 | `rainbond-console/console/views/app_config/app_domain.py` | `/console/teams/{team}/vm/assets` |
| region VM 导出路由 | `rainbond/api/api_routers/version2/v2Routers.go` | 现有 vm-exports 路由 |
| region VM 导出处理 | `rainbond/api/handler/vm_export.go` | 创建/查询导出 CR |
| region 持久化实现 | `rainbond/api/handler/vm_export_persist.go` | 需要从主链路移除的 MinIO/S3 路径 |
| VM 创建入口 | `rainbond-console/console/views/app_create/vm_run.py` | 需要改成直接使用 live export URL |
| VM 资产目录 UI | `rainbond-ui/src/components/VMAssetCatalogModal/index.js` | 资产展示和删除入口 |
| VM 详情页导出入口 | `rainbond-ui/src/pages/Component/index.js` | 导出确认与状态轮询 |
