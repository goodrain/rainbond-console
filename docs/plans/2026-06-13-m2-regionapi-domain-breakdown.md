# M2 — `regionapi.py` mypy 注解工作分解

> Read-only 分析产物。目标文件 `www/apiclient/regionapi.py`（4007 行，类 `RegionInvokeApi`，375 个 class-level `def`）。
> 基类 `www/apiclient/regionapibaseclient.py`（693 行）、`www/apiclient/baseclient.py`（312 行）。
> 本文档是 M2 注解阶段的输入：先注解请求源（_request → _check_status → _get/_post/...），再按域分块并行注解 376 个方法。

---

## Section 1 — 请求源分析（M2 Phase-0 前置）

`RegionInvokeApi` 继承 `RegionApiBaseHttpClient`（`regionapibaseclient.py`）。**几乎所有** `regionapi.py` 方法走的是 `RegionApiBaseHttpClient` 的 `_get/_post/_put/_delete`，它们内部调用本类的 `_request` 与 `_check_status`。`baseclient.py` 的 `HttpClient`（httplib2 版本）只被 `make_proxy_http` 等少数旧路径间接使用；`ClientAuthService` 提供 token 查询，不返回 HTTP body。

### 1.1 关键事实：两套 `_request`，返回形状不同

| 文件:行 | 类 | 方法 | 返回 | `response` 类型 | 第二元素 |
|---------|----|------|------|----------------|----------|
| `regionapibaseclient.py:238` | `RegionApiBaseHttpClient` | `_request` | `Tuple[int, bytes]`（正常）/ `Tuple[urllib3.HTTPResponse, None]`（`preload_content is False`） | 正常路径返回 `response.status`（**int**）+ `response.data`（**bytes**） | bytes 或 None |
| `baseclient.py:72` | `HttpClient` | `_request` | `Tuple[httplib2.Response, bytes]` | httplib2 `response` 对象 | `content`（bytes） |

> **要点**：`RegionApiBaseHttpClient._request` **正常路径返回 `(status:int, data:bytes)`，不是 (response_obj, body)**。`status` 是 int，第二个是原始 bytes。仅当 `preload_content is False`（流式：`sse_proxy`、`get_component_pod_log` 等）时返回 `(urllib3.HTTPResponse, None)`。`baseclient.py._request` 返回的是 httplib2 的 `(response, content)`。

### 1.2 `_check_status`（解析层 —— body 的真实形状来源）

| 文件:行 | 方法 | 现签名 | 返回 |
|---------|------|--------|------|
| `regionapibaseclient.py:166` | `_check_status(self, url, method, status, content)` | 第三参 `status:int`、第四参 `content:bytes` | `Tuple[addict.Dict, Optional[addict.Dict]]` |
| `baseclient.py:48` | `_check_status(self, url, method, response, content)` | 第三参 `response`（httplib2 resp） | `Tuple[addict.Dict, addict.Dict]` |

解析细节（`regionapibaseclient.py:166-216`）：
- `body = self._jsondecode(content)`（`json.loads`；失败回退 `{"raw": ...}`）→ 若是 dict 再包成 `addict.Dict`。
- `content` 为空（如 204）时 `body = None`。
- `res = Dict({"status": status})` —— **`res` 不是 HTTP 响应对象，而是一个 `addict.Dict`，只有 `.status` 字段（int）**。
- 4xx/5xx 抛异常（`ServiceHandleException` / `CallApiError` / 各类资源不足异常），不返回。
- 成功返回 `return res, body`，即 `(Dict{status:int}, Optional[Dict])`。

`_jsondecode`：`regionapibaseclient.py:156` / `baseclient.py:38`，返回 `dict | list | {"raw": str}`（`json.loads` 结果，可能是 list）。
`_unpack`：`regionapibaseclient.py:218` / `baseclient.py:60`，从 `body` 取 `data.bean` 或 `data.list`，返回 `dict | list`（少用）。

### 1.3 `_get/_post/_put/_delete`（regionapi 方法直接调用的入口）

`regionapibaseclient.py:365-400`，签名 `_get(self, url, headers, body=None, *args, **kwargs)`：
- 默认 `return res, body` → `Tuple[addict.Dict, Optional[addict.Dict]]`。
- `_get` 有两个分支例外：`preload_content is False` → `return response, None`（`response` 是 `urllib3.HTTPResponse`）；`check_status is False` → `return response, content`（`(int, bytes)` 未解析）。
- `_post/_put/_delete` 始终 `return self._check_status(...)`。

### 1.4 推荐的具体返回注解（让契约向上流到 regionapi）

```python
# addict.Dict 子类化 dict，注解上当成 Dict / Any 容器
from addict import Dict as AddictDict
from typing import Any, Optional, Tuple, Union
import urllib3

# regionapibaseclient.py
def _jsondecode(self, string: Union[str, bytes]) -> Union[dict, list]: ...
def _check_status(self, url: str, method: str, status: int, content: Optional[bytes]
                  ) -> Tuple[AddictDict, Optional[AddictDict]]: ...
def _request(self, url: str, method: str, headers: Optional[dict] = None,
             body: Optional[Any] = None, *args: Any, **kwargs: Any
             ) -> Tuple[Union[int, "urllib3.HTTPResponse"], Optional[bytes]]: ...
def _get(self, url: str, headers: dict, body: Optional[Any] = None,
         *args: Any, **kwargs: Any) -> Tuple[Any, Any]: ...   # 同样 _post/_put/_delete
```

向 regionapi 方法的传导规则（用于自动注解 376 个方法）：
- `res, body = self._get(...)` 之后 `return body` → 返回 `Optional[AddictDict]`（实践中调用方按 dict 用，注解 `Optional[Dict[str, Any]]` 或 `Any`）。
- `return res, body` → `Tuple[AddictDict, Optional[AddictDict]]`（`res` 是 `Dict{status:int}`，**不是** http response）。
- `preload_content=False` 的流式方法（`return resp` / `return response`）→ `urllib3.HTTPResponse` 或 `StreamingHttpResponse`。
- `return None` / 无 return → `Optional[...]` / `None`。

> 注：`addict.Dict` 无官方 stub。建议在 mypy 中将其视作 `Any`（或为本仓写一个最小 `.pyi`），否则 `body["bean"]`、`body.get(...)`、`res.get("status")` 混用会大量报错。这是 Phase-0 必须先决策的一项。

---

## Section 2 — 域分组总表

> 行范围为「该域方法的起始行 ~ 域内最后一个方法的下一个方法前」，连续不重叠（见 Section 5 的并行切块）。计数为该范围内 class-level `def` 数。

