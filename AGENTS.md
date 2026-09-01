# Rainbond Console — Python/Django Backend

## Overview

Rainbond Console is the web backend for the Rainbond platform. It serves the React frontend (`rainbond-ui`) and proxies/orchestrates calls to the Go core services (`rainbond`).

- Language: Python 3.11
- Framework: Django 5.2 (LTS) + Django REST Framework 3.16
- Auth: JWT (djangorestframework-simplejwt)
- Database: MySQL (shared with Go services)
- Code formatter: yapf (config: `style.cfg`)
- Linter: flake8 (max-line-length 129)

## Key Directories

```
console/
  views/                 — DRF API views (HTTP layer)
    base.py              — Base view classes (JWTAuthApiView, TenantHeaderView, etc.)
    app_config/          — Component configuration views
    app_create/          — Component creation views
    app/                 — Application-level views
  services/              — Business logic layer (singleton instances)
  repositories/          — Data access layer (singleton instances)
  models/                — Django ORM models
  urls.py                — URL routing for /console/* endpoints
  utils/                 — Shared utilities, permissions
openapi/
  views/                 — OpenAPI v1 views (external API)
  serializer/            — DRF serializers for OpenAPI
  services/              — OpenAPI business logic
  urls.py                — URL routing for /openapi/v1/* endpoints
  auth/                  — OpenAPI authentication
www/
  apiclient/
    regionapi.py         — RegionInvokeApi: HTTP client to call Go backend
    regionapibaseclient.py — Base HTTP client for region API calls
region_client/           — Region API client utilities
goodrain_web/            — Legacy web module
```

## Architecture: Request Flow

```
rainbond-ui (React)
    ↓ HTTP (/console/*, /openapi/v1/*)
Django URL Router → DRF View.initial() → View method (get/post/put/delete)
    ↓                    ↓
    ↓              Auth + Permission + Tenant context injection
    ↓
Service layer (business logic)
    ↓
Repository layer (database queries)
    ↓
RegionInvokeApi (HTTP calls to Go backend at /v2/tenants/...)
```

## View Class Hierarchy

```
APIView (DRF)
  └── BaseApiView              — No auth required (AllowAny + safe JWT)
  └── AlowAnyApiView           — No auth at all
  └── JWTAuthApiView           — JWT auth + enterprise permissions
      └── EnterpriseAdminView  — + enterprise user context
      └── CloudEnterpriseCenterView — + OAuth context
      └── TenantHeaderView     — + team/tenant context + team permissions
          (most common base class for team-scoped APIs)
```

Choose the right base class:
- Public endpoint → `AlowAnyApiView`
- Authenticated, no team context → `JWTAuthApiView`
- Team-scoped endpoint → `TenantHeaderView` (provides `self.tenant`, `self.team`, `self.user`)

## Adding a New Console API

1. Add Django model in `console/models/main.py` if new table needed
2. Add repository in `console/repositories/` with singleton instance at module bottom
3. Add service in `console/services/` with singleton instance at module bottom
4. Add view in `console/views/` inheriting appropriate base class
5. Register URL in `console/urls.py`

## Adding a New OpenAPI Endpoint

1. Add serializer in `openapi/serializer/`
2. Add service in `openapi/services/` if needed
3. Add view in `openapi/views/`
4. Register URL in `openapi/urls.py`

## Code Patterns

### Service Singleton Pattern
```python
# At the bottom of console/services/some_service.py
class SomeService:
    def do_something(self, tenant, ...):
        # business logic
        repo_instance.get_by_id(...)
        region_api.call_something(...)

some_service = SomeService()  # singleton instance
```

### Repository Singleton Pattern
```python
# At the bottom of console/repositories/some_repo.py
class SomeRepository:
    def get_by_id(self, pk):
        return SomeModel.objects.get(pk=pk)

some_repo = SomeRepository()  # singleton instance
```

### View Pattern
```python
class SomeView(TenantHeaderView):
    def get(self, request, *args, **kwargs):
        # self.user, self.tenant, self.team available from base class
        result = some_service.get_data(self.tenant, ...)
        return Response(general_message(200, "success", "OK", bean=result))

    def post(self, request, *args, **kwargs):
        serializer = SomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = some_service.create(self.tenant, serializer.validated_data)
        return Response(general_message(200, "success", "OK", bean=result))
```

### Region API Call Pattern
```python
# In service layer, call Go backend via region API
from www.apiclient.regionapi import RegionInvokeApi
region_api = RegionInvokeApi()
region_api.some_method(region_name, tenant_name, ...)
```

## Cross-Repository Relationships

- Called by: `rainbond-ui` (React) via `/console/*` and `/openapi/v1/*`
- Calls: `rainbond` (Go) via `RegionInvokeApi` → `/v2/tenants/{tenant_name}/...`
- Shared database: MySQL (both console and Go services read/write same tables)

