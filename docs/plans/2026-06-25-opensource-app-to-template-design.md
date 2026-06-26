# 开源应用自动化转 Rainbond 应用模版 设计文档

> 状态:**M0 实证版 v2** · M0 端到端跑通 + M3 预验证(2026-06-25)
> 日期:2026-06-25
> 主协调:AI(Claude) · 决策:yangk
> 关联记忆:`opensource-app-to-template-initiative`、`rainbond-test-env-topology`、`test-server-build-ops`
> M0 实证记录:`docs/plans/poc/`(run-log / failure-mode-playbook-dify / evidence-diagnosis-fix-map / action-space-inventory)

---

## 一、项目背景

### 1.1 项目架构

跨仓库项目,涉及:

| 仓库 | 角色 | 本项目中的职责 |
|------|------|----------------|
| rainbond-console (Python/Django) | Web 后端 | 新增闭环信号 MCP 工具;复用 share/upgrade/check |
| rainbond (Go) | 核心服务 | 复用 service-check parser、构建、部署、Pod/事件查询 |
| app-store (Go) | 应用市场后端 | 复用 OpenAPI(8080) 上架;`/Users/yangk/go/src/goodrain.com/app-store` |
| Claude skills | 编排层 | troubleshooter/app-assistant 为半成品发动机,新增/扩展排障 loop skill |

### 1.2 现有基础(调研已确认,可复用约 90%)

- **导入+配置提取**:`check` 机制(源码/镜像/compose/helm)已能自动探测端口、env、卷、内存、语言、依赖。`rainbond/builder/parser/parser.go` 的 `ServiceInfo` 即"依赖配置提取器"。
- **运行态→模版快照**:`console/services/share_services.py` 的 `query_share_service_info` + `create_share_info`,把跑通的应用拓扑导出成 `RainbondCenterAppVersion.app_template`(v2 JSON)。
- **上架**:app-store OpenAPI(8080,AccessKey 认证)`createApp → createAppVersion → upShelves` 可程序化。
- **升级**:share→新版本→upgrade diff(`console/services/market_app/property_changes.py`)→部署/回滚,全可程序化。
- **半成品排障发动机**:`~/.claude/skills/rainbond-fullstack-troubleshooter/SKILL.md` 已有 6 态 `RuntimeState` 故障分类决策树、修复动作优先级链(单阻滞最多修一次再验证)、config-file 覆盖 gate、provider/consumer 连接契约纪律。修复动作空间(MCP 工具)齐全:`manage_component_envs / connection_envs / dependency / probe / storage / ports`、`operate_app`、`change_component_image`。诊断证据工具齐全:`get_component_summary / pods / logs / events`、`get_operation_failure_context`。

### 1.3 核心需求

把开源应用(Dify/Harbor 等)自动转成 Rainbond 应用模版,实现闭环:

```
自动寻找 → 部署 → 测试验证 → 上架 → 升级
```

**关键认知(经用户澄清确立):内核不是"格式转译",而是"AI 自动排障调优 loop"——替代人工"看日志+查文档+改配置+重部署"把多组件应用调到能跑。** 两端(导入解析、跑通后快照)现成,中段"让多组件运行时配置真正工作"是全部人工成本所在,是要造的发动机。

**已确立的设计决策:**
1. 走**部署快照法**(部署跑通→现有 share 快照成模版),非转译。
2. 诊断**主动抓上游 README/官方镜像文档**辅助。
3. **半自动起步**:AI 诊断+提方案,关键修复动作人工点确认。
4. 建在现有 MCP + skill 之上,顺带增强这两个能力。
5. PoC 先 **Dify** 后 **Harbor**;运行环境 **当前 MCP 默认集群 `rainbond`/北京**(`172.16.0.2:8443`,v6.9.2,2 节点,**仅 amd64**,空闲 RAM ~42GB / CPU ~25 核,2026-06-25 实测够跑 Dify 核心子集);PoC 由 AI 主导、yangk 旁观确认。
   - **集群决策(2026-06-25 订正)**:原设计假设 bygpu GPU 集群,但当前 MCP 实际指向默认 `rainbond` 集群,且 Dify PoC 不需 GPU,故 M0 直接在此集群进行。多架构(amd64-only 限制)是 M3 议题,不影响 M0/M1。
