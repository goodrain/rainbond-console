# Rainbond VM Live Migration 存储选择设计文档

## 一、项目背景

### 1.1 项目架构

本次需求覆盖 Rainbond 虚拟机创建链路的三层：

```text
rainbond-ui
  -> rainbond-console
    -> rainbond / worker
      -> KubeVirt VirtualMachine / CDI DataVolume / PVC
```

用户在 `rainbond-ui` 中创建 VM，`rainbond-console` 负责接收创建参数、落库存储与 VM 运行时属性，`rainbond worker` 最终把组件转换为 KubeVirt `VirtualMachine`、`PersistentVolumeClaim` 与 `DataVolumeTemplate`。

### 1.2 现有基础

- VM 创建页已经有“环境配置”和“高级配置 -> 存储”两处磁盘配置入口。
- 控制台存储体系已经有统一的 `volume-options` 能力，支持返回 `volume_type / access_mode / provisioner` 等元数据。
- `TenantServiceVolume` 已能保存 `volume_type / access_mode / volume_provider_name`。
- VM 运行时已有 `vm_disk_layout` 与 `vm_disk_imports` 两套元数据：
  - `vm_disk_layout` 描述根盘、数据盘、安装介质顺序
  - `vm_disk_imports` 描述需要从 URL 导入的磁盘
- Worker 在为 VM 生成 DataVolumeTemplate 时，会继承 claim 的 `StorageClassName` 与 `AccessModes`。

当前存在的核心问题是：

- VM 创建页还没有把“存储类型”正式贯通到根盘和数据盘。
- VM 盘的后端/worker 创建链路里，部分 claim 仍被硬编码为 `local-path`，导致前端即便将来支持选择存储，也无法真正同步到底层 PVC。
- KubeVirt live migration 需要所有 VM PVC 都满足共享访问约束，否则会报：
  - `PVC manual9 is not shared, live migration requires that all PVCs must be shared`

### 1.3 核心需求

- VM 根盘和数据盘都支持选择存储类型。
- `CD-ROM / ISO` 安装介质不需要选择存储类型。
- 创建页中只展示“支持 live migration”的存储类型。
- 当前产品定义中，“支持 live migration”的判断规则为：
  - 仅展示 `access_mode` 包含 `RWX` 的存储类型。
- 创建页的两处入口都要支持：
  - 预配置环境中的根盘
  - 高级配置中新增的数据盘
- 用户选中的存储类型需要一路同步到底层 PVC / DataVolumeTemplate。

## 二、用户旅程（MUST — 禁止跳过）

### 2.1 用户操作流程

1. 用户进入 VM 创建页，选择镜像来源。
2. 用户在“环境配置”中配置 CPU、内存、根盘大小。
3. 页面展示根盘的“存储类型”下拉框，只包含支持 `RWX` 的选项。
4. 用户进入“高级配置 -> 存储”时，可以继续新增数据盘。
5. 新增数据盘时，同样只能选择支持 `RWX` 的存储类型。
6. 如果镜像来源是 ISO/CD-ROM，安装介质不出现存储类型选择。
7. 用户提交创建。
8. console 校验所有 VM 盘的存储类型都满足 `RWX`。
9. console 为根盘和数据盘创建对应的 `TenantServiceVolume` 记录，并保存 VM 磁盘布局和导入信息。
10. worker 根据这些记录生成 PVC / DataVolumeTemplate，最终创建出底层 VM。
11. 后续用户对 VM 执行 live migration / hot update 时，不会再因为 PVC 不是共享卷而失败。

### 2.2 页面原型

- VM 创建页“环境配置”
  - 根盘字段从“仅容量”扩展为“容量 + 存储类型”
  - 若没有可选 `RWX` 存储类型，页面直接提示并阻止继续创建
- VM 创建页“高级配置 -> 存储”
  - VM 数据盘弹窗继续保留磁盘类型（`/disk`、`/lun`、`/cdrom`）与容量
  - 仅当磁盘不是安装介质时显示“存储类型”
  - 存储类型下拉框只显示 `RWX` 选项

### 2.3 外部系统交互

- `rainbond-console` 调用现有存储类型能力获取 `volume-options`
- `rainbond-console` 落库 `TenantServiceVolume`
- `rainbond worker` 根据数据库记录生成 PVC / DataVolumeTemplate
- `KubeVirt` 使用这些 PVC 作为 VM 根盘与数据盘

## 三、整体架构设计

### 3.1 系统架构图

```text
UI VM Create Form
  -> 获取 RWX volume options
  -> 提交 root/data disk storage selections
    -> console vm_run create API
      -> 校验 RWX 存储类型
      -> 创建 TenantServiceVolume(root/data)
      -> 保存 vm_disk_layout / vm_disk_imports
        -> worker volume conversion
          -> PVC / DataVolumeTemplate with selected StorageClassName
            -> KubeVirt VM
```

