# Browser Slow Request Offline Control Spec

- Design doc: `/Users/goodrain/.config/superpowers/worktrees/rainbond-ui/browser-slow-request-telemetry/docs/plans/2026-07-23-browser-slow-request-telemetry-design.md`
- Scope: `rainbond-console`
- Goal: guarantee that `DISABLE_DEFAULT_APP_MARKET=true` prevents browser Sentry initialization and upstream proxy traffic without changing the Console server SDK.

## Execution Order

1. Add the failing offline configuration tests, then reuse `is_offline_mode()` in frontend config generation only.
2. Add the failing offline proxy test, then short-circuit POST handling before any upstream work.
3. Run the focused tests, affected-file lint, and test-manifest validation.

## Required Behavior

- Online configuration and proxy behavior are unchanged.
- Console server SDK configuration is unchanged.
- Offline frontend config returns `enabled=false` and `dsn=""`.
- `DISABLE_CLOUD_MARKET=true` alone does not disable frontend Sentry.
- Offline proxy POST returns 204 with existing CORS headers.
- `_send_upstream_request` is never called offline.

## Commit

`fix: disable Sentry in offline mode`

## Baseline Note

The repository-wide `make check` command was run and remains red on the existing
lint baseline across unrelated files. This change is gated by the focused tests,
affected-file lint (with the touched file's existing E501/E302 debt excluded),
and test-manifest validation; it does not expand into repository-wide cleanup.
