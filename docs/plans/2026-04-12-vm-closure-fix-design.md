# Rainbond VM 闭环修复设计文档

## 一、项目背景
### 1.1 项目架构

本次修复覆盖 Rainbond 虚拟机现有功能在以下三层的调用链：

```text
rainbond-ui
  -> rainbond-console
    -> rainbond
      -> KubeVirt / CDI / Multus
```

现有实现已经具备虚拟机创建、暂停恢复、VNC、导出到镜像组、保存模板、模板实例化、固定 IP、GPU/USB 等能力入口，但三层之间仍存在语义错配、错误处理缺失、运行时属性未真正落地的问题。

### 1.2 现有基础

当前已经存在的能力基础：

- `rainbond-ui`
  - 创建虚拟机页面
  - 组件详情页 / 侧边栏中的虚拟机操作入口
  - 模板中心与模板实例化入口
- `rainbond-console`
  - `VirtualMachineImage` / `VMTemplate` / `VMTemplateVersion` / `VMTemplateDisk`
  - 虚拟机运行时属性持久化到 `ComponentK8sAttributes`
  - VM 导出、模板、模板实例化服务逻辑
- `rainbond`
  - VM export / snapshot / capability controller & handler
  - worker 侧 KubeVirt workload conversion
  - VM 固定 IP / GPU / USB / 数据盘导入处理

### 1.3 核心需求

本次只做“现有虚拟机功能闭环修复”，不新增新的业务能力，不做历史代码大重构。

修复目标：

- 虚拟机创建可正常使用
- 暂停 / 恢复结果真实，不允许假成功
- VNC 入口保持正常
- “导出到镜像组”和“保存模板”语义明确、入口一致
- 模板实例化可继承并真正应用运行时配置
- fixed IP、boot mode、probe 等关键能力落到 region 生成物

---

## 二、用户旅程（MUST — 禁止跳过）
### 2.1 用户操作流程

用户当前主要通过以下路径使用虚拟机能力：

1. 在创建页通过公共镜像、URL、上传、已有资产或模板版本创建虚拟机
2. 在组件详情页或侧边栏执行：
   - 暂停 / 恢复
   - 打开 VNC
   - 导出到镜像组
   - 保存为模板
3. 在模板中心查看模板详情，并基于模板版本再次创建虚拟机

本次修复后，用户应该得到的结果：

- 点击“导出到镜像组”时，一定创建导出资产，而不是误保存模板
- 点击“保存为模板”时，一定创建模板版本，而不是创建导出资产
- pause / unpause 失败时，界面收到真实失败，不再显示“操作成功”
- 从模板创建出的 VM，网络、boot mode、GPU/USB、probe 等配置能够真正生效

### 2.2 页面原型

本次不新增页面，修正现有页面行为：

- `rainbond-ui/src/pages/Create/virtual-machine.js`
- `rainbond-ui/src/components/ImageVirtualMachineForm/index.js`
- `rainbond-ui/src/pages/Component/index.js`
- `rainbond-ui/src/components/SlidePanel/components/components.js`
- `rainbond-ui/src/pages/VMTemplateCenter/index.js`

关键交互：

- 创建页：
  - 选择镜像来源
  - 配置网络 / GPU / USB / fixed IP
  - 通过模板快速实例化
- 组件详情页 / 侧边栏：
  - VM 暂停 / 恢复
  - VNC 跳转
  - 导出资产
  - 保存模板
- 模板中心：
  - 查看模板版本与磁盘布局
  - 重试模板版本
  - 用模板版本创建 VM

### 2.3 外部系统交互

本次涉及的外部系统交互：

- `rainbond-console` 调用 `rainbond` region API
- `rainbond` 调用：
  - KubeVirt `VirtualMachine` / `VirtualMachineInstance`
  - KubeVirt snapshot
  - CDI `DataExport` / `DataVolume`
  - Multus `network-attachment-definitions`
- 浏览器通过 VNC URL 打开 VM 控制台

本次不涉及 webhook、回调、第三方 SaaS 集成。

---

## 三、整体架构设计
### 3.1 系统架构图

