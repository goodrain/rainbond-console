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

| 缺口 | M0 痛点 | 痛感 |
|------|---------|------|
| **无 compose 上传 MCP 工具** | `check_yaml_app` 要 `compose_id`,但 MCP 无"创建 compose 记录"步 → 程序化 compose 导入走不通,改逐组件建 | 中(逐组件建反而更可控) |
| **无逐组件健康聚合** | `get_app_detail` 只给计数;要逐个 summary 才知哪个 abnormal+为何 | **高 → M1 `get_app_health_overview`** |
| **无构建/部署就绪信号** | 每次 deploy 后 `for+sleep+curl /health` 自旋 | **高 → M1 `wait_for_build_completion`** |
| **改内部域名要两步** | `add` 不认 `k8s_service_name`,需再 `update_alias` | 低(记录即可) |
| **vertical_scale 必传 new_gpu=0** | 不传报 500 | 低(工具应默认 0) |

## 一句话结论

现有 MCP **修复动作**足以驱动整个 loop(envs/ports/storage/scale/operate);真正缺的是 **3 个信号聚合/就绪类只读工具**(健康总览、构建就绪、config 内容/env 冲突),这与 M1 设计的 3 个闭环工具完全吻合,且 M0 给出了**痛感排序:健康总览 > 构建就绪 > config 比对**。
