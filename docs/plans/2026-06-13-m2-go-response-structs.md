# M2 — Go Backend HTTP Response Structs (for console TypedDicts)

READ-ONLY extraction from `/Users/yangk/code/rainbond` (Go core). Goal: capture the
exact JSON shape of the response `data` (`bean` / `list`) for the highest-frequency
`/v2/tenants/...` endpoints that `rainbond-console`'s `www/apiclient/regionapi.py` calls,
so they can be turned into Python `TypedDict`s.

## How the Go side builds responses

All success responses go through a single envelope helper:

- `util/http/api.go:164` — `func ReturnSuccess(r, w, datas interface{})`
  - `datas == nil` → `{"bean": null}`
  - `datas` is a **slice** → wrapped as `{"list": datas}`
  - otherwise → wrapped as `{"bean": datas}`
- `util/http/api.go:180` — `ReturnList(...)` → `{"list": ..., "number": N, "page": P}`

Envelope struct `ResponseBody` (`util/http/api.go:126`):

| json key | Go type | optional? | notes |
|---|---|---|---|
| `validation_error` | url.Values (map[string][]string) | omitempty | only on validation errors |
| `msg` | string | omitempty | error/info message |
| `bean` | interface{} | omitempty | single-object payload (most endpoints) |
| `list` | interface{} | omitempty | array payload |
| `number` | int | omitempty | total count (paged lists) |
| `page` | int | omitempty | current page (paged lists) |

So on the console side, a typical response is `{"bean": <struct below>}` or
`{"list": [<struct below>, ...]}`. Note: console code often also wraps the region call
again; the structs below describe **the Go `data` payload** only.

### Route → handler wiring

- Router: `api/api_routers/version2/v2Routers.go` (chi). `/v2` → `tenantRouter()` →
  `tenantNameRouter()` → `serviceRouter()` (mounted at `/services/{service_alias}`) and
  `applicationRouter()` (at `/apps/{app_id}`).
- Handlers live in `api/controller/*.go`; business logic + struct assembly in
  `api/handler/*.go`; struct definitions in `api/model/*.go` and `db/model/*.go`.

### Caveats / confidence

- **Confidence HIGH** for structs whose handler returns a named Go struct (`ReturnSuccess(r, w, sl)`).
- **Confidence MEDIUM** where the handler returns `map[string]interface{}` or
  `[]map[string]interface{}` — keys are hardcoded in code, listed below but no compile-time guarantee.
- Many DB-model responses embed `Model` (`db/model/tenant.go:30`), which adds
  `ID uint` (json key **`ID`**, no tag → capital) and `create_time` (time.Time).
- Go `time.Time` serializes as an RFC3339 string in JSON → map to Python `str`.
- Pointer fields (`*X`) and `omitempty` → `NotRequired`/`Optional` in TypedDict.
- `*bool` / `*int` → value may be `null` → `Optional`.
- Embedded `Model` repeated in every DB struct is noted once per struct as "(+ Model: `ID`, `create_time`)".

Type mapping cheat-sheet: Go `string`→`str`, `int/int32/int64/uint`→`int`,
`bool`→`bool`, `float64`→`float`, `time.Time`→`str`, `[]X`→`List[X]`,
`map[string]string`→`Dict[str, str]`, `*X`→`Optional[X]`.

---

## 1. ServiceEvent — async/sync action result

**Endpoints (all return `{"bean": ServiceEvent}`):**
`POST .../services/{alias}/build`, `/start`, `/stop`, `/restart`, `/upgrade`, `/rollback`,
`PUT .../vertical`, `PUT .../horizontal`. Controller: `api/controller/service_action.go`
(`sEvent := ctx.Value("event")`, `ReturnSuccess(r, w, sEvent)` e.g. line 116, 166, 245).
Struct: `db/model/event.go:79`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| (ID) | uint | — | `json:"-"` → **omitted** |
| `create_time` | string | no | |
| `event_id` | string | no | |
| `tenant_id` | string | no | |
| `service_id` | string | no | |
| `target` | string | no | |
| `target_id` | string | no | |
| `request_body` | string | no | |
| `user_name` | string | no | |
| `start_time` | string | no | |
| `end_time` | string | no | |
| `opt_type` | string | no | |
| `syn_type` | int | no | 0/1 |
| `status` | string | no | |
| `final_status` | string | no | |
| `message` | string | no | |
| `reason` | string | no | |

---

## 2. StatusList — single component status

