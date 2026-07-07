# -*- coding: utf-8 -*-
import ast
import os
import shlex
import time
from typing import Any, Dict, List, Optional

from console.services.app import package_upload_service
from console.services.market_app_preflight_service import MarketInstallPreflightService


class DeployPreflightService(object):
    STATUS_PASS = "pass"
    STATUS_WARNING = "warning"
    STATUS_BLOCK = "block"

    DEPLOY_TYPE_IMAGE = "image"
    DEPLOY_TYPE_DOCKER_RUN = "docker_run"
    DEPLOY_TYPE_SOURCE_CODE = "source_code"
    DEPLOY_TYPE_PACKAGE = "package"
    DEPLOY_TYPE_UPLOADED_TEMPLATE = "uploaded_template"
    DEPLOY_TYPE_TEMPLATE = "template"

    SUPPORTED_PACKAGE_EXTENSIONS = (".jar", ".war", ".zip")

    def __init__(self) -> None:
        self.template_preflight = MarketInstallPreflightService()
        self.package_upload_service = package_upload_service

    def run(self, tenant: Any, region: Any, deploy_type: str, payload: Optional[dict],
            user: Optional[Any] = None) -> Dict[str, Any]:
        started = time.time()
        payload = payload or {}
        normalized_type = self._normalize_deploy_type(deploy_type)
        if normalized_type in (self.DEPLOY_TYPE_IMAGE, self.DEPLOY_TYPE_DOCKER_RUN):
            result = self._run_image_preflight(tenant, region, normalized_type, payload)
        elif normalized_type == self.DEPLOY_TYPE_SOURCE_CODE:
            result = self._build_result(normalized_type, [self._check_source_repository(payload)], started)
        elif normalized_type == self.DEPLOY_TYPE_PACKAGE:
            result = self._build_result(normalized_type, [self._check_package_upload(tenant, region, payload)], started)
        elif normalized_type in (self.DEPLOY_TYPE_UPLOADED_TEMPLATE, self.DEPLOY_TYPE_TEMPLATE):
            result = self._run_template_preflight(tenant, region, payload, started)
        else:
            result = self._build_result(normalized_type, [
                self._check("deploy_type", self.STATUS_BLOCK, "不支持的部署方式", "deploy_type_unsupported",
                            {"deploy_type": deploy_type})
            ], started)
        return result

    def _run_image_preflight(self, tenant: Any, region: Any, deploy_type: str,
                             payload: Dict[str, Any]) -> Dict[str, Any]:
        image = self._extract_image_reference(payload)
        if not image:
            return self._build_result(deploy_type, [
                self._check("image_reference", self.STATUS_BLOCK, "镜像地址不能为空或无法解析", "image_reference_missing")
            ], time.time())
        template = {
            "arch": payload.get("arch") or "amd64",
            "apps": [{
                "service_cname": payload.get("service_cname") or "component",
                "image": image,
                "memory": payload.get("memory") or 512,
                "container_cpu": payload.get("container_cpu") or 0,
            }]
        }
        result = self.template_preflight.run(tenant, region, template)
        result["deploy_type"] = deploy_type
        result["payload_summary"] = {"image": image, "registry_auth_id": payload.get("registry_auth_id") or ""}
        return result

    def _run_template_preflight(self, tenant: Any, region: Any, payload: Dict[str, Any],
                                started: float) -> Dict[str, Any]:
        app_template = payload.get("app_template") or payload.get("template") or {}
        if not app_template:
            return self._build_result(self.DEPLOY_TYPE_TEMPLATE, [
                self._check("template", self.STATUS_BLOCK, "应用模板不能为空", "template_missing")
            ], started)
        result = self.template_preflight.run(tenant, region, app_template)
        result["deploy_type"] = self.DEPLOY_TYPE_TEMPLATE
        return result

    def _check_source_repository(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        git_url = (payload.get("git_url") or "").strip()
        code_from = (payload.get("code_from") or "").strip()
        server_type = (payload.get("server_type") or "git").strip()
        username = payload.get("username")
        password = payload.get("password")
        if not git_url:
            return self._check("source_repository", self.STATUS_BLOCK, "仓库地址不能为空", "repository_missing")
        if not code_from:
            return self._check("source_repository", self.STATUS_BLOCK, "代码来源不能为空", "source_type_missing")
        if not server_type:
            return self._check("source_repository", self.STATUS_BLOCK, "仓库类型不能为空", "server_type_missing")
        if not self._is_supported_repository_url(git_url):
            return self._check("source_repository", self.STATUS_BLOCK, "仓库地址格式不正确", "repository_url_invalid",
                               {"git_url": git_url})
        if bool(username) != bool(password):
            return self._check("source_repository", self.STATUS_BLOCK, "仓库账号和密码需要同时填写", "repository_auth_incomplete")
        if payload.get("is_oauth") and not payload.get("service_id"):
            return self._check("source_repository", self.STATUS_BLOCK, "OAuth 仓库未选择授权服务", "oauth_service_missing")
        if not payload.get("code_version"):
            return self._check("source_repository", self.STATUS_WARNING, "未指定代码版本，将使用默认分支", "branch_defaulted")
        return self._check("source_repository", self.STATUS_PASS, "源码仓库参数完整")

    def _check_package_upload(self, tenant: Any, region: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
        event_id = payload.get("event_id")
        region_name = payload.get("region") or payload.get("region_name") or getattr(region, "region_name", "")
        if not event_id:
            return self._check("package_upload", self.STATUS_BLOCK, "上传事件不能为空", "package_event_missing")
        record = self.package_upload_service.get_upload_record(tenant.tenant_name, region_name, event_id)
        if not record:
            return self._check("package_upload", self.STATUS_BLOCK, "未找到软件包上传记录", "package_record_missing")
        packages = self._parse_package_names(getattr(record, "source_dir", ""))
        if not packages:
            return self._check("package_upload", self.STATUS_BLOCK, "未找到已上传的软件包", "package_missing")
        unsupported = [
            package for package in packages
            if not package.lower().endswith(self.SUPPORTED_PACKAGE_EXTENSIONS)
        ]
        if unsupported:
            return self._check("package_upload", self.STATUS_BLOCK, "软件包格式不支持", "package_type_unsupported",
                               {"packages": packages, "unsupported": unsupported})
        if getattr(record, "status", "") not in ("finished", "success"):
            return self._check("package_upload", self.STATUS_WARNING, "软件包上传状态未确认，安装可继续观察", "package_status_unknown",
                               {"status": getattr(record, "status", "")})
        return self._check("package_upload", self.STATUS_PASS, "软件包上传记录可用", details={"packages": packages})

    def _build_result(self, deploy_type: str, checks: List[Dict[str, Any]], started: float) -> Dict[str, Any]:
        status = self._result_status(checks)
        mode = os.getenv("DEPLOY_PREFLIGHT_MODE", "block")
        should_block = status == self.STATUS_BLOCK and mode == "block"
        if status == self.STATUS_BLOCK and mode != "block":
            status = self.STATUS_WARNING
        return {
            "deploy_type": deploy_type,
            "status": status,
            "mode": mode,
            "should_block": should_block,
            "duration_ms": int((time.time() - started) * 1000),
            "summary": self._summary(status, checks),
            "checks": checks,
        }

    def _extract_image_reference(self, payload: Dict[str, Any]) -> str:
        docker_cmd = (payload.get("docker_cmd") or payload.get("image") or "").strip()
        image_type = payload.get("image_type") or self.DEPLOY_TYPE_IMAGE
        if image_type == "docker_image":
            return docker_cmd
        try:
            tokens = shlex.split(docker_cmd)
        except ValueError:
            return ""
        if tokens[:2] == ["docker", "run"]:
            tokens = tokens[2:]
        skip_next = False
        for token in tokens:
            if skip_next:
                skip_next = False
                continue
            if token in ("-e", "--env", "-p", "--publish", "--name", "-v", "--volume", "--network"):
                skip_next = True
                continue
            if token.startswith("-"):
                continue
            return token
        return docker_cmd if "/" in docker_cmd or ":" in docker_cmd else ""

    @staticmethod
    def _parse_package_names(source_dir: Any) -> List[str]:
        if isinstance(source_dir, list):
            return [str(item) for item in source_dir if item]
        if not source_dir:
            return []
        try:
            parsed = ast.literal_eval(source_dir)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item]
        except (SyntaxError, ValueError):
            return [str(source_dir)]
        return []

    @staticmethod
    def _is_supported_repository_url(git_url: str) -> bool:
        return git_url.startswith(("http://", "https://", "ssh://", "git@"))

    def _result_status(self, checks: List[Dict[str, Any]]) -> str:
        if any(item["status"] == self.STATUS_BLOCK for item in checks):
            return self.STATUS_BLOCK
        if any(item["status"] == self.STATUS_WARNING for item in checks):
            return self.STATUS_WARNING
        return self.STATUS_PASS

    def _summary(self, status: str, checks: List[Dict[str, Any]]) -> str:
        if status == self.STATUS_BLOCK:
            for item in checks:
                if item["status"] == self.STATUS_BLOCK:
                    return item["message"]
        if status == self.STATUS_WARNING:
            return "部分部署前检测未完成，部署可继续"
        return "部署前检测通过"

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

    @staticmethod
    def _normalize_deploy_type(deploy_type: str) -> str:
        if deploy_type in ("docker_image", "image_name"):
            return DeployPreflightService.DEPLOY_TYPE_IMAGE
        if deploy_type in ("package_build", "jar_war"):
            return DeployPreflightService.DEPLOY_TYPE_PACKAGE
        return deploy_type or ""


deploy_preflight_service = DeployPreflightService()
