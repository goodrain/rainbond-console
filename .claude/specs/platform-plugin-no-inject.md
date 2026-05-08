# 平台插件发布支持“不注入” — 实施规范

**设计文档：** `docs/plans/2026-05-08-platform-plugin-no-inject-design.md`  
**创建时间：** 2026-05-08

## 关键约束

- `NoInject` 只允许存在于 `rainbond-ui` 表单态，禁止持久化到模板或 region API。
- 模板持久化语义固定为：`不注入 = inject_position: []`。
- 平台插件其他字段 `plugin_type / frontend_component / entry_path / menu_title / route_path` 保持原有填写要求。
- 平台插件列表页仍应展示已安装插件，不能因为空 `plugin_views` 被误隐藏。
- 前端质量门控为 `yarn build`，console 质量门控为相关测试通过。

## 执行顺序

1. `rainbond-ui`：完成 `NoInject` 交互、回显、提交归一化、完成态校验
2. `rainbond-console`：完成模板归一化与测试
3. 运行构建和测试验证跨仓库兼容性

## 预期提交分组

1. `feat: support no-inject platform plugin publish option`
2. `test: normalize empty platform plugin views in share template`