| # | 域 (Domain) | 行范围 | 方法数 | 高频样例方法 (caller) | 主导返回 |
|---|-------------|--------|--------|------------------------|----------|
| 0 | infra/内部辅助 (`__init__`,`_set_headers`,`__get_region_access_info`...) | 29–91, 943–967, 1389–1448, 2451–2464, 3340–3356 | ~12 | `get_enterprise_region_info`(41), `get_region_info`(51) | mixed / `url,token` |
| 1 | service/component 生命周期+配置 | 92–432 | 33 | `check_service_status`(7), `get_service_pods`(7), `add_service_dependency`(10) | `body` |
| 2 | ports / envs / labels | 433–526 (+268–303,347–400) | — | `add_service_port`(17), `delete_service_port`(8), `delete_service_env`(10) | `body` |
| 3 | probe / lifecycle 操作 (start/stop/restart/upgrade) | 527–662 | 17 | `add_service_probe`(11), `delete_service_probe`(8), `rollback`(4) | `body` |
| 4 | helm / chart (旧 helm 检测+上传) | 663–725, 670–725 | 9 | `check_helm_app`(7), `get_upload_chart_resource`(2) | `res,body` |
| 5 | volumes（含 dep volumes） | 726–842 | 14 | `get_service_volumes`(17), `add_service_volume`(12), `delete_service_volumes`(7) | mixed |
| 6 | logs / events / status | 843–942, 1369–1388 | ~20 | `get_event_log`(4), `get_target_events_list`(3), `service_status`(6) | `body`/`res,body` |
| 7 | gateway / domain / cert / route | 1054–1216, 1075–1216 | 25 | `bind_http_domain`(2), `bindTcpDomain`(3), `get_ips`(2) | `body` |
| 8 | plugin（组件插件 + 集群插件） | 1224–1325, 1499–1551, 2799–2838 | ~26 | `list_plugins`(14), `build_plugin`(7), `create_plugin`(4) | mixed |
| 9 | monitoring / metrics / query | 1326–1359, 2385–2392, 2514–2520 | ~7 | `get_query_data`(7), `get_query_range_data`(6), `get_region_alerts`(1) | `res,body` |
| 10 | app import/export/backup/migrate | 1564–1780 | 30 | `get_upload_file_dir`(4), `export_app`(2), `backup_group_apps`(3) | `res,body` |
| 11 | build version / deploy version | 1781–1849 | 6 | `get_service_build_versions`(2), `get_service_build_version_by_id`(2) | mixed |
| 12 | third-party endpoints / 3rd party | 1857–1921 | 6 | `get_third_party_service_pods`(7), `post_third_party_service_endpoints`(3) | `res,body` |
| 13 | autoscaler / xpa / batch op / config | 1922–1989 | 7 | `batch_operation_service`(6), `restore_properties`(7), `list_scaling_records`(4) | mixed |
| 14 | cluster / region resources / namespaces / yaml-import | 1990–2115, 2152–2196, 2514+ | ~30 | `list_plugins`(14)*, `get_region_resources`(5), `list_tenants`(2) | `res,body` |
| 15 | tenant / team | 110–145, 2104–2125 | ~5 | `create_tenant`(3), `delete_tenant`(3), `set_tenant_resource_limit`(5) | mixed |
| 16 | service monitor / maven setting | 2126–2196 | 10 | `create_service_monitor`(2), `add_maven_setting`(1) | `res,body` |
| 17 | application(app-group)/config-group/governance | 2197–2450, 2986–3010 | ~45 | `install_app`(9), `delete_app`(7), `sync_components`(6), `get_app_status`(13) | `body`/`expr` |
| 18 | license | 2451–2490 | 5 | `get_license_status`(5), `activate_license`(4) | `body` |
| 19 | component log/exec/registry/k8s-attr | 2498–2548, 2595–2628, 3264–3356 | ~18 | `create_component_k8s_attribute`(4), `get_component_pod_log`(3), `create_registry_auth`(2) | mixed |
| 20 | k8s-resource (app resource) | 2550–2594 | 5 | `get_app_resource`(2), `create_app_resource`(1) | `res,body` |
| 21 | rbd cluster ops / nodes / vm | 2629–2798, 2708–2726, 2717 | ~24 | `get_cluster_nodes_arch`(12), `get_cluster_nodes`(5), `get_vm_capabilities`(5) | `res,body` |
| 22 | lang version / cnb framework | 2839–2896, 3371–3452 | 9 (含4重复×2) | `get_lang_version`(2) | `body` |
| 23 | generic proxy / api-gateway proxy / sse | 2897–3262 | ~16 | `api_gateway_get_proxy`(10), `api_gateway_post_proxy`(5), `api_gateway_bind_http_domain`(7) | mixed |
| 24 | upgrade region / over-score | 3357–3464 | 4 | `manage_cluster_status`(8)†, `upgrade_region`(1) | `body` |
| 25 | kubeblocks (DB cluster) | 3465–3774 | 26 | `manage_cluster_status`(8), `delete_kubeblocks_cluster`(6), `get_cluster_resource`(6) | `res,body` |
| 26 | generic cluster-resource / tenant-ns-resource / helm-release / resource-center | 3775–4007 | 31 | `get_cluster_resource`(6), `post_cluster_resource`(3), `get_tenant_ns_resource`(2) | `res,body`/`expr` |

> 上表「域」是功能视角，部分方法在文件中物理位置交错（标注了多段行范围）。Section 5 给出**物理连续、不重叠**的切块，那才是用于并行编辑的依据。`*`/`†` 标注方法被归入多个语义域，按物理位置只属一个 chunk。

主导返回模式整体分布（见 Section 3 明细）：`body` 与 `res,body` 各占大头，`expr:*`（如 `body["bean"]` / `body.get("list")`）集中在 app-group/governance 域，`no-return`/`None` 集中在 delete/sync 类，流式 `urllib3.HTTPResponse` 集中在 log/exec/proxy。

---

## Section 3 — 全量方法清单

> 列：方法名 | 起始行 | 返回模式 | 端点（best-effort，`{}`/`{0}` 为占位）| caller 数 | 域#。
> 返回模式取自方法体内 `return` 语句的归一化：`body`=`return body`；`res,body`=`return res, body`；`expr:X`=返回表达式 X（如 `body["bean"]`）；`passthrough`=`return self._xxx(...)`；`None`/`no-return`。
> caller 数 = 跨 `console/ openapi/ www/` 对 `.<name>(` 的引用计数（排除 def 行）。`_set_headers`(296) 是内部自用，非外部调用，已剔除出"高频外部"判断。