6. **镜像策略**:发布的模版**默认引用上游多架构原镜像**(保多架构+血缘),验证部署仍沿用内部仓库;离线 bundle(保留 manifest list 的内部同步)列为后续可选,需改 rainbond 核心。详见 6.3。

### 1.4 为什么不走"纯转译"路线(直接 compose/helm → 模版,不部署)

结论:**转译能转出"骨架"(约 80%),但转不出"能跑";而能不能跑,不部署一次无法确认。所以转译不能替代部署,只能当"loop 冷启动加速器"。**

四个决定性理由:

1. **现有的直接导入就是转译,而它正是今天要人工调的那条路。** Rainbond 已有 compose 导入(`check_yaml_app`/`create_app_from_yaml`)和 helm 导入(`check_helm_app`)。"基础解析后运行时配置不工作、需人工按日志+文档调"——就是现有转译路径的产物。再写更聪明的转译器只能把 80% 提到 85~90%,**消除不了调优步骤**。
2. **修复所需信息不在源文件里,或在但需运行才能解读。** 实证(Dify):`CELERY_BROKER_URL` 把 host 嵌在 URL 字符串里(光做语法映射会漏)、`plugin_daemon→http://api:5001` 是反向回调依赖(`depends_on` 不表达)、`dify_plugin` 独立库、migration 竞态、nginx/squid 的 `.conf.template`+envsubst 渲染、ssrf_proxy 专用网络段、凭证一致性——要么不在 compose 里,要么要执行才能确认对错。
3. **"直接可用"无法证伪。** 不装一次就不知道它跑不跑得起来。给市场一个"看着合法、实际起不来"的模版**比没有更糟**——砸的是市场"一键即用"的信任。
4. **价值/难度倒挂。** 转译只搞得定简单应用(用户不痛),恰恰搞不定 Dify/Harbor 这种复杂多组件应用(用户最痛、最有价值)。

> Helm 比 compose 更难:需先 `helm template` 渲染成任意 K8s 资源,再映射到 Rainbond 组件模型——Job(migration)、init container、operator/CRD、sidecar 是有损映射。

**一句话框架:部署快照法 = 我们替用户把坑踩平一次(成本集中在策展时);纯转译 = 把坑留给每个安装的用户(成本分摊到每次安装)。** 目标"让用户装了就能用"要求模版预先验证,故"部署跑通一次"是**产品需求**而非工程麻烦。转译的正确定位见 M3+(可选 importer 优化,永不直接出未验证模版)。

---

## 二、用户旅程

### 2.1 用户操作流程

本项目有两类用户:

**A. 模版策展人(我们/Rainbond 团队 —— 本项目主要服务对象)**
1. 触发:指定一个开源应用来源(compose / helm / 镜像 / git),发起"转模版"流程。v1 形态 = 一次 AI 编排会话(类似本对话),由 skill 驱动 MCP 工具。
2. 调通:AI 进入排障 loop——部署→检测→抓文档→诊断→提修复方案→**(半自动)人工确认关键动作**→应用修复→重部署,直到全绿+对外可访问+冒烟通过。
3. 上架:验证通过后 AI 自动 share 快照成模版 → 推送到目标市场。
4. 复盘:产出该应用的"动作空间清单 + 失败模式 playbook + 验证报告",沉淀进知识库供后续同类应用复用。

**B. 终端用户(平台用户 —— 受益方,本项目不改其体验)**
- 在 Rainbond 应用市场直接用模版一键安装该开源应用,无需手工调依赖配置。

### 2.2 页面原型

**v1 不做新 UI(YAGNI)。** v1 的"界面"是 AI 编排会话 + 现有 Rainbond 控制台(用于人工确认时旁观组件状态)。

后续里程碑(M4/M5 规模化)再评估是否需要:策展任务列表页、转化流水线状态页、模版血缘(上游来源/版本/验证报告)展示页。**本设计不提前实现。**

### 2.3 外部系统交互

- **上游文档源**:GitHub(README/docker-compose)、Docker Hub / 镜像官方文档、应用官方文档站。loop 通过 WebFetch/WebSearch 抓取(skill 能力,非后端代码)。
- **app-store 市场**:通过 OpenAPI(8080,AccessKey)上架。
- **上游版本源(M4)**:镜像 registry tag、helm chart version、git release,用于升级追踪。

---

