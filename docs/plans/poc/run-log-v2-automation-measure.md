# M1 Task 1.6 自动化率实测（dify-poc-v2，从零重建）

> 2026-06-26。用 `rainbond-app-to-template` skill 当司机，从零在 team `tynwrm27`/region `rainbond` 重建一个完整 Dify（app `dify-poc-v2`，app_id **3154**），度量「人工确认次数较 M0 是否显著下降」。dify-poc（3141）保留未动。

## 结论

**9/9 running，nginx 单入口对外可达，0 次人工确认（headless 范围）。** 入口 `http://gra63041-80-tynwrm27.dev.goodrain.com`：`/console/api/setup`→200 `{"step":"not_started"}`、`/apps`→200。三条模版硬约束全部在导入阶段前置满足（依赖边 / nginx 单入口 config-file / api·worker 共享持久存储）。

## 排障 loop 实跑（3 信号工具全程驱动）

planted 一个真实可复现的阻滞：plugin-daemon 故意**不配** `PLUGIN_REMOTE_INSTALLING_HOST`（复现 M0 的 FM-01），让 loop 去发现并修。

| loop 步 | 工具 | 实测 |
|---|---|---|
| 4 发现 | `get_app_health_overview` | 一次返回全 9 组件；plugin-daemon `abnormal / crash_loop`（其余按需 undeploy/running） |
| 5a 证据 | `get_component_logs(action=container, previous=true)` | `invalid configuration: plugin remote installing host is empty` |
| 5b 分类 | playbook | 命中 **FM-01**（config-missing）→ 门控判定 **auto-apply** |
| 5e 改 env 前 gate | `analyze_env_conflicts` | `conflicts=[]` → 安全 |
| 5d 修复 | `manage_component_envs(upsert)` | 补 `PLUGIN_REMOTE_INSTALLING_HOST=0.0.0.0`(+PORT=5003)——**自动，未打断** |
| 5f 验证 | `wait_for_build_completion` → `get_app_health_overview` | 终态 `success` → plugin-daemon `running` |

`get_app_health_overview` 全程用 5 次（每次 1 调用替代 9× `get_component_summary`）；`wait_for_build_completion` 4 次（替代 for+sleep+curl 自旋）；`analyze_env_conflicts` 1 次（改 env 前 gate，干净）。

## 自动化率：M0 vs M1

| M0 需人工交互修复的阻滞 | M1 处置 |
|---|---|
| FM-01 必填 env 缺失 | **自动**（playbook 命中 + 门控 auto，仅播报） |
| 跨 origin 路由（FM-02/04）| **前置预防**：导入即建 nginx 单入口 + config-file 路由（自动） |
| 依赖边未建（15A）| **前置预防**：导入即显式建依赖边（自动） |
| 登录前端加密误判（FM-03）| playbook 已沉淀，无需现场诊断（双轨文档） |
| 密钥对丢失 reset（FM-05）| 唯一**人工确认**项（进 pod 跑 `flask reset-encrypt-key-pair`），本次 headless 未触发（需浏览器 setup→配 key 才暴露） |

**人工确认数：M0 ≈5 次 → M1 = 0 次（headless）/ 预测 1 次（含浏览器冒烟时仅 FM-05）。**

```yaml
AppToTemplateLoopResult:
  app: { team: tynwrm27, region: rainbond, app_id: 3154, components_total: 9, components_running: 9 }
  convergence: snapshot_ready
  blockers:
    - { fm_id: FM-01, bucket: config-missing, fix: "add PLUGIN_REMOTE_INSTALLING_HOST=0.0.0.0(+PORT=5003)", applied: auto }
  automation:
    auto_applied_count: 1          # FM-01；另有 3 条硬约束前置预防、若干动作空间坑自动规避
    human_confirmed_count: 0       # headless；含浏览器冒烟时预测 1（FM-05）
    abandoned: []
  hard_constraints: { dep_edges: ok, nginx_single_entry: ok, persistent_shared_storage: ok }
  smoke:
    reachable_url: "http://gra63041-80-tynwrm27.dev.goodrain.com"
    layers_passed: [ "L1 /console/api/setup 200 not_started", "web /apps 200 via nginx" ]
    layers_deferred: [ "L2 浏览器登录(FM-03 前端加密，需浏览器)", "L3 知识库索引(需 Embedding)", "L4 代码节点(需 LLM key)" ]
  next_handoff: m3_snapshot_publish
```

## 本轮新发现 / 坑

1. **内部 DNS 同租户冲突（新增缺口）**：同 team/namespace 部署第二个同款应用，内部域名 `db-postgres`/`redis`/… 被 dify-poc 占用 → `409 k8s service name already exists`。本次用 `-v2` 后缀（`db-postgres-v2` 等）+ 重指向所有 host env 解决。M0 单实例从未触发。**对终端用户无影响**（模版安装进各自独立 app/namespace 不撞），但**同租户策展/并行验证会撞**，需在 skill/playbook 标注：二次实例必须改内部域名并同步改 host 引用。
2. `add` 端口忽略 `k8s_service_name`（回落 `grXXXX`）→ 必须 `update_alias` 二次设置。**复现并自动处理**，印证 playbook。
3. `vertical_scale` 必传 `new_gpu=0`——自动带上，未踩坑。
4. `manage_component_storage create_mnt` 的 `mounts` 项是 `{id, path}`，不是 `{dep_vol_id, mount_path}`（描述与 schema 不一致）→ 首次 500 后自纠。

## 与 M0 的等价性

v2 用 dify-poc(3141) 的**已知良好配置作 ground truth**逐字复制（再 `-v2` 重指向），仅 planted FM-01 作被发现阻滞。等价于「M0 的策展知识已固化、二次跑只需发现并修剩余阻滞」——这正是 M1 要证明的：策展成本一次性付清后，loop 把重复阻滞自动消解。