| 方法 | 行 | 返回 | 端点 | callers | 域 |
|------|----|------|------|---------|----|
| get_tenant_resources | 92 | body | /v2/tenants/.../resources | 0 | 1 |
| get_region_publickey | 103 | res,body | /v2/builder/publickey/{id} | 1 | 1 |
| create_tenant | 110 | res,body / err-dict | /v2/tenants | 3 | 15 |
| delete_tenant | 135 | body | /v2/tenants/{} | 3 | 15 |
| create_service | 146 | body | /v2/tenants/.../services | 2 | 1 |
| get_service_info | 159 | body | /v2/tenants/.../services/{} | 0 | 1 |
| update_service | 170 | body | /v2/tenants/.../services/{} | 3 | 1 |
| delete_service | 181 | body | /v2/tenants/.../services/{} | 3 | 1 |
| build_service | 195 | body | /v2/tenants/.../builds | 1 | 1 |
| code_check | 206 | body | /v2/tenants/.../code-check | 0 | 1 |
| get_service_language | 219 | body | /v2/builder/codecheck/service/{0} | 0 | 1 |
| add_service_dependency | 229 | body | /v2/tenants/.../dependency | 10 | 1 |
| add_service_dependencys | 242 | body | /v2/tenants/.../dependencys | 1 | 1 |
| delete_service_dependency | 255 | body | /v2/tenants/.../dependency | 5 | 1 |
| add_service_env | 268 | body | /v2/tenants/.../env | 8 | 2 |
| delete_service_env | 281 | body | /v2/tenants/.../env | 10 | 2 |
| update_service_env | 294 | res,body | /v2/tenants/.../env | 4 | 2 |
| horizontal_upgrade | 304 | body | /v2/tenants/.../horizontal | 5 | 3 |
| vertical_upgrade | 315 | body | /v2/tenants/.../vertical | 6 | 3 |
| get_vm_live_update_capability | 326 | res,body | /v2/tenants/{}/services/{}/vm-live-update-capability | 1 | 3 |
| change_memory | 336 | body | /v2/tenants/.../language | 0 | 3 |
| get_region_labels | 347 | body | /v2/resources/labels | 2 | 2 |
| addServiceNodeLabel | 357 | body | /v2/tenants/.../node-label | 1 | 2 |
| deleteServiceNodeLabel | 368 | body | /v2/tenants/.../node-label | 1 | 2 |
| add_service_state_label | 379 | body | /v2/tenants/.../service-state-label | 0 | 2 |
| update_service_state_label | 390 | res,body | /v2/tenants/.../service-state-label | 2 | 2 |
| get_service_pods | 401 | body | /v2/tenants/.../pods | 7 | 1 |
| get_dynamic_services_pods | 413 | body | /v2/tenants/.../pods | 2 | 1 |
| pod_detail | 421 | body | /v2/tenants/.../pods/{}/detail | 4 | 1 |
| add_service_port | 433 | body | /v2/tenants/.../ports | 17 | 2 |
| update_service_port | 447 | body | /v2/tenants/.../ports/{} | 6 | 2 |
| delete_service_port | 461 | body | /v2/tenants/.../ports/{} | 8 | 2 |
| manage_inner_port | 473 | body | /v2/tenants/.../ports/{}/inner | 2 | 2 |
| api_gateway_manage_outer_port | 485 | body | /v2/tenants/.../ports/{}/outer | 0 | 2 |
| manage_outer_port | 506 | body | /v2/tenants/.../ports/{}/outer | 1 | 2 |
| update_service_probec | 527 | res,body | /v2/tenants/.../probe | 2 | 3 |
| add_service_probe | 539 | res,body | /v2/tenants/.../probe | 11 | 3 |
| delete_service_probe | 551 | body | /v2/tenants/.../probe | 8 | 3 |
| restart_service | 562 | body | /v2/tenants/.../restart | 1 | 3 |
| rollback | 573 | body | /v2/tenants/.../rollback | 4 | 3 |
| start_service | 584 | body | /v2/tenants/.../start | 1 | 3 |
| pause_service | 595 | body | /v2/tenants/.../pause | 1 | 3 |
| un_pause_service | 606 | body | /v2/tenants/.../unpause | 1 | 3 |
| stop_service | 617 | body | /v2/tenants/.../stop | 1 | 3 |
| upgrade_service | 628 | body | /v2/tenants/.../upgrade | 1 | 3 |
| check_service_status | 639 | body | /v2/tenants/.../status | 7 | 3 |
| get_user_service_abnormal_status | 651 | None/body | /v2/enterprise/{}/abnormal_status | 2 | 6 |
| get_volume_options | 663 | body | /v2/volume-options | 1 | 4 |
| get_chart_information | 670 | res,body | /v2/helm/get_chart_information | 1 | 4 |
| check_helm_app | 677 | res,body | /v2/helm/check_helm_app | 7 | 4 |
| get_yaml_by_chart | 684 | res,body | /v2/helm/get_chart_yaml | 1 | 4 |
| get_upload_chart_information | 691 | res,body | /v2/helm/get_upload_chart_information | 2 | 4 |
| check_upload_chart | 698 | res,body | /v2/helm/check_upload_chart | 2 | 4 |
| get_upload_chart_resource | 705 | res,body | /v2/helm/get_upload_chart_resource | 2 | 4 |
| import_upload_chart_resource | 712 | res,body | /v2/helm/import_upload_chart_resource | 2 | 4 |
| get_upload_chart_value | 719 | res,body | /v2/helm/get_upload_chart_value | 2 | 4 |
| get_service_volumes_status | 726 | res,body | /v2/tenants/{}/services/{}/volumes-status | 0 | 5 |
| get_service_volumes | 735 | res,body | /v2/tenants/{}/services/{}/volumes | 17 | 5 |
| add_service_volumes | 745 | passthrough | /v2/tenants/{}/services/{}/volumes | 2 | 5 |
| delete_service_volumes | 753 | passthrough | /v2/tenants/{}/services/{}/volumes/{} | 7 | 5 |
| upgrade_service_volumes | 762 | passthrough | /v2/tenants/{}/services/{}/volumes | 3 | 5 |
| get_service_dep_volumes | 770 | res,body | /v2/tenants/{}/services/{}/depvolumes | 0 | 5 |
| add_service_dep_volumes | 780 | res,body | /v2/tenants/{}/services/{}/depvolumes | 2 | 5 |
| delete_service_dep_volumes | 790 | passthrough | /v2/tenants/{}/services/{}/depvolumes | 1 | 5 |
| add_service_volume | 799 | res,body | /v2/tenants/.../volumes | 12 | 5 |
| delete_service_volume | 810 | res,body | /v2/tenants/.../volumes | 0 | 5 |
| add_service_volume_dependency | 821 | body | /v2/tenants/.../volume-dependency | 0 | 5 |
| delete_service_volume_dependency | 832 | body | /v2/tenants/.../volume-dependency | 0 | 5 |
| service_status | 843 | body | /v2/tenants/.../status | 6 | 6 |
| watch_operator_managed | 854 | body | /v2/tenants/{}/apps/{}/watch_operator_managed | 1 | 6 |
| get_enterprise_running_services | 862 | None/body | /v2/enterprise/{}/running-services | 2 | 6 |
| get_docker_log_instance | 873 | body | /v2/tenants/.../log-instance | 2 | 6 |
| get_service_logs | 885 | body | /v2/tenants/{}/services/{}/logs | 2 | 6 |
| get_service_log_files | 894 | body | /v2/tenants/.../log-file | 1 | 6 |
| get_event_log | 906 | res,body | /v2/tenants/.../event-log | 4 | 6 |
| get_target_events_list | 916 | res,body | /v2/events | 3 | 6 |
| get_myteams_events_list | 924 | res,body | /v2/events/myteam | 1 | 6 |
| get_events_log | 935 | res,body | /v2/events/{}/log | 3 | 6 |
| get_api_version | 943 | res,body | /v2/show | 1 | 0 |
| get_api_version_v2 | 950 | res,body | /v2/show | 1 | 0 |
| get_enterprise_api_version_v2 | 958 | res,body | /v2/show | 3 | 0 |
| get_region_tenants_resources | 968 | body | /v2/resources/tenants | 2 | 14 |
| get_service_resources | 976 | body | /v2/resources/services | 2 | 14 |
| share_clound_service | 985 | res,body | /v2/tenants/.../share | 0 | 8 |
| share_service | 997 | res,body | /v2/tenants/.../share | 1 | 8 |
| create_vm_export | 1006 | res,body | /v2/tenants/.../vm-export | 3 | 21 |
| get_vm_export | 1015 | res,body | /v2/tenants/.../vm-export/{} | 3 | 21 |
| share_service_result | 1025 | res,body | /v2/tenants/.../share/{}/result | 1 | 8 |
| share_plugin | 1035 | res,body | /v2/tenants/.../plugin/.../share | 2 | 8 |
| share_plugin_result | 1044 | res,body | /v2/tenants/.../plugin/.../share/{} | 2 | 8 |
| bindDomain | 1054 | body | /v2/tenants/.../domains | 0 | 7 |
| unbindDomain | 1065 | body | /v2/tenants/.../domains | 0 | 7 |
| list_gateway_http_route | 1075 | body | /v2/tenants/.../gateway/http-route | 1 | 7 |
| get_gateway_certificate | 1082 | body | /v2/tenants/.../gateway/certificate | 0 | 7 |
| create_gateway_certificate | 1088 | body | /v2/tenants/.../gateway/certificate | 1 | 7 |
| update_gateway_certificate | 1094 | body | /v2/tenants/.../gateway/certificate | 1 | 7 |
| delete_gateway_certificate | 1100 | body | /v2/tenants/.../gateway/certificate/{} | 1 | 7 |
| get_gateway_http_route | 1106 | body | /v2/tenants/.../gateway/http-route/{} | 1 | 7 |
| add_gateway_http_route | 1112 | body | /v2/tenants/.../gateway/http-route | 1 | 7 |
| update_gateway_http_route | 1118 | body | /v2/tenants/.../gateway/http-route | 1 | 7 |
| delete_gateway_http_route | 1124 | body | /v2/tenants/.../gateway/http-route/{} | 2 | 7 |
| bind_http_domain | 1131 | body | /v2/tenants/.../http-domains | 2 | 7 |
| update_http_domain | 1141 | body | /v2/tenants/.../http-domains | 1 | 7 |
| delete_http_domain | 1152 | body | /v2/tenants/.../http-domains | 2 | 7 |
| bindTcpDomain | 1161 | body | /v2/tenants/.../tcp-domains | 3 | 7 |
| create_http_limiting_policy | 1171 | body | /v2/tenants/.../limit | 0 | 7 |
| update_http_limiting_policy | 1179 | body | /v2/tenants/.../limit | 0 | 7 |
| delete_http_limiting_policy | 1188 | body | /v2/tenants/.../limit/{} | 0 | 7 |
| updateTcpDomain | 1197 | body | /v2/tenants/.../tcp-domains | 1 | 7 |
| unbindTcpDomain | 1208 | body | /v2/tenants/.../tcp-domains | 2 | 7 |
| get_ips | 1217 | res,body | /v2/gateway/ips | 1 | 7 |
| pluginServiceRelation | 1224 | passthrough | /v2/tenants/.../plugin | 1 | 8 |
| delPluginServiceRelation | 1233 | passthrough | /v2/tenants/.../plugin/{} | 3 | 8 |
| updatePluginServiceRelation | 1242 | passthrough | /v2/tenants/.../plugin | 1 | 8 |
| postPluginAttr | 1251 | passthrough | /v2/tenants/.../plugin/{}/attr | 1 | 8 |
| putPluginAttr | 1261 | passthrough | /v2/tenants/.../plugin/{}/attr | 1 | 8 |
| create_plugin | 1272 | res,body | /v2/tenants/.../plugin | 4 | 8 |
| build_plugin | 1283 | body | /v2/tenants/{0}/plugin/{1}/build | 7 | 8 |
| get_build_status | 1293 | body | /v2/tenants/{0}/plugin/{1}/build-version/{2} | 2 | 8 |
| get_plugin_event_log | 1304 | body | /v2/tenants/{0}/event-log | 3 | 8 |
| delete_plugin_version | 1314 | body | /v2/tenants/{0}/plugin/{1}/build-version/{2} | 2 | 8 |
| get_query_data | 1326 | res,body | /api/v1/query | 7 | 9 |
| get_query_range_data | 1334 | res,body | /api/v1/query_range | 6 | 9 |
| get_query_service_access | 1342 | res,body | /api/v1/query | 2 | 9 |
| get_query_domain_access | 1351 | res,body | /api/v1/query | 2 | 9 |
| get_service_publish_status | 1360 | res,body | /v2/builder/publish/service/{0}/version/{1} | 0 | 6 |
| get_tenant_events | 1369 | body | /v2/tenants/.../events | 5 | 6 |
| get_events_by_event_ids | 1380 | body | /v2/event | 1 | 6 |
| get_protocols | 1422 | body | /v2/tenants/.../protocols | 1 | 1 |
| get_region_info | 1433 | None/configs[0] | (DB lookup) | 51 | 0 |
| get_enterprise_region_info | 1439 | None/configs[0] | (DB lookup) | 41 | 0 |
| get_tenant_image_repositories | 1449 | res,body | /v2/tenants/.../image-repositories | 1 | 1 |
| get_tenant_image_tags | 1459 | res,body | /v2/tenants/.../image-tags | 1 | 1 |
| service_source_check | 1469 | res,body | /v2/tenants/.../servicecheck | 3 | 1 |
| get_service_check_info | 1479 | res,body | /v2/tenants/.../servicecheck/{} | 9 | 1 |
| service_chargesverify | 1489 | res,body | /v2/tenants/.../chargesverify | 0 | 1 |
| update_plugin_info | 1499 | body | /v2/tenants/{0}/plugin/{1} | 1 | 8 |
| delete_plugin | 1507 | res,body | /v2/tenants/{0}/plugin/{1} | 5 | 8 |
| install_service_plugin | 1515 | passthrough | /v2/tenants/.../plugin | 4 | 8 |
| uninstall_service_plugin | 1524 | passthrough | /v2/tenants/.../plugin/{} | 3 | 8 |
| update_plugin_service_relation | 1532 | passthrough | /v2/tenants/.../plugin | 1 | 8 |
| update_service_plugin_config | 1541 | passthrough | /v2/tenants/.../plugin/{}/setenv | 4 | 8 |
| get_services_pods | 1552 | body | /v2/tenants/.../pods | 1 | 1 |
| export_app | 1564 | res,body | /v2/app/export | 2 | 10 |
| get_app_export_status | 1572 | res,body | /v2/app/export/{} | 1 | 10 |
| import_app_2_enterprise | 1580 | res,body | /v2/app/import | 2 | 10 |
| import_app | 1588 | res,body | /v2/app/import | 2 | 10 |
| get_app_import_status | 1596 | res,body | /v2/app/import/{} | 1 | 10 |
| get_enterprise_app_import_status | 1604 | res,body | /v2/app/import/{} | 2 | 10 |
| get_enterprise_import_file_dir | 1611 | res,body | /v2/app/import/ids/{} | 1 | 10 |
| get_import_file_dir | 1618 | res,body | /v2/app/import/ids/{} | 0 | 10 |
| delete_enterprise_import | 1626 | res,body | /v2/app/import/{} | 1 | 10 |
| delete_import | 1633 | res,body | /v2/app/import/{} | 1 | 10 |
| create_import_file_dir | 1641 | res,body | /v2/app/import/ids/{} | 1 | 10 |
| delete_enterprise_import_file_dir | 1649 | res,body | /v2/app/import/ids/{} | 3 | 10 |
| delete_import_file_dir | 1656 | res,body | /v2/app/import/ids/{} | 1 | 10 |
| create_upload_file_dir | 1664 | res,body | /v2/app/upload/events/{} | 2 | 10 |
| get_upload_file_dir | 1672 | res,body | /v2/app/upload/events/{} | 4 | 10 |
| delete_upload_file_dir | 1680 | res,body | /v2/app/upload/events/{} | 1 | 10 |
| update_upload_file_dir | 1688 | res,body | /v2/app/upload/events/{} | 0 | 10 |
| load_tar_image | 1696 | res,body | /v2/tenants/.../docker-image-load | 1 | 10 |
| get_tar_load_result | 1705 | res,body | /v2/tenants/.../docker-image-load/{} | 1 | 10 |
| backup_group_apps | 1714 | body | /v2/tenants/.../groupapp/backups | 3 | 10 |
| get_backup_status_by_backup_id | 1723 | body | /v2/tenants/.../backups/{} | 2 | 10 |
| delete_backup_by_backup_id | 1732 | body | /v2/tenants/.../backups/{} | 1 | 10 |
| get_backup_status_by_group_id | 1741 | body | /v2/tenants/.../groupapp/backups | 1 | 10 |
| star_apps_migrate_task | 1750 | body | /v2/tenants/.../backups/{}/restore | 1 | 10 |
| get_apps_migrate_status | 1760 | body | /v2/tenants/.../backups/{}/restore/{} | 2 | 10 |
| copy_backup_data | 1771 | body | /v2/tenants/.../backupcopy | 2 | 10 |
| get_service_build_versions | 1781 | body | /v2/tenants/.../build-versions | 2 | 11 |
| delete_service_build_version | 1792 | body | /v2/tenants/.../build-version/{} | 1 | 11 |
| get_service_build_version_by_id | 1804 | res,body | /v2/tenants/.../build-version/{} | 2 | 11 |
| update_service_build_version_by_id | 1816 | res,body | /v2/tenants/.../build-version/{} | 0 | 11 |
| get_team_services_deploy_version | 1828 | res,body | /v2/tenants/.../deployversions | 2 | 11 |
| get_service_deploy_version | 1838 | res,body | /v2/tenants/.../deployversions | 1 | 11 |
| get_app_abnormal | 1850 | res,body | /v2/notificationEvent | 0 | 6 |
| put_third_party_service_endpoints | 1857 | res,body | /v2/tenants/.../endpoints | 2 | 12 |
| post_third_party_service_endpoints | 1868 | res,body | /v2/tenants/.../endpoints | 3 | 12 |
| delete_third_party_service_endpoints | 1879 | res,body | /v2/tenants/.../endpoints | 2 | 12 |
| get_third_party_service_pods | 1890 | res,body | /v2/tenants/.../pods | 7 | 12 |
| get_third_party_service_health | 1901 | res,body | /v2/tenants/.../3rd-party/probe | 1 | 12 |
| put_third_party_service_health | 1912 | res,body | /v2/tenants/.../3rd-party/probe | 1 | 12 |
| batch_operation_service | 1922 | res,body | /v2/tenants/.../batchoperation | 6 | 13 |
| upgrade_configuration | 1931 | res,body | /v2/tenants/.../upgrade | 1 | 13 |
| restore_properties | 1941 | body | /v2/tenants/.../{uri} | 7 | 13 |
| list_scaling_records | 1952 | body | /v2/tenants/.../xparecords | 4 | 13 |
| create_xpa_rule | 1964 | body | /v2/tenants/.../xparules | 1 | 13 |
| update_xpa_rule | 1973 | body | /v2/tenants/.../xparules | 1 | 13 |
| update_ingresses_by_certificate | 1982 | res,body | /v2/tenants/.../certificate | 1 | 7 |
| get_region_resources | 1990 | res,body | /v2/cluster | 5 | 14 |
| test_region_api | 2002 | passthrough | /v2/show | 1 | 14 |
| check_region_api | 2007 | None/body | /v2/show | 1 | 14 |
| list_gateways | 2019 | res,body | /v2/cluster/batch-gateway | 2 | 14 |
| list_namespaces | 2028 | res,body | /v2/cluster/namespace | 2 | 14 |
| list_namespace_resources | 2041 | res,body | /v2/cluster/resource | 1 | 14 |
| list_convert_resource | 2050 | res,body | /v2/cluster/convert-resource | 1 | 14 |
| resource_import | 2059 | res,body | /v2/cluster/convert-resource | 2 | 14 |
| yaml_resource_name | 2068 | res,body | /v2/cluster/yaml_resource_name | 1 | 14 |
| yaml_resource_detailed | 2077 | res,body | /v2/cluster/yaml_resource_detailed | 3 | 14 |
| yaml_resource_import | 2086 | res,body | /v2/cluster/yaml_resource_import | 1 | 14 |
| add_resource | 2095 | res,body | /v2/cluster/convert-resource | 0 | 14 |
| list_tenants | 2104 | res,body / err | /v2/tenants?tenant_ids={} | 2 | 15 |
| set_tenant_resource_limit | 2117 | res,body | /v2/tenants/{0}/limit_resource | 5 | 15 |
| create_service_monitor | 2126 | res,body | /v2/tenants/{0}/services/{1}/service-monitors | 2 | 16 |
| update_service_monitor | 2135 | res,body | /v2/tenants/.../service-monitors/{2} | 1 | 16 |
| delete_service_monitor | 2144 | no-return | /v2/tenants/.../service-monitors/{2} | 2 | 16 |
| delete_maven_setting | 2152 | res,body | /v2/cluster/builder/mavensetting/{0} | 1 | 16 |
| add_maven_setting | 2161 | res,body | /v2/cluster/builder/mavensetting | 1 | 16 |
| get_maven_setting | 2170 | res,body | /v2/cluster/builder/mavensetting/{0} | 1 | 16 |
| update_maven_setting | 2179 | res,body | /v2/cluster/builder/mavensetting/{0} | 1 | 16 |
| list_maven_settings | 2188 | res,body | /v2/cluster/builder/mavensetting | 1 | 16 |
| update_app_ports | 2197 | body | /v2/tenants/.../apps/{}/ports | 0 | 17 |
| get_app_status | 2206 | body["bean"] | /v2/tenants/.../apps/{}/status | 13 | 17 |
| get_app_detect_process | 2215 | body["list"] | /v2/tenants/.../apps/{}/detect-process | 1 | 17 |
| get_pod | 2224 | body["bean"] | /v2/tenants/.../pods/{} | 2 | 17 |
| install_app | 2233 | no-return | /v2/tenants/.../apps/{}/install | 9 | 17 |
| list_app_services | 2241 | body["list"] | /v2/tenants/.../apps/{}/services | 2 | 17 |
| create_application | 2250 | body.get("bean") | /v2/tenants/.../apps | 3 | 17 |
| batch_create_application | 2259 | body.get("list") | /v2/tenants/.../batch_create_apps | 1 | 17 |
| update_service_app_id | 2268 | body.get("bean") | /v2/tenants/.../services/{}/app-id | 1 | 17 |
| batch_update_service_app_id | 2277 | body.get("bean") | /v2/tenants/.../apps/{}/services | 1 | 17 |
| update_app | 2286 | body.get("bean") | /v2/tenants/.../apps/{} | 3 | 17 |
| create_app_config_group | 2295 | body.get("bean") | /v2/tenants/.../apps/{}/configgroups | 1 | 17 |
| update_app_config_group | 2304 | body.get("bean") | /v2/tenants/.../apps/{}/configgroups/{} | 1 | 17 |
| delete_app | 2313 | no-return | /v2/tenants/.../apps/{} | 7 | 17 |
| delete_compose_app_by_k8s_app | 2321 | no-return | /v2/tenants/.../k8s-app/{} | 1 | 17 |
| delete_app_config_group | 2329 | res,body | /v2/tenants/.../configgroups/{} | 1 | 17 |
| batch_delete_app_config_group | 2338 | res,body | /v2/tenants/{0}/apps/{1}/configgroups/{2}/batch | 1 | 17 |
| check_app_governance_mode | 2348 | no-return | /v2/tenants/{}/apps/{}/governance/check | 1 | 17 |
| list_governance_mode | 2357 | body.get("list") | /v2/cluster/governance-mode | 1 | 17 |
| create_governance_mode_cr | 2364 | body.get("bean") | /v2/tenants/{}/apps/{}/governance-cr | 1 | 17 |
| update_governance_mode_cr | 2371 | body.get("bean") | /v2/tenants/{}/apps/{}/governance-cr | 1 | 17 |
| delete_governance_mode_cr | 2378 | body.get("bean") | /v2/tenants/{}/apps/{}/governance-cr | 1 | 17 |
| get_monitor_metrics | 2385 | body | /v2/monitor/metrics | 2 | 9 |
| check_resource_name | 2393 | body["bean"] | /v2/tenants/.../checkResourceName | 2 | 17 |
| parse_app_services | 2406 | body["list"] | /v2/tenants/.../apps/{}/parse-services | 1 | 17 |
| list_app_releases | 2418 | body["list"] | /v2/tenants/.../apps/{}/releases | 1 | 17 |
| sync_components | 2427 | no-return | /v2/tenants/{}/apps/{}/components | 6 | 17 |
| sync_config_groups | 2433 | no-return | /v2/tenants/{}/apps/{}/app-config-groups | 1 | 17 |
| sync_plugins | 2439 | no-return | /v2/tenants/{}/plugins | 1 | 8 |
| build_plugins | 2445 | no-return | /v2/tenants/{}/batch-build-plugins | 1 | 8 |
| get_region_license | 2451 | res,content | (license endpoint) | 0 | 18 |
| get_region_license_feature | 2458 | body | (license feature) | 1 | 18 |
| get_license_cluster_id | 2465 | body | /v2/license/cluster-id | 1 | 18 |
| activate_license | 2472 | body | /v2/license/activate | 4 | 18 |
| get_license_status | 2484 | body | /v2/license/status | 5 | 18 |
| list_app_statuses_by_app_ids | 2491 | body | /v2/tenants/{}/appstatuses | 2 | 17 |
| get_component_log | 2498 | resp (stream) | /v2/tenants/{}/services/{}/log | 1 | 19 |
| change_application_volumes | 2507 | resp | /v2/tenants/{}/apps/{}/volumes | 2 | 19 |
| get_region_alerts | 2514 | res,body | /api/v1/alerts | 1 | 9 |
| create_registry_auth | 2521 | resp | /v2/tenants/{}/registry/auth | 2 | 19 |
| update_registry_auth | 2528 | resp | /v2/tenants/{}/registry/auth | 2 | 19 |
| delete_registry_auth | 2535 | resp | /v2/tenants/{}/registry/auth | 2 | 19 |
| get_component_authorization_policy | 2542 | body | /v2/tenants/{}/services/{}/component_authorization_policy | 0 | 19 |
| get_app_resource | 2550 | res,body | /v2/cluster/k8s-resource | 2 | 20 |
| create_app_resource | 2559 | res,body | /v2/cluster/k8s-resource | 1 | 20 |
| update_app_resource | 2568 | res,body | /v2/cluster/k8s-resource | 1 | 20 |
| delete_app_resource | 2577 | res,body | /v2/cluster/k8s-resource | 1 | 20 |
| batch_delete_app_resources | 2586 | res,body | /v2/cluster/batch-k8s-resource | 1 | 20 |
| sync_k8s_resources | 2595 | res,body | /v2/cluster/sync-k8s-resources | 1 | 19 |
| get_component_k8s_attribute | 2601 | res,body | /v2/tenants/{}/services/{}/k8s-attributes | 1 | 19 |
| create_component_k8s_attribute | 2608 | res,body | /v2/tenants/{}/services/{}/k8s-attributes | 4 | 19 |
| update_component_k8s_attribute | 2615 | res,body | /v2/tenants/{}/services/{}/k8s-attributes | 4 | 19 |
| delete_component_k8s_attribute | 2622 | res,body | /v2/tenants/{}/services/{}/k8s-attributes | 2 | 19 |
| get_rbd_pods | 2629 | body | /v2/cluster/rbd-resource/pods | 1 | 21 |
| get_rbd_pod_log | 2639 | res (stream) | /v2/cluster/rbd-resource/log | 1 | 21 |
| get_rbd_component_logs | 2650 | body | /v2/cluster/rbd-name/{0}/logs | 1 | 21 |
| get_rbd_log_files | 2660 | body | /v2/cluster/log-file | 1 | 21 |
| create_shell_pod | 2670 | body | /v2/cluster/shell-pod | 1 | 21 |
| delete_shell_pod | 2680 | body | /v2/cluster/shell-pod | 1 | 21 |
| get_cluster_nodes | 2690 | res,body | /v2/cluster/nodes | 5 | 21 |
| get_cluster_nodes_arch | 2699 | res,body | /v2/cluster/nodes/arch | 12 | 21 |
| get_vm_capabilities | 2708 | res,body | /v2/tenants/.../vm-capabilities | 5 | 21 |
| create_vm_snapshot | 2717 | res,body | /v2/tenants/{}/services/{}/vm-snapshots | 0 | 21 |
| get_node_info | 2727 | res,body | /v2/cluster/nodes/{0}/detail | 1 | 21 |
| operate_node_action | 2736 | res,body | /v2/cluster/nodes/{0}/action/{1} | 1 | 21 |
| get_node_labels | 2745 | res,body | /v2/cluster/nodes/{0}/labels | 1 | 21 |
| update_node_labels | 2754 | res,body | /v2/cluster/nodes/{0}/labels | 1 | 21 |
| get_node_taints | 2763 | res,body | /v2/cluster/nodes/{0}/taints | 1 | 21 |
| update_node_taints | 2772 | res,body | /v2/cluster/nodes/{0}/taints | 1 | 21 |
| get_rainbond_components | 2781 | res,body | /v2/cluster/rbd-components | 1 | 21 |
| get_container_disk | 2790 | res,body | /v2/container_disk/{} | 1 | 21 |
| list_plugins | 2799 | res,body | /v2/cluster/plugins | 14 | 8 |
| create_rbdplugin | 2807 | res,body | /v2/cluster/plugins | 1 | 8 |
| list_abilities | 2815 | res,body | /v2/cluster/abilities | 2 | 14 |
| update_ability | 2823 | res,body | /v2/cluster/abilities/{ability_id} | 2 | 14 |
| get_ability | 2831 | res,body | /v2/cluster/abilities/{ability_id} | 2 | 14 |
| get_lang_version **(DUP-1)** | 2839 | body | /v2/cluster/langVersion | 2 | 22 |
| create_lang_version **(DUP-1)** | 2861 | body | /v2/cluster/langVersion | 1 | 22 |
| update_lang_version **(DUP-1)** | 2870 | body | /v2/cluster/langVersion | 1 | 22 |
| delete_lang_version **(DUP-1)** | 2879 | body | /v2/cluster/langVersion | 1 | 22 |
| get_cnb_frameworks | 2888 | body | /v2/cluster/cnb/frameworks | 1 | 22 |
| post_proxy | 2897 | body | (proxy path) | 3 | 23 |
| get_proxy | 2906 | body | (proxy path) | 2 | 23 |
| get_files | 2918 | body | /v2/tenants/.../files | 2 | 19 |
| get_pod_volume | 2931 | res,body | /v2/tenants/{0}/services/{1}/pod-volume | 0 | 5 |
| get_app_peer_authentications | 2943 | body | /v2/tenants/{}/apps/{}/app_peer_authentications | 1 | 17 |
| app_peer_authentications | 2952 | body | /v2/tenants/{}/apps/{}/app_peer_authentications | 0 | 17 |
| get_app_authorization_policy | 2960 | body | /v2/tenants/{}/apps/{}/app_authorization_policy | 1 | 17 |
| app_authorization_policy | 2969 | body | /v2/tenants/{}/apps/{}/app_authorization_policy | 0 | 17 |
| get_app_gray_release | 2977 | res,body | /v2/tenants/{}/apps/{}/gray_release | 0 | 17 |
| create_app_gray_release | 2986 | body.get("bean") | /v2/tenants/{}/apps/{}/gray_release | 0 | 17 |
| update_app_gray_release | 2994 | body.get("bean") | /v2/tenants/{}/apps/{}/gray_release | 0 | 17 |
| operate_app_gray_release | 3002 | body | /v2/tenants/{}/apps/{}/operate_gray_release | 0 | 17 |
| save_yaml | 3011 | no-return | (proxy) | 0 | 23 |
| api_gateway_post_proxy | 3025 | body["bean"] | /api-gateway proxy | 5 | 23 |
| api_gateway_get_proxy | 3071 | body | /api-gateway proxy | 10 | 23 |
| api_gateway_delete_proxy | 3121 | body["bean"] | /api-gateway proxy | 2 | 23 |
| get_port | 3131 | res,body | /v2/gateway/ports | 2 | 23 |
| api_gateway_bind_tcp_domain | 3138 | passthrough(post_proxy) | /v2/proxy-pass/gateway/ | 5 | 23 |
| api_gateway_bind_http_domain | 3160 | passthrough(post_proxy) | /api-gateway/v1/ | 7 | 23 |
| get_api_gateway | 3184 | passthrough(get_proxy) | /api-gateway/v1/ | 3 | 23 |
| api_gateway_bind_http_domain_convert | 3188 | passthrough(post_proxy) | /api-gateway/v1/ | 1 | 23 |
| delete_proxy | 3210 | body | (proxy path) | 2 | 23 |
| put_proxy | 3222 | body | (proxy path) | 0 | 23 |
| sse_proxy | 3231 | response (stream) | /v2/tenants/ | 3 | 23 |
| get_component_pod_log | 3264 | resp (stream) | /v2/tenants/{}/services/{}/pods/{}/logs | 3 | 19 |
| exec_component_pod | 3301 | body | /v2/tenants/{}/services/{}/pods/{}/exec | 1 | 19 |
| upgrade_region | 3357 | body | /v2/cluster/rbd-upgrade | 1 | 24 |
| list_upgrade_status | 3364 | body | /v2/cluster/rbd-upgrade/status | 1 | 24 |
| get_lang_version **(DUP-2 winner)** | 3371 | body | /v2/cluster/langVersion | 2 | 22 |
| create_lang_version **(DUP-2 winner)** | 3393 | body | /v2/cluster/langVersion | 1 | 22 |
| update_lang_version **(DUP-2 winner)** | 3413 | body | /v2/cluster/langVersion | 1 | 22 |
| delete_lang_version **(DUP-2 winner)** | 3433 | body | /v2/cluster/langVersion | 1 | 22 |
| set_over_score_rate | 3453 | ret_data | /v2/cluster/over_score | 2 | 24 |
| get_kubeblocks_supported_databases | 3465 | res,body | /v2/cluster/kubeblocks/supported-databases | 1 | 25 |
| get_kubeblocks_storage_classes | 3478 | res,body | /v2/cluster/kubeblocks/storage-classes | 1 | 25 |
| get_kubeblocks_backup_repos | 3491 | res,body | /v2/cluster/kubeblocks/backup-repos | 2 | 25 |
| create_kubeblocks_backup_repo | 3504 | res,body | /v2/cluster/kubeblocks/backup-repos | 1 | 25 |
| update_kubeblocks_backup_repo | 3517 | res,body | /v2/cluster/kubeblocks/backup-repos/{repo_name} | 1 | 25 |
| delete_kubeblocks_backup_repo | 3530 | res,body | /v2/cluster/kubeblocks/backup-repos/{repo_name} | 1 | 25 |
| create_kubeblocks_cluster | 3543 | res,body | /v2/cluster/kubeblocks/clusters | 1 | 25 |
| get_kubeblocks_connect_info | 3556 | res,body | /v2/cluster/kubeblocks/clusters/connect-infos | 1 | 25 |
| get_kubeblocks_cluster_detail | 3570 | res,body | /v2/cluster/kubeblocks/clusters/{service_id} | 1 | 25 |
| expansion_kubeblocks_cluster | 3583 | res,body | /v2/cluster/kubeblocks/clusters/{service_id} | 1 | 25 |
| update_kubeblocks_backup_config | 3596 | res,body | /v2/cluster/kubeblocks/clusters/{service_id}/backup-schedules | 1 | 25 |
| create_kubeblocks_manual_backup | 3609 | res,body | /v2/cluster/kubeblocks/clusters/{service_id}/backups | 1 | 25 |
| get_kubeblocks_backup_list | 3622 | res,body | /v2/cluster/kubeblocks/clusters/{service_id}/backups | 1 | 25 |
| delete_kubeblocks_backups | 3645 | res,body | /v2/cluster/kubeblocks/clusters/{service_id}/backups | 1 | 25 |
| delete_kubeblocks_cluster | 3660 | res,body | /v2/cluster/kubeblocks/clusters | 6 | 25 |
| get_kubeblocks_cluster_events | 3673 | res,body | /v2/cluster/kubeblocks/clusters/{service_id}/events | 1 | 25 |
| manage_cluster_status | 3687 | res,response_body | /v2/cluster/kubeblocks/clusters/actions | 8 | 25 |
| kubeblocks_cluster_pod_detail | 3704 | body | /v2/cluster/kubeblocks/clusters/{service_id}/pods/{pod_name}/details | 2 | 25 |
| get_kubeblocks_cluster_parameters | 3717 | res,body | /v2/cluster/kubeblocks/clusters/{service_id}/parameters | 1 | 25 |
| update_kubeblocks_cluster_parameters | 3743 | res,response_body | /v2/cluster/kubeblocks/clusters/{service_id}/parameters | 1 | 25 |
| restore_cluster_from_backup | 3756 | res,response_body | /v2/cluster/kubeblocks/clusters/{old_service_id}/restores | 2 | 25 |
| get_cluster_resource | 3775 | res,body | /v2/cluster/{path} | 6 | 26 |
| post_cluster_resource | 3788 | res,response_body | /v2/cluster/{path} | 3 | 26 |
| delete_cluster_resource | 3801 | res,body | /v2/cluster/{path} | 3 | 26 |
| put_cluster_resource | 3814 | res,response_body | /v2/cluster/{path} | 1 | 26 |
| get_tenant_ns_resource_types | 3827 | res,body | /v2/tenants/{}/ns-resource-types | 1 | 26 |
| get_tenant_ns_resources | 3835 | res,body | /v2/tenants/{}/ns-resources | 1 | 26 |
| get_tenant_ns_resource | 3846 | res,body | /v2/tenants/{}/ns-resources/{} | 2 | 26 |
| post_tenant_ns_resource | 3857 | res,response_body | /v2/tenants/{}/ns-resources | 1 | 26 |
| put_tenant_ns_resource | 3871 | res,response_body | /v2/tenants/{}/ns-resources/{} | 2 | 26 |
| delete_tenant_ns_resource | 3885 | res,body | /v2/tenants/{}/ns-resources/{} | 1 | 26 |
| get_tenant_helm_releases | 3896 | res,body | /v2/tenants/{}/helm/releases | 1 | 26 |
| install_tenant_helm_release | 3906 | res,response_body | /v2/tenants/{}/helm/releases | 1 | 26 |
| preview_tenant_helm_chart | 3914 | res,response_body | /v2/tenants/{}/helm/chart-preview | 1 | 26 |
| get_tenant_helm_release_history | 3922 | res,body | /v2/tenants/{}/helm/releases/{}/history | 1 | 26 |
| get_tenant_helm_release_detail | 3932 | res,body | /v2/tenants/{}/helm/releases/{} | 1 | 26 |
| upgrade_tenant_helm_release | 3942 | res,response_body | /v2/tenants/{}/helm/releases/{} | 1 | 26 |
| rollback_tenant_helm_release | 3950 | res,response_body | /v2/tenants/{}/helm/releases/{}/rollback | 1 | 26 |
| uninstall_tenant_helm_release | 3958 | res,body | /v2/tenants/{}/helm/releases/{} | 1 | 26 |
| get_resource_center_workload_detail | 3968 | res,body | /v2/tenants/{}/resource-center/workloads/{}/{} | 1 | 26 |
| get_resource_center_pod_detail | 3979 | res,body | /v2/tenants/{}/resource-center/pods/{} | 1 | 26 |
| get_resource_center_events | 3987 | res,body | /v2/tenants/{}/resource-center/events | 1 | 26 |
| get_resource_center_pod_log | 3998 | resp (stream) | /v2/tenants/{}/resource-center/pods/{}/logs | 1 | 26 |

