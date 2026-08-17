# Rainbond 外部遥测开关设计文档

## 一、项目背景

### 1.1 项目架构

Rainbond UI 通过 `rainbond-console` 提供的平台设置接口读取和更新平台级配置。Console 当前存在三类外部遥测出口：Python Sentry SDK、PostHog 后端事件上报，以及 `/console/sentry`、`/console/posthog` 两个浏览器代理接口。

### 1.2 现有基础

- `DISABLE_DEFAULT_APP_MARKET=true` 已作为离线环境总开关。
- `RAINBOND_TELEMETRY_DISABLED=true` 已作为环境变量遥测开关。
- `ConsoleSysConfig` 可保存平台级开关，无需新增数据表。
- 平台管理的“基础设置”已通过 `platform-settings` 接口管理其他平台开关。
- 浏览器慢接口采样已独立实现，采用 1% 采样、1 秒阈值和每分钟最多 10 条限制。

### 1.3 核心需求

平台管理员可以在平台管理的基础设置中关闭 Console 发起的 Sentry 和 PostHog 外部请求。开关默认开启；离线环境变量具有最高优先级；关闭和外部网络异常都不得影响主要产品业务。浏览器直接发送的慢接口采样继续由现有环境变量控制，不纳入本开关。

## 二、用户旅程

### 2.1 用户操作流程

1. 平台管理员进入“平台管理 → 设置 → 基础设置”。
2. 页面展示“后端诊断数据上报”开关，首次使用时默认开启。
3. 管理员关闭开关，页面调用现有平台设置更新接口并提示成功。
4. Console 立即停止 Python Sentry SDK 事件、PostHog 后端事件及两个代理接口的外部请求，无需重启。
5. 管理员重新开启后，后续遥测事件恢复发送。

### 2.2 页面原型

- 页面：平台管理 → 设置 → 基础设置。
- 新增项：后端诊断数据上报。
- 说明：用于改进 Rainbond 产品质量；关闭后不再由 Console 向外部诊断服务发送数据。
- 控件：Ant Design `Switch`，沿用现有设置卡片布局和成功通知。

### 2.3 外部系统交互

- Sentry：Python SDK 和 `/console/sentry` 代理。
- PostHog：Console 后端事件和 `/console/posthog` 代理。
- 浏览器慢接口交易直接发送到 Sentry，不经过 Console，继续服从现有前端环境配置。

## 三、整体架构设计

### 3.1 系统架构图

```text
rainbond-ui 平台设置
        |
        v
platform-settings API
        |
        v
ConsoleSysConfig: EXTERNAL_TELEMETRY_ENABLED (默认 true)
        |
        +--> Sentry before_send: 关闭时丢弃
        +--> Sentry proxy: 关闭时返回 204
        +--> PostHog service: 关闭时不入队
        +--> PostHog proxy: 关闭时返回 200

DISABLE_DEFAULT_APP_MARKET / RAINBOND_TELEMETRY_DISABLED
        +--> 始终覆盖数据库开关并关闭外部遥测
```

### 3.2 核心流程

开关读取优先级为：离线环境变量或全局遥测环境变量关闭 > 数据库开关关闭 > 默认开启。数据库查询只发生在遥测路径，并使用短时进程缓存；普通业务请求不新增配置查询。PostHog 后端发送使用有界、守护线程队列，业务请求只做非阻塞入队，队列满时直接丢弃。

## 四、数据模型设计

### 4.1 新增数据库表

不新增数据库表，不创建迁移。

复用 `console_sys_config`：

| 字段 | 值 |
|------|----|
| key | `EXTERNAL_TELEMETRY_ENABLED` |
| type | `boolean` |
| value | 空 |
| enable | `true` 表示开启，`false` 表示关闭 |
| enterprise_id | 空字符串，作为平台全局配置 |

配置不存在时按开启处理，保证升级兼容和默认开启。

### 4.2 数据关系

该配置是平台全局配置，不与企业数据建立外键关系。平台管理员通过任一当前企业入口管理同一个全局开关。

## 五、API设计