## 三、整体架构设计

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│  编排层(Claude skill:rainbond-app-to-template)              │
│  导入 → [排障调优 loop] → 验证门禁 → 快照 → 上架            │
│                │                                              │
│        ┌───────┴────────┐                                    │
│        │ 文档知识获取    │ (WebFetch/WebSearch 抓 README/镜像文档) │
│        └───────┬────────┘                                    │
└────────────────┼─────────────────────────────────────────────┘
                 │ MCP 工具调用
┌────────────────┼─────────────────────────────────────────────┐
│  rainbond-console (MCPQueryService)                          │
│  诊断证据工具(现成) + 修复动作工具(现成)                  │
│  + 【新增 3 个闭环信号工具】                                 │
│    wait_for_build_completion / get_app_health_overview /     │
│    get_config_file_content + analyze_env_conflicts           │
│  + 复用 share(快照) / upgrade(升级)                       │
└────────────────┼─────────────────────────────────────────────┘
                 │ HTTP /v2/...
┌────────────────┼──────────────┐   ┌──────────────────────────┐
│  rainbond (Go core)            │   │  app-store (OpenAPI 8080)│
│  check parser / 构建 / 部署    │   │  createApp/Version/上架  │
│  Pod/事件 / etcd 检测结果       │   └──────────────────────────┘
└────────────────────────────────┘
```

### 3.2 核心流程(排障调优 loop)

```
1. 导入        compose/helm/image → check → 创建多组件应用(暂不部署或单副本部署)
2. 文档获取    抓该应用 README/官方镜像文档/env 说明 → 形成"配置预期"
3. 部署        operate_app(deploy)
4. 健康检测    get_app_health_overview → 全组件状态 + critical_blocker
   ├─ 全绿 → 转 6
   └─ 有阻滞 → 5
5. 诊断+修复(半自动)
   a. 收集证据:summary/pods/pod_detail/logs/events/failure_context
   b. 结合文档诊断 → 套用 troubleshooter 决策树分类 RuntimeState
   c. 提出修复方案(改 env/连接变量/依赖/端口/探针/存储/配置文件)
   d. 【人工确认关键动作】→ 应用修复
   e. config 覆盖 gate:挂了配置文件则读内容(get_config_file_content)比对
   f. 重部署 → wait_for_build_completion → 回 4
   g. 收敛保护:同阻滞最多修 N 次、根因性失败(镜像拉不到)立即放弃并报告
