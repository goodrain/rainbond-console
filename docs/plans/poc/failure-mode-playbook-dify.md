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

### FM-03: 登录 "Invalid encrypted data"(存储权限 / 密钥对;未结)
- **症状**:`POST /console/api/login` 401 `Invalid encrypted data`;错/对密码同错,早于密码校验。
- **根因假设**:① 砍 `init_permissions`(chown 存储)→ api uid 1001 对 `/app/api/storage`(opendal 本地)不可写(佐证启动日志 `Permission denied: '/home/dify'`)→ setup 期租户 RSA 密钥对存坏 → 登录解密失败;**或** ② curl 发明文,而前端对密码做加密(服务端期待密文)。
- **RuntimeState**:存储权限缺失 / 客户端协议差异。
- **已试修法**:给 api 挂可写 `share-file` 卷于 `/app/api/storage` + 重部署 → curl 登录仍失败(现有租户密钥对已坏,需重置才能重生成)。
- **待验证**:浏览器 UI 登录(若前端加密则可能直接成功);或清账号+writable storage 重跑 setup。
- **是否需文档**:是,需懂 Dify 存储/密钥对与 init_permissions 职责。
- **模版启示**:Dify 模版必须保证 `/app/api/storage` 可写且 api/worker **共享**该卷;`init_permissions`(或等价 chown/fsGroup)是必备前置。

## 预判坑对照(执行后复盘)

| 预判坑 | 是否命中 | 实际 |
|--------|----------|------|
| service-name host 重指向(下划线非法 K8s 名) | ✅ **命中(架构层)** | `db_postgres`/`plugin_daemon`/`ssrf_proxy` 带下划线非法;改连字符 + `update_alias` 设内部域名 + 全量重指向 env 解决。最核心的策展工作。 |
| plugin_daemon 独立库 dify_plugin + 竞态 | ❌ **证伪** | plugin-daemon **自建库自迁移**,不阻滞。 |
| sandbox/ssrf_proxy 网络段 + proxy 变量 | ⚪ 未触发 | 子集砍了 ssrf_proxy;sandbox 免代理起来了;代码节点联网行为待层4验证。 |
| CELERY_BROKER_URL 内嵌 host | ✅ 已消解 | host=`redis` 无下划线,免密后 `redis://redis:6379/1` 直接可用。 |