## Build & Verify

```bash
make format             # Format code with yapf
make check              # Lint with flake8 (max-line 129)
pytest                  # Run tests
python manage.py runserver 0.0.0.0:7070  # Local dev server
```

## Coding Conventions

- Format with `yapf` using `style.cfg` (column_limit=128)
- Lint with `flake8` (max-line-length 129, ignore W605)
- Use singleton pattern for services and repositories
- Import singletons directly: `from console.services.app import app_service`
- Use `general_message()` for API response formatting
- Use `ServiceHandleException` for business errors
- URL patterns use Django `url()` with regex
- Commit messages in English, Conventional Commits format

## Rainbond Development Workflow Override

When working in this Rainbond repository, the development flow MUST follow this chain automatically. The user does NOT need to type any slash command — each step flows into the next naturally.

### Automatic Flow Chain

1. **User describes a feature or task** (natural language)
2. **Superpowers brainstorming activates** (auto, via session hook — do NOT skip)
   - After approval, the design document MUST use the **Rainbond 7-section template** (see below)
   - Save to `docs/plans/YYYY-MM-DD-<topic>-design.md` and git commit
3. **Superpowers worktrees** — create isolated workspace
4. **Run `/spec-gen`** — convert design document into YAML task specification with commit grouping, 2-5 min step granularity, complete code, and line-number precision (replaces `writing-plans`)
5. **Execution** — use Superpowers `subagent-driven-development` via `/spec-driven`:
   - For each commit group, dispatch a **fresh subagent** per task
   - Each subagent follows `test-driven-development` (Red-Green-Refactor) **for Go/Python**
   - **For React (rainbond-ui):** use `yarn build` as quality gate + `frontend-patterns` review (no TDD)
   - After each task: **two-stage review** (spec compliance → code quality)
   - When all tasks pass review → `git commit` with the spec's commit message
   - Proceed to next commit group
6. **If tasks are independent** → use Superpowers `dispatching-parallel-agents`
7. **After all commits** → run `/go-review` (Go) or `/python-review` (Python) or `frontend-patterns` (React)
8. **If cross-repo** → run `/check-api-compat`
9. **Finally** → use Superpowers `finishing-a-development-branch`

### Rainbond 7-Section Design Template

When brainstorming produces a design document for this Rainbond repository, it MUST follow this structure:

```markdown
# {项目名称} 设计文档

## 一、项目背景
### 1.1 项目架构
### 1.2 现有基础
### 1.3 核心需求

## 二、整体架构设计
### 2.1 系统架构图
### 2.2 核心流程

## 三、数据模型设计
### 3.1 新增数据库表
### 3.2 数据关系

## 四、API设计
### 4.1 接口列表
### 4.2 请求/响应结构

## 五、核心实现设计
### 5.1 关键逻辑
### 5.2 复用现有代码

## 六、实施计划
### Sprint 1: {阶段名称}
#### Task 1.1: {任务名称}
- 文件：{精确路径:行号}
- 实现内容：
- 验收标准：

## 七、关键参考代码
| 功能 | 文件 | 说明 |
|------|------|------|
```

### What comes from where

| Capability | Source | Why |
|-----------|--------|-----|
| Requirement discussion + hard gate | Superpowers `brainstorming` | Mandatory, cannot be skipped |
| 7-section design template | Project instructions (injected into brainstorming) | Rainbond-specific architecture |
| Isolated workspace | Superpowers `using-git-worktrees` | Branch isolation |
| YAML spec + commit grouping + 2-5 min steps | Rainbond `/spec-gen` (replaces `writing-plans`) | Richer structure than writing-plans |
| Fresh subagent per task | Superpowers `subagent-driven-development` | Solves context pollution |
| Two-stage adversarial review | Superpowers `subagent-driven-development` | Spec compliance + code quality |
| Parallel task execution | Superpowers `dispatching-parallel-agents` | Speed up independent tasks |
| TDD iron law | Superpowers `test-driven-development` | No code without failing test |
| Evidence before completion | Superpowers `verification-before-completion` | No unverified claims |
| Commit grouping + auto-commit | Rainbond `/spec-driven` | Logical commit units |
| Language-specific review | ECC `/go-review`, `/python-review` | Idiomatic checks |
| Cross-repo API check | Rainbond `/check-api-compat` | Multi-repo consistency |
| Branch completion | Superpowers `finishing-a-development-branch` | Merge/PR workflow |

### Key Rules

- **Do NOT use `writing-plans`** in this Rainbond repository — `/spec-gen` replaces it with YAML + commit grouping + step-level code
- **DO use `subagent-driven-development`** — it provides the execution engine (subagent isolation + adversarial review)
- **DO use `executing-plans`** as alternative — for parallel session batch execution
