# Rainbond Console — Python/Django Backend

## Overview

Rainbond Console is the web backend for the Rainbond platform. It serves the React frontend (`rainbond-ui`) and proxies/orchestrates calls to the Go core services (`rainbond`).

- Language: Python 3.6
- Framework: Django 2.2 + Django REST Framework 3.8
- Auth: JWT (djangorestframework-jwt)
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
