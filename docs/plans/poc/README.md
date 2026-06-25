# M0 PoC — 开源应用转模版(Dify @ rainbond/北京 集群)

> 关联设计:`../2026-06-25-opensource-app-to-template-design.md`(Sprint 0 / M0)
> 集群:region `rainbond`(北京,`172.16.0.2:8443`,v6.9.2,amd64,空闲 RAM ~42GB / CPU ~25 核)
> 主导:AI(Claude),yangk 旁观确认关键动作

## M0 目标

用真实 Dify 跑一遍半成品排障发动机(`rainbond-fullstack-troubleshooter` skill),验证:
1. 故障分类决策树够不够用;
2. 文档输入(README/镜像文档)对诊断有多关键;
3. 三个闭环信号缺口(`wait_for_build_completion` / `get_app_health_overview` / `get_config_file_content`+`analyze_env_conflicts`)有多痛 —— 给 M1 写代码定优先级。

## 退出标准

- Dify 可正常登录使用,四层冒烟通过:`/install` 建号 → 控制台无插件错 → 知识库索引 → 代码节点跑通。
- 三件套文档完成(见下)。

## 三件套交付物(M0 全程记录,逐步填充)

| 文件 | 内容 | 状态 |
|------|------|------|
| `action-space-inventory.md` | 动作空间清单 —— loop 中实际用到的 MCP 修复/诊断工具及调用模式 | 待填 |
| `failure-mode-playbook-dify.md` | Dify 失败模式 playbook —— 每个坑的症状/根因/修法/验证 | 待填 |
| `evidence-diagnosis-fix-map.md` | 证据→诊断→修法映射样本 —— 喂给 M1 决策树/skill 知识 | 待填 |
| `run-log.md` | M0 实操流水账(导入→部署→每轮排障→冒烟),按时间记录 | 待填 |

## 预判三大坑(M0 重点验证,来自前期调研)

1. **service-name host 重指向**:含 `CELERY_BROKER_URL` 内嵌 host、`plugin_daemon` 反向回调 `http://api:5001`。
2. **plugin_daemon 独立 `dify_plugin` 库 + migration 竞态**。
3. **sandbox / ssrf_proxy 专用网络段 + proxy 变量**。
