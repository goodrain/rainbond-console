# 动作空间清单(M0 Dify PoC)

> M0 排障 loop 中实际用到的 MCP 工具及调用模式。完成后作为 M1 skill 的"动作空间"参考。

## 诊断证据工具(只读)

| 工具 | 用途 | M0 实际调用次数 / 备注 |
|------|------|------------------------|
| `get_app_detail` | 应用拓扑总览 | |
| `get_component_summary` | 单组件状态摘要 | |
| `get_component_pods` / `get_pod_detail` | Pod 列表/详情 | |
| `get_component_logs` | 运行日志 | |
| `get_component_events` | K8s 事件 | |
| `get_operation_failure_context` | 操作失败上下文 | |
| `get_config_file` | 配置文件卷(挂载存在性) | 缺口:读不到内容 → M1 补 |

## 修复动作工具(写)

| 工具 | 用途 | M0 实际调用次数 / 备注 |
|------|------|------------------------|
| `manage_component_envs` | 改环境变量 | |
| `manage_component_connection_envs` | 连接变量(provider/consumer 契约) | |
| `manage_component_dependency` | 组件依赖 | |
| `manage_component_probe` | 健康探针 | |
| `manage_component_storage` | 存储卷 | |
| `manage_component_ports` | 端口 | |
| `change_component_image` | 换镜像 | |
| `operate_app` | 部署/启停/重启 | |

## 闭环缺口实证(给 M1 定优先级)

| 缺口 | M0 中暴露的痛点(具体场景) | 痛感评级 |
|------|------------------------------|----------|
| 无统一构建就绪信号 | | 待填 |
| 多组件健康要逐个查 | | 待填 |
| config-file 读不到内容/env 冲突检测不了 | | 待填 |
