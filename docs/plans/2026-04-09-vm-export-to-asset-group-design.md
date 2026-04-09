# 虚拟机关机导出到镜像组设计文档

## 一、项目背景
### 1.1 项目架构

当前虚拟机能力已经形成如下主链路：

```text
rainbond-ui
  -> /console/teams/{team}/apps/{serviceAlias}/detail
  -> /console/teams/{team}/apps/{serviceAlias}/vm-profile
  -> /console/teams/{team}/vm/assets
rainbond-console
  -> 聚合 VM 资产目录、运行时配置、VNC 连接信息
  -> 调用 rainbond region API 创建 VM / 查询 VM 能力
rainbond
  -> KubeVirt / CDI / Kubernetes API
```

当前已有能力：

- 通过 VM 资产创建虚拟机：`rainbond-console/console/views/app_create/vm_run.py:22`
- VM 资产目录与资产详情：`rainbond-console/console/services/virtual_machine.py:27`
- VM 详情页专属信息聚合：`rainbond-console/console/views/app_overview.py:90`
- VM 资产列表入口：`rainbond-console/console/urls/__init__.py:647`
- UI 资产列表弹窗：`rainbond-ui/src/components/VMAssetCatalogModal/index.js:5`

当前缺失能力：

- 用户无法把“已经运行过、当前已关机”的 VM 当前状态导出成新的 VM 资产
- 用户无法把包含多块磁盘的 VM 原封不动导出到“虚拟机镜像组”
- 资产目录当前只有单条镜像资产概念，还没有“整机资产 + 磁盘明细”结构

### 1.2 现有基础

- `rainbond-ui`
  - 已有 VM 详情页和滑窗页
  - 已有 VM 资产目录列表、快速复制、删除、详情查看能力
  - 已有 VM 挂起/恢复入口：`rainbond-ui/src/pages/Component/index.js:933`
- `rainbond-console`
  - 已有 `virtual_machine_image` 资产模型，包含来源、格式、大小、状态、父资产等字段：
    `rainbond-console/www/models/main.py:950`
  - 已有 VM 资产聚合与运行时配置服务：
    `rainbond-console/console/services/virtual_machine.py:27`
  - 已有 VM 详情页 `vm_profile` 聚合接口：
    `rainbond-console/console/views/app_overview.py:179`
- `rainbond`
  - 已有 VM 能力探测动态 client 模式：
    `rainbond/api/handler/vm_capability.go:47`
  - 已有 VM 运行时配置消费逻辑（GPU / USB / 固定 IP）
  - 已有 KubeVirt VM 挂起/恢复能力

### 1.3 核心需求

- 支持对“已关闭”的 VM 发起导出
- 导出语义必须是“整机导出”，不是只导 rootdisk
- 导出结果直接进入现有“虚拟机镜像组/资产目录”
- 导出结果必须保留：
  - 系统盘
  - 所有数据盘
  - boot mode
  - GPU / USB / 网络模式等运行时信息
- 资产目录中能看到导出中的状态、导出完成后的新资产
- 后续从该资产再次创建 VM 时，应恢复为完整机器，而不是只恢复单盘

## 二、用户旅程
### 2.1 用户操作流程

- 用户进入 VM 详情页或滑窗页
- 系统展示 VM 当前绑定资产、网络、GPU / USB 等信息
- 当 VM 状态为 `closed` 时，显示 `导出到镜像组` 操作
- 用户点击导出，输入资产名称并确认
- 系统立即在“虚拟机镜像组”里创建一条新的整机资产记录，状态为 `exporting`
- 后端为该 VM 的每块磁盘分别发起 `DataExport`
- 所有磁盘导出与内部化完成后，整机资产状态变为 `ready`
- 用户在现有资产列表中可以看到该资产，并可用于再次创建 VM

### 2.2 页面原型

- 详情页入口
  - `rainbond-ui/src/pages/Component/index.js`
  - 在现有 VM 专属操作附近新增 `导出到镜像组`
- 滑窗页入口
  - `rainbond-ui/src/components/SlidePanel/components/components.js:1249`
  - 与现有 `挂起/恢复` 按钮并列展示
- 资产目录入口
  - 继续复用现有 `VMAssetCatalogModal`
  - 增加“导出中 / 导出失败 / 整机资产 / 磁盘数”展示
  - 资产详情中展示整机导出的磁盘清单与来源 VM

### 2.3 外部系统交互

- `rainbond-console` 调用 `rainbond` 启动 VM 导出任务
- `rainbond` 调用 Kubernetes 动态 API 创建 CDI `DataExport`
- `rainbond` 查询 `DataExport` 状态和导出 URL
- `rainbond` 复用现有 VM 镜像导入链路，将导出的磁盘结果内部化成可复用的 VM 资产镜像

