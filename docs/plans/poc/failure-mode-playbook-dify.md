# Dify 失败模式 Playbook(M0 PoC)

> 来源:2026-06-25 Dify 1.14.2 核心子集(8 服务)在 Rainbond `rainbond`/北京集群、`KUBERNETES_NATIVE_SERVICE` 治理模式、逐组件 image 建模跑通。
> 沉淀进 M1 skill 的失败模式知识库。

## 条目模板

### FM-NN: <一句话症状>
- 症状(证据) / 根因 / RuntimeState 分类 / 修法(MCP 工具+值) / 验证 / 是否需文档 / 人工确认点

---

## 已记录条目

### FM-01: plugin-daemon 启动即退出 exit code 1
- **症状**:`status=abnormal`,事件 `ContainerExitError`;日志 `invalid configuration: plugin remote installing host is empty`。
- **根因**:策展精简 env 时漏了**必填** `PLUGIN_REMOTE_INSTALLING_HOST`(原 compose `=${PLUGIN_DEBUGGING_HOST:-0.0.0.0}`)。
- **RuntimeState**:配置缺失(必填 env 未提供)。
- **修法**:`manage_component_envs` upsert `PLUGIN_REMOTE_INSTALLING_HOST=0.0.0.0` + `PLUGIN_REMOTE_INSTALLING_PORT=5003` → `operate_app deploy`。
- **验证**:重启后日志 `cluster master` + 监听 5003;组件 running。
- **是否需文档**:否,纯日志即定位。
- **人工确认点**:无(低风险 env 补全)。

### FM-02: web→api 浏览器跨 origin 调不通(砍 nginx 的代价)
- **症状**:web、api 各自 200,但浏览器端控制台请求打到 web 自身 origin 的 `/console/api/*` → 无 nginx 路由 → 失败。
- **根因**:原 Dify 用 nginx 单入口反代 `/console/api`→api、`/`→web;子集砍了 nginx,且 `CONSOLE_API_URL` 留空走相对路径。
- **RuntimeState**:连接契约/路由缺失。
- **修法**:web 设 `CONSOLE_API_URL`/`APP_API_URL`=api 外网网关;api 设 `CONSOLE_WEB_URL`/`APP_WEB_URL`=web 外网网关 + `CONSOLE_CORS_ALLOW_ORIGINS=*`/`WEB_API_CORS_ALLOW_ORIGINS=*` → 重部署。
- **验证**:setup/health 经 api 网关 200。
- **是否需文档**:部分,需懂 Dify 的 nginx 反代职责才能正确接线。
- **人工确认点**:URL 形态(跨 origin 直连 vs 后续改回 nginx 单入口模版)。
- **模版启示**:正式模版应保留 nginx 单入口(config-file 挂载 `nginx.conf`),比跨 origin 直连更干净、单 URL。

### FM-03: 登录 "Invalid encrypted data" → 真根因=前端加密密码(已解,需外部知识)
- **症状**:`POST /console/api/login`(curl 明文)401 `Invalid encrypted data`;错/对密码同错;**经 nginx 同源后仍同错** → 排除跨 origin/CORS。
- **真根因(WebSearch 命中)**:Dify 登录端点带 `@decrypt_password_field`,**前端 `encryptPassword` 把密码加密后再发,后端拒绝明文** → curl 发明文必然报此错。源码:`api/controllers/console/auth/login.py`、`wraps.py`。
- **结论**:**curl 永远复现不了登录**(发明文);**浏览器前端会加密 → 登录正常**。早先"砍 init_permissions/存储权限"是误判(`/home/dify` 警告虚惊,不影响登录)。
- **关键纠偏**:这是本轮**唯一一个"纯日志/平台知识定位不了、必须查外部文档/源码"的阻滞** → 印证 M1"文档/源码获取"环节对**协议级**问题有不可替代价值(虽对配置类问题非必需)。
- **RuntimeState**:客户端协议契约(前端加密)。
- **是否需文档**:**是,且不可省** —— 决策树无此知识会误判为存储/SECRET_KEY 问题并做无用的破坏性修复(差点清库重 setup)。
- **模版启示**:验证脚本测登录必须复刻前端加密逻辑(取 pubkey + encrypt),或直接走 UI/E2E,不能用明文 curl 判定登录失败。

### FM-04: web UI "This page couldn't load"(跨 origin 路由 → nginx 单入口解)
- **症状**:直接访问 web 外网地址 `/apps` 浏览器报 "This page couldn't load";web 容器日志干净(Next.js ready 无报错)→ 纯 client 端。
- **根因**:砍 nginx 后 web 与 api 不同 origin,client 端 `CONSOLE_API_URL` 注入/跨 origin 取数失败。
- **修法(Dify 本来设计)**:加 **nginx 单入口**组件(`nginx:1.27-alpine` + **config-file 挂载** `/etc/nginx/conf.d/default.conf` 路由 `/console/api|/api|/v1|/files|/mcp|/e`→api、`/`→web)+ 对外端口 80 + 依赖 nginx→api,web;web/api 的 `CONSOLE_API_URL`/`CONSOLE_WEB_URL` 全指 nginx 外网地址(同源)。
- **验证**:经 nginx `/signin`/`/install` 200 真页面、`/console/api/*` 200、根路径 →`/apps`、`_next` 静态资源正常。
- **是否需文档**:部分(需懂 Dify nginx 反代职责)。
- **模版启示**:**正式模版必用 nginx 单入口**(单 URL、同源、前端加密登录才工作);跨 origin 直连是死路。config-file 挂载是 Dify 模版的必备能力 → 印证 M1 `get_config_file_content` 工具价值。
- **正确入口 URL**:`http://gre6dee1-80-tynwrm27.dev.goodrain.com`(nginx),**不是** web 直连的 3000 地址。

## 预判坑对照(执行后复盘)

| 预判坑 | 是否命中 | 实际 |
|--------|----------|------|
| service-name host 重指向(下划线非法 K8s 名) | ✅ **命中(架构层)** | `db_postgres`/`plugin_daemon`/`ssrf_proxy` 带下划线非法;改连字符 + `update_alias` 设内部域名 + 全量重指向 env 解决。最核心的策展工作。 |
| plugin_daemon 独立库 dify_plugin + 竞态 | ❌ **证伪** | plugin-daemon **自建库自迁移**,不阻滞。 |
| sandbox/ssrf_proxy 网络段 + proxy 变量 | ⚪ 未触发 | 子集砍了 ssrf_proxy;sandbox 免代理起来了;代码节点联网行为待层4验证。 |
| CELERY_BROKER_URL 内嵌 host | ✅ 已消解 | host=`redis` 无下划线,免密后 `redis://redis:6379/1` 直接可用。 |
