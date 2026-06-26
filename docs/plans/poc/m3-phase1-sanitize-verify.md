# M3 Phase 1: Sanitized Snapshot → Reinstall Verification

> Date: 2026-06-26
> App: dify-m3-verify (app_id 3156), installed from sanitized snapshot of dify-poc (app_id 3141)
> Team: tynwrm27, Region: rainbond

## Objective

Verify that a Dify deployment snapshot can be sanitized (sensitive envs cleared, gateway URLs removed) and successfully reinstalled with fresh secrets — proving the "safe, portable template" workflow works end-to-end.

## Research Findings

### Platform Native Env Parameterization

| Mechanism | Supported? | Detail |
|-----------|-----------|--------|
| `**None**` auto-generation on install | Only outer envs | `service_connect_info_map_list` entries with `attr_value="**None**"` → `make_uuid()[:8]` at install time (`new_components.py:287-288`) |
| User-must-fill at install | No | No `is_required` field, no pre-install editing UI |
| Inner env auto-generation | No | `service_env_map_list` entries copy `**None**` as literal string |
| Cross-component secret groups | No | No mechanism to link secrets across components |

**Conclusion**: All Dify sensitive envs are inner envs. The native `**None**` mechanism doesn't apply. Cross-component secret matching (e.g., same DB_PASSWORD on postgres/api/worker/plugin-daemon) has no platform support.

### Chosen Approach: Three-Step Install (Zero Platform Code Change)

1. **Sanitized snapshot**: Replace sensitive env values with `""` in `share_service_list` parameter of `create_app_version_snapshot`
2. **Install without deploy**: `create_app_from_snapshot_version` with `is_deploy=false`
3. **Post-install secret injection**: Generate grouped secrets, update all components via `manage_component_envs`, then `operate_app(start)`

## Execution Log

### Step 1: Create Sanitized Snapshot

- Source: dify-poc (app_id 3141), snapshot v1.14.2 (version_id 492)
- Sanitized 23 env values across 7 components:
  - 6 secret groups (SECRET_KEY, POSTGRES_PASSWORD/DB_PASSWORD, WEAVIATE_API_KEY, sandbox API_KEY, PLUGIN_DAEMON_KEY/SERVER_KEY, INNER_API_KEY) → `""`
  - 4 gateway URL envs (CONSOLE_WEB_URL, APP_WEB_URL, CONSOLE_API_URL, APP_API_URL) → `""`
- Output: snapshot version_id 501, version `1.14.2-safe`
- Diff verified: only env value changes, no structural changes

### Step 2: Install from Sanitized Snapshot

- Target: dify-m3-verify (app_id 3156) in same team tynwrm27
- `is_deploy=false` — components created but not started
- **DNS collision handling**: Same team → k8s_service_names auto-suffixed:
  - `redis` → `redis-45eb`
  - `db-postgres` → `db-postgres-6a05`
  - `weaviate` → `weaviate-7047`
  - `api` → `api-ec02`
  - `sandbox` → `sandbox-80f4`
  - `web` → `web-e219`
  - `plugin-daemon` → `plugin-daemon-6627`
  - `nginx` → `gre6dee1-aabd`
- **Critical finding**: Inner env host references (DB_HOST, REDIS_HOST, CELERY_BROKER_URL, etc.) are NOT updated to match suffixed names. Only connection env (outer) HOST values are updated.

### Step 3: Post-Install Secret Injection + Host Env Fix

Generated 6 secret groups:
- DB_PASSWORD: 16 chars random
- SECRET_KEY: sk- prefix + 48 chars
- WEAVIATE_API_KEY: 36 chars
- SANDBOX_API_KEY: 24 chars
- PLUGIN_DAEMON_KEY: 48 chars
- INNER_API_KEY: 48 chars

Updated envs on 7 components (parallel batch upsert):
- **Secrets**: Each group set to same value on all relevant components
- **Host envs**: Updated to suffixed k8s_service_names (db-postgres-6a05, redis-45eb, etc.)
- **URL envs in URLs**: CELERY_BROKER_URL, WEAVIATE_ENDPOINT, CODE_EXECUTION_ENDPOINT, PLUGIN_DAEMON_URL, etc.
- **Nginx config-file**: Updated proxy_pass targets to `api-ec02:5001` and `web-e219:3000`

### Step 4: Deploy and Verify

- `operate_app(deploy)` → build success but pods stayed "closed" (build-only for market-installed components)
- `operate_app(start)` → pods created and started
- Health: **9/9 running**, all `critical_blocker: null`
- Nginx entry: `http://gr3e3f70-80-tynwrm27.dev.goodrain.com/console/api/setup` → `{"step":"not_started"}` ✅
- Runtime env verification (exec into api pod):
  - SECRET_KEY = new value (not original `sk-jhGabJ6v6O/...`) ✅
  - DB_PASSWORD = new value (not `difyai123456`) ✅
  - CONSOLE_WEB_URL = empty (not original gateway domain) ✅
  - All 6 secret groups = freshly generated ✅

## Key Discoveries

### 1. `deploy` vs `start` for Market-Installed Components

`operate_app(deploy)` on freshly installed market components triggers build (image pull → internal registry push) but does NOT start pods. Must follow with `operate_app(start)` or use the original install with `is_deploy=true`.

### 2. Same-Team DNS Collision is Manageable but Costly

Installing same app twice in same team requires updating ALL inner env host references — a ~40-env mass update across 4 components. In production, templates should be installed into fresh teams/namespaces to avoid this.

### 3. Inner Env `**None**` Gap

The platform's `**None**` auto-generation only works for outer envs. A future platform enhancement to support `**None**` for inner envs + secret group linking would make the three-step install collapse to one step.

### 4. `share_service_list` Override Works

The `create_app_version_snapshot` `share_service_list` parameter successfully overrides env values in the snapshot template. However, `_hydrate_snapshot_delivery_info` still overrides `share_image`/`service_image` with internal registry paths — image rewriting needs a different approach (M3 Phase 2).

## Verification Checklist

- [x] Sanitized snapshot created with 0 leaked secrets
- [x] Install from snapshot succeeded (9 components)
- [x] Fresh secrets generated and injected consistently across components
- [x] DNS collision handled (host envs + nginx config updated)
- [x] 9/9 components running
- [x] Nginx single-entry accessible (setup API responds)
- [x] No original secrets in runtime env (verified via exec)
- [x] No gateway domain in runtime env (URL envs empty)

## Assets

- Sanitized snapshot: version_id 501, version `1.14.2-safe` on dify-poc (app_id 3141)
- Verification app: dify-m3-verify (app_id 3156) — **can be cleaned up after review**
- Original dify-poc (app_id 3141) — **preserved, do not delete**
- Sanitize script: `docs/plans/poc/sanitize_snapshot_template.py`
