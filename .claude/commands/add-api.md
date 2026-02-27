# 新增 Console API

引导开发者在 rainbond-console 新增一个 API 端点。

## 请提供以下信息

1. API 路径（例如：`/console/teams/{tenantName}/apps/{app_id}/something`）
2. HTTP 方法（GET/POST/PUT/DELETE）
3. 功能描述
4. 是否需要调用 Go 后端 API？
5. 是否需要新的数据库表？

## 实施步骤

### 1. 数据模型（如需新表）
- 文件：`console/models/main.py`
- 定义 Django Model 类

### 2. Repository 层
- 文件：`console/repositories/` 下新建或修改
- 在文件底部创建单例：`some_repo = SomeRepository()`
- 实现数据库查询方法

### 3. Service 层
- 文件：`console/services/` 下新建或修改
- 在文件底部创建单例：`some_service = SomeService()`
- 实现业务逻辑，调用 repository 和 region API

### 4. Region API 调用（如需调用 Go 后端）
- 文件：`www/apiclient/regionapi.py`
- 在 `RegionInvokeApi` 类中添加方法
- 使用 `self._get/self._post/self._put/self._delete` 发送请求

### 5. View 层
- 文件：`console/views/` 下新建或修改
- 选择合适的基类：
  - 无需认证：`AlowAnyApiView`
  - 需要认证：`JWTAuthApiView`
  - 需要团队上下文：`TenantHeaderView`（最常用）
- 实现 `get/post/put/delete` 方法

### 6. URL 注册
- 文件：`console/urls.py`
- 使用 `url(r'^...', SomeView.as_view())` 注册

### 7. 验证
```bash
make format
make check
```
