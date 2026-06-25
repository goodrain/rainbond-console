# M0 实操流水账(Dify PoC)

> 按时间记录:导入 → 部署 → 每轮排障 → 冒烟。每个动作记:做了什么、看到什么、下一步判断。

## 环境

- 集群:region `rainbond`(北京,`172.16.0.2:8443`)
- 团队:**开发环境** `tynwrm27`(team_id `36b48a61e31c4f7f8166577a169d1475`,owner 杨轲)
- 应用:Dify(compose 核心子集 ~9 服务)

## 时间线

<!-- M0 执行时逐条追加,格式:### [步骤] 标题 -->

### 0. 准备

- 团队:开发环境 `tynwrm27`。应用 `dify-poc` app_id **3141** 已创建。
- 抓取 Dify 官方 compose(main,1200 行,`langgenius/dify-api:1.14.2`)到 `/tmp/dify-compose.yaml`。

### 1. 导入前结构性发现(还没部署就印证设计论点)

> **这些是 M0 的核心证据:纯 compose 转译为何转不出"能跑"。**

1. **配置全外置**:compose 用 `x-shared-*` YAML 锚点 + `env_file:` 引用 `./envs/**/*.env` 和 `./.env`(从 `.env.example` 生成,数百变量)。compose 里 `environment:` 块只有少量覆盖项。**连接类关键配置(DB_HOST/PORT/USER/PASS、REDIS_*、CELERY_BROKER_URL、SECRET_KEY、VECTOR_STORE/WEAVIATE_ENDPOINT/API_KEY)全部不在 compose 文件里** → Rainbond 导入器拿不到。
2. **核心服务被 profiles 默认禁用**:`db_postgres`(profile `postgresql`)、`db_mysql`(`mysql`)、`weaviate`(`weaviate`)、`api_websocket`(`collaboration`)、`certbot`、20+ 备选向量库。不激活 profile 就不启动 → 朴素导入会漏掉 DB 和向量库。
3. **反向回调依赖**:`plugin_daemon → DIFY_INNER_API_URL=http://api:5001`、`api → PLUGIN_DAEMON_URL`(互指),`depends_on` 不表达。
4. **plugin_daemon 用独立库** `DB_DATABASE=dify_plugin`(与 api 的 `dify` 不同库)。
5. **ssrf_proxy / nginx 用 `.conf.template` + 挂载脚本 + entrypoint sed 渲染**,非纯镜像即可跑。

**结论(M0 早期)**:必须人工策展一份**自包含子集 compose**(内联具体 env 值、移除 profiles、删备选向量库),才谈得上导入。这正是"部署快照法替用户踩坑"的成本所在。

### 2. 构建自包含子集 compose(进行中)

核心子集 10 服务:api / worker / web / nginx / db_postgres / redis / sandbox / ssrf_proxy / plugin_daemon / weaviate(默认向量库)。从 `.env.example` 解析默认值内联。

### 3. 动作空间发现:MCP 无 compose 上传工具 → 改逐组件建

> **M0 动作空间证据**:`check_yaml_app` 需要的 `compose_id` 只能由 Web UI 上传 compose 生成,**MCP 链路缺"创建 compose 记录"这一步** → 程序化 compose 导入走不通。务实改用 `create_component_from_image` 逐个建 8 组件,用 `manage_*` 配端口/env/依赖。反而更贴合排障 loop 的动作空间(完全绕开 compose 解析器)。

### 4. 逐组件建 8 个(image,is_deploy=false),service_id 映射

| 组件(=内部域名) | image | service_id | 内部端口 |
|------|-------|-----------|---------|
| db-postgres | postgres:15-alpine | `5ba6223cfd0cf48b8579c93d5f0ba162` | 5432 |
| redis | redis:6-alpine | `190f5f0925e67a9201ebb4c371fec4dc` | 6379 |
| weaviate | semitechnologies/weaviate:1.27.0 | `72face3e3a59c3a2359a7a566a0d401b` | 8080 |
| sandbox | langgenius/dify-sandbox:0.2.15 | `8564e30595ae5ee958e13a173c62780f` | 8194 |
| plugin-daemon | langgenius/dify-plugin-daemon:0.6.1-local | `f890ba7e1c3d7768b3729e549a0a10a1` | 5002 |
| api | langgenius/dify-api:1.14.2 | `7d3de5ba1f6da1f6cb7836be0a00e60b` | 5001 |
| worker | langgenius/dify-api:1.14.2 | `f5a503b60d4a96d66719d71442cde9c9` | 无 |
| web | langgenius/dify-web:1.14.2 | `ce62ec49d868b5ade80585aea3e49f17` | 3000 |

