# Local Snapshot Offline Upgrade — Execution Specification

Design: `docs/plans/2026-08-14-local-snapshot-offline-upgrade-design.md`

## Commit 1 — `fix: detect local snapshot upgrades in offline mode`

1. Add a managed regression test in `console/tests/market_app_service_test.py` proving that, with cloud-market access disabled, a locally installed snapshot at `1.0.2` sees local version `1.0.3` as upgradeable. Register `console.market-app.local-snapshot-offline-upgrade` in `test-manifest.json`.
2. Run the test and observe the current failure caused by the global early return in `get_market_apps_in_app`.
3. Make `MarketAppService` source-aware: retain the cloud-market guard only for cloud-installed sources; continue local repository lookup for local templates and snapshots.
4. Run focused tests, the manifest validator, `make check`, then complete specification and quality reviews before committing.
