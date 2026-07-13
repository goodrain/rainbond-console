# -*- coding: utf-8 -*-
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class MarketInstallPreflightService(object):
    STATUS_PASS = "pass"
    STATUS_WARNING = "warning"
    STATUS_BLOCK = "block"

    REASON_REGION_CAPABILITY_MISSING = "region_capability_missing"
    REASON_IMAGE_NOT_FOUND = "image_not_found"
    REASON_REGISTRY_AUTH_REQUIRED = "registry_auth_required"
    REASON_REGISTRY_NETWORK_ERROR = "registry_network_error"
    REASON_REGISTRY_PROBE_TIMEOUT = "registry_probe_timeout"

    DEFAULT_TIMEOUT_BUDGET_MS = 5000
    DEFAULT_REGISTRY_TIMEOUT_SECONDS = 2

    def run(self,
            tenant: Any,
            region: Any,
            app_template: dict,
            timeout_budget_ms: int = DEFAULT_TIMEOUT_BUDGET_MS,
            mode: Optional[str] = None) -> Dict[str, Any]:
        started = time.time()
        mode = mode or os.getenv("MARKET_INSTALL_PREFLIGHT_MODE", "block")
        requirements = self.parse_template_requirements(app_template)
        checks = [
            self._check_resource_capacity(tenant, region, requirements),
            self._check_architecture(region, requirements),
            self._check_image_manifests(requirements, started, timeout_budget_ms),
        ]
        status = self._result_status(checks)
        should_block = status == self.STATUS_BLOCK and mode == "block"
        if status == self.STATUS_BLOCK and mode != "block":
            status = self.STATUS_WARNING
        return {
            "status": status,
            "mode": mode,
            "should_block": should_block,
            "duration_ms": int((time.time() - started) * 1000),
            "summary": self._summary(status, checks, requirements),
            "requirements": requirements,
            "checks": checks,
        }

    def parse_template_requirements(self, app_template: dict) -> Dict[str, Any]:
        apps = app_template.get("apps") or []
        cpu = 0
        memory = 0
        images = []
        for app in apps:
            cpu += self._int_value(app.get("container_cpu") or app.get("cpu"))
            memory += self._component_memory(app)
            for image in (app.get("share_image"), app.get("image")):
                image = (image or "").strip()
                if image and image not in images:
                    images.append(image)
        template_arch = app_template.get("arch") or "amd64"
        return {
            "component_count": len(apps),
            "cpu": cpu,
            "memory": memory,
            "arch": template_arch,
            "images": images,
        }

    def _check_resource_capacity(self, tenant: Any, region: Any, requirements: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resources = self._get_region_resources(tenant, region)
        except Exception as exc:
            return self._check(
                "resource_capacity",
                self.STATUS_WARNING,
                "集群资源检测不可用，无法确认资源是否满足安装要求",
                self.REASON_REGION_CAPABILITY_MISSING,
                {"error": str(exc)})
        ready_nodes = self._int_value(resources.get("node_ready"))
        all_nodes = self._int_value(resources.get("all_node"))
        if ready_nodes <= 0:
            return self._check(
                "resource_capacity",
                self.STATUS_BLOCK,
                "当前集群没有 Ready 节点，无法安装应用",
                "no_ready_nodes",
                {"all_node": all_nodes, "node_ready": ready_nodes})

        total_cpu, used_cpu = self._cluster_cpu_millicores(resources.get("cap_cpu"), resources.get("req_cpu"))
        free_cpu = total_cpu - used_cpu
        free_memory = self._int_value(resources.get("cap_mem")) - self._int_value(resources.get("req_mem"))
        required_cpu = self._int_value(requirements.get("cpu"))
        required_memory = self._int_value(requirements.get("memory"))
        details = {
            "total_cpu": total_cpu,
            "used_cpu": used_cpu,
            "free_cpu": free_cpu,
            "required_cpu": required_cpu,
            "free_memory": free_memory,
            "required_memory": required_memory,
            "all_node": all_nodes,
            "node_ready": ready_nodes,
        }
        messages = []
        if required_cpu > 0 and free_cpu < required_cpu:
            messages.append("CPU不足：预计需要{}m，当前可用{}m".format(required_cpu, max(free_cpu, 0)))
        if required_memory > 0 and free_memory < required_memory:
            messages.append("内存不足：预计需要{}Mi，当前可用{}Mi".format(required_memory, max(free_memory, 0)))
        if messages:
            return self._check("resource_capacity", self.STATUS_BLOCK, "；".join(messages), "resource_not_enough", details)
        return self._check("resource_capacity", self.STATUS_PASS, "集群资源满足安装要求", "", details)

    def _check_architecture(self, region: Any, requirements: Dict[str, Any]) -> Dict[str, Any]:
        template_arch = requirements.get("arch") or "amd64"
        try:
            arches = self._get_cluster_arches(region)
        except Exception as exc:
            return self._check(
                "architecture",
                self.STATUS_WARNING,
                "集群架构检测不可用，无法确认架构是否匹配",
                self.REASON_REGION_CAPABILITY_MISSING,
                {"error": str(exc), "template_arch": template_arch})
        details = {
            "template_arch": template_arch,
            "cluster_arches": arches,
        }
        if template_arch not in arches and len(arches) < 2:
            return self._check("architecture", self.STATUS_BLOCK, "应用架构与集群节点架构不匹配", "arch_mismatch", details)
        return self._check("architecture", self.STATUS_PASS, "应用架构与集群匹配", "", details)

    def _check_image_manifests(self, requirements: Dict[str, Any], started: float,
                               timeout_budget_ms: int) -> Dict[str, Any]:
        images = requirements.get("images") or []
        if not images:
            return self._check("image_manifest", self.STATUS_WARNING, "模板中未解析到镜像，已跳过镜像版本检测", "image_not_declared")
        warnings = []
        for image in images:
            remaining = self._remaining_seconds(started, timeout_budget_ms)
            if remaining <= 0:
                return self._check(
                    "image_manifest",
                    self.STATUS_WARNING,
                    "镜像仓库检测超时，无法确认镜像版本",
                    self.REASON_REGISTRY_PROBE_TIMEOUT,
                    {"images": images})
            status, message, reason = self._probe_image_manifest(image, remaining)
            if status in (self.STATUS_WARNING, self.STATUS_BLOCK):
                warnings.append({"image": image, "message": message, "reason": reason})
        if warnings:
            return self._check("image_manifest", self.STATUS_WARNING, "部分镜像版本检测无法确认", warnings[0]["reason"],
                               {"warnings": warnings})
        return self._check("image_manifest", self.STATUS_PASS, "镜像版本存在", "", {"images": images})

    def _get_region_resources(self, tenant: Any, region: Any) -> Dict[str, Any]:
        _, body = region_api.get_region_resources(tenant.enterprise_id, region=region.region_name)
        return (body or {}).get("bean") or {}

    def _get_cluster_arches(self, region: Any) -> List[str]:
        _, body = region_api.get_cluster_nodes_arch(region.region_name)
        return list(set((body or {}).get("list") or []))

    def _probe_image_manifest(self, image: str, timeout_seconds: float) -> Tuple[str, str, str]:
        parsed = self._parse_image(image)
        if not parsed:
            return self.STATUS_WARNING, "镜像地址无法解析，无法确认镜像版本", "image_reference_invalid"
        registry, repository, tag = parsed
        url = "https://{}/v2/{}/manifests/{}".format(registry, quote(repository), quote(tag))
        try:
            response = requests.head(
                url,
                timeout=min(max(timeout_seconds, 0.1), self.DEFAULT_REGISTRY_TIMEOUT_SECONDS),
                headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
            )
        except requests.Timeout:
            return self.STATUS_WARNING, "镜像仓库检测超时，无法确认镜像版本", self.REASON_REGISTRY_PROBE_TIMEOUT
        except requests.RequestException:
            return self.STATUS_WARNING, "镜像仓库访问异常，无法确认镜像版本", self.REASON_REGISTRY_NETWORK_ERROR
        if response.status_code == 404:
            return self.STATUS_WARNING, "镜像版本无法确认，可能不存在：{}".format(image), self.REASON_IMAGE_NOT_FOUND
        if response.status_code in (401, 403):
            return self.STATUS_WARNING, "镜像仓库需要认证，无法确认镜像版本", self.REASON_REGISTRY_AUTH_REQUIRED
        if 200 <= response.status_code < 300:
            return self.STATUS_PASS, "镜像版本存在", ""
        return self.STATUS_WARNING, "镜像仓库返回状态{}，无法确认镜像版本".format(response.status_code), "registry_probe_failed"

    def _parse_image(self, image: str) -> Optional[Tuple[str, str, str]]:
        image = (image or "").strip()
        if not image:
            return None
        parts = image.split("/")
        first = parts[0]
        if len(parts) > 1 and ("." in first or ":" in first or first == "localhost"):
            registry = first
            rest = "/".join(parts[1:])
        else:
            registry = "registry-1.docker.io"
            rest = image
        if ":" in rest.rsplit("/", 1)[-1]:
            repository, tag = rest.rsplit(":", 1)
        else:
            repository, tag = rest, "latest"
        if not repository:
            return None
        if registry == "registry-1.docker.io" and "/" not in repository:
            repository = "library/{}".format(repository)
        return registry, repository, tag

    def _remaining_seconds(self, started: float, timeout_budget_ms: int) -> float:
        elapsed_ms = (time.time() - started) * 1000
        return float(timeout_budget_ms - elapsed_ms) / 1000

    def _component_memory(self, app: dict) -> int:
        memory = self._int_value(app.get("memory"))
        extend_method_map = app.get("extend_method_map") or {}
        if not memory:
            memory = self._int_value(extend_method_map.get("init_memory") or extend_method_map.get("min_memory"))
        return memory

    def _cluster_cpu_millicores(self, cap_cpu: Any, req_cpu: Any) -> Tuple[int, int]:
        total_cpu = self._float_value(cap_cpu)
        used_cpu = self._float_value(req_cpu)
        if 0 < total_cpu <= 512:
            return int(round(total_cpu * 1000)), int(round(used_cpu * 1000))
        return int(round(total_cpu)), int(round(used_cpu))

    @staticmethod
    def _int_value(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _float_value(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0

    def _result_status(self, checks: List[Dict[str, Any]]) -> str:
        if any(item["status"] == self.STATUS_BLOCK for item in checks):
            return self.STATUS_BLOCK
        if any(item["status"] == self.STATUS_WARNING for item in checks):
            return self.STATUS_WARNING
        return self.STATUS_PASS

    def _summary(self, status: str, checks: List[Dict[str, Any]], requirements: Dict[str, Any]) -> str:
        if status == self.STATUS_BLOCK:
            for item in checks:
                if item["status"] == self.STATUS_BLOCK:
                    return item["message"]
        if status == self.STATUS_WARNING:
            return "部分安装前检测无法确认"
        return "安装环境检测通过，应用预计需要{}m CPU、{}Mi 内存".format(
            requirements.get("cpu", 0), requirements.get("memory", 0))

    @staticmethod
    def _check(name: str, status: str, message: str, reason: str = "",
               details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "name": name,
            "status": status,
            "message": message,
            "reason": reason,
            "details": details or {},
        }


market_install_preflight_service = MarketInstallPreflightService()
