# MCP 组件默认资源规范设计文档

## 一、项目背景
### 1.1 项目架构

当前 Rainbond 的组件创建主链路已经通过 MCP 暴露为统一工具集合，主要包含镜像创建、源码一键创建、软件包一键创建，以及检测、构建、部署等阶段。

MCP 工具的外部契约目前强调的是“创建流程”，例如自动检测、默认配置、按需部署，但并没有把组件创建时的默认 CPU / 内存策略上升为显式规范。

### 1.2 现有基础

- `console/services/mcp_query_service.py`
  - 已定义 MCP 工具 schema 与 description
  - 已提供 `rainbond_create_component*` 与 `rainbond_build_component`
- `console/services/app.py`
  - 已为不同创建来源设置初始资源默认值
- `console/services/app_check_service.py`
  - 已在检测成功后更新源码/软件包组件的资源值
- `rainbond-agent/MCP_CONSOLE_API_SUMMARY_ZH.md`
  - 已沉淀 MCP 工具总览与推荐使用方式

### 1.3 核心需求

- 将组件创建时的默认 CPU / 内存策略提升为 MCP 对外规范
- 保持现有 MCP 输入参数不变，不新增资源入参
- 让各种创建工具在生成组件时具备稳定、合理、可解释的默认资源行为
- 避免默认值仅散落在后端实现中，减少“魔法数字”与隐式约定

## 二、整体架构设计
### 2.1 系统架构图

```text
MCP Tool Description / MCP Summary
        ↓
MCPQueryService
        ↓
AppService / AppCheckService
        ↓
Component persisted with normalized default CPU / memory
        ↓
create_region_service / deploy
```

### 2.2 核心流程

1. MCP 工具对外声明默认资源规范
2. 组件创建阶段根据来源写入初始默认资源
3. 源码 / 软件包组件检测成功后，根据检测结果应用规范化默认资源
4. 构建 / 部署阶段直接使用组件对象上已确定的资源值

## 三、数据模型设计
### 3.1 新增数据库表

无新增表。

### 3.2 数据关系

- `TenantServiceInfo.min_memory`
  - 组件默认或归一化后的内存请求值
- `TenantServiceInfo.min_cpu`
  - 组件默认或归一化后的 CPU 请求值
- `TenantServiceInfo.total_memory`
  - 组件总内存，通常为 `min_node * min_memory`

本次不新增字段，只统一默认资源值的来源和语义。

## 四、API设计
### 4.1 接口列表

本次不新增 MCP 工具，也不修改已有创建工具的输入 schema 字段。

涉及说明更新的工具：

- `rainbond_create_component`
- `rainbond_create_component_from_image`
- `rainbond_create_component_from_source`
- `rainbond_create_component_from_package`
- `rainbond_create_component_from_local_package`
- `rainbond_check_component`
- `rainbond_get_component_check_result`
- `rainbond_build_component`

### 4.2 请求/响应结构

请求结构不变。

响应结构不强制新增资源字段，但规范中明确：

- 组件在创建后、检测后、构建后所使用的默认资源值必须可通过现有组件详情或查询接口观察到
- MCP 文档与 tool description 必须能解释这些默认值的来源

## 五、核心实现设计
### 5.1 关键逻辑

本次将默认资源策略划分为两层：

- 初始创建默认值
  - 源码组件：`128MB`，CPU 按 `memory / 128 * 20` 计算
  - 软件包组件：`128MB`，CPU 按 `memory / 128 * 20` 计算
  - 镜像组件：`512MB`，CPU 默认为 `0m`
- 检测成功后的规范化默认值
  - 仅适用于源码 / 软件包组件
  - 内存取检测结果中的 `memory`，缺失时回退 `128MB`
  - 内存向下对齐到 `32MB` 整数倍
  - CPU 统一设为 `500m`

部署阶段不再重新决定默认值，只透传组件对象上的 `min_memory` 与 `min_cpu`。

### 5.2 复用现有代码

- 复用 `baseService.calculate_service_cpu`
- 复用 `app_check_service.save_service_info`
- 复用 `source_component_service.auto_create_component`
- 复用 `package_component_service.auto_create_component`
- 复用 `create_region_service` 的资源透传逻辑

### 5.3 规范抽取策略

- 在 `app.py` 中提炼创建默认资源常量与辅助方法
- 在 `app_check_service.py` 中提炼检测后默认资源归一化常量与辅助方法
- 在 `mcp_query_service.py` 中复用统一文案，确保各 MCP 创建工具对外描述一致
- 在 `MCP_CONSOLE_API_SUMMARY_ZH.md` 中增加单独章节，明确该规范属于 MCP 契约的一部分

## 六、实施计划
### Sprint 1: 默认资源规则提炼
#### Task 1.1: 抽取创建默认资源常量
- 文件：`console/services/app.py`
- 实现内容：
  - 抽取源码、软件包、镜像组件的默认内存与 CPU 规则
  - 修正创建代码中的散落常量引用
- 验收标准：
  - 创建默认资源值由显式命名常量或辅助方法统一提供

#### Task 1.2: 抽取检测后默认资源归一化逻辑
- 文件：`console/services/app_check_service.py`
- 实现内容：
  - 提炼检测后内存对齐与 CPU 默认值逻辑
- 验收标准：
  - 检测成功后资源行为不变，但逻辑具备可复用命名

### Sprint 2: MCP 规范上升
#### Task 2.1: 更新 MCP tool description
- 文件：`console/services/mcp_query_service.py`
- 实现内容：
  - 为组件创建与构建相关工具补充默认资源规范描述
- 验收标准：
  - 通过 `tools/list` 可直接看到默认资源策略说明

#### Task 2.2: 更新 MCP 总结文档
- 文件：`../rainbond-agent/MCP_CONSOLE_API_SUMMARY_ZH.md`
- 实现内容：
  - 增加“组件创建默认资源规范”说明
  - 说明不同创建类型与检测阶段的默认值策略
- 验收标准：
  - 文档能独立解释 MCP 默认资源规则

### Sprint 3: 测试与验证
#### Task 3.1: 补充测试覆盖
- 文件：`console/tests/app_service_test.py`、`console/tests/app_check_service_*`、`console/tests/mcp_query_service_test.py`
- 实现内容：
  - 覆盖创建默认资源值
  - 覆盖检测后资源归一化规则
  - 覆盖 MCP description 中的默认资源说明
- 验收标准：
  - 相关测试可证明规范与实现一致

## 七、关键参考代码

| 功能 | 文件 | 说明 |
|------|------|------|
| MCP 工具定义 | `console/services/mcp_query_service.py` | 创建类工具的 schema 与 description |
| 创建初始默认值 | `console/services/app.py` | 各类组件初始资源默认值 |
| 检测后资源归一化 | `console/services/app_check_service.py` | 检测成功后的默认资源覆盖逻辑 |
| 源码一键创建 | `console/services/source_component_service.py` | 高层自动检测与构建流程 |
| 软件包一键创建 | `console/services/package_component_service.py` | 高层软件包检测与构建流程 |
| MCP 总结文档 | `../rainbond-agent/MCP_CONSOLE_API_SUMMARY_ZH.md` | 对外能力说明与工具映射 |
