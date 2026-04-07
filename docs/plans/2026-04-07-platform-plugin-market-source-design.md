# 平台插件列表改造设计文档

## 一、项目背景
### 1.1 项目架构

当前“平台管理 -> 功能扩展 -> 插件”页面由 `rainbond-ui` 调用 `rainbond-console` 的 `/console/enterprise/{enterprise_id}/regions/{region_name}/platform-plugins` 接口，`rainbond-console` 再聚合授权信息、应用市场信息和 region 已安装插件状态。

当前聚合逻辑的问题是：平台插件列表的主来源仍然是 license 中的 `plugin_mapping`，导致未授权前无法直接展示应用市场中的全部平台插件，也无法稳定展示“免费/商业”标签。

### 1.2 现有基础

- `rainbond-ui`
  - 页面已存在，交互骨架完整
  - 插件卡片、安装确认弹窗、授权弹窗、轮询安装状态已具备
- `rainbond-console`
  - 已存在 `platform_plugin_service` 聚合层
  - 已具备企业 license 查询能力：`license_service.get_license_status`
  - 已具备平台插件安装能力：`install_platform_plugin`
- `rainbond`
  - 已具备 cluster license status 和 plugin install 能力
- `app-store`
  - 已支持识别平台插件（`platform_plugin`）
  - 已支持应用级别 `appLevel=enterprise/free`

### 1.3 核心需求

- 未授权前，平台插件页展示应用市场返回的全部平台插件
- 授权后，仅展示：
  - 免费插件
  - 已授权的企业插件
- 已授权但未包含在授权映射中的企业插件，直接过滤，不展示
- 商业插件安装逻辑保持原有授权约束，不得绕过授权
- 页面交互风格尽量不变，主要替换底层数据源与过滤逻辑

## 二、用户旅程
### 2.1 用户操作流程

- 用户进入“平台管理 -> 功能扩展 -> 插件”
- 系统加载平台插件列表
- 若企业未授权：
  - 页面展示全部应用市场平台插件
  - 免费插件可直接安装
  - 商业插件仍可展示，但点击安装时进入现有授权路径
- 若企业已授权：
  - 页面仅展示免费插件和已授权企业插件
  - 未授权企业插件不展示
- 用户安装插件后，仍通过现有轮询查看安装结果，并进入管理页

### 2.2 页面原型

- 页面入口不变：`平台管理 -> 功能扩展`
- 主要卡片布局不变
- 插件标签由静态“商业”改成动态：
  - `免费`
  - `商业`
- 未授权前不再依赖前端硬编码 `defaultPluginList` 兜底

### 2.3 外部系统交互

- `rainbond-console` 调用 `app-store` 获取平台插件模板列表
- `rainbond-console` 调用 `rainbond` 获取 region license status 和已安装插件状态

## 三、整体架构设计
### 3.1 系统架构图

```text
rainbond-ui
  -> /console/enterprise/{eid}/regions/{region}/platform-plugins
rainbond-console
  -> app-store: 获取平台插件市场列表（全量）
  -> rainbond: 获取 license status / plugin_mapping / access_key
  -> rainbond: 获取已安装 RBDPlugin 列表
  => 聚合为 UI 所需插件卡片列表
```

### 3.2 核心流程

1. `rainbond-console` 从 `app-store` 拉取平台插件全量列表
2. 按 `appLevel` 将插件划分为 `free` 和 `enterprise`
3. `rainbond-console` 从 `rainbond` 获取当前企业在当前集群的 license status
4. 根据授权状态过滤：
   - 未授权：返回全量平台插件
   - 已授权：返回 `free` + `plugin_mapping` 命中的企业插件
5. 合并 region 已安装状态、已安装版本、可升级状态
6. `rainbond-ui` 仅根据聚合结果渲染标签和按钮

## 四、数据模型设计
### 4.1 新增数据库表

无新增表。

### 4.2 数据关系

- `app-store.applications.appLevel`
  - `enterprise` 表示商业插件
  - `free` 表示免费插件
- `app-store.app_versions.template`
  - `platform_plugin.plugin_id` 表示插件唯一标识
- `rainbond license status.bean.plugin_mapping`
  - `plugin_id -> app_key`
  - 代表企业当前被授权的商业插件集合

## 五、API设计
### 5.1 接口列表

- `app-store`
  - 新增或扩展平台插件市场列表接口，返回：
    - `app_key`
    - `plugin_id`
    - `plugin_name`
    - `description`
    - `logo`
    - `latest_version`
    - `app_level`
