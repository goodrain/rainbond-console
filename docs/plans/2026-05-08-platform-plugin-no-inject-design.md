# 平台插件发布支持“不注入”设计文档

## 一、项目背景
### 1.1 项目架构

当前平台插件模板的发布链路分为三层：

- `rainbond-ui`
  - 应用发布页面负责采集“平台插件”元数据
  - 表单中通过 `inject_position` 决定插件入口挂载位置
- `rainbond-console`
  - 接收发布表单数据，构造 `app_template.platform_plugin`
  - 模板安装时把 `inject_position` 转成 region 侧 `plugin_views`
- `rainbond`
  - 接收 `CreateRBDPluginReq`
  - 把 `plugin_views` 写入 `RBDPlugin.spec.plugin_views`

### 1.2 现有基础

- `rainbond-ui`
  - 已支持“作为平台插件发布”
  - 已有 `Platform / Team / Application / Component` 四种注入位置
  - 当前校验要求至少选择一个注入位置
- `rainbond-console`
  - 已支持在分享模板时把平台插件信息写入 `app_template.platform_plugin`
  - 已支持模板安装时把 `inject_position` 原样传给 region `plugin_views`
- `rainbond`
  - `plugin_views` 已支持空数组
  - 平台插件列表展示不依赖 `plugin_views` 是否非空

### 1.3 核心需求

- 平台插件模板发布时，新增一个“`不注入`”选项
- 选择“`不注入`”后：
  - 仍然按平台插件模板发布
  - 仍然出现在平台插件列表中
  - 不在平台、团队、应用、组件任一页面显示入口
- 其他平台插件字段保持不变，仍然照常填写

## 二、用户旅程（MUST）
### 2.1 用户操作流程

- 用户在应用发布页勾选“平台插件”
- 用户填写 `plugin_id / plugin_name / plugin_type / frontend_component / entry_path / menu_title / route_path`
- 用户在“注入位置”中选择：
  - 常规入口位置：`Platform / Team / Application / Component`
  - 或 `不注入`
- 若选择 `不注入`：
  - 表单自动清空其他入口位置
  - 仍允许继续发布
- 模板安装后：
  - 插件仍在平台插件列表可见
  - 不会在任何页面宿主位置自动展示入口

### 2.2 页面原型

- 页面入口不变：应用发布流程第一页
- 涉及 UI 位置：
  - `rainbond-ui/src/pages/Group/components/AppPublishSetting.js`
  - `rainbond-ui/src/pages/Group/components/AppShareBase.js`
- 交互变更：
  - “注入位置”增加 `不注入`
  - `不注入` 与其他位置互斥
  - 编辑已有空注入配置时，回显为 `不注入`

### 2.3 外部系统交互

- 无新增第三方交互
- 现有链路保持：
  - `rainbond-ui` → `rainbond-console`
  - `rainbond-console` → `rainbond` region API

## 三、整体架构设计
### 3.1 系统架构图

```text
rainbond-ui
  -> 发布表单 inject_position
  -> 选择“不注入”时转换为空数组 []
rainbond-console
  -> app_template.platform_plugin.inject_position = []
  -> 安装模板时传给 region plugin_views = []
rainbond
  -> RBDPlugin.spec.plugin_views = []
  -> 无任何页面入口，但插件 CR 和平台插件列表仍存在
```

### 3.2 核心流程

1. UI 表单新增 `NoInject` 视图态选项，仅用于页面交互
2. 提交前把：
   - `["NoInject"]` 归一化为 `[]`
   - 与其他位置混选的情况归一化为仅保留 `NoInject` 的语义
3. console 在构建 `platform_plugin` 模板时再次规范化，确保最终持久化为 `[]`
4. 模板安装时，console 继续把 `[]` 传给 region `plugin_views`
5. region 侧维持现有语义：空 `plugin_views` 表示不挂载到任何宿主页面

## 四、数据模型设计
### 4.1 新增数据库表

无新增表。

### 4.2 数据关系

- UI 表单态：
  - 新增哨兵值 `NoInject`，仅在 `rainbond-ui` 内部使用
- 模板持久化态：
  - `app_template.platform_plugin.inject_position`
  - 允许空数组 `[]`
- 安装态：
  - `CreateRBDPluginReq.plugin_views`
  - `RBDPlugin.spec.plugin_views`
  - 允许空数组 `[]`

## 五、API设计
### 5.1 接口列表

接口保持不变：

- `POST /console/teams/{team_name}/apps/{app_id}/share/{share_id}/two`
- `POST /v2/tenants/{tenant_name}/plugins`

### 5.2 请求/响应结构

#### UI -> console

平台插件开启且选择“`不注入`”时，提交结构为：

