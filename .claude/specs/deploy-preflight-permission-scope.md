# Deploy Preflight Permission Scope Spec

- Design: `docs/plans/2026-07-28-deploy-preflight-permission-scope-design.md`
- Repository: `rainbond-console`
- Commit: `fix: respect deploy preflight permission scope`

## Required Behavior

1. A top-level `group_id` selects that application's permission scope.
2. The legacy nested `payload.group_id` remains supported.
3. Existing applications require `300013` in the selected application scope.
4. Requests without `group_id` require team-level `300001`.
5. Invalid non-empty group IDs remain on the stricter component-create path.
6. The endpoint and preflight response contracts do not change.

## Verification

Run the focused regression suite first, then validate `test-manifest.json`, lint the affected Python files, and run `make check`.