6. 验证门禁    健康 + 对外端口可访问探测 + 业务冒烟(应用专属脚本)
7. 快照上架    share → app_template → app-store OpenAPI 上架 + 写入模版血缘
8. 复盘沉淀    产出动作空间清单 + 失败模式 playbook + 验证报告
```

---

## 四、数据模型设计

### 4.1 新增数据库表

- **M0/M1:无新增表**(YAGNI)。PoC 与 v1 loop 的产物(动作记录、playbook、验证报告)以 Markdown 文件沉淀在 `docs/` / 知识库,不入库。
- **M4(升级追踪)需要时新增**:`template_lineage`(模版血缘)表——映射 `app_template ↔ 上游来源(repo/chart/image) ↔ 上游版本 ↔ 验证报告 ↔ 最近转化时间`。设计待 M0 后细化。

### 4.2 数据关系

复用现有:`RainbondCenterApp` / `RainbondCenterAppVersion`(模版)、`ServiceShareRecord`(上架)、`AppUpgradeRecord`(升级)。M4 的 `template_lineage` 以 `app_id` 关联 `RainbondCenterApp`。

---

## 五、API 设计

### 5.1 接口列表

**新增(rainbond-console MCPQueryService,Python;3 个闭环信号工具):**

| 工具 | 用途 | 解决的缺口 |
|------|------|-----------|
| `wait_for_build_completion(team,region,app_id,service_id,event_id,timeout)` | 轮询构建/部署直到终态,返回 成功/失败/超时 + 关键错误摘要(非原始日志) | loop 无统一就绪信号 |
| `get_app_health_overview(team,region,app_id)` | 一次返回全组件状态 + 每组件 critical_blocker | 30 组件要查 30 次 |
| `get_config_file_content(team,region,app_id,service_id,volume_id)` + `analyze_env_conflicts(...,service_id)` | 读 config-file 卷内容、检测 env 多源冲突 | config 覆盖 gate 只能"检测有挂载"无法"读内容比对" |

**复用(无需新增):** check 系列、create_component_from_*、manage_component_*、operate_app、share 系列、upgrade 系列、app-store OpenAPI。

### 5.2 请求/响应结构

`get_app_health_overview` 返回示例:
```json
{
  "app_status": "partially_running",
  "components": [
    {"service_id":"...","name":"api","status":"abnormal","critical_blocker":"db_not_ready"},
    {"service_id":"...","name":"db_postgres","status":"running","critical_blocker":null}
  ]
}
```
其余结构待实现阶段对齐现有 region API 返回。

---

## 六、核心实现设计

### 6.1 关键逻辑

- **排障 loop = skill 编排,非后端服务**(KISS/YAGNI)。v1 由 Claude 驱动现有+新增 MCP 工具完成;不写新的 Python loop 服务。规模化(M4/M5)再评估产品化为 Job/Service。
- **文档知识获取 = skill 内 WebFetch/WebSearch**,非后端代码。抓取后作为诊断上下文,弥补"纯日志调不通、靠文档能调通"的差距。
- **半自动确认点**:写类 MCP 工具(改配置/部署)调用前,由 skill 规则要求人工确认(沿用 app-assistant 的 skill-select gate 模式)。
- **收敛/放弃判据**:同阻滞修复次数预算(参考 troubleshooter 的"单阻滞最多 1 次"+ 全局轮次上限);根因性失败(镜像不可达/集群容量)立即停。

### 6.2 复用现有代码

| 能力 | 复用位置 |
|------|----------|
| 故障分类决策树/修复优先级 | `~/.claude/skills/rainbond-fullstack-troubleshooter/SKILL.md` |
| 顶层路由/硬规则 | `~/.claude/skills/rainbond-app-assistant/SKILL.md` |
| 运行态→模版快照 | `console/services/share_services.py:273-454, 1145+` |
| 升级 diff | `console/services/market_app/property_changes.py:109-249` |
| check 结果结构 | `rainbond/builder/parser/parser.go:181-212` |
| MCP 工具实现 | `console/services/mcp_query_service.py` |
| 上架 OpenAPI | `app-store/pkg/app/controller/market_hub.go:42-219` |

---

## 七、实施计划

### 里程碑总览(定义)

| 里程碑 | 目标(一句话) | 核心交付物 | 退出标准 | 优先级 | 依赖 |
|--------|--------------|-----------|---------|--------|------|
| **M0 端到端 PoC** | 用真实 Dify 跑一遍半成品发动机,验证决策树够不够、文档输入与 3 个闭环缺口多关键 | Dify 在 `rainbond`/北京 集群跑通;动作空间清单 / 失败模式 playbook / 证据→诊断→修法映射(三件套) | Dify 可正常登录使用(四层冒烟过);三件套文档完成 | **P0(立即)** | MCP 就绪(✓ 2026-06-25 已确认) |
| **M1 自动排障 loop 内核** | 把 M0 人工干的活自动化,产出"保证能跑"的模版前置环节 | 3 个闭环信号 MCP 工具 + `rainbond-app-to-template` skill(含文档获取、半自动确认、收敛判据) | Dify 用新 loop 跑通,人工确认次数较 M0 显著下降;3 工具有测试覆盖 | **P0** | M0 产出 |
| **M2 验证门禁** | 把"测试验证"固化成红绿灯 | 对外 URL 可访问性探测 + 业务冒烟脚本框架 + 收敛/放弃判据 | 能对一个应用自动判定 通过/失败/需人工 并出诊断报告 | **P1** | 与 M1 耦合,可并入 M1 收尾 |
| **M3 快照上架自动化** | 验证通过→快照→推市场,全自动 | share 快照→app-store OpenAPI 上架封装 + AccessKey 配置 + 模版血缘最小记录 + **镜像策略(见 6.3)** + **【M0实证新增】敏感 env 参数化 + 对外 URL 模板化(见第九章)**;**第二个应用 Harbor** 验证 | Dify/Harbor 两个模版自动上架成功,终端用户可一键安装跑通(**密钥安装时生成、URL 自动回填**),**arm64 节点也能装** | **P1** | M1+M2 |
| **M4 升级追踪** | 上游出新版→自动重出升级版本 | `template_lineage` 表 + 上游版本监测(镜像 tag/chart/release)→重跑 loop→升级 diff | 监测到 Dify 新版本能自动产出升级版本模版 | **P2** | M3 |
| **M5 自动发现** | 自动找候选开源应用喂给 loop | 从 Artifact Hub/Helm repo/awesome 清单索引候选 | 能自动产出一批候选并喂入 M1 | **P3(最后)** | M1~M4 闭环成立 |

**优先级说明:** 用户直觉顺序是"自动寻找"在最前,但工程上它排最后——因为它在核心闭环(M1~M3)跑通前毫无价值,且最不确定。**先证明"一个应用能自动转出可用模版并上架",再谈"自动找一堆应用"。**

**当前进度(2026-06-25 更新):** **M0 已端到端跑通 + M3 预验证完成**(详见第九章实证回灌与 `docs/plans/poc/`)。**M1 三闭环信号工具已实现**:`get_app_health_overview` / `wait_for_build_completion` / `analyze_env_conflicts` 按 M0 痛感排序逐个 TDD 落地于 `console/services/mcp_query_service.py`,测试全绿无回归(规范 `.claude/specs/m1-closed-loop-mcp-tools.{yaml,md}`);`get_config_file_content` 复用现有 `rainbond_get_config_file`(#1930),未重复实现。**M1 Task 1.4–1.6 已完成(2026-06-25)**:新建 skill `rainbond-app-to-template`(`~/code/rainbond-skills/`,主 `SKILL.md` + `references/failure-mode-playbook.md`)串 导入→文档获取(双轨)→排障 loop(分级自动确认门控)→收敛/放弃判据,复用 troubleshooter 决策树作修复引擎、app-assistant Iron Law 作写动作纪律;3 信号工具按痛感融入 loop;M0 五类阻滞(FM-01…FM-05)+ 三条模版硬约束 + Dify 逐组件导入拓扑沉淀进 playbook。**3 工具经 dify-poc(app_id 3141)活体验证通过**(MCP 热同步后调用);收敛终点=快照就绪+交接 M3,不自动发布。**自动化率从零重建实测(2026-06-26,dify-poc-v2 app_id 3154)**:用 skill 当司机从零重建完整 Dify 9 组件、planted FM-01 作被发现阻滞,loop 经 health_overview 发现→日志取证→playbook 命中→analyze_env_conflicts gate→自动补 env→wait_for_build→**9/9 running、nginx 单入口对外 200**,**人工确认 0 次(headless)/ 预测 1 次(仅 FM-05 浏览器路径)**,对比 M0 ≈5 次显著下降。新发现:同租户内部 DNS 冲突(二次实例须 `-v2` 后缀重指向),已写入 playbook。记录见 `docs/plans/poc/run-log-v2-automation-measure.md`。**M1 全部完成。下一步 M2/M3。**

### 跨层覆盖检查

- [x] **Go (rainbond)**:不涉及新增(复用 check/构建/部署/Pod 查询)。
- [x] **Python (console)**:需要 —— 新增 3 个闭环信号 MCP 工具 + 工具注册;复用 share/upgrade。
- [x] **app-store (Go)**:M3 需要 —— 确认 OpenAPI AccessKey 申请/配置方式;可能新增"程序化上架"封装。
- [x] **React (rainbond-ui)**:v1 不涉及(无新 UI)。
- [x] **Skills**:需要 —— 新增/扩展 `rainbond-app-to-template` 排障+转化 loop skill,含文档获取与半自动确认。

### Sprint 0(M0)— 端到端 PoC(Dify @ `rainbond`/北京 集群,无新代码)

> 目标:用真实 Dify 跑一遍半成品发动机,验证决策树够不够用、文档输入与 3 个闭环缺口有多关键。产出 M1 设计输入。

- **Task 0.1**:确认集群 MCP 连接就绪、可操作(team/region/JWT)。✓ **2026-06-25 已确认**:region `rainbond`(北京),企业 admin yangk,资源充足;待建专属 PoC 团队。
- **Task 0.2**:导入 Dify(优先 compose 核心子集 ~9 服务:api/worker/web/nginx/db_postgres/redis/sandbox/ssrf_proxy/plugin_daemon + weaviate),基础解析 + 部署(api 单副本)。
- **Task 0.3**:进入排障 loop(AI 主导、人工确认),对照预判三大坑调通:① service-name host 重指向(含 `CELERY_BROKER_URL` 内嵌 host、plugin_daemon 反向 `http://api:5001`)② plugin_daemon 独立 `dify_plugin` 库+竞态 ③ sandbox/ssrf_proxy 网络段+proxy 变量。
- **Task 0.4**:四层冒烟验收(`/install` 建号 → 控制台无插件错 → 知识库索引 → 代码节点跑通)。
- **Task 0.5**:**全程记录**,产出三件套:动作空间清单 / 失败模式 playbook(Dify)/ 证据→诊断→修法映射样本。保存到 `docs/plans/poc/`。
- **验收标准**:Dify 在 `rainbond`/北京 集群可正常登录使用;三件套文档完成。