**Endpoint:** `GET .../services/{alias}/status`. Controller `api/controller/resources.go:799`
→ handler `GetStatus` `api/handler/service.go:2637`. Struct `api/model/model.go:682`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `tenant_id` | string | no | |
| `service_id` | string | no | |
| `service_alias` | string | no | |
| `deploy_version` | string | no | |
| `replicas` | int | no | |
| `container_memory` | int | no | (Go field ContainerMem) |
| `cur_status` | string | no | e.g. running/closed/undeploy |
| `container_cpu` | int | no | |
| `status_cn` | string | no | localized status |
| `start_time` | string | no | |
| `pod_list` | List[PodsList] | no | see §3 |
| `vm_restore` | Optional[VMRestore] | omitempty | only for VM components |

### PodsList (§3) — `api/model/model.go:723`

| json key | Go type | optional? | notes |
|---|---|---|---|
| `pod_ip` | string | no | |
| `phase` | string | no | |
| `pod_name` | string | no | |
| `node_name` | string | no | |

### VMRestore — `api/model/model.go:698` (only present for VM kind)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `status` | string | no | |
| `status_cn` | string | no | |
| `progress` | string | no | |
| `message` | string | no | |
| `data_volumes` | List[VMRestoreDataVolume] | no | `{name, phase, progress, message}` |
| `importer_pods` | List[VMRestoreImporterPod] | no | `{name, volume, namespace}` |

---

## 3. Batch status list — `services_status`

**Endpoint:** `POST .../services_status`. Controller `api/controller/resources.go:836` →
handler `GetServicesStatus` `api/handler/service.go:2680`. Returns a **slice of map** →
`{"list": [...]}`. **Confidence MEDIUM** (hardcoded map keys, `api/handler/service.go:2720`).

| json key | Go type | optional? | notes |
|---|---|---|---|
| `service_id` | string | no | |
| `status` | string | no | |
| `status_cn` | string | no | |
| `used_mem` | int | no | always `0` in current code |

---

## 4. GetSingleServiceInfo — `{"bean": map}`

**Endpoint:** `GET .../services/{alias}`. Controller `api/controller/resources.go:955`.
Returns `map[string]string`. **Confidence HIGH** (keys hardcoded, lines 982-985).

| json key | Go type | optional? | notes |
|---|---|---|---|
| `tenantName` | string | no | camelCase! |
| `serviceAlias` | string | no | |
| `tenantId` | string | no | |
| `serviceId` | string | no | |

---

## 5. K8sPodInfos — component pods (new/old)

**Endpoint:** `GET .../services/{alias}/pods`. Controller `api/controller/resources.go:1706`
→ `GetPods` `api/handler/service.go:2928`. Struct `api/handler/service.go:2913`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `new_pods` | List[K8sPodInfo] | no | may be null |
| `old_pods` | List[K8sPodInfo] | no | may be null |

### K8sPodInfo — `api/handler/service.go:2919`

| json key | Go type | optional? | notes |
|---|---|---|---|
| `pod_name` | string | no | |
| `pod_ip` | string | no | |
| `pod_status` | string | no | |
| `service_id` | string | no | |
| `container` | Dict[str, Dict[str, str]] | no | container_name → {field → value} |

---

## 6. PodDetail — pod detail / kubeblocks pod detail

**Endpoint:** `GET .../services/{alias}/pods/{pod_name}/detail` (also
`GET .../pods/{pod_name}`). Struct `api/model/pods.go:4`. All fields `omitempty`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `name` | string | omitempty | |
| `node` | string | omitempty | |
| `start_time` | string | omitempty | |
| `status` | Optional[PodStatus] | omitempty | |
| `ip` | string | omitempty | |
| `init_containers` | List[PodContainer] | omitempty | |
| `containers` | List[PodContainer] | omitempty | |
| `events` | List[PodEvent] | omitempty | |

### PodStatus `api/model/pods.go:16` — `{type:int, type_str, reason, message, advice}` (all omitempty)
### PodContainer `api/model/pods.go:25` — `{image, state, reason, started, limit_memory, limit_cpu}` (all omitempty)
### PodEvent `api/model/pods.go:35` — `{type, reason, age, message}` (all omitempty)

---

## 7. PodExecResult — exec in pod

**Endpoint:** `POST .../services/{alias}/pods/{pod_name}/exec`. Struct `api/model/pods.go:56`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `stdout` | string | no | |
| `stderr` | string | no | |
| `exit_code` | int | no | |
| `truncated` | bool | no | |

---

## 8. VersionInfo — build version (deploy/build version info)