> 私有/内部方法（不计入 376 业务方法的外部契约，但仍需注解）：`__init__`(29)、`make_proxy_http`(33)、`_set_headers`(44)、`__get_tenant_region_info`(77)、`__get_region_access_info`(1389)、`__get_region_access_info_by_enterprise_id`(1409)、`__is_container_not_running_message`(3340，staticmethod)。

---

## Section 4 — 重复 / 死代码方法

文件中**唯一**的重复定义是这 4 个，每个定义两次，函数体完全等价（仅第二份多了中文 docstring）。Python 后定义胜出，因此 **2839–2887 这一段是死代码**，M2 删除即可（删除后注意 `get_cnb_frameworks` 起始行从 2888 上移）。

| 方法 | 第一次定义（死代码） | 第二次定义（生效） | 备注 |
|------|--------------------|------------------|------|
| `get_lang_version` | 2839–2859 | 3371–3391 | 体相同，第二份带 docstring |
| `create_lang_version` | 2861–2868 | 3393–3411 | 同上 |
| `update_lang_version` | 2870–2877 | 3413–3431 | 同上 |
| `delete_lang_version` | 2879–2886 | 3433–3451 | 同上 |

**待删除行段：2839–2887（含 4 个死方法及其间空行）。** 程序化校验已确认全文件无其它重名 `def`。