### Sprint 1(M1)— 自动排障调优 loop 内核(核心)

> 依赖 M0 产出。

- **Task 1.1**:实现 `wait_for_build_completion`(console,TDD)。
- **Task 1.2**:实现 `get_app_health_overview`(console,TDD)。
- **Task 1.3**:实现 `get_config_file_content` + `analyze_env_conflicts`(console,TDD)。
- **Task 1.4**:新建 `rainbond-app-to-template` skill,串起 导入→文档获取→排障 loop(半自动确认)→收敛判据。
- **Task 1.5**:把 M0 的 Dify playbook 沉淀为 skill 内的失败模式知识。
- **Task 1.6**:Dify 二次跑通(尽量少人工干预),度量自动化率提升。
- **验收标准**:Dify 用新 loop 跑通,人工确认次数较 M0 显著下降;3 工具有测试覆盖。

### Sprint 2(M2)— 验证门禁

- 对外 URL 可访问性探测、业务冒烟脚本框架、收敛/放弃判据固化(与 M1 耦合,可并入 M1 收尾)。

### Sprint 3(M3)— 快照上架自动化

- share 快照 → app-store OpenAPI 上架封装;AccessKey 配置;模版血缘最小记录。Harbor 作为第二个验证应用。
- **镜像策略落地(见 6.3)**:发布时把模版组件 image 改写为上游多架构原镜像;新增 arch manifest 探测步骤,正确填 `arch` 字段;验证 arm64 节点可安装。

