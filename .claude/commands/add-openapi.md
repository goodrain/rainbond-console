# 新增 OpenAPI 端点

引导开发者在 rainbond-console 的 OpenAPI 模块新增一个外部 API 端点。

OpenAPI 是面向外部集成的 API（路径前缀 `/openapi/v1/`），与内部 Console API 分离。

## 请提供以下信息

1. API 路径（例如：`/openapi/v1/teams/{team_id}/apps`）
2. HTTP 方法（GET/POST/PUT/DELETE）
3. 功能描述

## 实施步骤

### 1. Serializer
- 文件：`openapi/serializer/` 下新建或修改
- 使用 DRF Serializer 定义请求/响应格式

### 2. Service 层（如需）
- 文件：`openapi/services/` 下新建或修改
- 可复用 `console/services/` 中的已有服务

### 3. View 层
- 文件：`openapi/views/` 下新建或修改
- 使用 OpenAPI 专用的认证和权限类
- 参考 `openapi/auth/authentication.py` 和 `openapi/auth/permissions.py`

### 4. URL 注册
- 文件：`openapi/urls.py`
- 使用 `url(r'^...', SomeView.as_view())` 注册

### 5. 验证
```bash
make format
make check
```