> 关键:各组件对内端口的 `k8s_service_name` 精确设为上表"内部域名",消解预判坑#1(下划线→连字符 host 重指向)。

### 5. 配置接线(动作空间实录)

- **内部域名**:`add` 端口忽略传入 `k8s_service_name`(回落成 alias),需再用 `update_alias`(action=`change_port_alias`,带 `k8s_service_name`)才改成功。→ **动作空间证据:设内部域名要两步**。
- **redis 免密**:组件从镜像建无法直接传 `--requirepass`,故 redis 不设密码 + 各处省 `REDIS_PASSWORD` + `CELERY_BROKER_URL` 去密码。
- **端口别名占用同名 env**:别名 `SANDBOX` 自动生成 `SANDBOX_PORT`/`SANDBOX_HOST`,upsert 同名 env 报 412 已存在 → 需避开。
- **vertical_scale 必须传 `new_gpu=0`**:否则 `container_gpu cannot be null` 500。→ 动作空间坑。
- 内存:api 2G、worker 1G(防 OOM);其余默认 512MB。
- 对外端口:web:3000、api:5001(经 Rainbond 网关)。

### 6. 首轮部署(2026-06-25)

- `operate_app(deploy)` 8 组件,构建事件全部 success(开始拉镜像)。
- **预判会炸**:plugin-daemon 连 `dify_plugin` 库,但 db-postgres 只建 `dify` → 预计起不来(坑#2)。
- **待观察**:无 nginx 时 web→api 同源路由;sandbox 无 ssrf_proxy 联网。

### 7. 首轮部署结果:7/8 直接 running,1 个阻滞

- **api**:迁移成功(`Database migration successful!`),gunicorn 监听 5001。⚠️ 非致命警告 `Permission denied: '/home/dify'`(原 compose 靠 init_permissions 容器 chown,被砍),待观察是否影响插件功能。
- **plugin-daemon**:`abnormal`,exit code 1。

### 8. 排障 loop 第 1 轮:plugin-daemon 单阻滞

- **证据**:日志 `invalid configuration: plugin remote installing host is empty`。
- **诊断**:策展精简 env 时漏了**必填** `PLUGIN_REMOTE_INSTALLING_HOST`(原 compose 有 `=0.0.0.0`)。RuntimeState=配置缺失。**纯日志即可定位,无需文档。**
- **修法**:`manage_component_envs` 补 `PLUGIN_REMOTE_INSTALLING_HOST=0.0.0.0` + `PLUGIN_REMOTE_INSTALLING_PORT=5003` → 重部署。
- **结果**:plugin-daemon 起来了。

### 9. 预判坑#2 被证伪(重要纠偏)

- plugin-daemon 日志确实先报 `database "dify_plugin" does not exist (SQLSTATE 3D000)`,但**它自己建库 + 迁移**(随即 `dify plugin db initialized` / `database migration completed successfully`),正常成为 cluster master、监听 5003。
- **结论**:plugin-daemon 会 self-provision 独立库,**根本不阻滞**。设计预判的"坑#2 会炸"不成立。→ 写入 playbook 纠偏。

### 10. 全绿 + 可达性验证

- `get_app_detail`:**8/8 running,status=running**。仅一次修复达成全绿。
- api `/health` → `{"status":"ok","version":"1.14.2"}`;`/console/api/setup` → `{"step":"not_started"}`。
- web `/apps` → 200。
- web 访问地址:`http://gre49f17-3000-tynwrm27.dev.goodrain.com`
- api 访问地址:`http://gr00e60b-5001-tynwrm27.dev.goodrain.com`

### 11. 排障 loop 第 2 轮:web→api 跨 origin 路由(回补 nginx gap)

- **问题**:web 与 api 是不同网关 origin,浏览器端 `CONSOLE_API_URL` 空走相对路径 → 无 nginx 单入口时调不到 api。**这是砍 nginx 的已知代价(坑#3 路由侧)。**
- **修法**:web 设 `CONSOLE_API_URL`/`APP_API_URL`=api 外网地址;api 设 `CONSOLE_WEB_URL`/`APP_WEB_URL`=web 外网地址 + `CONSOLE_CORS_ALLOW_ORIGINS=*`/`WEB_API_CORS_ALLOW_ORIGINS=*` → 重部署 web+api。
- **结果**:web/api 各自可达,但浏览器跨 origin 登录暴露新阻滞(见 13)。

### 12. 四层冒烟 · 第 1 层通过

- `POST /console/api/setup`(经 api 外网网关)建管理员 `admin@dify.local` → `{"result":"success"}` 201。
- 证明:外部写路径打通,api↔db 写入正常,网关链路 OK。

### 13. 排障 loop 第 3 轮:登录 "Invalid encrypted data"(未结)

- **证据**:`POST /console/api/login` 401 `{"code":"authentication_failed","message":"Invalid encrypted data"}`,响应 0.003s 无 500 栈。
- **判别测试**:错误密码与正确密码**报同一错** → 系统性解密失败,早于密码校验,非密码问题。`system-features.enable_email_password_login=true`。
- **根因假设(高置信)**:砍掉 `init_permissions` 容器(负责 chown 存储目录)→ api 以 uid 1001 跑、`/app/api/storage`(opendal 本地)不可写(佐证:启动日志 `Permission denied: '/home/dify'`)→ setup 生成的租户 RSA 密钥对存坏 → 登录加载解密失败。
- **拟修法(下一轮)**:给 api(及 worker)在 `/app/api/storage` 挂可写持久存储(`manage_component_storage`,Rainbond 卷默认容器用户可写);必要时清账号重跑 setup 让密钥对重新生成。
- **M0 价值**:坐实"`init_permissions`/存储权限"是 Dify 模版的必备前置 —— 朴素导入/转译绝不会自动补上。

> **M0 阶段性结论**:Dify 8 服务核心子集在 Rainbond 跑通(8/8 running),四层冒烟第 1 层过;排障 loop 3 轮共 3 个阻滞,2 个已清(plugin host、跨 origin 路由),1 个定位待修(存储权限)。决策树对"配置缺失/连接重指向"类阻滞够用且纯日志可定位;尚未遇到"必须查文档才能定位"的阻滞。

### 14. 存储权限修法第 1 步 + 待办

- 给 api 挂 `share-file` RWX 卷于 `/app/api/storage`(volume_id 10592)+ 重部署 → curl 登录仍 `Invalid encrypted data`(现有租户密钥对在只读期已生成坏,挂卷不自愈)。
- **两条待验证路径(交给下一步/用户)**:
  1. **浏览器 UI 登录**:`http://gre49f17-3000-tynwrm27.dev.goodrain.com`,`admin@dify.local` / `Dify123456`。若前端对密码加密,curl 明文失败但浏览器可能直接成功 → 则 FM-03 仅是 curl 测法问题。
  2. 若浏览器也失败:清账号(exec db-postgres 删 accounts/tenants)+ 保持可写存储 → 重跑 `/console/api/setup` 让密钥对重新生成 → 再登录。
- **layers 3–4(知识库索引/代码节点)**:需配置 LLM provider API Key,属用户在 UI 内完成,M0 不代办。
- **api/worker 共享存储**:目前仅 api 挂了卷;Dify 文件存储需 api+worker 共享同一卷,层3验证前需补 worker 挂载同卷。

### 15. 用户反馈驱动的两处修正(2026-06-25)

**(A) 拓扑无依赖边**:用户指出拓扑图 8 组件全绿但**无连线**(只 api/web 连网关)。根因:我全靠"k8s 原生 DNS + 手填 env"接线,**没建 Rainbond 依赖边** → 运行时连通但拓扑不反映关系,**且 share 成模版时依赖结构 capture 不到**(依赖是模版核心价值)。
- 修法:`manage_component_dependency add` 建边:api/worker→db-postgres·redis·weaviate·sandbox·plugin-daemon;plugin-daemon→db-postgres·redis;web→api;nginx→api·web。
- **重要 M0 纪律**:逐组件建模时**必须显式建依赖边**,不能只靠 DNS 连通 —— 否则模版残缺。写入 playbook/M1 skill 硬规则。

**(B) web UI 打不开 + 登录**:见 FM-03 / FM-04。加 nginx 单入口(config-file 挂载路由)修好 web UI;登录 "Invalid encrypted data" 经 WebSearch 定位为**前端加密密码**(curl 明文必败,浏览器正常)。

### 16. 最终拓扑(11 组件,8 核心 + nginx;全 running + 依赖成形)

- 入口:**nginx** 单入口 `http://gre6dee1-80-tynwrm27.dev.goodrain.com`(对外)。
- nginx → api(`/console/api|/api|/v1|/files|/mcp|/e`)、web(`/`)。
- web → api;api/worker → db-postgres·redis·weaviate·sandbox·plugin-daemon;plugin-daemon → db-postgres·redis。
- **四层冒烟**:层1(建号)✅;登录/层2–4 待用户浏览器在 nginx 入口验证(层3–4 需 LLM Key)。

### 17. 登录成功 + 配 API Key 500 → 密钥对丢失(FM-05)

- 用户浏览器经 nginx 入口**登录成功**(层1+2 过),进入设置→模型供应商。
- 配 Xiaomi MiMo API Key → **500 Internal Server Error**(`credentials`/`model-providers`/`llm`/`datasets` 全 500)。
- 栈定位:`PrivkeyNotFoundError: Private key not found, tenant_id 263d3aea...`(`libs/rsa.py:58` ← `opendal_storage.py:50 FileNotFoundError`)。凭据用 PKCS1_OAEP(租户 RSA 公钥)加密。
- 根因:setup 时密钥对写进**非持久临时 fs**,重部署丢失;新持久卷空 → 私钥找不到。**FM-03 担心的存储问题在此真正坐实(咬凭据非登录)。**
- 修法:`rainbond_exec` 进 api pod 跑 `flask reset-encrypt-key-pair`(uid=1001 可写,成功重生成密钥对入持久卷)+ 给 worker `create_mnt` 挂 api 同卷 + 重部署 worker。
- 验证:待用户 UI 重配 API Key。

### 18. 四层冒烟结果(M0 验收)

| 层 | 内容 | 结果 | 证据 |
|----|------|------|------|
| 1 | /install 建号 | ✅ | `POST /console/api/setup` 201 |
| 2 | 登录 + 控制台 + 模型供应商配置 | ✅ | 浏览器经 nginx 登录成功;配 API Key 保存成功(reset-encrypt-key-pair 后凭据加解密通) |
| 4 | 代码节点跑 sandbox | ✅ | `POST .../workflows/draft/run` 200;sandbox `POST /v1/sandbox/run` 200,代码节点 UI 测试成功(用户侧配置后) |
| 3 | 知识库索引 | ⏳ 未做 | 需配 Embedding 模型(MiMo 仅 LLM)或用经济模式;非阻塞,留作可选 |

> **M0 验收结论:达成。** Dify 核心子集在 Rainbond 真正可用——建号、登录、配模型、跑代码节点全通,9 组件 running、nginx 单入口、依赖成形、api/worker 共享持久存储。层3 仅差一个 Embedding 模型,属用户侧配置,不阻塞 M0 结论。

### 19. M3 预验:share→快照→app_template(趁 dify-poc running)

- `create_app_share_record`(scope="")→ share_id 702 → `get_app_share_info` 拿到 runtime 草稿。
- **依赖完整 capture ✅**(因为建了依赖边):api/worker→5依赖、nginx→api·web、web→api、plugin-daemon→db·redis;**worker `mnt_relation` 共享存储、nginx `config-file` 全文**都进模版。→ 坐实"依赖边不建则模版残缺"。
- **本地发布受阻 + 新 MCP 缺口**:`submit_app_share_info` 要 `app_version_info.app_model_id`,但**无"建本地 app_model"的 MCP 工具**(Web 端发布页现建)→ 程序化本地市场发布走不通。与 compose 上传缺口同类,记入 action-space。
- **改走快照路线(MCP 完整)**:`create_app_version_snapshot` 成功 → version_id 492、app_model_id `c56344e369f94b1f05cd99b0468ac198`、arch amd64。这是"部署快照法"的 app_template 工件;`create_app_from_snapshot_version` 可回装验证(未做,避免再起一套 ~6GB)。
- **模版质量隐患(M3 必解)**:模版把 `SECRET_KEY`、`DB_PASSWORD`、inner API Key、WEAVIATE_API_KEY 等**明文冻结**进 env。真正上架必须**密钥参数化**(安装时生成/填写),否则全网用户共享同一套密钥=安全事故。→ M3 设计新增"敏感 env 参数化"环节。
- **入口 URL 写死隐患**:nginx/web/api 的 `CONSOLE_API_URL` 等含本次网关域名 `gre6dee1-80-tynwrm27.dev.goodrain.com`,模版到别的环境会失效 → M3 需把对外 URL 改为安装时回填(留空走相对路径,靠 nginx 单入口同源)。

> **M0 总结(终)**:排障 loop 共 **5 类阻滞**:配置缺失(FM-01)、跨 origin 路由(FM-04)、依赖未建(15A)、登录协议(FM-03)、存储非持久致密钥对丢失(FM-05)。3 类靠日志/平台知识定位,2 类(FM-03/05)需 Dify 框架知识。决策树补强规则:①逐组件必显式建依赖边;②登录类协议查源码、别用明文 curl 误判;③Dify 模版必须持久化 `/app/api/storage` 且 api/worker 共享、保证可写。三个 M1 闭环工具痛感排序:get_app_health_overview > wait_for_build_completion > get_config_file_content。**整条"导入→排障→跑通"耗时主要在策展(理解 Dify 结构 + 接线),验证了'内核是排障调优而非格式转译'的核心假设。**