## 三、整体架构设计
### 3.1 系统架构图

```text
rainbond-ui
  -> POST /console/teams/{team}/apps/{serviceAlias}/vm-export
  -> GET  /console/teams/{team}/apps/{serviceAlias}/vm-profile
  -> GET  /console/teams/{team}/vm/assets

rainbond-console
  -> 创建整机资产父记录（status=exporting）
  -> 创建磁盘子记录（每盘一条）
  -> 调用 rainbond region 导出接口
  -> 轮询导出状态并回填资产状态

rainbond
  -> 解析 VM 挂载的 rootdisk + data disk PVC
  -> 为每个 PVC 创建 DataExport
  -> 获取导出结果并执行内部镜像化
  -> 返回磁盘级结果给 console

Kubernetes / KubeVirt / CDI
  -> VirtualMachine / PVC / DataExport
```

### 3.2 核心流程

1. 用户在 VM 详情页点击 `导出到镜像组`
2. console 校验：
   - 组件必须是 VM
   - 当前状态必须是 `closed`
   - 资产名称在当前团队下未重复
3. console 创建父资产记录：
   - `asset_kind=machine`
   - `source_type=vm_export`
   - `status=exporting`
   - `extra_json` 保存来源 VM、运行时快照、导出盘数
4. rainbond 按磁盘维度创建多个 `DataExport`
5. rainbond 对每块磁盘执行：
   - 等待 `DataExport` ready
   - 获取导出地址
   - 复用当前 VM URL/上传导入能力，将磁盘内部化为平台可复用镜像
6. console 为每块磁盘写入子记录
7. 全部成功：
   - 父资产 `status=ready`
   - 子记录 `status=ready`
8. 任一失败：
   - 父资产 `status=failed`
   - 子记录记录错误原因
9. 用户在现有资产目录看到新整机资产，可继续复用创建 VM

## 四、数据模型设计
### 4.1 新增数据库表

#### 1. 扩展 `virtual_machine_image`

当前模型位置：`rainbond-console/www/models/main.py:950`

新增字段：

- `asset_kind`
  - `disk`：单盘镜像资产（现有上传、公网、复制等）
  - `machine`：整机导出资产
- `disk_count`
  - 记录整机资产包含的磁盘数量
- `source_service_id`
  - 来源 VM 的 `service_id`
- `export_status_message`
  - 最近一次导出错误消息

说明：

- 现有资产默认视为 `asset_kind=disk`
- 整机导出后的父记录为 `asset_kind=machine`

#### 2. 新增 `virtual_machine_image_disk`

建议表名：`virtual_machine_image_disk`

字段建议：

- `tenant_id`
- `asset_id`
- `disk_key`
- `disk_name`
- `disk_role`
  - `root`
  - `data`
- `order_index`
- `pvc_namespace`
- `pvc_name`
- `image_url`
- `source_uri`
- `format`
- `size_bytes`
- `checksum`
- `status`
- `boot`
- `extra_json`
- `create_time`
- `update_time`

用途：

- 表示整机资产下每一块导出磁盘
- 支持后续“按整机资产恢复完整 VM”

### 4.2 数据关系

```text
virtual_machine_image (asset_kind=machine)
  1 -> N
virtual_machine_image_disk

virtual_machine_image (asset_kind=disk)
  保持现有单盘镜像语义
```

关系约束：

- `virtual_machine_image_disk.asset_id` 指向父资产 `virtual_machine_image.ID`
- `disk_role=root` 的记录只能有 1 条
- `order_index` 用于恢复磁盘挂载顺序

## 五、API设计
### 5.1 接口列表

#### rainbond-console

- `POST /console/teams/{tenantName}/apps/{serviceAlias}/vm-export`
  - 发起导出
- `GET /console/teams/{tenantName}/apps/{serviceAlias}/vm-export`
  - 查询当前 VM 最近一次导出状态
- `GET /console/teams/{tenantName}/vm/assets`
  - 继续作为资产目录入口，但返回整机资产摘要
- `GET /console/teams/{tenantName}/vm/assets/{asset_id}`
  - 返回资产详情时补充磁盘清单

#### rainbond

- `POST /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports`
  - 启动整机导出
- `GET /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports/{export_id}`
  - 查询导出状态

说明：

- region 侧导出使用 CDI `DataExport`
- `DataExport` 以“每块 PVC 一条 CR”的方式创建

### 5.2 请求/响应结构

#### console 发起导出请求

```json
{
  "name": "ubuntu-24.04-dev-snapshot",
  "description": "从 demo-vm 导出",
  "export_all_disks": true
}
```

#### console 导出响应

```json
{
  "asset_id": 128,
  "status": "exporting",
  "name": "ubuntu-24.04-dev-snapshot"
}
```