### 3.2 核心流程

#### 3.2.1 RWX 存储选项加载

1. UI 调用现有存储选项接口。
2. 读取返回项中的 `access_mode`。
3. 仅保留包含 `RWX` 的存储类型。
4. 根盘和数据盘的存储下拉框都复用这批数据。

#### 3.2.2 VM 创建提交流程

1. UI 提交 VM 基础配置。
2. UI 同时提交：
   - 根盘容量与 `volume_type`
   - 数据盘列表（容量、盘位、`volume_type`）
3. console 校验：
   - 根盘和数据盘必须都带 `volume_type`
   - `volume_type` 对应的 `access_mode` 必须包含 `RWX`
   - 安装介质盘不参与该校验
4. console 创建 VM 组件后，创建对应的 `TenantServiceVolume` 记录。
5. console 保存 `vm_disk_layout`，确保根盘 / 数据盘顺序与角色清晰。
6. 若需要导入镜像，则继续保存 `vm_disk_imports`。

#### 3.2.3 Worker PVC 生成流程

1. worker 读取 `TenantServiceVolume`。
2. 对 VM 根盘和数据盘：
   - 使用记录中的 `volume_type`
   - 使用记录中的 `access_mode`
   - 生成正确的 `StorageClassName`
3. 若是导入盘，则 DataVolumeTemplate 继承这份 claim 配置。
4. 若是空白盘，则空白 DataVolumeTemplate 同样继承这份 claim 配置。
5. 安装介质盘不走共享存储选择逻辑。

## 四、数据模型设计

### 4.1 新增数据库表

本次不新增数据库表。

### 4.2 数据关系

复用现有表与属性：

- `TenantServiceVolume`
  - 为 VM 根盘和数据盘分别保存：
    - `volume_type`
    - `access_mode`
    - `volume_provider_name`
    - `volume_capacity`
    - `volume_path`
- `ComponentK8sAttributes`
  - `vm_disk_layout`：描述根盘 / 数据盘 / 安装介质顺序
  - `vm_disk_imports`：描述导入盘来源

约定：

- 根盘统一使用 `volume_name=disk`
- 数据盘沿用现有 `manual*` / 逻辑卷名映射
- 安装介质不创建需要用户选存储类型的 `TenantServiceVolume`

## 五、API设计

### 5.1 接口列表

#### 复用接口

- `GET /console/teams/{team}/apps/{serviceAlias}/volumes/options`
- `POST /console/teams/{team}/apps/vm_run`

#### 调整的请求体

`POST /console/teams/{team}/apps/vm_run`

新增字段：

```json
{
  "root_disk": {
    "volume_capacity": 40,
    "volume_type": "nfs-storage"
  },
  "data_disks": [
    {
      "volume_name": "data-1",
      "volume_path": "/disk",
      "volume_capacity": 100,
      "volume_type": "nfs-storage"
    }
  ]
}
```

说明：

- `root_disk` 必填，且必须带 `volume_type`
- `data_disks` 可选
- `CD-ROM / ISO` 安装介质不放入 `root_disk` / `data_disks` 的共享存储校验范围

### 5.2 请求/响应结构

请求校验原则：

- `root_disk.volume_type` 必须存在
- `data_disks[*].volume_type` 必须存在
- 对应存储类型的 `access_mode` 必须包含 `RWX`

失败响应：

- `400`：请求字段缺失
- `409`：存储类型不支持 live migration

## 六、核心实现设计

### 6.1 关键逻辑

#### UI 侧

- 提供 `filterVMLiveMigrationVolumeOptions(volumeOptions)` 工具函数
- 统一用 `access_mode.includes("RWX")` 过滤
- 根盘和数据盘复用同一批过滤结果
- 若过滤结果为空：
  - 显示“当前没有可用于 VM live migration 的共享存储类型”
  - 禁止提交

#### console 侧

- 新增 VM 存储选择解析逻辑：
  - 解析根盘与数据盘请求体
  - 按 `volume-options` 再校验一次 `RWX`
- VM 创建成功后：
  - 根盘通过 `add_service_volume(..., volume_type=selected_type)` 落库
  - 数据盘同理
- 保持 `vm_disk_layout` 与 `TenantServiceVolume` 一致

#### worker / rainbond 侧

- 修复 VM 磁盘 claim 仍硬编码 `local-path` 的逻辑
- `vm-file` 不应再默认视为 `local-path`
- VM 根盘 / 数据盘创建 claim 时，应优先使用：
  - `TenantServiceVolume.VolumeType`
  - `TenantServiceVolume.AccessMode`