```json
{
  "app_version_info": {
    "is_platform_plugin": true,
    "plugin_id": "demo-plugin",
    "plugin_name": "demo-plugin",
    "plugin_type": "JSInject",
    "frontend_component": "demo-frontend",
    "entry_path": "/static/main.js",
    "inject_position": [],
    "menu_title": "Demo",
    "route_path": "/plugins/demo"
  }
}
```

#### console -> rainbond

```json
{
  "plugin_id": "demo-plugin",
  "plugin_views": []
}
```

## 六、核心实现设计
### 6.1 关键逻辑

- `rainbond-ui`
  - 在 `AppPublishSetting` 中定义注入位置选项常量
  - 新增 `normalizeInjectPositionForSubmit()` 与 `normalizeInjectPositionForDisplay()`
  - 在选择器 `onChange` 中处理 `NoInject` 与其他选项互斥
  - 在 `handleModeSubmit` 中统一把 `NoInject` 转成 `[]`
  - 在发布完成态检查中，把“非空常规位置”或“选择了 `NoInject`”都视为已完成
- `rainbond-console`
  - 在 `share_services` 中新增 `normalize_platform_plugin_positions()`
  - 构造 `platform_plugin` 模板时统一使用规范化后的结果
  - 防止未来有其他客户端直接传入 `["NoInject"]`

### 6.2 复用现有代码

- 复用现有 `platform_plugin` 模板结构，不新增字段
- 复用现有 `market_app_service._create_rbdplugin_if_needed()` 的空数组透传逻辑
- 复用现有 `platform_plugin_service` 的平台插件列表逻辑，不新增过滤规则

## 七、实施计划
### 跨层覆盖检查（MUST）

- [ ] Go (rainbond): 不涉及 — 现有 `plugin_views=[]` 语义可复用，仅做兼容验证
- [ ] Python (console): 需要 — 归一化 `inject_position` 并补测试
- [ ] React (rainbond-ui): 需要 — 新增 `不注入` 交互、回显、提交归一化、完成态校验
- [ ] Plugin: 不涉及

### Sprint 1: UI 交互与提交归一化
#### Task 1.1: 平台插件注入位置支持“不注入”
- 仓库：`rainbond-ui`
- 文件：
  - `src/pages/Group/components/AppPublishSetting.js`
  - `src/pages/Group/components/AppShareBase.js`
  - `src/locales/zh-CN/app.js`
  - `src/locales/en-US/app.js`
- 实现内容：
  - 增加 `不注入` 选项
  - 实现互斥逻辑、编辑态回显、提交前归一化
  - 调整平台插件完成态校验
- 验收标准：
  - `NoInject` 只在前端表单层存在
  - 提交给 console 的 `inject_position` 为 `[]`
  - `yarn build` 通过

### Sprint 2: Console 模板归一化与测试
#### Task 2.1: 分享模板时规范化平台插件注入位置
- 仓库：`rainbond-console`
- 文件：
  - `console/services/share_services.py`
  - `console/tests/service_share_test.py`
- 实现内容：
  - 新增归一化函数
  - 构造 `platform_plugin` 时统一清洗 `inject_position`
  - 增加“空数组不注入”测试
- 验收标准：
  - 模板中的 `platform_plugin.inject_position` 正确落为 `[]`
  - 相关测试通过

### Sprint 3: 跨仓库联动验证
#### Task 3.1: 平台插件安装与列表兼容验证
- 仓库：`rainbond-console` / `rainbond-ui`
- 文件：
  - `console/services/market_app_service.py`
  - `src/pages/Extension/pluginCapacity/pluginTable.js`
- 实现内容：
  - 只做兼容性确认，避免误改现有管理入口逻辑
  - 确认空 `plugin_views` 不影响平台插件列表展示
- 验收标准：
  - 平台插件列表仍可看到已安装插件
  - 页面宿主入口不出现

## 八、关键参考代码
| 功能 | 文件 | 说明 |
|------|------|------|
| 平台插件发布表单 | `rainbond-ui/src/pages/Group/components/AppPublishSetting.js` | 平台插件字段采集与提交 |
| 发布完成态校验 | `rainbond-ui/src/pages/Group/components/AppShareBase.js` | 当前要求必须选中注入位置 |
| 平台插件模板构造 | `rainbond-console/console/services/share_services.py` | `platform_plugin` 写入模板的主入口 |
| 模板安装创建 RBDPlugin | `rainbond-console/console/services/market_app_service.py` | `inject_position -> plugin_views` 透传 |
| RBDPlugin 视图定义 | `rainbond/api/model/model.go` | `CreateRBDPluginReq.PluginViews` |