#### region 启动导出请求

```json
{
  "export_id": "vm-export-128",
  "asset_name": "ubuntu-24.04-dev-snapshot",
  "export_all_disks": true
}
```

#### region 状态响应

```json
{
  "status": "exporting",
  "disks": [
    {
      "disk_key": "rootdisk",
      "disk_role": "root",
      "pvc_name": "rootdisk-xxx",
      "status": "ready",
      "download_url": "https://..."
    }
  ]
}
```

## 六、核心实现设计
### 6.1 关键逻辑

#### 1. 导出前置校验

- VM 组件类型必须是 `extend_method=vm`
- VM 状态必须是 `closed`
- 禁止对 `paused/running/upgrading` 状态发起导出
- 当前团队下资产名不可重复

#### 2. 整机资产落库策略

- 发起导出时，先创建父资产：
  - `asset_kind=machine`
  - `source_type=vm_export`
  - `status=exporting`
- `extra_json` 保存：
  - `source_service_id`
  - `source_service_alias`
  - `source_asset_id`
  - `runtime_snapshot`
    - `network_mode`
    - `network_name`
    - `fixed_ip`
    - `gpu_enabled`
    - `gpu_resources`
    - `usb_enabled`
    - `usb_resources`
    - `boot_mode`

#### 3. 磁盘发现与导出

- rootdisk：
  - 从当前 VM rootdisk PVC 解析
- data disk：
  - 从 VM 挂载的 PVC / volume 关系解析
- rainbond 对每块盘创建一个 `DataExport`
- 命名规则建议：
  - `vmexport-{serviceAlias}-{assetID}-{diskKey}`

#### 4. 导出结果内部化

仅创建 `DataExport` 还不能直接复用于当前 VM 创建链路，因为当前创建链路仍依赖平台内部可复用的 `image_url`。

因此需要二段式处理：

1. `DataExport` 负责把 PVC 当前状态稳定导出
2. rainbond 复用现有 VM URL/下载导入链路，把导出的磁盘内部化成平台镜像

这样最终每块磁盘子记录都能得到：

- `image_url`
- `source_uri`
- `format`
- `status`

#### 5. 资产目录展示策略

- 资产目录默认展示父资产
- `asset_kind=machine` 显示为“整机资产”
- `source_type=vm_export` 显示为“VM 导出”
- 详情弹窗补充磁盘清单：
  - rootdisk
  - data disk
  - 状态
  - 大小

#### 6. 从整机资产再次创建 VM

为保证导出后的资产可真正复用，需要扩展现有创建流程：

- 若选择的是 `asset_kind=machine`
  - `vm_run.py` 不再只取单个 `image_url`
  - 需要同时解析父资产运行时快照 + 子磁盘清单
- rootdisk 使用子记录中的 root 磁盘
- data disk 按 `order_index` 一并挂载
- 默认恢复父资产里的：
  - `boot_mode`
  - `network_mode`
  - `network_name`
  - `fixed_ip`
  - `gpu/usb`
- UI 仍允许用户在创建时覆盖这些默认值

### 6.2 复用现有代码

- VM 资产聚合与序列化：
  - `rainbond-console/console/services/virtual_machine.py:27`
- VM 创建入口与资产绑定：
  - `rainbond-console/console/views/app_create/vm_run.py:22`
- VM 详情页聚合：
  - `rainbond-console/console/views/app_overview.py:90`
- VM 资产目录接口：
  - `rainbond-console/console/urls/__init__.py:647`
- UI 资产目录弹窗：
  - `rainbond-ui/src/components/VMAssetCatalogModal/index.js:5`
- UI 当前 VM 操作按钮：
  - `rainbond-ui/src/pages/Component/index.js:933`
- rainbond 动态 client 模式：
  - `rainbond/api/handler/vm_capability.go:47`

## 七、实施计划
### 跨层覆盖检查

- [ ] Go (rainbond): 需要 — 增加 VM 整机导出 API、DataExport 编排、导出状态查询、整机资产恢复输入支持
- [ ] Python (console): 需要 — 增加整机资产与磁盘明细模型、导出任务编排、详情/列表聚合、创建链路适配
- [ ] React (rainbond-ui): 需要 — 增加详情页导出入口、资产目录整机展示、导出状态与资产复用交互
- [ ] Plugin: 不涉及

### Sprint 1: rainbond 导出能力
#### Task 1.1: 新增 VM 导出 region API
- 仓库：rainbond
- 文件：`api/api_routers/version2/v2Routers.go:480`、`api/controller/vm_capability.go:15`
- 实现内容：
  - 新增 `POST/GET vm-exports` 路由与 controller
  - 定义导出请求、状态响应结构