- `rainbond-console`
  - 保持现有：
    - `GET /console/enterprise/{enterprise_id}/regions/{region_name}/platform-plugins`
    - `POST /console/enterprise/{enterprise_id}/regions/{region_name}/platform-plugins/{plugin_id}/install`

### 5.2 请求/响应结构

- 平台插件列表响应增加/稳定以下字段：
  - `plugin_id`
  - `plugin_name`
  - `description`
  - `logo`
  - `latest_version`
  - `installed_version`
  - `installed`
  - `status`
  - `upgradeable`
  - `team_name`
  - `app_id`
  - `plugin_type`
  - `plugin_views`
  - `app_level`

## 六、核心实现设计
### 6.1 关键逻辑

- `rainbond-console.platform_plugin_service.list_platform_plugins`
  - 将“主数据源”从 `plugin_mapping` 改为 `app-store` 全量平台插件列表
  - `license status` 只负责企业插件过滤和 access_key 获取
- 过滤规则：
  - `license 无效/未授权`：
    - 返回 `free + enterprise`
  - `license 有效/已授权`：
    - `free` 永远展示
    - `enterprise` 仅展示 `plugin_mapping` 命中的插件
- `install_platform_plugin`
  - `free` 插件允许安装
  - `enterprise` 插件必须在 `plugin_mapping` 中

### 6.2 复用现有代码

- 复用 `license_service.get_license_status`
- 复用 `region_api.list_plugins`
- 复用 `market_app_service._create_rbdplugin_if_needed`
- 复用 `rainbond-ui` 现有弹窗和轮询安装状态逻辑

## 七、实施计划
### 跨层覆盖检查

- [ ] Go (rainbond): 不涉及 — 复用现有 license status / plugin install 能力
- [ ] Python (console): 需要 — 改造平台插件聚合逻辑，接应用市场新数据源
- [ ] React (rainbond-ui): 需要 — 动态展示免费/商业标签，沿用现有交互
- [ ] App Store: 需要 — 提供平台插件市场列表所需字段
- [ ] Plugin: 不涉及

### Sprint 1: app-store 平台插件列表能力
#### Task 1.1: 暴露平台插件市场列表
- 仓库：app-store
- 文件：`pkg/app/controller/market_hub.go`、`pkg/app/usecase/market_usecase.go`、`pkg/app/models/application.go`
- 实现内容：
  - 提供可按 `platform_plugin` 过滤的平台插件列表
  - 返回 `appLevel`
  - 返回 `plugin_id`
- 验收标准：
  - console 可以一次性拿到渲染所需插件元数据

### Sprint 2: rainbond-console 聚合逻辑
#### Task 2.1: 平台插件列表主数据源切换
- 仓库：rainbond-console
- 文件：`console/services/platform_plugin_service.py`
- 实现内容：
  - 改为从应用市场全量平台插件列表构建结果
  - 应用授权过滤规则
- 验收标准：
  - 未授权前返回全量平台插件
  - 授权后仅返回免费插件和已授权企业插件

#### Task 2.2: 安装授权兜底
- 仓库：rainbond-console
- 文件：`console/services/platform_plugin_service.py`
- 实现内容：
  - 免费插件可直接安装
  - 企业插件仍需命中授权映射
- 验收标准：
  - 企业插件未授权时不可安装

### Sprint 3: rainbond-ui 展示接入
#### Task 3.1: 插件卡片标签改为动态
- 仓库：rainbond-ui
- 文件：`src/pages/Extension/pluginCapacity/pluginTable.js`
- 实现内容：
  - 按后端返回的 `app_level` 展示 `免费/商业`
  - 未授权前不依赖写死默认列表
- 验收标准：
  - 页面交互不变
  - 标签与过滤结果正确

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| 平台插件聚合 | `rainbond-console/console/services/platform_plugin_service.py` | 当前平台插件列表主逻辑 |
| 授权信息获取 | `rainbond-console/console/services/license.py` | 提供 `plugin_mapping` / `access_key` |
| 平台插件页面 | `rainbond-ui/src/pages/Extension/pluginCapacity/pluginTable.js` | 现有 UI 和安装交互 |
| 应用市场模板列表 | `app-store/pkg/app/controller/market_hub.go` | 现有开放模板列表入口 |
| 平台插件识别 | `app-store/pkg/app/models/application.go` | 已支持 `platform_plugin` 识别 |