### 5.1 接口列表

- `GET /console/enterprise/{eid}/platform-settings`
  - 响应增加 `enable_external_telemetry`。
- `PUT /console/enterprise/{eid}/platform-settings/update`
  - 请求可选增加 `enable_external_telemetry`。
  - 保持现有 `EnterpriseAdminView` 权限。

### 5.2 请求/响应结构

```json
{
  "enable_external_telemetry": false
}
```

```json
{
  "enable_team_resource_view": false,
  "enable_global_image_registry": true,
  "enable_external_telemetry": false
}
```

## 六、核心实现设计

### 6.1 关键逻辑

- 新增遥测开关服务，负责数据库默认值、环境变量优先级和短时缓存。
- 平台设置接口更新后主动清理缓存，使开关立即生效。
- Sentry `before_send` 在清洗事件前检查运行时开关，关闭时返回 `None`。
- 两个代理在构造上游地址前检查开关，关闭时直接本地返回。
- PostHog `capture` 只进行非阻塞入队；队列满、线程启动失败、外部异常均返回失败但不抛给业务。
- 守护线程负责实际 HTTP 请求，进程退出不等待遥测完成。

### 6.2 复用现有代码

- 复用 `ConsoleSysConfig`。
- 复用 `platform-settings` 接口、DVA effect 和 UI 卡片布局。
- 复用 `DISABLE_DEFAULT_APP_MARKET`、`RAINBOND_TELEMETRY_DISABLED` 环境变量判断。
- 保持现有 Sentry 数据清洗、代理 CORS 返回和 PostHog 属性清洗逻辑。

## 七、实施计划

### 跨层覆盖检查

- [ ] Go (rainbond): 不涉及 - 无 Region API 或 Kubernetes 能力变更。
- [x] Python (console): 需要 - 配置存储、接口、运行时拦截、异步 PostHog 和测试。
- [x] React (rainbond-ui): 需要 - 基础设置开关、service、DVA 状态和国际化。
- [ ] Plugin: 不涉及 - 无插件功能变更。

### Sprint 1: Console 运行时开关

#### Task 1.1: 平台配置与 API

- 仓库：`rainbond-console`
- 文件：`console/services/telemetry_switch.py`、`console/views/platform_settings.py`、`console/tests/platform_settings_test.py`
- 实现内容：默认开启的全局配置读取、更新和缓存失效。
- 验收标准：GET/PUT 支持新字段，离线变量优先级正确。

#### Task 1.2: 遥测出口拦截与异步发送

- 仓库：`rainbond-console`
- 文件：`goodrain_web/sentry_config.py`、`console/services/telemetry.py`、两个代理及相关测试。
- 实现内容：运行时拦截 Sentry/PostHog，PostHog 后端非阻塞发送。
- 验收标准：关闭时无外部请求；网络异常和队列满不影响业务。

### Sprint 2: UI 开关

#### Task 2.1: 平台设置交互

- 仓库：`rainbond-ui`
- 文件：`src/services/platformSettings.js`、`src/models/global.js`、`src/pages/EnterpriseSetting/infrastructure.js`、中英文 locale。
- 实现内容：展示默认开启的开关并保存状态。
- 验收标准：平台管理员可切换，状态正确回显，构建通过。

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| 平台设置接口 | `console/views/platform_settings.py` | 现有平台级配置 GET/PUT |
| 配置存储 | `console/models/main.py` | `ConsoleSysConfig` 模型 |
| 后端 Sentry | `goodrain_web/sentry_config.py` | SDK 初始化和 `before_send` |
| 后端 PostHog | `console/services/telemetry.py` | 后端事件发送 |
| Sentry 代理 | `console/views/sentry_proxy.py` | 浏览器错误代理 |
| PostHog 代理 | `console/views/posthog_proxy.py` | 浏览器 PostHog 代理 |
| 设置页面 | `rainbond-ui/src/pages/EnterpriseSetting/infrastructure.js` | 基础设置卡片 |
| 设置数据流 | `rainbond-ui/src/models/global.js` | DVA effects 和企业状态合并 |