**Endpoints:** `GET .../services/{alias}/build-version/{v}`,
`GET .../services/{alias}/deployversion`, `POST .../deployversions` (list).
Controller `api/controller/service_action.go:628,639,674`. Struct `db/model/version.go:30`.
(+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | from embedded Model |
| `build_version` | string | no | |
| `event_id` | string | no | |
| `service_id` | string | no | |
| `kind` | string | no | |
| `delivered_type` | string | no | image / slug |
| `delivered_path` | string | no | |
| `image_name` | string | no | |
| `cmd` | string | no | |
| `repo_url` | string | no | |
| `code_version` | string | no | |
| `code_branch` | string | no | |
| `code_commit_msg` | string | no | |
| `code_commit_author` | string | no | |
| `final_status` | string | no | success/failure/lost |
| `finish_time` | string | no | time.Time |
| `plan_version` | string | no | |

Note: `POST .../deployversions` returns `{"list": [VersionInfo, ...]}`; entries can be `null`
when a service has no matching version (`api/controller/service_action.go:672` appends nil).

---

## 9. TenantServices (DB) — list components of an app

**Endpoint:** `GET .../apps/{app_id}/services` returns `ListServiceResponse` (§10) whose
`services` are `TenantServices`. Struct `db/model/tenant.go:233`. (+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | Model |
| `tenant_id` | string | no | |
| `service_id` | string | no | |
| `service_key` | string | no | |
| `service_alias` | string | no | |
| `service_name` | string | no | |
| `service_type` | string | no | (deprecated, see extend_method) |
| `comment` | string | no | |
| `container_cpu` | int | no | |
| `container_memory` | int | no | |
| `container_gpu` | int | no | |
| `upgrade_method` | string | no | Rolling/OnDelete |
| `extend_method` | string | no | stateless_singleton等 |
| `replicas` | int | no | |
| `deploy_version` | string | no | |
| `category` | string | no | |
| `cur_status` | string | no | |
| `status` | int | no | (deprecated) |
| `event_id` | string | no | |
| `namespace` | string | no | |
| `update_time` | string | no | time.Time |
| `service_origin` | string | no | |
| `kind` | string | no | internal/third_party/custom |
| `app_id` | string | no | |
| `k8s_component_name` | string | no | |
| `job_strategy` | string | no | |

---

## 10. ListServiceResponse / ListAppResponse — paged wrappers

**Endpoints:** `GET .../apps/{app_id}/services` → `ListServiceResponse` (`api/model/model.go:2108`);
`GET .../apps` → `ListAppResponse` (`api/model/model.go:2101`). Returned as `{"bean": ...}`.

### ListAppResponse

| json key | Go type | optional? | notes |
|---|---|---|---|
| `page` | int | no | |
| `pageSize` | int | no | camelCase |
| `total` | int | no | int64 |
| `apps` | List[Application] | no | see §11 |

### ListServiceResponse — same shape, `services: List[TenantServices]` (§9).

---

## 11. Application (DB) — app/group info

**Endpoints:** entries inside `ListAppResponse.apps`; also app create/get.
Struct `db/model/application.go:42`. (+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | Model |
| `eid` | string | no | |
| `tenant_id` | string | no | |
| `app_name` | string | no | |
| `app_id` | string | no | |
| `app_type` | string | no | default 'rainbond' |
| `app_store_name` | string | no | |
| `app_store_url` | string | no | |
| `app_template_name` | string | no | |
| `version` | string | no | |
| `governance_mode` | string | no | |
| `k8s_app` | string | no | |

---

## 12. AppStatus — application runtime status

**Endpoint:** `PUT .../apps/{app_id}/status`. Controller `api/controller/application.go:233`
→ `GetStatus` `api/handler/application_handler.go:617`. Struct `api/model/app.go:14`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `app_id` | string | no | |
| `app_name` | string | no | |
| `status` | string | no | |
| `cpu` | Optional[int] | no | *int64, nullable |
| `gpu` | Optional[int] | no | *int64, nullable |
| `memory` | Optional[int] | no | *int64, nullable |
| `disk` | int | no | int64 |
| `phase` | string | no | |
| `version` | string | no | |
| `overrides` | List[str] | no | |
| `conditions` | List[AppStatusCondition] | no | |
| `k8s_app` | string | no | |

### AppStatusCondition — `api/model/app.go:30`: `{type:str, status:bool, reason:str, message:str}`

---

## 13. TenantServicesPort (DB) — component ports

**Endpoint:** ports returned via component detail / `GET volumes`-adjacent flows;
`POST/PUT .../services/{alias}/ports`. Struct `db/model/tenant.go:406`. (+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | Model |
| `tenant_id` | string | no | |
| `service_id` | string | no | |
| `container_port` | int | no | |
| `mapping_port` | int | no | |
| `protocol` | string | no | http/https/tcp/grpc/udp/mysql |
| `port_alias` | string | no | |
| `is_inner_service` | Optional[bool] | no | *bool nullable |
| `is_outer_service` | Optional[bool] | no | *bool nullable |
| `k8s_service_name` | string | no | |
| `name` | string | no | |

---

## 14. TenantServiceEnvVar (DB) — component envs

**Endpoint:** `POST/PUT/DELETE .../services/{alias}/env`. Struct `db/model/tenant.go:468`.
(+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | Model |
| `tenant_id` | string | no | |
| `service_id` | string | no | |
| `container_port` | int | no | |
| `name` | string | no | |
| `attr_name` | string | no | |
| `attr_value` | string | no | |
| `is_change` | bool | no | |
| `scope` | string | no | outer/inner/both |

---

## 15. TenantServiceRelation (DB) — component dependencies

**Endpoint:** `POST/DELETE .../services/{alias}/dependency`. Struct `db/model/tenant.go:453`.
(+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | Model |
| `tenant_id` | string | no | |
| `service_id` | string | no | |
| `depend_service_id` | string | no | |
| `dep_service_type` | string | no | |
| `dep_order` | int | no | |

---

## 16. TenantServiceMountRelation (DB) — dep volumes

**Endpoint:** `GET/POST/DELETE .../services/{alias}/depvolumes`. Struct `db/model/tenant.go:487`.
(+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | Model |
| `tenant_id` | string | no | |
| `service_id` | string | no | |
| `dep_service_id` | string | no | |
| `volume_path` | string | no | |
| `host_path` | string | no | |
| `volume_name` | string | no | |
| `volume_type` | string | no | |

---

## 17. VolumeWithStatusStruct — component volumes (with status)

**Endpoint:** `GET .../services/{alias}/volumes`. Controller registers `controller.GetVolume`;
handler `GetVolumes` `api/handler/service.go:2484`. Struct `api/model/volume.go:267`.
Returned as `{"list": [...]}`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `service_id` | string | no | |
| `category` | string | no | |
| `volume_type` | string | no | share-file/local/... |
| `volume_name` | string | no | |
| `host_path` | string | no | |
| `volume_path` | string | no | |
| `is_read_only` | bool | no | |
| `volume_capacity` | int | no | int64 |
| `access_mode` | string | no | |
| `share_policy` | string | no | |
| `backup_policy` | string | no | |
| `reclaim_policy` | string | no | |
| `allow_expansion` | bool | no | |
| `volume_provider_name` | string | no | |
| `status` | string | no | runtime volume status |

---

## 18. TenantServiceProbe (DB) — component probe

**Endpoint:** `POST/PUT/DELETE .../services/{alias}/probe`. Struct `db/model/tenant.go:633`.
(+ Model: `ID`, `create_time`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `create_time` | string | no | Model |
| `service_id` | string | no | |
| `probe_id` | string | no | |
| `mode` | string | no | liveness/readiness |
| `scheme` | string | no | |
| `path` | string | no | |
| `port` | int | no | |
| `cmd` | string | no | |
| `http_header` | string | no | |
| `initial_delay_second` | int | no | |
| `period_second` | int | no | |
| `timeout_second` | int | no | |
| `is_used` | Optional[int] | no | *int nullable (1/0) |
| `failure_threshold` | int | no | |
| `success_threshold` | int | no | |
| `failure_action` | string | no | |

---

## 19. AutoScalerRule / AutoscalerRuleResp — autoscaler

**Endpoints:** `POST/PUT .../services/{alias}/xparules`; records via `GET .../xparecords`.
Structs `api/model/autoscaler.go:40` (Resp) and `:56` (AutoScalerRule).

### AutoScalerRule (`:56`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `rule_id` | string | no | |
| `enable` | bool | no | |
| `xpa_type` | string | no | |
| `min_replicas` | int | no | |
| `max_replicas` | int | no | |
| `metrics` | List[RuleMetric] | no | |

### RuleMetric (`api/model/autoscaler.go:78`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `metric_type` | string | no | |
| `metric_name` | string | no | |
| `metric_target_type` | string | no | |
| `metric_target_value` | int | no | |

(`AutoscalerRuleResp` `:40` is the same shape plus `service_id`, with an inline `metrics` array of identical fields.)

---

## 20. StatsInfo — tenant resource usage

**Endpoint:** `GET .../{tenant_name}/resources` (SingleTenantResources).
Controller `api/controller/resources.go:1932` → `StatsMemCPU`. Struct `api/model/model.go:731`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `uuid` | string | no | set to tenant_id |
| `cpu` | int | no | |
| `memory` | int | no | |

(`TotalStatsInfo` `api/model/model.go:738` wraps `{"data": [StatsInfo]}`.)

---

## 21. TenantResource — tenant resource (resources router)

**Endpoint:** `GET /v2/resources/tenants/{tenant_name}/res` and related under
`resourcesRouter()` (`api/api_routers/version2/v2Routers.go:148`). Struct
`api/model/tenantResourceModel.go:35`; paged wrapper `PagedTenantResList` (`:29`)
= `{"list": [TenantResource], "length": int}`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `alloc_cpu` | int | no | |
| `alloc_memory` | int | no | |
| `used_cpu` | int | no | |
| `used_memory` | int | no | |
| `used_disk` | float | no | float64 |
| `name` | string | no | |
| `uuid` | string | no | |
| `eid` | string | no | |

---

## 22. GatewayHTTPRouteStruct — gateway HTTP route

**Endpoint:** `GET/POST/PUT/DELETE .../{tenant_name}/gateway-http-route`,
`GET .../batch-gateway-http-route`. Struct `api/model/gateway_model.go:76`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `name` | string | no | |
| `app_id` | string | no | |
| `section_name` | string | no | |
| `namespace` | string | no | |
| `gateway_name` | string | no | |
| `gateway_namespace` | string | no | |
| `hosts` | List[str] | no | |
| `rules` | List[Rules] | no | see below |
| `exist` | bool | no | |

### Rules (`api/model/gateway_model.go:89`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `matches_rule` | List[MatchesRule] | no | |
| `backend_refs_rule` | List[BackendRefsRule] | no | |
| `filters_rule` | List[FiltersRule] | no | |

### FiltersRule (`:96`)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `type` | string | omitempty | |
| `request_header_modifier` | Optional[HTTPHeaderFilter] | omitempty | `{set,add:[{name,value}], remove:[str]}` |
| `request_redirect` | Optional[HTTPRequestRedirectFilter] | omitempty | `{scheme,hostname,port,...}` |

(Nested `MatchesRule`/`BackendRefsRule`/`MatchesRulePath`/`MatchesRuleHeader` defined
`api/model/gateway_model.go:124-172` — capture on demand; not all are response-only.)

---

## 23. GatewayHTTPRouteConcise — concise route list

**Endpoint:** part of gateway-http-route GET responses. Struct `api/model/gateway_model.go:57`.

| json key | Go type | optional? | notes |
|---|---|---|---|
| `name` | string | no | |
| `hosts` | List[str] | no | |
| `app_id` | string | no | |
| `gateway_class_name` | string | no | |
| `gateway_class_namespace` | string | no | |

---

## 24. AddServiceMonitorRequestStruct — component service monitor

**Endpoint:** `POST/PUT .../services/{alias}/service-monitors`. Struct `api/model/service_monitor.go:6`.
(Request struct, but echoed in component detail responses as `component_monitors`.)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `name` | string | no | |
| `service_show_name` | string | no | |
| `port` | int | no | |
| `path` | string | no | |
| `interval` | string | no | |

---

## 25. Tenants (DB) — team/tenant info

**Endpoint:** `GET/PUT .../{tenant_name}`, `POST /tenants`. Controller `Tenant`/`Tenants`.
Struct `db/model/tenant.go:62`. **NOTE: most fields have NO `json:` tag** → Go serializes
using the **Go field name** (PascalCase). (+ Model embed adds `ID` and `create_time`.)

| json key | Go type | optional? | notes |
|---|---|---|---|
| `ID` | int | no | from Model, no tag → "ID" |
| `create_time` | string | no | Model (has tag) |
| `Name` | string | no | **no json tag → "Name"** |
| `UUID` | string | no | no tag → "UUID" |
| `EID` | string | no | no tag → "EID" |
| `LimitCPU` | int | no | no tag → "LimitCPU" |
| `LimitStorage` | int | no | no tag |
| `LimitMemory` | int | no | no tag |
| `Status` | string | no | no tag |
| `Namespace` | string | no | no tag |

**Caveat:** confirm actual serialization at runtime — untagged Go fields keep their exported
field name as the JSON key. The console may rely on these PascalCase keys.
