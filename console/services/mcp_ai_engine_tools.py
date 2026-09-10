# -*- coding: utf-8 -*-
from typing import Any, Dict, List

from console.exception.main import ServiceHandleException


class MCPAIEngineTools(object):
    TOOL_METHODS = {
        "rainbond_get_ai_engine_capabilities": "get_capabilities",
        "rainbond_get_ai_engine_resource_capacity": "get_resource_capacity",
        "rainbond_search_ai_engine_model_catalog": "search_model_catalog",
        "rainbond_get_ai_engine_model_catalog_detail": "get_model_catalog_detail",
        "rainbond_list_ai_engine_model_recommendations": "list_model_recommendations",
        "rainbond_list_ai_engine_team_models": "list_team_models",
        "rainbond_get_ai_engine_team_model": "get_team_model",
        "rainbond_get_ai_engine_model_download": "get_model_download",
        "rainbond_get_ai_engine_model_download_logs": "get_model_download_logs",
        "rainbond_create_ai_engine_model_download": "create_model_download",
        "rainbond_delete_ai_engine_team_model": "delete_team_model",
        "rainbond_list_ai_engine_instances": "list_instances",
        "rainbond_get_ai_engine_instance": "get_instance",
        "rainbond_get_ai_engine_instance_deployment": "get_instance_deployment",
        "rainbond_list_ai_engine_instance_events": "list_instance_events",
        "rainbond_get_ai_engine_instance_logs": "get_instance_logs",
        "rainbond_create_ai_engine_instance": "create_instance",
        "rainbond_update_ai_engine_instance_state": "update_instance_state",
        "rainbond_delete_ai_engine_instance": "delete_instance",
        "rainbond_get_ai_engine_monitoring_overview": "get_monitoring_overview",
        "rainbond_list_ai_engine_gpu_devices": "list_gpu_devices",
        "rainbond_get_ai_engine_gpu_device_timeseries": "get_gpu_device_timeseries",
        "rainbond_list_ai_engine_gpu_instance_bindings": "list_gpu_instance_bindings",
        "rainbond_list_ai_engine_gpu_instance_usage": "list_gpu_instance_usage",
    }
    READ_DESCRIPTIONS = {
        "rainbond_get_ai_engine_capabilities":
        ("Get AI Engine deployment, storage, network, runtime and ModelScope capabilities."),
        "rainbond_get_ai_engine_resource_capacity":
        "Get a compact AI workload resource-capacity summary for the team.",
        "rainbond_search_ai_engine_model_catalog":
        "Search the built-in ModelScope model catalog with stable pagination.",
        "rainbond_get_ai_engine_model_catalog_detail":
        "Get one built-in model catalog item without its README body.",
        "rainbond_list_ai_engine_model_recommendations":
        "List resource-aware model recommendations produced by AI Engine.",
        "rainbond_list_ai_engine_team_models":
        "List models downloaded and verified for the team.",
        "rainbond_get_ai_engine_team_model":
        "Get one team model by model_key.",
        "rainbond_get_ai_engine_model_download":
        "Get one team model download by model_key or job_name.",
        "rainbond_get_ai_engine_model_download_logs":
        "Get bounded and redacted logs for one team model download.",
        "rainbond_list_ai_engine_instances":
        "List team-owned AI Engine instances with stable pagination.",
        "rainbond_get_ai_engine_instance":
        "Get team-owned instance configuration and runtime details.",
        "rainbond_get_ai_engine_instance_deployment":
        "Get the persisted deployment-stage state machine for one team-owned instance.",
        "rainbond_list_ai_engine_instance_events":
        "List bounded, instance-scoped and redacted Kubernetes events.",
        "rainbond_get_ai_engine_instance_logs":
        "Get bounded and redacted logs for one team-owned instance.",
        "rainbond_get_ai_engine_monitoring_overview":
        ("Get the AI Engine 15-minute monitoring overview without converting unavailable metrics to zero."),
        "rainbond_list_ai_engine_gpu_devices":
        "List bounded GPU device diagnostics without raw Kubernetes objects.",
        "rainbond_get_ai_engine_gpu_device_timeseries":
        "Get a bounded GPU device metric window.",
        "rainbond_list_ai_engine_gpu_instance_bindings":
        "List provider-aware GPU allocation bindings for team-owned instances.",
        "rainbond_list_ai_engine_gpu_instance_usage":
        "List real or explicitly unavailable GPU memory usage for team-owned instances.",
    }

    @staticmethod
    def _string(max_length: int = 512) -> Dict[str, Any]:
        return {
            "type": "string",
            "minLength": 1,
            "maxLength": max_length,
            "pattern": r"^[^\x00-\x1f\x7f]+$",
        }

    def _context_properties(self) -> Dict[str, Any]:
        return {
            "team_name": self._string(64),
            "region_name": self._string(64),
        }

    def _schema(self,
                properties: Dict[str, Any] = None,
                required: List[str] = None,
                one_of: List[dict] = None) -> Dict[str, Any]:
        merged = self._context_properties()
        merged.update(properties or {})
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": merged,
            "required": ["team_name", "region_name"] + list(required or []),
        }
        if one_of:
            schema["oneOf"] = one_of
        return schema

    @staticmethod
    def _pagination_properties() -> Dict[str, Any]:
        return {
            "page": {
                "type": "integer",
                "minimum": 1,
                "default": 1
            },
            "page_size": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 20
            },
        }

    @staticmethod
    def _log_properties() -> Dict[str, Any]:
        return {
            "tail_lines": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "default": 200
            },
        }

    def _resources_schema(self) -> Dict[str, Any]:
        non_negative = {"type": "number", "minimum": 0, "maximum": 1000000}
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gpu_count": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 64
                },
                "gpu_type": self._string(128),
                "node_name": self._string(253),
                "cpu_request_cores": dict(non_negative),
                "cpu_limit_cores": dict(non_negative),
                "memory_request_gib": dict(non_negative),
                "memory_limit_gib": dict(non_negative),
                "shared_memory_gib": dict(non_negative),
            },
        }

    def _dynamic_params_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gpu_memory_utilization": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "maximum": 1
                },
                "cpu_kvcache_space_gb": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1048576
                },
                "max_model_len": {
                    "type": "string",
                    "pattern": r"^(auto|model_config|[1-9][0-9]*)$",
                    "maxLength": 32
                },
                "runner": {
                    "type": "string",
                    "enum": ["auto", "generate", "pooling", "draft"]
                },
                "convert": {
                    "type": "string",
                    "enum": ["auto", "none", "embed", "classify", "reward"]
                },
                "model_impl": {
                    "type": "string",
                    "enum": ["auto", "vllm", "transformers"]
                },
                "dtype": {
                    "type": "string",
                    "enum": ["auto", "half", "float16", "bfloat16", "float", "float32"]
                },
                "kv_cache_dtype": {
                    "type": "string",
                    "enum": ["auto", "bfloat16", "float16", "fp8"]
                },
                "max_num_seqs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1048576
                },
                "max_num_batched_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2147483647
                },
                "prefix_caching": {
                    "type": "string",
                    "enum": ["inherit", "enabled", "disabled"]
                },
                "kv_cache_memory_bytes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 9223372036854775807
                },
                "tensor_parallel_size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 64
                },
                "pipeline_parallel_size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 64
                },
                "trust_remote_code": {
                    "type": "boolean"
                },
                "runtime_quantization": {
                    "type": "string",
                    "enum": ["none", "bitsandbytes"]
                },
            },
        }

    def list_tools(self, user: Any = None) -> List[dict]:
        del user
        pagination = self._pagination_properties()
        definitions = {
            "rainbond_get_ai_engine_capabilities":
            self._schema(),
            "rainbond_get_ai_engine_resource_capacity":
            self._schema(),
            "rainbond_search_ai_engine_model_catalog":
            self._schema(
                dict(
                    pagination, **{
                        "keyword": self._string(256),
                        "owner": self._string(256),
                        "section": {
                            "type": "string",
                            "enum": ["recommended", "popular", "text", "multimodal", "embedding"]
                        },
                    })),
            "rainbond_get_ai_engine_model_catalog_detail":
            self._schema({
                "owner": self._string(256),
                "repo_name": self._string(256),
            }, ["owner", "repo_name"]),
            "rainbond_list_ai_engine_model_recommendations":
            self._schema({
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 10
                },
            }),
            "rainbond_list_ai_engine_team_models":
            self._schema(
                dict(pagination, **{
                    "status": {
                        "type": "string",
                        "enum": ["pending", "downloading", "ready", "failed", "deleting"]
                    },
                })),
            "rainbond_get_ai_engine_team_model":
            self._schema({"model_key": self._string()}, ["model_key"]),
            "rainbond_get_ai_engine_model_download":
            self._schema({
                "model_key": self._string(),
                "job_name": self._string(253),
            },
                         one_of=[{
                             "required": ["model_key"]
                         }, {
                             "required": ["job_name"]
                         }]),
            "rainbond_get_ai_engine_model_download_logs":
            self._schema(dict(self._log_properties(), **{
                "job_name": self._string(253),
            }), ["job_name"]),
            "rainbond_create_ai_engine_model_download":
            self._schema(
                {
                    "catalog_model_id": self._string(),
                    "modelscope_model": self._string(1024),
                    "display_name": self._string(256),
                    "requested_revision": self._string(256),
                },
                one_of=[{
                    "required": ["catalog_model_id"]
                }, {
                    "required": ["modelscope_model"]
                }]),
            "rainbond_delete_ai_engine_team_model":
            self._schema({"model_key": self._string()}, ["model_key"]),
            "rainbond_list_ai_engine_instances":
            self._schema(
                dict(
                    pagination, **{
                        "status": {
                            "type": "string",
                            "enum": ["Creating", "Running", "Stopped", "Failed"]
                        },
                        "model_id": self._string(),
                    })),
            "rainbond_get_ai_engine_instance":
            self._schema({"instance_id": self._string(128)}, ["instance_id"]),
            "rainbond_get_ai_engine_instance_deployment":
            self._schema({"instance_id": self._string(128)}, ["instance_id"]),
            "rainbond_list_ai_engine_instance_events":
            self._schema(
                {
                    "instance_id": self._string(128),
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 50
                    },
                    "since_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 86400,
                        "default": 1800
                    },
                }, ["instance_id"]),
            "rainbond_get_ai_engine_instance_logs":
            self._schema(
                dict(
                    self._log_properties(), **{
                        "instance_id": self._string(128),
                        "previous": {
                            "type": "boolean",
                            "default": False
                        },
                        "since_seconds": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 86400
                        },
                    }), ["instance_id"]),
            "rainbond_create_ai_engine_instance":
            self._schema(
                {
                    "instance_name": self._string(128),
                    "model_key": self._string(),
                    "compute_mode": {
                        "type": "string",
                        "enum": ["gpu", "cpu"]
                    },
                    "gpu_count": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 64
                    },
                    "gpu_type": self._string(128),
                    "node_name": self._string(253),
                    "resources": self._resources_schema(),
                    "dynamic_params": self._dynamic_params_schema(),
                    "extra_argv": {
                        "type": "array",
                        "maxItems": 256,
                        "items": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 4096
                        },
                    },
                }, ["instance_name", "model_key", "compute_mode"]),
            "rainbond_update_ai_engine_instance_state":
            self._schema(
                {
                    "instance_id": self._string(128),
                    "target_state": {
                        "type": "string",
                        "enum": ["Running", "Stopped"]
                    },
                }, ["instance_id", "target_state"]),
            "rainbond_delete_ai_engine_instance":
            self._schema({"instance_id": self._string(128)}, ["instance_id"]),
            "rainbond_get_ai_engine_monitoring_overview":
            self._schema(),
            "rainbond_list_ai_engine_gpu_devices":
            self._schema(dict(pagination, **{"node_name": self._string(253)})),
            "rainbond_get_ai_engine_gpu_device_timeseries":
            self._schema(
                {
                    "device_id": self._string(512),
                    "window": {
                        "type": "string",
                        "enum": ["1h", "24h"],
                        "default": "1h"
                    },
                    "max_points": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 720,
                        "default": 360
                    },
                }, ["device_id"]),
            "rainbond_list_ai_engine_gpu_instance_bindings":
            self._schema(pagination),
            "rainbond_list_ai_engine_gpu_instance_usage":
            self._schema(pagination),
        }
        mutation_descriptions = {
            "rainbond_create_ai_engine_model_download": "Create a server-validated ModelScope model download.",
            "rainbond_delete_ai_engine_team_model": "Delete a team model after destructive confirmation.",
            "rainbond_create_ai_engine_instance": "Create an AI Engine instance from a ready verified team model.",
            "rainbond_update_ai_engine_instance_state": "Start or stop a team-owned AI Engine instance.",
            "rainbond_delete_ai_engine_instance": "Delete a team-owned AI Engine instance after destructive confirmation.",
        }
        result = []
        for name in self.TOOL_METHODS:
            item = {
                "name": name,
                "description": self.READ_DESCRIPTIONS.get(name) or mutation_descriptions[name],
                "inputSchema": definitions[name],
            }
            if name in ("rainbond_delete_ai_engine_team_model", "rainbond_delete_ai_engine_instance"):
                item["annotations"] = {"destructiveHint": True}
            result.append(item)
        return result

    def handles(self, tool_name: str) -> bool:
        return tool_name in self.TOOL_METHODS

    def call_tool(self, user: Any, tool_name: str, arguments: dict) -> Any:
        method_name = self.TOOL_METHODS.get(tool_name)
        if not method_name:
            raise ServiceHandleException(msg="tool not found", msg_show="工具不存在", status_code=404)
        from console.services.ai_engine_service import ai_engine_service
        return getattr(ai_engine_service, method_name)(user, arguments)


mcp_ai_engine_tools = MCPAIEngineTools()
