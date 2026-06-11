# KubeBlocks BackupRepo Management Spec

This spec implements the approved design document:

`/Users/zhangqihang/MyWork/workrc/rainbond-console/docs/plans/2026-06-09-kubeblocks-backuprepo-management-design.md`

Execution order:

1. `rainbond-plugins/rainbond-kb`: add real Kubernetes `BackupRepo` and `Secret` CRUD, including delete protection and RBAC.
2. `rainbond`: proxy create/update/delete through `/v2/cluster/kubeblocks/backup-repos`.
3. `rainbond-console`: store team-owned S3 repos, generate namespace-prefixed real names, call region API, and enforce ownership before using a repo.
4. `rainbond-ui`: quick-create S3 on database creation and full repo management in component backup tab.

Important constraints:

- Real resource name is `{tenant.namespace}-{name}`.
- Credential Secret is always in `rbd-plugins`.
- Console stores public repo config and ownership only. It never stores or returns access keys.
- `storageProviderRef` is immutable; edit keeps provider fixed.
- Adapter refuses deletion if any KubeBlocks Cluster references `spec.backup.repoName`.
- Creation page only quick-creates S3; component backup tab is the management surface.

Quality gates:

- Adapter: `go test ./...`
- Rainbond: `go test ./api/controller -run KubeBlocks -count=1`, `go build ./...`, `go vet ./...`
- Console: targeted pytest for `kubeblocks_backup_repo`
- UI: `yarn build`
