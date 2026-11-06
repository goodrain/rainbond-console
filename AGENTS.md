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
  urls/                  — URL routing for /console/* endpoints (package; __init__.py + modules)
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
goodrain_web/            — Django project: settings.py, test_settings.py, root urls.py
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
5. Register URL in `console/urls/__init__.py` (or a module under `console/urls/`), with a permission from `console/utils/perms_route_config.py`

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
make check              # Lint with flake8 (max-line 129) + test manifest check
python scripts/run_pytest.py . -- -q   # Run tests the way CI does (sqlite test DB)
make typecheck-gate     # Strict mypy for services/views/repositories/openapi (CI)
python manage.py runserver 0.0.0.0:7070  # Local dev server
```

## Coding Conventions

- Format with `yapf` using `style.cfg` (column_limit=128)
- Lint with `flake8` (max-line-length 129, ignore W605)
- Use singleton pattern for services and repositories
- Import singletons directly: `from console.services.app import app_service`
- Use `general_message()` for API response formatting
- Use `ServiceHandleException` for business errors
- URL patterns use Django `re_path()` with regex; console routes take a permission as the third argument
- Commit messages in English, Conventional Commits format

## Agent Workflow (bug fixes and PRs)

These rules apply to every AI agent working in this repo (Multica agents, the
`claude` / `codex` / `mimo` comment bots, local sessions). CI enforces some of
them; a PR that breaks the others will be sent back.

### Scope

- One issue → one branch → one PR. Make the minimal correct change; do not
  refactor, reformat, rename or upgrade dependencies unless the issue asks for it.
- Find the repo that actually owns the bug before editing
  (UI → `rainbond-ui`, console API / permissions / DB → `rainbond-console`,
  Kubernetes / build / runtime → `rainbond`). A fix that spans repos gets one PR
  per repo, linked to each other.
- Reproduce first. If you cannot reproduce or cannot find the cause, report what
  you checked instead of guessing a fix.

### Branches

- Branch off the latest `main`; name it `fix/<short-slug>` or `feat/<short-slug>`
  (lowercase, no personal names). The comment bots keep the branch name their
  workflow prompt gives them.
- Push the branch to this repository itself, not a fork: the E2E gate only tests
  same-repo branches, and it builds components by branch name.
- Never push to `main`, never merge a PR, never force-push a branch you did not
  create. Humans merge.

### Commits (CI-enforced)

- First line: `type(scope): summary`, type one of
  `feat fix docs style refactor test ci perf revert chore`; English.
- **Every line ≤ 72 characters**, body included (Check Commit Message fails otherwise).
- Sign off every commit: `git commit -s` (the DCO check is required).
- No AI attribution lines (`Co-authored-by` an AI, "Generated with …").

### Tests

- Add a regression test that fails before the fix and passes after it, when the
  code path is testable. Call the real code; never copy the logic under test into
  the test.
- A test marked with a `capability_id` comment must be registered in
  `test-manifest.json` with `scripts/manage_test_manifest.py add` (see above);
  never hand-edit `test-manifest.md`.
- Run the verification commands below and paste the actual results into the PR.

### Pull request

- Title in the same Conventional Commits format. Body:
  **Problem** (link the issue / Multica task), **Root cause**, **Fix**,
  **Verification** (commands and results), **Risk**.
- After `pr-ci-build` passes, request the functional gate by adding the
  `run-e2e` label. It deploys the branch to the shared staging environment and
  reports `e2e/product-gate` on the PR. Runs are serialized; do not re-trigger
  while one is queued. If you cannot add labels, say so in the PR.
- Report back where the task came from: PR link, CI result, E2E result, and
  anything you could not verify.

### Stop and ask a human first when the fix

- changes the database schema (any model field or table) or touches migrations;
- changes an API contract (console ↔ region `/v2/...`, `/openapi/v1/...`,
  response fields) or removes/renames a field;
- adds or renames configuration (env vars, Helm values, CRD fields);
- touches install, upgrade or release paths;
- needs a new dependency, or tests fail for reasons unrelated to your change.

### Never

- Edit `.github/workflows/`, release tooling, or generated files by hand.
- Print, commit or ask for credentials (tokens, passwords, AK/SK, kubeconfig).
- Run anything against production clusters, registries or download sites.

### Verify before opening a PR (rainbond-console)

```bash
pip install -r requirements.txt && bash scripts/install_openapi_client.sh
python scripts/run_pytest.py . -- -q        # or a subset: -- -q console/tests/<file>_test.py
make typecheck-gate                         # CI job "typecheck"
make check                                  # flake8 + test manifest (not run in CI, still required)
```

Tests use `goodrain_web.test_settings` (sqlite). Local dev defaults to sqlite
too (`DB_TYPE` unset); set `DB_TYPE=mysql` and `MYSQL_*` to use MySQL.

### Repo-specific risks (rainbond-console)

- **Schema changes are not applied on upgrade**: images ship without
  `migrations/` (`.dockerignore`), and `entrypoint.sh` regenerates a fresh
  `0001_initial` at every start, which is only faked on existing installations.
  `repair_legacy_schema` creates missing tables but not missing columns, so a new
  model field reaches fresh installs but not upgraded ones. Any model field or
  table change is stop-and-ask, even a nullable one. Never add, edit or rely on
  files under `*/migrations/`, and do not change the migration rules in
  `.gitignore`.
- **API responses**: return `Response(general_message(code, msg, msg_show, ...))`;
  raise `ServiceHandleException` (or a typed error in `console/exception/bcode.py`)
  for business errors. `msg` is English, `msg_show` is the Chinese text users see.
- **Region calls** go through `region_api` (`www/apiclient/regionapi.py`); a new
  region endpoint needs a matching change in `goodrain/rainbond`.
- Do not edit `script/install-rainbond*.sh`, `entrypoint.sh`, `Dockerfile*`,
  `default_region*.py`, `upgrade.py` or vendored code (`www/alipay_direct`,
  `www/utils/mnssdk`) unless the issue is about them.