---

## Section 5 — 并行注解的物理不重叠切块

> 一文件多人改会冲突；下表把 4007 行按**物理连续区间**切成 10 块，块间无重叠、可分派给独立 subagent。每块都覆盖整数个完整方法（不会切断方法体）。先单独完成 Phase-0（基类 + 块 A 的请求源），再并行 B–J。
> "DUP 处理"：块 G 负责删除 2839–2887 死代码。删除发生在块 G 内部，不影响其它块的行号（其它块在 G 之后/之前各自独立完成注解后再合并；建议 G 最后合并或先合并 G 再 rebase 其它块）。

| 块 | 行范围 | 域（Section 2 #） | 方法数(约) | 高频方法(caller≥5) |
|----|--------|------------------|-----------|---------------------|
| **A** (Phase-0, 串行先做) | 基类两文件 + `regionapi.py` 29–91 | 请求源 + infra | 7 + 5 | `_get/_post/_put/_delete`、`_check_status`、`_request` |
| **B** | 92–662 | service 生命周期 / ports / envs / labels / probe / lifecycle (1,2,3) | 59 | add_service_port(17), add_service_probe(11), add_service_dependency(10), delete_service_env(10), delete_service_port(8), delete_service_probe(8), check_service_status(7), get_service_pods(7), vertical_upgrade(6), update_service_port(6), horizontal_upgrade(5), delete_service_dependency(5) |
| **C** | 663–1053 | helm/chart + volumes + logs/events + share/vm-export (4,5,6,8,21) | ~46 | get_service_volumes(17), add_service_volume(12), check_helm_app(7), delete_service_volumes(7), service_status(6), get_event_log(4) |
| **D** | 1054–1388 | gateway/domain/cert/route + plugin + monitoring query + events (7,8,9,6) | ~52 | get_query_data(7), build_plugin(7), get_query_range_data(6), get_tenant_events(5), delete_plugin(5)†, create_plugin(4)† |
| **E** | 1389–1989 | region access + image/check + plugin install + import/export/backup + build-version + 3rd-party + autoscaler (0,1,8,10,11,12,13) | ~70 | get_region_info(51), get_enterprise_region_info(41), get_third_party_service_pods(7), restore_properties(7), batch_operation_service(6), set... |
| **F** | 1990–2450 | cluster/region resources + tenant + service-monitor/maven + app-group/config-group/governance (14,15,16,17) | ~70 | get_app_status(13), install_app(9), delete_app(7), sync_components(6), get_region_resources(5), set_tenant_resource_limit(5) |
| **G** | 2451–2897 | license + component log/registry/k8s-attr + app-resource + rbd/nodes/vm + cluster plugins + lang-version(**删 2839–2887**) (18,19,20,21,8,14,22) | ~58 | list_plugins(14), get_cluster_nodes_arch(12), delete_kubeblocks_cluster? n/a, get_license_status(5), get_cluster_nodes(5), get_vm_capabilities(5), create_component_k8s_attribute(4), update_component_k8s_attribute(4), activate_license(4) |
| **H** | 2898–3356 | files + app peer/authz/gray + 各类 proxy + sse + component pod log/exec (19,17,23) | ~36 | api_gateway_get_proxy(10), api_gateway_bind_http_domain(7), api_gateway_post_proxy(5), api_gateway_bind_tcp_domain(5) |
| **I** | 3357–3774 | upgrade-region + over-score + lang-version(生效副本) + kubeblocks 全套 (24,22,25) | ~34 | manage_cluster_status(8), delete_kubeblocks_cluster(6), get_cluster_resource? in J |
| **J** | 3775–4007 | generic cluster-resource + tenant-ns-resource + helm-release + resource-center (26) | 31 | get_cluster_resource(6), post_cluster_resource(3), delete_cluster_resource(3) |

