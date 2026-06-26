# Harbor v2.11.2 Deployment Run Log

> Date: 2026-06-26
> App: harbor-poc (app_id 3159), team tynwrm27, region rainbond
> Entry: http://grb6b99c-8080-tynwrm27.dev.goodrain.com

## Result: 9/9 running, Harbor v2.11.2 fully operational

## Components

| Component | Image | k8s_service_name | Status |
|-----------|-------|-----------------|--------|
| harbor-log | goharbor/harbor-log:v2.11.2 | log | running |
| harbor-db | goharbor/harbor-db:v2.11.2 | harbor-postgresql | running |
| harbor-redis | goharbor/redis-photon:v2.11.2 | harbor-redis | running |
| registry | goharbor/registry-photon:v2.11.2 | registry | running |
| registryctl | goharbor/harbor-registryctl:v2.11.2 | registryctl | running |
| harbor-core | goharbor/harbor-core:v2.11.2 | core | running |
| harbor-portal | goharbor/harbor-portal:v2.11.2 | portal | running |
| harbor-jobservice | goharbor/harbor-jobservice:v2.11.2 | jobservice | running |
| harbor-nginx | goharbor/nginx-photon:v2.11.2 | harbor-nginx | running |

## Config Files (Rainbond config-file volumes)

| Volume | Component | Path | Purpose |
|--------|-----------|------|---------|
| core-app-conf | harbor-core | /etc/core/app.conf | Beego app config |
| core-private-key | harbor-core | /etc/core/private_key.pem | Token signing RSA key |
| core-secret-key | harbor-core | /etc/core/key | 16-byte AES encryption key |
| registry-config | registry | /etc/registry/config.yml | Registry storage/auth/redis config |
| registry-root-cert | registry | /etc/registry/root.crt | Token verification certificate |
| registry-config-shared | registryctl | /etc/registry/config.yml | Shared with registry |
| registryctl-config | registryctl | /etc/registryctl/config.yml | Registryctl own config |
| jobservice-config | harbor-jobservice | /etc/jobservice/config.yml | Worker pool/redis/logger config |
| nginx-conf | harbor-nginx | /etc/nginx/nginx.conf | Reverse proxy routing |
| portal-nginx-conf | harbor-portal | /etc/nginx/nginx.conf | Static file server |
| logrotate-conf | harbor-log | /etc/logrotate.d/logrotate.conf | Log rotation |

## Blockers Encountered (Harbor Playbook)

| ID | Symptom | Root Cause | Fix | Loop Round |
|----|---------|-----------|-----|------------|
| HB-01 | registry panic: missing `/etc/registry/root.crt` | Harbor `prepare` script generates token auth cert; manual deploy must replicate | Generate RSA key pair, mount cert on registry + privkey on core | 1 |
| HB-02 | jobservice crash: `POSTGRESQL_PORT=tcp://...` parse error | K8s auto-injects `POSTGRESQL_PORT=tcp://IP:PORT` for service named `postgresql` | Rename k8s_service_name from `postgresql` to `harbor-postgresql` | 2 |
| HB-03 | registryctl crash: missing `/etc/registryctl/config.yml` | Forgot to create registryctl config volume | Create config-file volume | 2 |
| HB-04 | nginx crash: `/etc/nginx/client_body_temp` permission denied | Non-root user can't write to `/etc/nginx/` | Add `*_temp_path /tmp/` directives to nginx.conf | 2 |
| HB-05 | DB tables missing (`relation "properties" does not exist`) | First DB init used literal `**None:group**` as password; re-deploy with real password triggers fresh DB init + full migration | Set real DB password, redeploy (ephemeral storage = fresh init) | 3 |
| HB-06 | registryctl needs `/etc/registry/config.yml` too | registryctl reads registry's config to load storage driver | Mount same registry config.yml on registryctl | 3 |
| HB-07 | jobservice core 500: `failed to load rest config` | Core not fully initialized when jobservice starts (startup order) | Rebuild jobservice after core stabilizes | 3 |

## Key Differences vs Dify

| Aspect | Dify | Harbor |
|--------|------|--------|
| Config style | Env vars only | Config files (YAML/conf) + env vars |
| Key material | None (all env-based) | RSA key pair + AES secret key + token auth cert |
| DB image | Standard postgres:15-alpine | goharbor/harbor-db (custom init scripts) |
| K8s service name collision | Underscore names illegal | `postgresql` collides with K8s auto-injected env |
| Shared config | None | registry + registryctl share config.yml |
| Startup order sensitivity | Low (components mostly independent) | High (jobservice depends on core being fully ready) |

## Smoke Test

```
$ curl -sk http://grb6b99c-8080-tynwrm27.dev.goodrain.com/api/v2.0/systeminfo
{"auth_mode":"db_auth","harbor_version":"v2.11.2-201d421d","self_registration":false}
```

## Secret Groups for Template (when sanitized)

| Group | Env Name | Components |
|-------|---------|------------|
| harbor_db_password | POSTGRES_PASSWORD / POSTGRESQL_PASSWORD | harbor-db, harbor-core |
| core_secret | CORE_SECRET | harbor-core, registryctl, harbor-jobservice |
| jobservice_secret | JOBSERVICE_SECRET | harbor-core, registryctl, harbor-jobservice |
| csrf_key | CSRF_KEY | harbor-core |
| harbor_admin_password | HARBOR_ADMIN_PASSWORD | harbor-core |
| registry_password | REGISTRY_CREDENTIAL_PASSWORD | harbor-core, harbor-jobservice |

Note: RSA key pair and AES secret key are mounted as config-file volumes, not env vars. They need separate parameterization strategy for templates (generate at install time or include in template as-is with rotation documentation).
