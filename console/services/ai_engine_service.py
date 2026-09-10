# -*- coding: utf-8 -*-
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

from console.exception.main import ServiceHandleException
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.repositories.team_repo import team_repo
from console.services.region_services import region_services
from console.services.team_services import team_services
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class AIEngineContext(object):
    def __init__(self, enterprise_id: str, team: Any, region_name: str) -> None:
        self.enterprise_id = enterprise_id
        self.team = team
        self.region_name = region_name

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "X-AI-Team-Name": self.team.tenant_name,
            "X-AI-Region-Name": self.region_name,
            "X-AI-Team-Namespace": self.team.namespace,
        }


class AIEngineProxyService(object):
    PLUGIN_NAME = "rainbond-ai-engine"
    API_PREFIX = "/api/v1/ai-engine"
    UPSTREAM_CONTRACT_SCHEMA = "rainbond.ai-engine.skills-prerequisites.v1"
    MAX_PAGE_SIZE = 50
    MAX_LOG_LINES = 1000
    DEFAULT_PAGE_SIZE = 20
    DEFAULT_LOG_LINES = 200
    MAX_LOG_BYTES = 64 * 1024
    MAX_EVENT_BYTES = 64 * 1024
    MAX_GPU_POINTS = 720
    MAX_EXTRA_ARGV_BYTES = 16 * 1024
    ERROR_DETAIL_FIELDS = frozenset({
        "argument",
        "arguments",
        "form_field",
        "reason",
        "index",
        "limit",
        "field",
        "replacement",
    })
    REGISTRY_ERROR_CODES = frozenset({
        "registry_access_unsupported",
        "registry_egress_unavailable",
        "registry_invalid_response",
        "registry_invalid_source",
        "registry_not_found",
        "registry_rate_limited",
        "registry_unavailable",
    })
    INTERNAL_OUTPUT_FIELDS = frozenset({
        "namespace",
        "local_path",
        "runtime_image",
        "runtime_image_digest",
        "env_vars",
        "model_source",
        "deployment_name",
        "service_name",
        "pod_name",
        "pod_ip",
        "readme",
        "uid",
        "annotations",
        "service_account",
        "service_account_name",
        "secret_ref",
    })
    SENSITIVE_NAME_PATTERN = re.compile(
        r"(?:^|[-_])(?:token|password|passwd|secret|authorization|cookie|api[-_]?key|private[-_]?key|"
        r"key[-_]?file|cert[-_]?file)(?:$|[-_])",
        re.I,
    )
    SENSITIVE_TEXT_PATTERN = re.compile(
        r"(?i)\b(token|password|passwd|secret|authorization|cookie|api[-_]?key)\s*([=:])\s*(?:bearer\s+)?[^\s,;]+")
    SENSITIVE_ARG_TEXT_PATTERN = re.compile(
        r"(?i)(--[a-z0-9_-]*(?:token|password|passwd|secret|authorization|cookie|api[-_]?key|"
        r"private[-_]?key|key[-_]?file|cert[-_]?file)[a-z0-9_-]*)(=|\s+)([^\s,;]+)")
    BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
    URL_CREDENTIAL_PATTERN = re.compile(r"(?i)(https?://)[^/@\s]+@")
    ABSOLUTE_PATH_PATTERN = re.compile(r"(^|\s)/[^\s]+")
    IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    MODELSCOPE_PART_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
    RESOURCE_FIELDS = frozenset({
        "gpu_count",
        "gpu_type",
        "node_name",
        "cpu_request_cores",
        "cpu_limit_cores",
        "memory_request_gib",
        "memory_limit_gib",
        "shared_memory_gib",
    })
    DYNAMIC_PARAM_FIELDS = frozenset({
        "gpu_memory_utilization",
        "cpu_kvcache_space_gb",
        "max_model_len",
        "runner",
        "convert",
        "model_impl",
        "dtype",
        "kv_cache_dtype",
        "max_num_seqs",
        "max_num_batched_tokens",
        "prefix_caching",
        "kv_cache_memory_bytes",
        "tensor_parallel_size",
        "pipeline_parallel_size",
        "trust_remote_code",
        "runtime_quantization",
    })
    LOCAL_PATH_ARG_NAMES = frozenset({"--model", "--model-path"})

    @staticmethod
    def _permission_denied(message: str) -> ServiceHandleException:
        return ServiceHandleException(
            msg="permission denied",
            msg_show=message,
            status_code=403,
            error_code="permission_denied",
        )

    @staticmethod
    def _required_string(arguments: dict, name: str, max_length: int = 512) -> str:
        value = arguments.get(name)
        if not isinstance(value, str):
            value = ""
        value = value.strip()
        if not value or len(value) > max_length or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ServiceHandleException(
                msg="invalid {}".format(name),
                msg_show="参数{}无效".format(name),
                status_code=400,
                error_code="invalid_input",
                details={"field": name},
            )
        return value

    def _context(self, user: Any, arguments: dict) -> AIEngineContext:
        enterprise_id = getattr(user, "enterprise_id", None)
        user_id = getattr(user, "user_id", None)
        if not enterprise_id or not user_id:
            raise self._permission_denied("缺少有效的企业用户上下文")
        team_name = self._required_string(arguments, "team_name", 64)
        region_name = self._required_string(arguments, "region_name", 64)
        team = team_services.get_enterprise_tenant_by_tenant_name(enterprise_id, team_name)
        if not team:
            raise ServiceHandleException(
                msg="team not found",
                msg_show="团队不存在",
                status_code=404,
                error_code="team_not_found",
            )
        if user_id != getattr(team, "creater", None) and not enterprise_user_perm_repo.is_admin(enterprise_id, user_id):
            member_team = team_repo.get_user_tenant_by_name(user_id, team_name)
            if not member_team or getattr(member_team, "tenant_id", None) != getattr(team, "tenant_id", None):
                raise self._permission_denied("无该团队访问权限")
        region = region_services.get_enterprise_region_by_region_name(enterprise_id, region_name)
        if not region:
            raise ServiceHandleException(
                msg="region not found",
                msg_show="集群不存在",
                status_code=404,
                error_code="region_not_found",
            )
        bindings = team_repo.get_team_region_by_name(team.tenant_id, region_name)
        if not bindings:
            raise self._permission_denied("团队未开通该集群")
        binding = bindings[0]
        if getattr(binding, "is_active", True) is False or getattr(binding, "is_init", True) is False:
            raise self._permission_denied("团队在该集群尚未完成初始化")
        if not getattr(team, "namespace", None):
            raise ServiceHandleException(
                msg="team namespace unavailable",
                msg_show="团队命名空间不可用",
                status_code=503,
                error_code="team_namespace_unavailable",
            )
        return AIEngineContext(enterprise_id, team, region_name)

    def _call(self,
              context: AIEngineContext,
              method: str,
              path: str,
              query: Optional[dict] = None,
              body: Optional[dict] = None) -> Any:
        status, envelope = region_api.request_plugin_backend(
            context.enterprise_id,
            context.region_name,
            self.PLUGIN_NAME,
            method,
            path,
            query=query,
            body=body,
            headers=context.headers,
            timeout=30,
        )
        if not isinstance(envelope, dict):
            raise ServiceHandleException(
                msg="invalid AI Engine response",
                msg_show="AI Engine 返回了无效响应",
                status_code=502,
                error_code="ai_engine_invalid_response",
            )
        code = envelope.get("code")
        failed = status >= 400 or (isinstance(code, int) and code >= 400)
        if failed:
            self._raise_upstream_error(status, envelope)
        if "data" not in envelope:
            raise ServiceHandleException(
                msg="invalid AI Engine response",
                msg_show="AI Engine 响应缺少 data",
                status_code=502,
                error_code="ai_engine_invalid_response",
            )
        return envelope.get("data")

    def _raise_upstream_error(self, status: int, envelope: dict) -> None:
        status_code = status if 400 <= status <= 599 else int(envelope.get("code") or 502)
        msg = str(envelope.get("msg") or "AI Engine request failed")
        error_code = envelope.get("error_code")
        if not error_code:
            prefix = msg.split(":", 1)[0].strip()
            error_code = prefix if prefix in self.REGISTRY_ERROR_CODES else "ai_engine_http_{}".format(status_code)
        raw_details = envelope.get("details")
        details = None
        if isinstance(raw_details, dict):
            details = {
                key: self._sanitize_output(value)
                for key, value in raw_details.items() if key in self.ERROR_DETAIL_FIELDS
            }
        raise ServiceHandleException(
            msg=self._redact_text(msg),
            msg_show=self._redact_text(msg),
            status_code=status_code,
            error_code=error_code,
            details=details,
        )

    def _sanitize_output(self, value: Any, key: str = "") -> Any:
        if key in ("extra_argv", "resolved_argv") and isinstance(value, list):
            return self._redact_argv(value)
        if key == "logs" and isinstance(value, str):
            return self._redact_text(value)
        if isinstance(value, dict):
            result = {}
            for item_key, item_value in value.items():
                normalized = str(item_key).lower()
                if normalized in self.INTERNAL_OUTPUT_FIELDS:
                    continue
                if self.SENSITIVE_NAME_PATTERN.search(normalized):
                    result[item_key] = "***"
                    continue
                result[item_key] = self._sanitize_output(item_value, normalized)
            return result
        if isinstance(value, list):
            return [self._sanitize_output(item) for item in value]
        if isinstance(value, str):
            return self._redact_text(value)
        return value

    def _redact_argv(self, argv: List[Any]) -> List[Any]:
        result = list(argv)
        redact_next = False
        for index, raw in enumerate(result):
            if not isinstance(raw, str):
                redact_next = False
                continue
            if redact_next:
                result[index] = "***"
                redact_next = False
                continue
            if raw.startswith("/"):
                result[index] = "***"
                continue
            if not raw.startswith("--"):
                continue
            name, separator, _ = raw.partition("=")
            if name in self.LOCAL_PATH_ARG_NAMES:
                if separator:
                    result[index] = "{}=***".format(name)
                else:
                    redact_next = True
                continue
            if not self.SENSITIVE_NAME_PATTERN.search(name):
                continue
            if separator:
                result[index] = "{}=***".format(name)
            else:
                redact_next = True
        return result

    def _redact_text(self, value: str) -> str:
        redacted = self.SENSITIVE_ARG_TEXT_PATTERN.sub(lambda match: "{}{}***".format(match.group(1), match.group(2)), value)
        redacted = self.SENSITIVE_TEXT_PATTERN.sub(lambda match: "{}{}***".format(match.group(1), match.group(2)), redacted)
        return self.BEARER_PATTERN.sub("Bearer ***", redacted)

    @staticmethod
    def _without_keys(value: Any, keys: Tuple[str, ...]) -> Any:
        if not isinstance(value, dict):
            return value
        return {key: item for key, item in value.items() if key not in keys}

    def _pagination(self, arguments: dict) -> Tuple[int, int]:
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", self.DEFAULT_PAGE_SIZE)
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ServiceHandleException(msg="invalid page", msg_show="参数page无效", status_code=400)
        if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= self.MAX_PAGE_SIZE:
            raise ServiceHandleException(msg="invalid page_size", msg_show="参数page_size无效", status_code=400)
        return page, page_size

    @staticmethod
    def _paginate(items: List[Any], page: int, page_size: int) -> dict:
        total = len(items)
        start = (page - 1) * page_size
        selected = items[start:start + page_size]
        return {
            "items": selected,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": start + len(selected) < total,
        }

    def _tail_lines(self, arguments: dict) -> int:
        tail_lines = arguments.get("tail_lines", self.DEFAULT_LOG_LINES)
        if not isinstance(tail_lines, int) or isinstance(tail_lines, bool) or not 1 <= tail_lines <= self.MAX_LOG_LINES:
            raise ServiceHandleException(msg="invalid tail_lines", msg_show="参数tail_lines无效", status_code=400)
        return tail_lines

    def _bounded_logs(self, data: Any, tail_lines: int) -> dict:
        data = data if isinstance(data, dict) else {}
        logs = self._redact_text(str(data.get("logs") or ""))
        encoded = logs.encode("utf-8")
        locally_truncated = len(encoded) > self.MAX_LOG_BYTES
        if locally_truncated:
            logs = encoded[-self.MAX_LOG_BYTES:].decode("utf-8", errors="ignore")
        return {
            "available": data.get("available") if isinstance(data.get("available"), bool) else bool(logs),
            "reason": str(data.get("reason") or ""),
            "log_source": str(data.get("log_source") or "current"),
            "logs": logs,
            "tail_lines": data.get("tail_lines") if isinstance(data.get("tail_lines"), int) else tail_lines,
            "truncated": bool(data.get("truncated")) or locally_truncated,
        }

    @staticmethod
    def _bounded_integer(arguments: dict, name: str, default: int, minimum: int, maximum: int) -> int:
        value = arguments.get(name, default)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise ServiceHandleException(
                msg="invalid {}".format(name),
                msg_show="参数{}无效".format(name),
                status_code=400,
                error_code="invalid_input",
                details={
                    "field": name,
                    "limit": maximum
                },
            )
        return value

    def _redact_event_text(self, value: Any) -> str:
        redacted = self._redact_text(str(value or ""))
        redacted = self.URL_CREDENTIAL_PATTERN.sub(r"\1***@", redacted)
        redacted = self.ABSOLUTE_PATH_PATTERN.sub(r"\1[path]", redacted)
        return self.IPV4_PATTERN.sub("[ip]", redacted)

    def get_capabilities(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        data = self._sanitize_output(self._call(context, "GET", self.API_PREFIX + "/deployment-capabilities"))
        if isinstance(data, dict) and isinstance(data.get("runtimes"), dict):
            data["runtimes"] = {name: self._without_keys(runtime, ("image", )) for name, runtime in data["runtimes"].items()}
        return data

    def get_resource_capacity(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        data = self._call(context, "GET", self.API_PREFIX + "/nodes")
        data = data if isinstance(data, dict) else {}
        node_fields = (
            "name",
            "architecture",
            "cpu_capacity",
            "cpu_allocatable",
            "memory_capacity_bytes",
            "memory_allocatable_bytes",
            "gpu_count",
            "gpu_provider",
            "gpu_provider_state",
            "gpu_provider_reason",
            "gpu_provider_observed_at",
            "physical_gpu_count",
            "virtual_gpu_count",
            "advertised_gpu_count",
            "expected_advertised_gpu_count",
            "device_plugin_conflict",
            "gpu_share_available",
            "gpu_share_reason",
            "hami_version",
            "gpu_products",
            "gpu_product",
        )
        nodes = []
        for node in data.get("nodes") or []:
            if isinstance(node, dict):
                nodes.append({key: node.get(key) for key in node_fields if key in node})
        return self._sanitize_output({
            "resource_capacity": data.get("resource_capacity"),
            "gpu_available": data.get("gpu_available"),
            "nodes": nodes,
        })

    def search_model_catalog(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        page, page_size = self._pagination(arguments)
        query = {key: arguments.get(key) for key in ("keyword", "owner", "section") if arguments.get(key) not in (None, "")}
        query.update({"page": page, "page_size": page_size, "include_status": "true"})
        data = self._call(context, "GET", self.API_PREFIX + "/model-catalog", query=query)
        data = data if isinstance(data, dict) else {}
        items = [self._without_keys(self._sanitize_output(item), ("readme", )) for item in (data.get("models") or [])]
        total = data.get("total") if isinstance(data.get("total"), int) else len(items)
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": page * page_size < total,
            "resource_meta": self._sanitize_output(data.get("resource_meta")),
        }

    def get_model_catalog_detail(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        owner = self._required_string(arguments, "owner", 256)
        repo_name = self._required_string(arguments, "repo_name", 256)
        path = self.API_PREFIX + "/model-catalog/{}/{}".format(quote(owner, safe=""), quote(repo_name, safe=""))
        data = self._sanitize_output(self._call(context, "GET", path))
        return self._without_keys(data, ("readme", ))

    def list_model_recommendations(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        limit = arguments.get("limit", 10)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise ServiceHandleException(msg="invalid limit", msg_show="参数limit无效", status_code=400)
        data = self._call(context, "GET", self.API_PREFIX + "/model-recommendations", query={"include_status": "true"})
        data = data if isinstance(data, dict) else {}
        items = [self._without_keys(self._sanitize_output(item), ("readme", )) for item in (data.get("models") or [])]
        items = items[:limit]
        return {
            "items": items,
            "total": len(items),
            "limit": limit,
            "resource_meta": self._sanitize_output(data.get("resource_meta")),
        }

    def _team_models(self, context: AIEngineContext) -> List[dict]:
        data = self._call(context, "GET", self.API_PREFIX + "/team/models")
        data = data if isinstance(data, dict) else {}
        return [self._sanitize_output(item) for item in (data.get("models") or []) if isinstance(item, dict)]

    def list_team_models(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        page, page_size = self._pagination(arguments)
        status = arguments.get("status")
        items = self._team_models(context)
        if status:
            items = [item for item in items if str(item.get("status") or "").lower() == str(status).lower()]
        items.sort(key=lambda item: str(item.get("model_key") or ""))
        return self._paginate(items, page, page_size)

    def _find_team_model(self, context: AIEngineContext, model_key: str) -> dict:
        for item in self._team_models(context):
            if item.get("model_key") == model_key:
                return item
        raise ServiceHandleException(
            msg="team model not found",
            msg_show="团队模型不存在",
            status_code=404,
            error_code="team_model_not_found",
        )

    def get_team_model(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        return self._find_team_model(context, self._required_string(arguments, "model_key"))

    def _downloads(self, context: AIEngineContext) -> List[dict]:
        data = self._call(context, "GET", self.API_PREFIX + "/team/downloads")
        data = data if isinstance(data, dict) else {}
        return [self._sanitize_output(item) for item in (data.get("downloads") or []) if isinstance(item, dict)]

    def _find_download(self, context: AIEngineContext, model_key: str = "", job_name: str = "") -> dict:
        for item in self._downloads(context):
            if model_key and item.get("model_key") == model_key:
                return item
            if job_name and item.get("job_name") == job_name:
                return item
        for item in self._team_models(context):
            if model_key and item.get("model_key") == model_key:
                return item
            if job_name and item.get("job_name") == job_name:
                return item
        raise ServiceHandleException(
            msg="model download not found",
            msg_show="模型下载任务不存在",
            status_code=404,
            error_code="model_download_not_found",
        )

    def get_model_download(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        model_key = str(arguments.get("model_key") or "").strip()
        job_name = str(arguments.get("job_name") or "").strip()
        if bool(model_key) == bool(job_name):
            raise ServiceHandleException(
                msg="model_key or job_name required",
                msg_show="model_key和job_name必须二选一",
                status_code=400,
            )
        return self._find_download(context, model_key=model_key, job_name=job_name)

    def get_model_download_logs(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        job_name = self._required_string(arguments, "job_name", 253)
        self._find_download(context, job_name=job_name)
        tail_lines = self._tail_lines(arguments)
        path = self.API_PREFIX + "/team/downloads/{}/logs".format(quote(job_name, safe=""))
        return self._bounded_logs(self._call(context, "GET", path, query={"tail_lines": tail_lines}), tail_lines)

    def normalize_modelscope_model(self, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ServiceHandleException(
                msg="invalid ModelScope model",
                msg_show="ModelScope 模型地址无效",
                status_code=400,
            )
        raw = value.strip()
        if "://" in raw:
            parsed = urlparse(raw)
            try:
                has_explicit_port = parsed.port is not None
            except ValueError:
                has_explicit_port = True
            if (parsed.scheme != "https" or parsed.hostname not in ("modelscope.cn", "www.modelscope.cn") or has_explicit_port
                    or parsed.username or parsed.password or parsed.query or parsed.fragment):
                raise ServiceHandleException(
                    msg="unsupported model source",
                    msg_show="仅支持 ModelScope 官方 HTTPS 模型地址",
                    status_code=400,
                )
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) != 3 or parts[0] != "models":
                raise ServiceHandleException(msg="invalid ModelScope URL", msg_show="ModelScope 模型地址无效", status_code=400)
            owner, repo_name = parts[1], parts[2]
        else:
            parts = raw.split("/")
            if len(parts) != 2:
                raise ServiceHandleException(
                    msg="invalid ModelScope ID",
                    msg_show="ModelScope 模型 ID 必须为 owner/repo",
                    status_code=400,
                )
            owner, repo_name = parts
        if not self.MODELSCOPE_PART_PATTERN.match(owner) or not self.MODELSCOPE_PART_PATTERN.match(repo_name):
            raise ServiceHandleException(msg="invalid ModelScope ID", msg_show="ModelScope 模型 ID 无效", status_code=400)
        if repo_name.lower().endswith(".git"):
            raise ServiceHandleException(msg="unsupported Git source", msg_show="不支持 Git 模型来源", status_code=400)
        return "{}/{}".format(owner, repo_name)

    def _catalog_model(self, user: Any, arguments: dict, catalog_model_id: str) -> dict:
        result = self.search_model_catalog(
            user,
            {
                "team_name": arguments.get("team_name"),
                "region_name": arguments.get("region_name"),
                "keyword": catalog_model_id,
                "page": 1,
                "page_size": 50,
            },
        )
        for item in result["items"]:
            if item.get("model_id") == catalog_model_id or item.get("model_key") == catalog_model_id:
                return item
        raise ServiceHandleException(
            msg="catalog model not found",
            msg_show="内置模型目录中不存在该模型",
            status_code=404,
            error_code="catalog_model_not_found",
        )

    def create_model_download(self, user: Any, arguments: dict) -> dict:
        catalog_model_id = str(arguments.get("catalog_model_id") or "").strip()
        modelscope_model = str(arguments.get("modelscope_model") or "").strip()
        if bool(catalog_model_id) == bool(modelscope_model):
            raise ServiceHandleException(
                msg="invalid model source",
                msg_show="catalog_model_id和modelscope_model必须二选一",
                status_code=400,
            )
        context = self._context(user, arguments)
        catalog = None
        if catalog_model_id:
            catalog = self._catalog_model(user, arguments, catalog_model_id)
            source_uri = self.normalize_modelscope_model(catalog.get("source_uri") or catalog.get("model_id"))
        else:
            source_uri = self.normalize_modelscope_model(modelscope_model)
        display_name = str(arguments.get("display_name")
                           or "").strip() or (catalog.get("display_name") if catalog else source_uri.split("/", 1)[1])
        body = {
            "display_name": display_name,
            "source_type": "modelscope",
            "source_uri": source_uri,
        }
        requested_revision = str(arguments.get("requested_revision") or "").strip()
        if requested_revision:
            body["requested_revision"] = requested_revision
        if catalog:
            if catalog.get("model_id"):
                body["model_id"] = catalog["model_id"]
            engine_type = catalog.get("engine_type") or catalog.get("default_engine") or catalog.get("launch_model_engine")
            if engine_type:
                body["engine_type"] = engine_type
            parameters = catalog.get("parameters") or catalog.get("parameter_label")
            if parameters:
                body["parameters"] = parameters
        data = self._sanitize_output(self._call(context, "POST", self.API_PREFIX + "/team/models/downloads", body=body))
        poll_arguments = {
            "team_name": context.team.tenant_name,
            "region_name": context.region_name,
        }
        if isinstance(data, dict) and data.get("job_name"):
            poll_arguments["job_name"] = data["job_name"]
        elif isinstance(data, dict) and data.get("model_key"):
            poll_arguments["model_key"] = data["model_key"]
        return dict(
            data or {}, **{
                "accepted": True,
                "poll_tool": "rainbond_get_ai_engine_model_download",
                "poll_arguments": poll_arguments,
                "poll_after_seconds": 5,
            })

    def delete_team_model(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        model_key = self._required_string(arguments, "model_key")
        self._find_team_model(context, model_key)
        self._call(context, "DELETE", self.API_PREFIX + "/team/models/{}".format(quote(model_key, safe="")))
        return {"deleted": True, "model_key": model_key}

    def _instances(self, context: AIEngineContext) -> List[dict]:
        data = self._call(context, "GET", self.API_PREFIX + "/instances")
        if not isinstance(data, list):
            return []
        return [self._sanitize_output(item) for item in data if isinstance(item, dict)]

    def list_instances(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        page, page_size = self._pagination(arguments)
        items = self._instances(context)
        status = arguments.get("status")
        model_id = arguments.get("model_id")
        if status:
            items = [item for item in items if str(item.get("status") or "").lower() == str(status).lower()]
        if model_id:
            items = [item for item in items if item.get("model_id") == model_id]
        items.sort(key=lambda item: str(item.get("instance_id") or ""))
        return self._paginate(items, page, page_size)

    def _find_instance(self, context: AIEngineContext, instance_id: str) -> dict:
        for item in self._instances(context):
            if item.get("instance_id") == instance_id:
                return item
        raise ServiceHandleException(
            msg="instance not found",
            msg_show="实例不存在或不属于当前团队",
            status_code=404,
            error_code="ai_engine_instance_not_found",
        )

    def get_instance(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        instance_id = self._required_string(arguments, "instance_id", 128)
        self._find_instance(context, instance_id)
        path = self.API_PREFIX + "/instances/{}/details".format(quote(instance_id, safe=""))
        return self._sanitize_output(self._call(context, "GET", path))

    def get_instance_deployment(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        instance_id = self._required_string(arguments, "instance_id", 128)
        self._find_instance(context, instance_id)
        path = self.API_PREFIX + "/instances/{}/deployment".format(quote(instance_id, safe=""))
        data = self._call(context, "GET", path)
        data = data if isinstance(data, dict) else {}
        stage_fields = (
            "name",
            "status",
            "source",
            "started_at",
            "finished_at",
            "error_code",
            "message",
            "safe_details",
            "retryable",
        )

        def stage(value: Any) -> dict:
            if not isinstance(value, dict):
                return {}
            return {key: self._sanitize_output(value.get(key), key) for key in stage_fields if key in value}

        result = {
            key: data.get(key)
            for key in (
                "instance_id",
                "status",
                "available",
                "unavailable_reason",
                "current_stage",
                "terminal",
                "poll_after_seconds",
            ) if key in data
        }
        result["stages"] = [stage(item) for item in (data.get("stages") or []) if isinstance(item, dict)]
        result["failure"] = stage(data.get("failure")) if isinstance(data.get("failure"), dict) else None
        return self._sanitize_output(result)

    def list_instance_events(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        instance_id = self._required_string(arguments, "instance_id", 128)
        self._find_instance(context, instance_id)
        limit = self._bounded_integer(arguments, "limit", 50, 1, 100)
        since_seconds = self._bounded_integer(arguments, "since_seconds", 1800, 1, 86400)
        path = self.API_PREFIX + "/instances/{}/events".format(quote(instance_id, safe=""))
        data = self._call(context, "GET", path, query={"limit": limit, "since_seconds": since_seconds})
        data = data if isinstance(data, dict) else {}
        allowed_fields = ("resource_type", "reason", "safe_message", "severity", "count", "first_seen", "last_seen", "source")
        items = []
        total_bytes = 0
        truncated = bool(data.get("truncated"))
        for raw in data.get("items") or []:
            if not isinstance(raw, dict):
                continue
            item = {key: self._sanitize_output(raw.get(key), key) for key in allowed_fields if key in raw}
            item["safe_message"] = self._redact_event_text(item.get("safe_message"))
            item_bytes = len(str(item).encode("utf-8"))
            if total_bytes + item_bytes > self.MAX_EVENT_BYTES:
                truncated = True
                break
            total_bytes += item_bytes
            items.append(item)
        return {
            "instance_id": instance_id,
            "items": items,
            "limit": limit,
            "truncated": truncated,
        }

    def get_instance_logs(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        instance_id = self._required_string(arguments, "instance_id", 128)
        self._find_instance(context, instance_id)
        tail_lines = self._tail_lines(arguments)
        previous = arguments.get("previous", False)
        if not isinstance(previous, bool):
            raise ServiceHandleException(msg="invalid previous", msg_show="参数previous无效", status_code=400)
        query = {"tail_lines": tail_lines, "previous": "true" if previous else "false"}
        if "since_seconds" in arguments:
            query["since_seconds"] = self._bounded_integer(arguments, "since_seconds", 600, 1, 86400)
        path = self.API_PREFIX + "/instances/{}/logs".format(quote(instance_id, safe=""))
        return self._bounded_logs(self._call(context, "GET", path, query=query), tail_lines)

    @staticmethod
    def _closed_object(value: Any, allowed: frozenset, field: str) -> dict:
        if value is None:
            return {}
        if not isinstance(value, dict) or set(value) - allowed:
            raise ServiceHandleException(
                msg="invalid {}".format(field),
                msg_show="参数{}包含不允许的字段".format(field),
                status_code=400,
                error_code="invalid_input",
                details={"field": field},
            )
        return dict(value)

    def create_instance(self, user: Any, arguments: dict) -> dict:
        extra_argv = arguments.get("extra_argv") or []
        if (not isinstance(extra_argv, list)
                or any(not isinstance(item, str) or not item or len(item) > 4096 for item in extra_argv)):
            raise ServiceHandleException(msg="invalid extra_argv", msg_show="参数extra_argv无效", status_code=400)
        if sum(len(item.encode("utf-8")) for item in extra_argv) > self.MAX_EXTRA_ARGV_BYTES:
            raise ServiceHandleException(
                msg="extra_argv is too large",
                msg_show="extra_argv 总大小不能超过 16 KiB",
                status_code=400,
                error_code="ai_engine_extra_argv_too_large",
                details={
                    "limit": self.MAX_EXTRA_ARGV_BYTES,
                    "field": "extra_argv"
                },
            )
        context = self._context(user, arguments)
        model_key = self._required_string(arguments, "model_key")
        model = self._find_team_model(context, model_key)
        if str(model.get("status") or "").lower() != "ready":
            raise ServiceHandleException(
                msg="team model is not ready",
                msg_show="团队模型尚未就绪",
                status_code=409,
                error_code="team_model_not_ready",
            )
        if str(model.get("source_type") or "").lower() == "modelscope":
            if (model.get("registry_check_status") != "verified" or model.get("metadata_consistency_status") != "verified"):
                raise ServiceHandleException(
                    msg="team model is not verified",
                    msg_show="ModelScope 模型校验尚未完成",
                    status_code=409,
                    error_code="team_model_not_verified",
                )

        compute_mode = self._required_string(arguments, "compute_mode", 8)
        if compute_mode not in ("gpu", "cpu"):
            raise ServiceHandleException(msg="invalid compute_mode", msg_show="compute_mode仅支持gpu或cpu", status_code=400)
        resources = self._closed_object(arguments.get("resources"), self.RESOURCE_FIELDS, "resources")
        for name in ("gpu_count", "gpu_type", "node_name"):
            if name in arguments:
                if name in resources and resources[name] != arguments[name]:
                    raise ServiceHandleException(
                        msg="conflicting resource field",
                        msg_show="资源字段{}重复且不一致".format(name),
                        status_code=400,
                    )
                resources[name] = arguments[name]
        gpu_count = resources.get("gpu_count", 1 if compute_mode == "gpu" else 0)
        if not isinstance(gpu_count, int) or isinstance(gpu_count, bool) or not 0 <= gpu_count <= 64:
            raise ServiceHandleException(msg="invalid gpu_count", msg_show="参数gpu_count无效", status_code=400)
        if compute_mode == "cpu" and gpu_count != 0:
            raise ServiceHandleException(msg="cpu mode requires zero GPUs", msg_show="CPU 模式的 gpu_count 必须为 0", status_code=400)
        if compute_mode == "gpu" and gpu_count < 1:
            raise ServiceHandleException(msg="gpu mode requires GPUs", msg_show="GPU 模式的 gpu_count 至少为 1", status_code=400)
        resources["gpu_count"] = gpu_count
        dynamic_params = self._closed_object(arguments.get("dynamic_params"), self.DYNAMIC_PARAM_FIELDS, "dynamic_params")
        if extra_argv:
            dynamic_params["extra_argv"] = extra_argv
        body = {
            "instance_name": self._required_string(arguments, "instance_name", 128),
            "model_key": model_key,
            "model_id": model.get("model_id"),
            "resources": resources,
            "dynamic_params": dynamic_params,
        }
        if model.get("engine_type"):
            body["engine_type"] = model["engine_type"]
            if model["engine_type"] == "vLLM":
                body["runtime_version"] = "0.26.0"
        data = self._sanitize_output(self._call(context, "POST", self.API_PREFIX + "/instances", body=body))
        instance_id = data.get("instance_id") if isinstance(data, dict) else None
        return dict(
            data or {}, **{
                "accepted": True,
                "resource_id": instance_id,
                "poll_tool": "rainbond_get_ai_engine_instance",
                "poll_arguments": {
                    "team_name": context.team.tenant_name,
                    "region_name": context.region_name,
                    "instance_id": instance_id,
                },
                "poll_after_seconds": 5,
            })

    def update_instance_state(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        instance_id = self._required_string(arguments, "instance_id", 128)
        target_state = self._required_string(arguments, "target_state", 16)
        if target_state not in ("Running", "Stopped"):
            raise ServiceHandleException(msg="invalid target_state", msg_show="目标状态仅支持Running或Stopped", status_code=400)
        self._find_instance(context, instance_id)
        path = self.API_PREFIX + "/instances/{}/state".format(quote(instance_id, safe=""))
        self._call(context, "PUT", path, body={"target_state": target_state})
        return {
            "accepted": True,
            "instance_id": instance_id,
            "target_state": target_state,
            "poll_tool": "rainbond_get_ai_engine_instance",
            "poll_arguments": {
                "team_name": context.team.tenant_name,
                "region_name": context.region_name,
                "instance_id": instance_id,
            },
            "poll_after_seconds": 5,
        }

    def delete_instance(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        instance_id = self._required_string(arguments, "instance_id", 128)
        self._find_instance(context, instance_id)
        path = self.API_PREFIX + "/instances/{}".format(quote(instance_id, safe=""))
        self._call(context, "DELETE", path)
        return {
            "deleted": True,
            "instance_id": instance_id,
            "cleanup_verified": False,
        }

    def _gpu_devices(self, context: AIEngineContext) -> List[dict]:
        data = self._call(context, "GET", self.API_PREFIX + "/gpu/devices")
        if isinstance(data, dict):
            data = data.get("devices") or []
        if not isinstance(data, list):
            return []
        allowed = (
            "device_id",
            "node_name",
            "vendor",
            "product_name",
            "compute_capability",
            "fp8_execution_mode",
            "fp8_compatibility_reason",
            "gpu_index",
            "memory_total_bytes",
            "memory_used_bytes",
            "utilization_rate",
            "memory_utilization_rate",
            "temperature_celsius",
            "health_status",
            "health_source",
            "missing_metrics",
            "risk_tags",
        )
        return [{
            key: self._sanitize_output(item.get(key), key)
            for key in allowed if key in item
        } for item in data if isinstance(item, dict)]

    def list_gpu_devices(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        page, page_size = self._pagination(arguments)
        items = self._gpu_devices(context)
        node_name = str(arguments.get("node_name") or "").strip()
        if node_name:
            items = [item for item in items if item.get("node_name") == node_name]
        items.sort(key=lambda item: (str(item.get("node_name") or ""), str(item.get("device_id") or "")))
        return self._paginate(items, page, page_size)

    def get_gpu_device_timeseries(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        device_id = self._required_string(arguments, "device_id")
        if device_id not in {str(item.get("device_id") or "") for item in self._gpu_devices(context)}:
            raise ServiceHandleException(
                msg="GPU device not found",
                msg_show="GPU 设备不存在或当前团队不可访问",
                status_code=404,
                error_code="ai_engine_gpu_device_not_found",
            )
        window = str(arguments.get("window") or "1h")
        if window not in ("1h", "24h"):
            raise ServiceHandleException(msg="invalid window", msg_show="参数window无效", status_code=400)
        max_points = self._bounded_integer(arguments, "max_points", 360, 1, self.MAX_GPU_POINTS)
        path = self.API_PREFIX + "/gpu/devices/{}/timeseries".format(quote(device_id, safe=""))
        data = self._call(context, "GET", path)
        data = data if isinstance(data, dict) else {}
        source = data.get("one_hour") if window == "1h" else data.get("twenty_four_hours")
        source = source if isinstance(source, dict) else {}
        series = {}
        truncated = False
        for name in ("utilization_rate", "memory_utilization_rate", "temperature_celsius"):
            points = source.get(name) if isinstance(source.get(name), list) else []
            safe_points = []
            for point in points:
                if not isinstance(point, dict):
                    continue
                safe_points.append({key: point.get(key) for key in ("timestamp", "value") if key in point})
            if len(safe_points) > max_points:
                safe_points = safe_points[-max_points:]
                truncated = True
            series[name] = safe_points
        return {
            "device_id": device_id,
            "window": window,
            "series": series,
            "max_points": max_points,
            "truncated": truncated,
        }

    def _list_scoped_gpu_instance_rows(self, context: AIEngineContext, path: str, arguments: dict,
                                       allowed_fields: Tuple[str, ...]) -> dict:
        page, page_size = self._pagination(arguments)
        owned_ids = {str(item.get("instance_id") or "") for item in self._instances(context)}
        data = self._call(context, "GET", self.API_PREFIX + path)
        if isinstance(data, dict):
            data = data.get("items") or data.get("bindings") or data.get("usage") or []
        if not isinstance(data, list):
            data = []
        items = []
        for raw in data:
            if not isinstance(raw, dict) or str(raw.get("instance_id") or "") not in owned_ids:
                continue
            items.append({key: self._sanitize_output(raw.get(key), key) for key in allowed_fields if key in raw})
        items.sort(key=lambda item: str(item.get("instance_id") or ""))
        return self._paginate(items, page, page_size)

    def list_gpu_instance_bindings(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        fields = (
            "instance_id",
            "instance_name",
            "model_id",
            "status",
            "node_name",
            "gpu_count_requested",
            "gpu_ids",
            "gpu_labels",
            "source",
            "binding_source",
            "estimated",
            "binding_scope",
            "provider",
            "allocation_mode",
            "request_unit",
            "memory_mib_per_gpu",
            "physical_memory_mib_per_gpu",
            "available_memory_mib_per_gpu",
            "available_vgpu_capacity",
            "share_available",
        )
        return self._list_scoped_gpu_instance_rows(context, "/gpu/instances/bindings", arguments, fields)

    def list_gpu_instance_usage(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        fields = (
            "instance_id",
            "instance_name",
            "model_id",
            "status",
            "node_name",
            "gpu_count_requested",
            "gpu_ids",
            "used_memory_bytes",
            "memory_by_gpu",
            "available",
            "unavailable_reason",
            "source",
            "provider",
            "allocation_mode",
            "request_unit",
            "memory_mib_per_gpu",
            "physical_memory_mib_per_gpu",
        )
        return self._list_scoped_gpu_instance_rows(context, "/gpu/instances/usage", arguments, fields)

    def get_monitoring_overview(self, user: Any, arguments: dict) -> dict:
        context = self._context(user, arguments)
        return self._sanitize_output(self._call(context, "GET", self.API_PREFIX + "/model-monitoring/overview"))


ai_engine_service = AIEngineProxyService()
