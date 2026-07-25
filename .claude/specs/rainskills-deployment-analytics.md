# RainSkills 部署数据独立采集 - 实施规范

设计文档：`docs/plans/2026-07-23-rainskills-deployment-analytics-design.md`

## 不可变约束

- request-server 新增独立 `/api/rainskills/deployments`，旧 `/api/enterprise/first-deploy`、旧模型和
  `deploy_statistics.go` 不修改。
- Console 只使用 `RAINSKILLS_DEPLOY_*` 保存新 tracker，不读写 `FIRST_DEPLOY_*` 或 `DEPLOY_DIAG_*`。
- 新统计错误必须被隔离，不能改变 MCP 返回、重放部署或影响旧首次部署判定。
- 来源是低信任分析标签，不用于计费、授权和产品状态。
- 只存固定字段与最多 50 个 ID，不存工具参数、凭据、完整上下文或日志。

## 执行顺序

1. `rainbond-request-server`：新表、独立 API、有序幂等、body/速率限制、旧统计隔离回归。
2. `rainbond-console`：专用路由、独立 tracker、工具矩阵、事件标准化、恢复和清理。
3. `rainskills`：客户端专用 URL、预校验、旧通用配置安全迁移及文档。
4. 执行三仓库质量门槛与跨仓库 API 兼容检查。

## 提交分组

1. `rainbond-request-server`：`feat: store RainSkills deployment analytics`
2. `rainbond-console`：`feat: add RainSkills MCP deployment routes`
3. `rainbond-console`：`feat: report RainSkills deployment outcomes`
4. `rainskills`：`feat: register client-specific RainSkills MCP routes`

完整任务、TDD 步骤、文件范围和验收命令见
`.claude/specs/rainskills-deployment-analytics.yaml`。