- DataVolumeTemplate 继承 claim 的 `StorageClassName` 与 `AccessModes`

### 6.2 复用现有代码

- `console.services.app_config.volume_service.get_service_support_volume_options`
- `console.services.app_config.volume_service.add_service_volume`
- `console.services.virtual_machine` 中现有的 `vm_disk_layout / vm_disk_imports` 逻辑
- `worker/appm/volume/vm_import.go` 中对 claim 的 `StorageClassName / AccessModes` 透传能力

## 七、实施计划

### 跨层覆盖检查（MUST）

- [x] Go (rainbond): 需要 — 修复 VM PVC / DataVolumeTemplate 使用所选存储类型，而不是硬编码 `local-path`
- [x] Python (console): 需要 — 接收并校验根盘/数据盘存储类型，创建对应 `TenantServiceVolume`
- [x] React (rainbond-ui): 需要 — VM 创建页根盘/数据盘仅展示 `RWX` 存储类型并提交选择结果
- [x] Plugin: 不涉及 — 本次不修改插件仓库

### Sprint 1: VM 创建页 RWX 存储选择

#### Task 1.1: 过滤 VM 可用存储类型

- 仓库：rainbond-ui
- 文件：
  - `src/components/ImageVirtualMachineForm/index.js`
  - `src/components/AddOrEditVMVolume/index.js`
- 实现内容：
  - 只展示 `RWX` 存储类型
  - 根盘和数据盘都复用该过滤结果
- 验收标准：
  - UI 中看不到非 `RWX` 存储类型
  - 无 `RWX` 时提示并禁止提交

#### Task 1.2: 提交根盘/数据盘存储配置

- 仓库：rainbond-ui
- 文件：
  - `src/services/createApp.js`
  - `src/components/ImageVirtualMachineForm/index.js`
- 实现内容：
  - `vm_run` 请求体新增 `root_disk / data_disks`
- 验收标准：
  - 提交请求包含根盘和数据盘的存储类型

### Sprint 2: Console 校验与落盘

#### Task 2.1: 校验 VM RWX 存储类型

- 仓库：rainbond-console
- 文件：
  - `console/views/app_create/vm_run.py`
  - `console/services/app_config/volume_service.py`
- 实现内容：
  - 校验根盘和数据盘 `volume_type` 是否为 `RWX`
- 验收标准：
  - 非 `RWX` 存储请求被拒绝

#### Task 2.2: 创建 VM 根盘和数据盘卷记录

- 仓库：rainbond-console
- 文件：
  - `console/views/app_create/vm_run.py`
  - `console/services/app.py`
  - `console/services/virtual_machine.py`
- 实现内容：
  - 创建 VM 组件后，补齐根盘和数据盘 `TenantServiceVolume`
- 验收标准：
  - 数据库中根盘和数据盘带有正确 `volume_type/access_mode/volume_provider_name`

### Sprint 3: Worker 同步到底层 PVC

#### Task 3.1: 去掉 VM claim 的 `local-path` 硬编码

- 仓库：rainbond
- 文件：
  - `worker/appm/volume/share-file.go`
  - `worker/appm/volume/volume.go`
- 实现内容：
  - VM 根盘和数据盘 claim 改为使用实际 `volume_type/access_mode`
- 验收标准：
  - 生成的 PVC / DataVolumeTemplate 的 `StorageClassName` 与 UI 选择一致

#### Task 3.2: 增加回归测试

- 仓库：rainbond-console / rainbond / rainbond-ui
- 文件：对应测试文件
- 实现内容：
  - 覆盖 RWX 过滤、console 校验、worker PVC 生成
- 验收标准：
  - 相关测试通过

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| VM 创建入口 | `rainbond-console/console/views/app_create/vm_run.py` | 当前 VM 创建主链路 |
| VM 根盘默认卷创建 | `rainbond-console/console/services/app.py` | 现有 VM 根盘落库入口 |
| 存储类型选项 | `rainbond-console/console/services/app_config/volume_service.py` | 返回 volume-options 并计算 access mode |
| VM 创建页 | `rainbond-ui/src/components/ImageVirtualMachineForm/index.js` | 预配置环境与创建表单 |
| VM 数据盘弹窗 | `rainbond-ui/src/components/AddOrEditVMVolume/index.js` | 高级配置新增磁盘 |
| VM claim 构造 | `rainbond/worker/appm/volume/share-file.go` | 当前 VM 盘 claim 存在 `local-path` 硬编码 |
| 通用 claim 构造 | `rainbond/worker/appm/volume/volume.go` | PVC `StorageClassName` / `AccessMode` 最终生成逻辑 |
| VM 导入模板 | `rainbond/worker/appm/volume/vm_import.go` | DataVolumeTemplate 会继承 claim 配置 |
