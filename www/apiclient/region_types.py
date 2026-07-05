# -*- coding: utf-8 -*-
"""TypedDicts for Rainbond region (Go core) HTTP response payloads.

These describe the JSON ``data`` payload (the ``bean`` / ``list`` content) returned
by the ``/v2/...`` endpoints that :class:`www.apiclient.regionapi.RegionInvokeApi`
calls. They are derived field-by-field from the Go structs in the ``rainbond`` core
repo (see ``docs/plans/2026-06-13-m2-go-response-structs.md``).

Conventions
-----------
* Go ``time.Time`` serialises as an RFC3339 string -> ``str``.
* Go ``*X`` (pointer) and ``omitempty`` fields may be missing/null -> ``NotRequired``
  and/or ``Optional``.
* DB structs embed ``Model`` which adds ``ID`` (int) and ``create_time`` (str).
* The runtime objects are ``addict.Dict`` (a ``dict`` subclass), so item access
  (``body["bean"]["foo"]``) is what these types model; addict attribute access
  (``body.bean``) is intentionally not modelled.

These are additive type aids; adopt them incrementally on regionapi methods that
already unwrap ``bean``/``list``.
"""
from typing import Any, Dict, List, Optional

from typing_extensions import NotRequired, TypedDict


class ResponseBody(TypedDict, total=False):
    """The Go ``util/http/api.go`` success/list envelope (all keys omitempty)."""
    bean: Any
    list: Any
    msg: str
    number: int
    page: int
    validation_error: Dict[str, List[str]]


# --- §1 ServiceEvent -------------------------------------------------------
class ServiceEvent(TypedDict):
    create_time: str
    event_id: str
    tenant_id: str
    service_id: str
    target: str
    target_id: str
    request_body: str
    user_name: str
    start_time: str
    end_time: str
    opt_type: str
    syn_type: int
    status: str
    final_status: str
    message: str
    reason: str


# --- §2 StatusList / PodsList / VMRestore ----------------------------------
class PodsList(TypedDict):
    pod_ip: str
    phase: str
    pod_name: str
    node_name: str


class VMRestoreDataVolume(TypedDict):
    name: str
    phase: str
    progress: str
    message: str


class VMRestoreImporterPod(TypedDict):
    name: str
    volume: str
    namespace: str


class VMRestore(TypedDict):
    status: str
    status_cn: str
    progress: str
    message: str
    data_volumes: List[VMRestoreDataVolume]
    importer_pods: List[VMRestoreImporterPod]


class StatusList(TypedDict):
    tenant_id: str
    service_id: str
    service_alias: str
    deploy_version: str
    replicas: int
    container_memory: int
    cur_status: str
    container_cpu: int
    status_cn: str
    start_time: str
    pod_list: List[PodsList]
    vm_restore: NotRequired[VMRestore]


# --- §3 batch services_status ----------------------------------------------
class ServiceStatusItem(TypedDict):
    service_id: str
    status: str
    status_cn: str
    used_mem: int


# --- §4 GetSingleServiceInfo (camelCase keys) ------------------------------
class SingleServiceInfo(TypedDict):
    tenantName: str
    serviceAlias: str
    tenantId: str
    serviceId: str


# --- §5 K8sPodInfos --------------------------------------------------------
class K8sPodInfo(TypedDict):
    pod_name: str
    pod_ip: str
    pod_status: str
    service_id: str
    container: Dict[str, Dict[str, str]]


class K8sPodInfos(TypedDict):
    new_pods: Optional[List[K8sPodInfo]]
    old_pods: Optional[List[K8sPodInfo]]


# --- §6 PodDetail ----------------------------------------------------------
class PodStatus(TypedDict, total=False):
    type: int
    type_str: str
    reason: str
    message: str
    advice: str


class PodContainer(TypedDict, total=False):
    image: str
    state: str
    reason: str
    started: str
    limit_memory: str
    limit_cpu: str


class PodEvent(TypedDict, total=False):
    type: str
    reason: str
    age: str
    message: str


class PodDetail(TypedDict, total=False):
    name: str
    node: str
    start_time: str
    status: PodStatus
    ip: str
    init_containers: List[PodContainer]
    containers: List[PodContainer]
    events: List[PodEvent]


# --- §7 PodExecResult ------------------------------------------------------
class PodExecResult(TypedDict):
    stdout: str
    stderr: str
    exit_code: int
    truncated: bool


# --- §8 VersionInfo --------------------------------------------------------
class VersionInfo(TypedDict):
    create_time: str
    build_version: str
    event_id: str
    service_id: str
    kind: str
    delivered_type: str
    delivered_path: str
    image_name: str
    cmd: str
    repo_url: str
    code_version: str
    code_branch: str
    code_commit_msg: str
    code_commit_author: str
    final_status: str
    finish_time: str
    plan_version: str


# --- §9 TenantServices -----------------------------------------------------
class TenantServices(TypedDict):
    create_time: str
    tenant_id: str
    service_id: str
    service_key: str
    service_alias: str
    service_name: str
    service_type: str
    comment: str
    container_cpu: int
    container_memory: int
    container_gpu: int
    upgrade_method: str
    extend_method: str
    replicas: int
    deploy_version: str
    category: str
    cur_status: str
    status: int
    event_id: str
    namespace: str
    update_time: str
    service_origin: str
    kind: str
    app_id: str
    k8s_component_name: str
    job_strategy: str


