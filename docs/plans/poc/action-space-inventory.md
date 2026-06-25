# 动作空间清单(M0 Dify PoC)

> M0 排障 loop 实际用到的 MCP 工具及调用模式。作为 M1 skill 的"动作空间"参考。
> 实测环境:Dify 8 服务,逐组件 image 建模,`KUBERNETES_NATIVE_SERVICE` 治理。

## 诊断证据工具(只读)

| 工具 | 用途 | M0 实测备注 |
|------|------|-------------|
| `get_app_detail` | 应用级 `running_service_count`/`status` | 快速判全绿(`8/8 running`)。但**不给逐组件状态** → 缺口见下 |
| `query_components` | 列组件 | 只给 `create_status`,**不给运行 status** |
| `get_component_summary` | 单组件 status+ports+envs+events | 定位 abnormal 的主力;一次一组件 |
| `get_component_logs action=service` | 组件日志 | 关键定位手段;失败自动回退首 pod;支持 `previous` 取崩溃前日志 |
| `get_component_events` | K8s 事件 | `ContainerExitError` 等 |
| (未用)`get_component_pods`/`get_pod_detail`/`get_operation_failure_context` | Pod 详情/失败上下文 | 本轮日志已够,未触发 |

## 修复动作工具(写)

| 工具 | 用途 | M0 实测备注 |
|------|------|-------------|
| `create_component_from_image` | 建组件 | `is_deploy=false` 先建后接线;`k8s_component_name` 设期望名 |
| `manage_component_ports operation=add` | 加端口 | ⚠️ **忽略传入 `k8s_service_name`**,回落成 alias |
| `manage_component_ports operation=update_alias` | **改内部域名** | 唯一能设 `k8s_service_name`(内部 DNS)的动作,带 `port_alias` |
| `manage_component_ports operation=enable_outer` | 开外网网关 | 返回 `access_infos` 外网 URL |
| `manage_component_envs operation=upsert` | 批量 env | `envs` 数组;⚠️ 与端口别名自动生成的 `<ALIAS>_PORT/_HOST` 同名会 412 |
| `manage_component_storage operation=create_volume` | 挂卷 | `share-file` RWX;config-file 类型可挂渲染配置 |
| `vertical_scale_component` | 改资源 | ⚠️ **必须传 `new_gpu=0`**,否则 `container_gpu cannot be null` |
| `operate_app action=deploy` | 部署/重部署 | 批量 service_ids;返回 event_ids |
| (未用)`change_component_image`/`manage_component_dependency`/`manage_component_probe`/`manage_component_connection_envs` | 换镜像/依赖/探针/连接变量 | 本轮 k8s 原生 DNS + 显式 env 已够,未触发 |

## 动作空间缺口(给 M1)

| 缺口 | M0 痛点 | 痛感 | M1 状态 |
|------|---------|------|---------|
| **无 compose 上传 MCP 工具** | `check_yaml_app` 要 `compose_id`,但 MCP 无"创建 compose 记录"步 → 程序化 compose 导入走不通,改逐组件建 | 中(逐组件建反而更可控) | M1 不补(记着) |
| **无逐组件健康聚合** | `get_app_detail` 只给计数;要逐个 summary 才知哪个 abnormal+为何 | **高 → `get_app_health_overview`** | ✅ **已实现**(`rainbond_get_app_health_overview`) |
| **无构建/部署就绪信号** | 每次 deploy 后 `for+sleep+curl /health` 自旋 | **高 → `wait_for_build_completion`** | ✅ **已实现**(`rainbond_wait_for_build_completion`,有界阻塞轮询 ≤120s) |
| **无 env 多源冲突检测** | upsert env 撞端口别名自动生成的 `<ALIAS>_PORT` → 412 | 中 → `analyze_env_conflicts` | ✅ **已实现**(`rainbond_analyze_env_conflicts`,敏感值脱敏) |
| **config 内容读取** | config 覆盖 gate 只能"检测有挂载" | 中 | ✅ 已被现有 `rainbond_get_config_file`(#1930)覆盖,M1 不重复造 |
| **改内部域名要两步** | `add` 不认 `k8s_service_name`,需再 `update_alias` | 低(记录即可) | 未改(记着) |
| **vertical_scale 必传 new_gpu=0** | 不传报 500 | 低(工具应默认 0) | 未改(记着) |

## 一句话结论

现有 MCP **修复动作**足以驱动整个 loop(envs/ports/storage/scale/operate);真正缺的是 **3 个信号聚合/就绪类只读工具**(健康总览、构建就绪、env 冲突),这与 M1 设计的 3 个闭环工具完全吻合,且 M0 给出了**痛感排序:健康总览 > 构建就绪 > env 冲突**。

> **M1 落地(2026-06-25):** 三工具已在 `console/services/mcp_query_service.py` 按痛感排序逐个 TDD 实现并接入(实现+`call_tool`分发+`_tool_*` schema+`list_tools`注册+`test-manifest.json` 能力登记),测试 `console/tests/mcp_query_{health_overview,wait_build,env_conflicts}_test.py` 全绿、无回归。`get_config_file_content` 复用现有 `rainbond_get_config_file`,未重复实现。规范见 `.claude/specs/m1-closed-loop-mcp-tools.{yaml,md}`。
>
> **M1.4–1.6 完成(2026-06-25):** 新建 skill `rainbond-app-to-template`(`~/code/rainbond-skills/`,含 `references/failure-mode-playbook.md`)串起 导入→文档获取(双轨)→排障 loop(分级自动确认门控)→收敛/放弃判据,3 信号工具按痛感融入(health_overview 做 step-4 健康总览、wait_for_build_completion 做 step-3/5f 就绪信号、analyze_env_conflicts 做 step-5e 改 env 前防 412)。**3 工具已对 dify-poc(app_id 3141)活体验证通过**(MCP 热同步后本会话拉到新工具):① `get_app_health_overview` 一次返回 `app_status=running` + 9/9 running + 各 `critical_blocker=null`(取代 9× summary);② `analyze_env_conflicts`(api)`conflicts=[]`(已收敛);③ `wait_for_build_completion` 传历史终态 build event 立即返回 `status=success`、`error_summary=[]`。收敛终点定在「快照就绪+交接 M3」,不自动发布。
>
> **自动化率(M1 vs M0,结构性提升):** M0 全程 5 类阻滞各需一次人工交互修复;新 skill 把 5 类沉淀进 playbook 并经分级门控:FM-01 必填 env、FM-02/04 nginx 单入口路由、依赖边未建 → **自动应用(仅播报)**;仅 FM-05(进 pod 跑 `flask reset-encrypt-key-pair`,触数据/存储)→ **人工确认**。预测人工确认数 5 → 1。叠加 3 信号工具把每轮数十次只读自旋压成个位数调用。