```text
UI Action
  -> console View
    -> console Service
      -> region API
        -> rainbond Controller / Handler
          -> worker conversion
            -> KubeVirt workload
```

### 3.2 核心流程

本次重点修复四条链路：

1. VM 导出资产
   - UI 导出按钮
   - console `AppVMExportView`
   - rainbond `vm-exports`

2. VM 保存模板
   - UI 模板保存入口
   - console `AppVMTemplateView`
   - snapshot + export 组合逻辑

3. VM pause / unpause
   - UI 操作入口
   - console `PauseAppView` / `UNPauseAppView`
   - rainbond pause / unpause handler

4. VM 创建 / 模板实例化
   - UI 提交 runtime config
   - console 持久化 k8s attrs
   - rainbond hydrate attrs
   - worker 生成正确的 KubeVirt workload

---

## 四、数据模型设计
### 4.1 新增数据库表

本次不新增数据库表。

### 4.2 数据关系

继续复用现有模型：

- `VirtualMachineImage`
- `VMTemplate`
- `VMTemplateVersion`
- `VMTemplateDisk`
- `ComponentK8sAttributes`

重点修正以下字段的消费闭环：

- `vm_boot_mode`
- `vm_disk_layout`
- `vm_network_mode`
- `vm_network_name`
- `vm_fixed_ip`
- `vm_gateway`
- `vm_dns_servers`
- `vm_os_family`
- `vm_os_name`
- `vm_gpu_enabled`
- `vm_gpu_resources`
- `vm_gpu_count`
- `vm_usb_enabled`
- `vm_usb_resources`
- VM probe 相关属性

---

## 五、API设计
### 5.1 接口列表

本次不新增公开 API，修正现有接口行为与语义：

#### console API

- `POST /console/teams/{team}/apps/{serviceAlias}/vm-export`
- `GET /console/teams/{team}/apps/{serviceAlias}/vm-export`
- `POST /console/teams/{team}/apps/{serviceAlias}/vm-templates`
- `POST /console/teams/{team}/apps/{serviceAlias}/pause`
- `POST /console/teams/{team}/apps/{serviceAlias}/unpause`
- `POST /console/teams/{team}/apps/vm_run`
- `GET /console/teams/{team}/vm/capabilities`
- `GET /console/teams/{team}/vm/templates/{template_id}`

#### region API

- `POST /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports`
- `GET /v2/tenants/{tenant}/services/{serviceAlias}/vm-exports/{export_id}`
- `POST /v2/tenants/{tenant}/services/{serviceAlias}/vm-snapshots`
- `POST /v2/tenants/{tenant}/services/{serviceAlias}/pause`
- `POST /v2/tenants/{tenant}/services/{serviceAlias}/un_pause`

### 5.2 请求/响应结构

本次不做大范围协议改动，重点修正：

- UI 不再把“导出资产”和“保存模板”混成一个操作
- console 对 region 失败结果做真实映射，不再无条件返回成功
- runtime attr 中已有的 `vm_boot_mode` 被真正透传到 region conversion

---

## 六、核心实现设计
### 6.1 关键逻辑

#### 1. UI 操作语义统一

- 组件详情页的“导出到镜像组”入口改为调用 `startVMExport`
- 模板保存入口只调用 `saveVMTemplate`
- 详情页与侧边栏行为保持一致
- 为导出 / 模板保存补失败分支，避免 Promise 卡住或 UI 无反馈

#### 2. console 真实透传 VM 状态操作结果

- `PauseAppView` / `UNPauseAppView` 必须消费 `app_manage_service.pause()` / `un_pause()` 返回的状态码
- region 失败时返回对应失败响应，而不是固定 200
- 保持原有 UI 契约，不新增额外返回结构

#### 3. rainbond 修复 VM probe 逻辑

- 修正 readiness / liveness 赋值对调
- 修复 `createVMProbe` 读取 attribute 时 nil 指针反序列化问题
- 保证：
  - 直接存储的 VM probe attr 可用
  - fallback 到 `ServiceProbe` 时语义正确

#### 4. boot mode 闭环修复

