# Rainbond VM qcow2 根盘导入修复设计文档

## 一、项目背景
### 1.1 项目架构

当前 Rainbond 虚拟机创建链路如下：

```text
rainbond-ui
  -> rainbond-console
    -> rainbond
      -> KubeVirt / CDI
```

创建 VM 时，console 负责确定镜像来源与运行时属性，region 负责把服务模型转换为 KubeVirt `VirtualMachine`。现有实现同时承载两种启动语义：

- ISO / 安装介质：空白根盘 + `CDROM`
- 已安装系统盘：应直接从导入后的根盘启动

问题在于当前 qcow2 根盘仍被错误落成“空白根盘 + 光驱镜像”，导致外部平台导出的 qcow2 在 Rainbond 中无法直接启动。

### 1.2 现有基础

- `rainbond-console`
  - `console/views/app_create/vm_run.py` 已能基于资产、模板、URL、上传创建 VM
  - `console/services/virtual_machine.py` 已持久化 `vm_boot_mode` 与 `vm_disk_imports`
  - `resolve_vm_boot_source()` 已对 HTTP qcow2 做“内部化启动源”判断
- `rainbond`
  - `worker/appm/volume/vm_import.go` 已支持将数据盘导入为 CDI `DataVolume`
  - `worker/appm/volume/share-file.go` 已根据 `/disk`、`/cdrom` 生成 KubeVirt 磁盘
  - `worker/appm/conversion/version.go` 已把 `vmimage` 统一挂为 `CDROM`

### 1.3 核心需求

- 通过外部平台导出的 qcow2 创建 VM 时，必须生成真正可启动的 root disk
- ISO 场景保持现有行为不变
- 根盘与数据盘的导入语义统一到 `vm_disk_imports`
- `vm_boot_mode` 在 qcow2 场景继续生效，UEFI 镜像可正常启动

## 二、用户旅程（MUST — 禁止跳过）
### 2.1 用户操作流程

- 用户在“创建虚拟机”中选择已有 VM 资产、模板版本、上传文件或远程 URL
- 如果来源是 qcow2 根盘，系统应把它视作“已安装系统盘”，创建后可直接开机
- 如果来源是 ISO，系统仍按“安装介质”创建，允许用户进安装流程
- 用户开机后：
  - qcow2 场景直接进入已安装系统
  - ISO 场景进入安装介质或空盘安装流程

### 2.2 页面原型

本次不新增页面，仅修正现有创建页的后端落地语义：

- `rainbond-ui/src/pages/Create/virtual-machine.js`
- `rainbond-ui/src/components/ImageVirtualMachineForm/index.js`

界面层不需要新增表单项，仍复用现有镜像来源、boot mode 等配置。

### 2.3 外部系统交互

- `rainbond-console` 调用 `rainbond` 既有 VM 创建链路
- `rainbond` 调用 CDI `DataVolume` 导入 HTTP qcow2
- `rainbond` 调用 KubeVirt `VirtualMachine` 创建 VM

本次不引入新的第三方系统。

## 三、整体架构设计
### 3.1 系统架构图

```text
VM source (asset/template/url/upload)
  -> console determines source semantics
  -> save vm_runtime attrs + vm_disk_imports
  -> region volume builder resolves root/data disk imports
  -> KubeVirt VM
       |- root DataVolume (qcow2)
       |- data DataVolume(s)
       |- optional vmimage CDROM (ISO only)
```

### 3.2 核心流程

#### qcow2 根盘创建

1. console 识别根盘来源为 qcow2 / 远程磁盘资产
2. console 持久化 root disk 对应的 `vm_disk_imports`
3. region 创建 `/disk` 根盘时优先使用 root import 配置
4. region 生成 `DataVolume(HTTP)` 作为 root disk，并设为 `bootOrder: 1`
5. 仅当启动源明确是 ISO / 安装介质时，才附加 `vmimage` `CDROM`

#### ISO 创建

1. console 不生成 root disk import
2. region 根盘仍创建 `Blank` `DataVolume`
3. `vmimage` 继续挂为 `CDROM`

## 四、数据模型设计
### 4.1 新增数据库表

本次不新增数据库表。

### 4.2 数据关系

继续复用 `ComponentK8sAttributes`：

- `vm_boot_mode`
- `vm_disk_imports`
- `vm_disk_layout`

调整点：

- `vm_disk_imports` 不再只承载数据盘导入信息，也承载 root disk 导入信息
- root disk 的 `volume_name` 使用现有根盘卷名，确保 region 可直接命中

## 五、API设计
### 5.1 接口列表

本次不新增 API，修正既有创建链路语义：

- `POST /console/teams/{team}/apps/vm_run`
- region 既有 VM 创建链路

### 5.2 请求/响应结构

不修改外部接口协议。

