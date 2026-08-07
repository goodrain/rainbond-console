# External Telemetry Switch Implementation Spec

Design: `docs/plans/2026-08-06-external-telemetry-switch-design.md`

## Commit 1: Console runtime switch

1. Add failing platform settings tests for a default-on global telemetry setting and updates.
2. Implement `EXTERNAL_TELEMETRY_ENABLED` using `ConsoleSysConfig` with environment variables taking precedence.
3. Add failing tests proving runtime Sentry and proxy suppression plus non-blocking PostHog behavior.
4. Implement Sentry runtime dropping, proxy early returns, and a bounded daemon worker for PostHog events.
5. Run focused pytest, py_compile, flake8, manifest validation, and diff checks.

## Commit 2: Rainbond UI switch

1. Pass `enable_external_telemetry` through the existing platform settings service.
2. Merge it into the existing global enterprise state.
3. Render a default-on switch under Platform Management → Settings → Basic Settings.
4. Add Simplified Chinese and English copy.
5. Run `yarn build` and frontend pattern review.