### Backlog(独立改进,不阻塞本项目)

- **rainbond 核心:保留 manifest list 的多架构镜像同步**(opt-in bundle 模式,面向离线客户)。把 `rainbond/builder/sources/image_containerd_client.go` 等的"节点 runtime 单架构 pull+push"改为**仓库到仓库 manifest list 整体拷贝**(crane/skopeo `--all`),使 goodrain.me 存真多架构。仅覆盖镜像型组件;源码构建型多架构另议。惠及全平台,优先级独立评估。落地后可重评"默认上游直连"决策。

### Sprint 4(M4)— 升级追踪

- `template_lineage` 表;上游版本监测(镜像 tag/chart/release)→重跑 loop→出升级版本。

### Sprint 5(M5)— 自动发现

- 从 Artifact Hub / Helm repo / awesome 清单索引候选应用喂给 loop。最不确定,排最后,先以人工选型替代。

---

## 八、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| 排障决策树/动作优先级 | `~/.claude/skills/rainbond-fullstack-troubleshooter/SKILL.md` | 6 态 RuntimeState、config 覆盖 gate、连接契约 |
| 顶层路由/硬规则 | `~/.claude/skills/rainbond-app-assistant/SKILL.md` | Iron Law 20/30/31/34/36/37/38 |
| 运行态→模版导出 | `console/services/share_services.py:273-454` | query_share_service_info |
| 模版组装 | `console/services/app_version_service.py:394-443` | _assemble_app_template |
| 升级 diff | `console/services/market_app/property_changes.py:109-249` | 支持的变更类型 |
| check 结果结构 | `rainbond/builder/parser/parser.go:181-212` | ServiceInfo |
| MCP 工具实现 | `console/services/mcp_query_service.py` | 诊断+修复动作空间 |
| 上架 OpenAPI | `app-store/pkg/app/controller/market_hub.go:42-219` | createApp/Version/上架 |

### 6.3 镜像与多架构策略

