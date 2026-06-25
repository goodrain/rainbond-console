# 证据 → 诊断 → 修法 映射(M0 Dify PoC)

> M0 核心产出:验证"半成品发动机决策树够不够用"。喂给 M1 决策树/skill。

## 映射表

| # | 证据(日志/事件/状态) | 诊断(根因 + RuntimeState) | 文档是否必需 | 修法(MCP 工具 + 参数) | 验证结果 |
|---|------------------------|----------------------------|--------------|--------------------------|----------|
| 1 | `port.k8s_service_name` 回落成 alias(`gr0ba162`) | K8s 原生模式下组件互访用内部域名;`add` 不认 `k8s_service_name` | 否(平台知识) | `manage_component_ports operation=update_alias` 带 `k8s_service_name` + `port_alias` | 内部域名 = `db-postgres` 等,host 重指向消解 |
| 2 | plugin-daemon `ContainerExitError`,日志 `plugin remote installing host is empty` | 必填 env 缺失 | 否(纯日志) | `manage_component_envs upsert PLUGIN_REMOTE_INSTALLING_HOST=0.0.0.0,PORT=5003` | running |
| 3 | plugin-daemon 日志 `database "dify_plugin" does not exist` 随后 `db initialized`/`migration completed` | **假阳性**:daemon 自建库 | 否 | 无需修 | 自愈 running |
| 4 | api 日志 `Database migration successful!` + gunicorn `Listening 0.0.0.0:5001` | api 正常 | 否 | 无 | `/health` ok |
| 5 | api 日志 `Control server error: Permission denied: '/home/dify'` | 存储/家目录不可写(砍 init_permissions) | 是(需懂 Dify 存储职责) | 挂可写卷 `/app/api/storage`(part);完整需 chown/fsGroup + api/worker 共享卷 | 部分,登录仍未通 |
| 6 | `login` 401 `Invalid encrypted data`,错/对密码同错 | 系统性解密失败:存储期密钥对损坏 **或** 前端加密协议差异 | 是 | 待:浏览器验证 / 清账号重 setup | 未结 |

## 决策树覆盖度评估(M0 结论)

- **决策树命中且够用**:配置缺失(必填 env)、连接重指向(service-name host)、连接契约(跨 origin 路由)—— 这三类是本次主要阻滞,troubleshooter 决策树能直接分类并给修法方向,且**纯日志/状态即可定位**。
- **预判需纠偏**:plugin_daemon 独立库"会炸"被证伪 → 决策树应增加"先观察组件是否自 provision 依赖,再判定阻滞"的规则,避免误修。
- **文档输入的价值(已修正)**:多数阻滞(配置缺失、连接重指向、跨 origin 路由、依赖未建)靠日志/平台知识即可定位;但**登录 "Invalid encrypted data"(FM-03)纯日志彻底定位不了,必须 WebSearch 源码知识**才知是"前端加密密码、后端拒明文"——否则会误判为存储/SECRET_KEY 并做无用的破坏性修复(差点清库)。→ 结论:**文档/源码获取对"协议级/框架约定级"阻滞不可替代**,对"配置级"阻滞非必需。M1 应:沉淀型 playbook(配置类)+ 按需源码/文档获取(协议类)**双轨**,而非二选一。
- **闭环信号缺口痛感排序(M0 实证)**:
  1. **`get_app_health_overview`(最痛)**:8 组件逐个 `get_component_summary`/`query_components` 才能定位 1 个 abnormal;一次性全组件状态+blocker 价值最高。
  2. **`wait_for_build_completion`(次痛)**:每次 deploy 后靠 `for+sleep+curl /health` 自旋等就绪,无统一构建/部署终态信号。
  3. **`get_config_file_content`+`analyze_env_conflicts`(本轮较低)**:子集砍了 nginx/ssrf 的 .conf 挂载,未触发 config-file 比对;但若正式模版保留 nginx 单入口,该工具会变关键。
- **动作空间结论**:现有 MCP 修复动作工具(envs/ports/dependency/storage/vertical_scale/operate_app)+ 诊断工具(summary/logs/events/pods)**足以驱动整个 loop**;主要缺的是上面 3 个"信号聚合/就绪"工具,而非新的修复动作。