- `hydrateVMRuntimeExtensionSet()` 增加 `vm_boot_mode`
- worker conversion 实际消费 `vm_boot_mode`
- 让 console 中保存的 boot mode、模板继承的 boot mode 真正作用到 KubeVirt 生成物

### 6.2 复用现有代码

本次优先复用并修复现有结构，不做大重构：

- 继续使用现有 VM asset / template / runtime attr 模型
- 继续使用现有 controller / service / conversion 分层
- 只修正错配、漏接和错误处理，不新增额外抽象层

---

## 七、实施计划
### 跨层覆盖检查（MUST）

- [x] Go (rainbond): 需要 / 涉及
  - 修 VM probe 逻辑
  - 修 boot mode hydration 与 conversion 落地
  - 增补 Go tests
- [x] Python (console): 需要 / 涉及
  - 修 pause / unpause 假成功
  - 视情况补充 Django tests
- [x] React (rainbond-ui): 需要 / 涉及
  - 修详情页导出按钮错接
  - 对齐侧边栏行为
  - 补失败分支反馈
- [x] Plugin: 不涉及 / 无插件侧改动

### Sprint 1: VM 主链路闭环修复

#### Task 1.1: 修复 UI 详情页 VM 导出入口错配
- 仓库：`rainbond-ui`
- 文件：
  - `src/pages/Component/index.js`
  - `src/models/appControl.js`
- 实现内容：
  - 将详情页“导出到镜像组”改为调用 `startVMExport`
  - 保留模板保存逻辑给正确入口使用
  - 为导出 / 模板保存补失败分支
- 验收标准：
  - 详情页与侧边栏行为一致
  - 导出入口不再误创建模板

#### Task 1.2: 修复 console pause / unpause 假成功
- 仓库：`rainbond-console`
- 文件：
  - `console/views/app_manage.py`
  - `console/services/app_actions/app_manage.py`
- 实现内容：
  - 让 view 读取 service 返回码
  - 失败时返回非 200
- 验收标准：
  - region 失败时 UI 能收到真实失败
  - 成功/失败与真实执行结果一致

#### Task 1.3: 修复 rainbond VM probe 逻辑
- 仓库：`rainbond`
- 文件：
  - `worker/appm/conversion/version.go`
  - 相关 tests
- 实现内容：
  - 修 readiness / liveness 对调
  - 修 `createVMProbe` attribute 反序列化 nil 指针问题
- 验收标准：
  - probe 语义正确
  - attribute / service probe 两种来源都能生效

#### Task 1.4: 修复 boot mode 闭环
- 仓库：`rainbond`
- 文件：
  - `worker/appm/conversion/version.go`
  - 相关 tests
- 实现内容：
  - hydrate `vm_boot_mode`
  - conversion 实际应用 boot mode
- 验收标准：
  - console 已存 `vm_boot_mode` 能被 region 使用
  - 模板实例化继承的 boot mode 真正落地

#### Task 1.5: 关键验证
- 仓库：三仓
- 文件：
  - 对应测试文件
- 实现内容：
  - 补单测
  - 跑 `go build ./...`
  - 跑 `go vet ./...`
  - 跑相关 Django tests
  - 跑 `yarn build`
- 验收标准：
  - 相关测试通过
  - 无明显 API 契约回归

---

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| VM 详情页操作 | `rainbond-ui/src/pages/Component/index.js` | 当前详情页 VM 操作与导出入口 |
| VM 侧边栏操作 | `rainbond-ui/src/components/SlidePanel/components/components.js` | 已有正确导出逻辑参考 |
| VM 创建 | `rainbond-console/console/views/app_create/vm_run.py` | VM 创建与 runtime attr 保存 |
| VM 服务逻辑 | `rainbond-console/console/services/virtual_machine.py` | asset/template/runtime attr 聚合逻辑 |
| VM 暂停恢复 | `rainbond-console/console/views/app_manage.py` | pause / unpause view |
| VM pause service | `rainbond-console/console/services/app_actions/app_manage.py` | region 状态操作封装 |
| VM export controller | `rainbond/api/controller/vm_export.go` | region VM export controller |
| VM worker conversion | `rainbond/worker/appm/conversion/version.go` | VM workload 组装、probe、runtime hydration |