**现状(已核实代码,2026-06-25):**
- Rainbond 对镜像组件**无条件**走"拉原镜像(仅当前节点架构)→换 tag→推内部仓库 `goodrain.me`→从内部仓库部署",**无绕过开关**。证据:`rainbond/builder/sources/image_containerd_client.go:143`(pull `platforms.Ordered([DefaultSpec()])` 只拉当前架构)、`:346-352`(push `NewMatcher(DefaultSpec())` 只推单平台)、`builder/exector/build_from_image_run.go:100-116`(建组件即同步)、`builder/exector/share_image.go:167-184`(share 同步)。
- **后果:多架构 manifest list 被压扁成单架构。** 模版 `arch` 字段来自组件部署节点架构(`console/services/share_services.py:331,1317,1366`),非镜像真实 manifest → 默认产出单架构模版。
- 内部仓库:默认 `goodrain.me`(`rainbond/util/constants/constants.go:9`,可 `BUILD_IMAGE_REPOSTORY_DOMAIN` 覆盖);命名 `{domain}/{service_id}:{deploy_version}`。

**设计决策:**
1. **验证部署沿用现状**(内部仓库、单架构)——它只为把应用跑起来验证,架构无关紧要,不动核心镜像管线。
2. **发布的模版默认引用上游多架构原镜像**(`component.image` 指上游如 `langgenius/dify-api:1.14.2`,而非 `goodrain.me` 单架构同步镜像)。理由:① k8s 拉 manifest list 自动选架构,多架构天然保住 ② 血缘清晰利于 M4 升级追踪 ③ 零核心改动。代价:安装依赖上游公共仓库(开源应用均在公共仓库,可接受)。
3. **`arch` 字段改由探测上游镜像真实 manifest 决定**(skopeo/crane/`docker manifest inspect`),正确标 `amd64`/`arm64`/`amd64&arm64`。这是 M3 上架环节的一个步骤。
4. **可选 bundle 模式(opt-in,面向离线客户)**:把上游多架构镜像**保留 manifest list 整体**同步进内部仓库。改完后 **`goodrain.me` 里存的就是真多架构**(自包含 + 多架构兼得)。
   - **改法**:当前压扁的根因是走"节点容器运行时 pull(单架构)+push(单平台)";修法是改成**仓库到仓库的 manifest list 整体拷贝**(`crane copy` / `skopeo copy --all` / go-containerregistry),绕过节点 runtime,把 OCI index + 各架构子 manifest + blobs 原样搬到 `goodrain.me/{service_id}:{version}`,内部命名规则可保留。前提:goodrain.me(Harbor/registry v2)支持 manifest list ✓。
   - **范围**:仅覆盖**镜像型组件**(直接拉上游 prebuilt 镜像 —— Dify/Harbor 全是);**源码构建型组件**的多架构是另一个更难的独立问题(需多架构节点各构建或 buildx 模拟),不在此范围。
   - **连带影响**:此核心改进落地后,决策 2 的"默认上游直连"可重新评估——届时"内部 bundle"也是多架构,离线客户可默认走自包含多架构内部镜像。故"默认上游直连"是**零核心改动的当下最优解,非永久绑定**。
   - **需改 rainbond 核心镜像客户端,惠及全平台,列为 backlog,不阻塞本项目。**
| Dify 部署坑地图 | 本设计 1.3 / Sprint0 + 调研记录 | service-name host / plugin_daemon / sandbox 网络 |

---

## 九、M0 / M3 实证回灌(2026-06-25)

> 本章把 M0 端到端 PoC + M3 预验证的实测结论回灌进设计。原始记录见 `docs/plans/poc/`。运行环境:默认集群 `rainbond`/北京,team `tynwrm27`,app_id 3141,9 组件(api/worker/web/nginx/db-postgres/redis/weaviate/sandbox/plugin-daemon)。

### 9.1 核心假设验证:成立

"内核是 AI 排障调优 loop、非格式转译"**得到端到端验证**:整条耗时主要在**策展**(读懂 Dify 结构 + 理顺接线),而非转译。9 组件只用 **1 次关键修复**(补 `PLUGIN_REMOTE_INSTALLING_HOST`)即全绿;四层冒烟 层1建号/层2登录+配模型/层4代码节点(sandbox)全部通过;快照成 app_template 成功(version_id 492)。

### 9.2 预判坑纠偏