内部语义调整：

- 当创建来源是 qcow2 根盘时，console 额外写入 root disk 的 `vm_disk_imports`
- 当创建来源是 ISO 时，不写 root import，保持旧行为

## 六、核心实现设计
### 6.1 关键逻辑

#### 1. console 为根盘保存导入配置

- 在 `vm_run.py` 的模板实例化、资产实例化、URL/上传实例化路径中，统一区分：
  - `ISO / 安装镜像`
  - `qcow2 / 已安装根盘`
- 对 qcow2 根盘，构造 root disk import 项并持久化到 `vm_disk_imports`
- 对模板创建：
  - `data_disks` 继续复用原逻辑
  - `root` 也进入统一导入配置

#### 2. region 根盘优先消费 import config

- `buildVMVolumeSource()` 已支持 import config 优先级
- 只需确保 `/disk` 根盘能拿到正确的 import config，就会创建 `DataVolume(HTTP)` 而不是 `Blank`
- 对没有 import config 的 `/disk` 继续保留 `Blank` 逻辑，兼容 ISO

#### 3. 仅 ISO 场景挂载 vmimage CDROM

- `version.go` 不再无条件追加 `vmimage`
- 需要根据启动源语义决定是否挂载 `vmimage`：
  - ISO：保留 `ContainerDisk + CDRom`
  - qcow2 根盘：不追加 `vmimage`

#### 4. boot mode 保持闭环

- 继续复用现有 `vm_boot_mode`
- qcow2 根盘场景中，若为 `uefi`，由 `applyVMBootMode()` 生效

### 6.2 复用现有代码

- 复用 `vm_disk_imports`，不新增新的根盘导入字段
- 复用 `buildVMVolumeSource()` 的 HTTP import 行为
- 复用 `applyVMBootMode()` 的 EFI/BIOS 切换

## 七、实施计划
### 跨层覆盖检查（MUST）
- [x] Go (rainbond): 需要 — 修正 VM conversion 对 `vmimage` 的挂载条件，并补 root import 回归测试
- [x] Python (console): 需要 — 为 qcow2 根盘创建写入 root `vm_disk_imports`，并补模板/资产实例化测试
- [ ] React (rainbond-ui): 不涉及 — 不改页面与请求结构
- [ ] Plugin: 不涉及

### Sprint 1: 修复 qcow2 根盘启动链路

#### Task 1.1: 为 qcow2 根盘持久化 root import 配置
- 仓库：rainbond-console
- 文件：
  - `console/views/app_create/vm_run.py`
  - `console/services/virtual_machine.py`
  - `console/tests/vm_template_instantiation_test.py`
- 实现内容：
  - 模板、资产、URL/上传创建路径为 root disk 写入 `vm_disk_imports`
  - ISO 路径保持不写 root import
- 验收标准：
  - qcow2 创建请求会生成 root import
  - ISO 创建请求不会生成 root import

#### Task 1.2: region 仅在 ISO 场景挂载 vmimage
- 仓库：rainbond
- 文件：
  - `worker/appm/conversion/version.go`
  - `worker/appm/volume/vm_import_test.go`
  - `worker/appm/conversion/version_vm_test.go`
- 实现内容：
  - 根据 root import / 启动源语义决定是否追加 `vmimage` `CDROM`
  - 覆盖 qcow2 与 ISO 两条路径的测试
- 验收标准：
  - qcow2 场景 VM 不再出现 `Blank root + CDRom vmimage`
  - ISO 场景行为保持兼容

#### Task 1.3: 端到端回归验证
- 仓库：rainbond、rainbond-console
- 文件：
  - 现有相关测试文件
- 实现内容：
  - 执行 Go 单测、`go vet ./...`、`go build ./...`
  - 执行 Django 对应 VM 创建回归测试
- 验收标准：
  - 新旧场景测试均通过
  - 无新增编译与静态检查错误

## 八、关键参考代码
| 功能 | 文件 | 说明 |
|------|------|------|
| VM 创建入口 | `rainbond-console/console/views/app_create/vm_run.py` | 决定根盘与模板/资产实例化路径 |
| VM 运行时属性服务 | `rainbond-console/console/services/virtual_machine.py` | 持久化 `vm_disk_imports` 与 `vm_boot_mode` |
| 根盘/DataVolume 导入 | `rainbond/worker/appm/volume/vm_import.go` | `/disk` 无 import 时会回退为 `Blank` |
| VM 卷与磁盘装配 | `rainbond/worker/appm/volume/share-file.go` | 负责 `/disk`、`/cdrom` 到 KubeVirt 磁盘的映射 |
| VM 转换与 vmimage 挂载 | `rainbond/worker/appm/conversion/version.go` | 当前固定追加 `vmimage` `CDROM` |