# --- §11 Application -------------------------------------------------------
class Application(TypedDict):
    create_time: str
    eid: str
    tenant_id: str
    app_name: str
    app_id: str
    app_type: str
    app_store_name: str
    app_store_url: str
    app_template_name: str
    version: str
    governance_mode: str
    k8s_app: str


# --- §10 paged wrappers ----------------------------------------------------
class ListServiceResponse(TypedDict):
    page: int
    pageSize: int
    total: int
    services: List[TenantServices]


class ListAppResponse(TypedDict):
    page: int
    pageSize: int
    total: int
    apps: List[Application]


# --- §12 AppStatus ---------------------------------------------------------
class AppStatusCondition(TypedDict):
    type: str
    status: bool
    reason: str
    message: str


class AppStatus(TypedDict):
    app_id: str
    app_name: str
    status: str
    cpu: Optional[int]
    gpu: Optional[int]
    memory: Optional[int]
    disk: int
    phase: str
    version: str
    overrides: List[str]
    conditions: List[AppStatusCondition]
    k8s_app: str


# --- §13 TenantServicesPort ------------------------------------------------
class TenantServicesPort(TypedDict):
    create_time: str
    tenant_id: str
    service_id: str
    container_port: int
    mapping_port: int
    protocol: str
    port_alias: str
    is_inner_service: Optional[bool]
    is_outer_service: Optional[bool]
    k8s_service_name: str
    name: str


# --- §14 TenantServiceEnvVar ------------------------------------------------
class TenantServiceEnvVar(TypedDict):
    create_time: str
    tenant_id: str
    service_id: str
    container_port: int
    name: str
    attr_name: str
    attr_value: str
    is_change: bool
    scope: str


# --- §15 TenantServiceRelation ---------------------------------------------
class TenantServiceRelation(TypedDict):
    create_time: str
    tenant_id: str
    service_id: str
    depend_service_id: str
    dep_service_type: str
    dep_order: int


# --- §16 TenantServiceMountRelation ----------------------------------------
class TenantServiceMountRelation(TypedDict):
    create_time: str
    tenant_id: str
    service_id: str
    dep_service_id: str
    volume_path: str
    host_path: str
    volume_name: str
    volume_type: str


# --- §17 VolumeWithStatusStruct --------------------------------------------
class VolumeWithStatusStruct(TypedDict):
    service_id: str
    category: str
    volume_type: str
    volume_name: str
    host_path: str
    volume_path: str
    is_read_only: bool
    volume_capacity: int
    access_mode: str
    share_policy: str
    backup_policy: str
    reclaim_policy: str
    allow_expansion: bool
    volume_provider_name: str
    status: str


# --- §18 TenantServiceProbe ------------------------------------------------
class TenantServiceProbe(TypedDict):
    create_time: str
    service_id: str
    probe_id: str
    mode: str
    scheme: str
    path: str
    port: int
    cmd: str
    http_header: str
    initial_delay_second: int
    period_second: int
    timeout_second: int
    is_used: Optional[int]
    failure_threshold: int
    success_threshold: int
    failure_action: str


# --- §19 AutoScaler --------------------------------------------------------
class RuleMetric(TypedDict):
    metric_type: str
    metric_name: str
    metric_target_type: str
    metric_target_value: int


class AutoScalerRule(TypedDict):
    rule_id: str
    enable: bool
    xpa_type: str
    min_replicas: int
    max_replicas: int
    metrics: List[RuleMetric]


class AutoscalerRuleResp(TypedDict):
    rule_id: str
    service_id: str
    enable: bool
    xpa_type: str
    min_replicas: int
    max_replicas: int
    metrics: List[RuleMetric]


# --- §20 StatsInfo ---------------------------------------------------------
class StatsInfo(TypedDict):
    uuid: str
    cpu: int
    memory: int


class TotalStatsInfo(TypedDict):
    data: List[StatsInfo]


# --- §21 TenantResource ----------------------------------------------------
class TenantResource(TypedDict):
    alloc_cpu: int
    alloc_memory: int
    used_cpu: int
    used_memory: int
    used_disk: float
    name: str
    uuid: str
    eid: str


class PagedTenantResList(TypedDict):
    list: List[TenantResource]
    length: int


# --- §22 GatewayHTTPRouteStruct --------------------------------------------
class FiltersRule(TypedDict, total=False):
    type: str
    request_header_modifier: Dict[str, Any]
    request_redirect: Dict[str, Any]


class Rules(TypedDict):
    matches_rule: List[Dict[str, Any]]
    backend_refs_rule: List[Dict[str, Any]]
    filters_rule: List[FiltersRule]


class GatewayHTTPRouteStruct(TypedDict):
    name: str
    app_id: str
    section_name: str
    namespace: str
    gateway_name: str
    gateway_namespace: str
    hosts: List[str]
    rules: List[Rules]
    exist: bool


# --- §23 GatewayHTTPRouteConcise -------------------------------------------
class GatewayHTTPRouteConcise(TypedDict):
    name: str
    hosts: List[str]
    app_id: str
    gateway_class_name: str
    gateway_class_namespace: str


# --- §24 AddServiceMonitorRequestStruct ------------------------------------
class ServiceMonitor(TypedDict):
    name: str
    service_show_name: str
    port: int
    path: str
    interval: str


# --- §25 Tenants (PascalCase keys; most fields have no json tag) -----------
class Tenants(TypedDict):
    ID: int
    create_time: str
    Name: str
    UUID: str
    EID: str
    LimitCPU: int
    LimitStorage: int
    LimitMemory: int
    Status: str
    Namespace: str