| 预判(1.3 / 调研) | 实证结论 |
|------|---------|
| 坑① service-name host 重指向 | ✅ **命中且更严重**:`db_postgres`/`plugin_daemon`/`ssrf_proxy` 带下划线是**非法 K8s service 名**,必须改连字符 + 重指向所有引用。 |
| 坑② plugin_daemon 独立 `dify_plugin` 库 + 竞态会炸 | ❌ **证伪**:plugin-daemon **自建库自迁移**,不阻滞。决策树应加"先看组件是否自 provision 依赖再判阻滞"。 |
| 坑③ sandbox/ssrf_proxy 网络段 | ⚪ 未触发(子集砍 ssrf_proxy,sandbox 免代理可跑;代码节点跑通)。 |

### 9.3 实测出的 5 类阻滞 & 文档获取价值修正

阻滞:① 必填 env 缺失(纯日志)② 跨 origin 路由(平台知识)③ 依赖边未建(平台知识)④ 登录 `Invalid encrypted data`=前端加密密码(**必须查源码**)⑤ setup 后租户 RSA 私钥丢失致凭据 500(**需框架运维知识 `flask reset-encrypt-key-pair`**)。

**修正 6.1 关于"文档获取"的判断**:配置类阻滞靠日志/平台知识即可;但**协议级/框架约定级阻滞(④⑤)纯日志彻底定位不了,文档/源码获取不可替代**。M1 应做**双轨**:沉淀型 playbook(配置类)+ 按需源码/文档获取(协议类),而非二选一。

### 9.4 Dify 模版三条硬约束(部署快照法必须替用户踩平)

1. **逐组件建模必须显式建依赖边**(`manage_component_dependency`)——只靠 K8s DNS 连通虽能跑,但 share 成模版时 `dep_service_map_list` 为空、拓扑与依赖丢失。M3 实证:建了边,模版才完整 capture 依赖 + 共享存储挂载 + nginx config-file。
2. **必用 nginx 单入口 + config-file 路由**(`/console/api|/api|/v1|/files|/mcp|/e`→api、`/`→web)——跨 origin 直连会让浏览器端 `CONSOLE_API_URL` 失效、登录前端加密无法工作。
3. **`/app/api/storage` 必须持久卷 + api/worker 共享 + 可写**(等价 init_permissions 的 chown/fsGroup)——否则 setup 后租户密钥对丢失,所有凭据功能瘫痪。

### 9.5 M3 新增设计项(模版上架前必做)

- **敏感 env 参数化**:快照模版把 `SECRET_KEY`/`DB_PASSWORD`/inner API Key/`WEAVIATE_API_KEY` 等**明文冻结**。上架前必须改为**安装时生成或用户填写**(Rainbond 模版支持 env 占位/必填项),否则全网用户共享同一套密钥=安全事故。
- **对外 URL 模板化**:`CONSOLE_API_URL`/`CONSOLE_WEB_URL`/`APP_*_URL` 含本次网关域名,换环境即失效。应**留空走相对路径 + 靠 nginx 单入口同源**,安装时无需回填。

### 9.6 MCP 动作空间实测(印证 M1 + 新增缺口)

- **M1 三闭环工具痛感实测排序(确认)**:`get_app_health_overview`(最痛,8 组件逐个查才知哪个 abnormal)> `wait_for_build_completion`(每次部署靠 for+sleep+curl 自旋)> `get_config_file_content`(本轮 nginx config-file 用到,价值确认)。**实现裁剪(2026-06-25 M1)**:`get_config_file_content` 已被现有 `rainbond_get_config_file`(#1930)覆盖,故 M1 第三件落地为更缺的 `analyze_env_conflicts`(env 多源冲突检测,敏感值脱敏),`get_app_health_overview` 仅对异常组件深挖 blocker、`wait_for_build_completion` 采有界阻塞轮询(默认 60s/上限 120s)。三者均已 TDD 实现+注册+test-manifest 登记。
- **新发现缺口(记入实施计划)**:① **无 compose 上传 MCP 工具** → 程序化 compose 导入走不通,改逐组件 `create_component_from_image`;② **无"建本地 app_model"MCP 工具** → 程序化本地市场发布受阻,M3 需补;③ 改内部域名要两步(`add` 忽略 `k8s_service_name`,需再 `update_alias`);④ `vertical_scale` 必传 `new_gpu=0`。
- **结论**:现有 MCP **修复动作**足以驱动 loop;缺的是**信号聚合/就绪类只读工具**(= M1 三工具)+ 上述发布链工具。