- 验收标准：
  - console 能发起导出并轮询状态

#### Task 1.2: 基于 CDI DataExport 编排每块 PVC 导出
- 仓库：rainbond
- 文件：`api/handler/vm_capability.go:47`（复用 dynamic client 模式）、新增 `api/handler/vm_export.go`
- 实现内容：
  - 发现 VM rootdisk 与数据盘 PVC
  - 按盘创建 `DataExport`
  - 聚合每块盘状态
- 验收标准：
  - 能返回盘级导出进度与导出地址

#### Task 1.3: 导出结果内部化与整机恢复输入
- 仓库：rainbond
- 文件：`worker/appm/conversion/*`、VM 创建相关 handler
- 实现内容：
  - 将导出结果转换为平台内部可复用磁盘镜像
  - 支持按“整机资产 + 磁盘明细”恢复 VM
- 验收标准：
  - 导出的整机资产可再次创建完整 VM

### Sprint 2: rainbond-console 资产与导出编排
#### Task 2.1: 扩展整机资产模型与磁盘子表
- 仓库：rainbond-console
- 文件：`www/models/main.py:950`、新增 `console/repositories/virtual_machine_disk.py`
- 实现内容：
  - 扩展 `virtual_machine_image`
  - 新增 `virtual_machine_image_disk`
- 验收标准：
  - 能表达“一个整机资产包含多块磁盘”

#### Task 2.2: 实现导出服务与导出状态聚合
- 仓库：rainbond-console
- 文件：`console/services/virtual_machine.py:27`、新增 `console/views/app_vm_export.py`
- 实现内容：
  - 创建父资产与子磁盘记录
  - 调用 region 启动导出
  - 轮询并更新资产状态
- 验收标准：
  - 资产目录能看到 `exporting/ready/failed`

#### Task 2.3: 适配创建流程消费整机资产
- 仓库：rainbond-console
- 文件：`console/views/app_create/vm_run.py:56`
- 实现内容：
  - `asset_kind=machine` 时解析整机资产与磁盘明细
  - 带上运行时快照默认值
- 验收标准：
  - 选择导出的整机资产可再次创建完整 VM

#### Task 2.4: 详情页补充导出信息
- 仓库：rainbond-console
- 文件：`console/views/app_overview.py:90`
- 实现内容：
  - `vm_profile` 中增加最近导出状态与导出资产摘要
- 验收标准：
  - 详情页可看到最近导出状态和跳转资产目录

### Sprint 3: rainbond-ui 导出交互
#### Task 3.1: VM 详情页新增导出入口
- 仓库：rainbond-ui
- 文件：`src/pages/Component/index.js:933`、`src/components/SlidePanel/components/components.js:1249`
- 实现内容：
  - VM 状态为 `closed` 时显示 `导出到镜像组`
  - 非 `closed` 时提示“请先关闭”
- 验收标准：
  - 用户可以从 VM 详情页直接发起导出

#### Task 3.2: 资产目录展示整机资产与导出状态
- 仓库：rainbond-ui
- 文件：`src/components/VMAssetCatalogModal/index.js:19`、`src/services/createApp.js:303`
- 实现内容：
  - 增加 `vm_export` 来源标签
  - 增加整机资产详情、磁盘数、导出状态展示
- 验收标准：
  - 导出的整机资产在现有资产目录可见

#### Task 3.3: 从整机资产创建 VM 的交互适配
- 仓库：rainbond-ui
- 文件：`src/components/ImageVirtualMachineForm/index.js`、`src/components/VMAssetCatalogModal/index.js:113`
- 实现内容：
  - 选择整机资产时加载运行时默认值
  - 允许用户覆盖 GPU/USB/网络等默认值
- 验收标准：
  - 导出资产可直接复用创建完整 VM

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| VM 资产目录聚合 | `rainbond-console/console/services/virtual_machine.py` | 当前资产模型、运行时聚合与序列化 |
| VM 创建绑定资产 | `rainbond-console/console/views/app_create/vm_run.py` | 当前从资产创建 VM 的主入口 |
| VM 详情页聚合 | `rainbond-console/console/views/app_overview.py` | 当前 `vm_profile` 返回入口 |
| VM 资产目录路由 | `rainbond-console/console/urls/__init__.py` | 当前 `/vm/assets` 路由集合 |
| VM 资产目录弹窗 | `rainbond-ui/src/components/VMAssetCatalogModal/index.js` | 现有资产列表、复制、详情展示 |
| VM 详情页按钮 | `rainbond-ui/src/pages/Component/index.js` | 当前 VM 挂起/恢复与详情操作 |
| VM capability dynamic client | `rainbond/api/handler/vm_capability.go` | 当前 dynamic client + unstructured 模式，可复用于 DataExport |