合计方法数对账：A(5 业务-ish)+B(59)+C(46)+D(52)+E(70)+F(70)+G(58)+H(36)+I(34)+J(31) ≈ 461 含重叠估计——以实际 `def` 计为准：全文件 375 个 class-level `def`（含 4 个重复方法的 8 处定义）。删除 4 处死代码后剩 371 个唯一定义。

### 建议执行顺序
1. **A 串行**：先注解 `baseclient.py` + `regionapibaseclient.py` 的 `_request/_check_status/_jsondecode/_unpack/_get/_post/_put/_delete`，并决策 `addict.Dict` 处理策略（视作 `Any` 或写最小 `.pyi`）。这是其它所有块的类型前提。
2. **B–J 并行**：每块一个 subagent，行号互不重叠。块内统一规则：`return body` → `Optional[Dict[str, Any]]`；`return res, body` → `Tuple[Any, Optional[Dict[str, Any]]]`；流式 → `urllib3.HTTPResponse`/`StreamingHttpResponse`；`no-return`/`return None` → `Optional[...]`/`None`；`return body["bean"]` 等 → `Any`（运行时下钻）。
3. **G 含删除**：块 G 删除 2839–2887。为避免与 I 的行号耦合（I 注解 3371+ 的生效副本），建议 G 与 I **不并行**，或 G 先合并、其余 rebase。
