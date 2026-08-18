# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.conf import settings

from console.exception.main import ServiceHandleException
from console.repositories.rainskills_audit_repo import rainskills_audit_repo
from console.services.deployment_invocation import get_deployment_invocation
from console.services.rainskills_audit_contract import extract_operation_meta, validate_operation_meta
from console.services.rainskills_tool_audit_policy import classify_tool

logger = logging.getLogger("default")

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:authorization|credential|password|passwd|secret|token|cookie|kubeconfig|certificate|"
    r"private[_-]?key|access[_-]?key|api[_-]?key)", re.I)
_SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)(bearer\s+|grjwt\s*|(?:password|passwd|secret|token|authorization|cookie|"
    r"kubeconfig|certificate|api[_-]?key)\s*[=:]\s*)[^\s,;]+")
_TARGET_ARGUMENT_FIELDS = frozenset({
    "team_name",
    "region_name",
    "app_id",
    "app_name",
    "service_id",
    "service_alias",
    "service_cname",
    "record_id",
    "snapshot_id",
    "action",
})
_MAX_INPUT_JSON_BYTES = 32 * 1024
_MAX_VALUE_TEXT_LENGTH = 512
_MAX_SUMMARY_LENGTH = 4096


def _audit_metric(name: str, value: int = 1, **labels: Any) -> None:
    """Emit low-cardinality audit rollout metrics through the existing logger."""
    label_text = " ".join(
        "{}={}".format(key, labels[key]) for key in sorted(labels))
    logger.info("rainskills_audit_metric name=%s value=%s %s", name, value, label_text)


@dataclass(frozen=True)
class RainSkillsAuditContext:
    operation: Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def arguments_digest(arguments: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(arguments).encode("utf-8")).hexdigest()


def _redact(value: Any, key: str = "") -> Any:
    if key and _SENSITIVE_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return value[:_MAX_VALUE_TEXT_LENGTH]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:_MAX_VALUE_TEXT_LENGTH]


def _safe_input(arguments: Dict[str, Any], digest: str) -> Dict[str, Any]:
    redacted = _redact(arguments)
    if len(canonical_json(redacted).encode("utf-8")) <= _MAX_INPUT_JSON_BYTES:
        return redacted
    return {"truncated": True, "arguments_digest": digest}


def _target_context(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: _redact(arguments[key], key)
        for key in _TARGET_ARGUMENT_FIELDS
        if key in arguments and isinstance(arguments[key], (str, int))
    }


def _safe_summary(value: Any) -> str:
    try:
        summary = canonical_json(_redact(value))
    except (TypeError, ValueError):
        summary = str(value)
    return _SENSITIVE_TEXT_PATTERN.sub(r"\1[REDACTED]", summary)[:_MAX_SUMMARY_LENGTH]


def _audit_unavailable(exc: Exception) -> ServiceHandleException:
    logger.exception("RainSkills started audit persistence failed")
    return ServiceHandleException(
        msg="RainSkills audit is unavailable",
        msg_show="审计服务暂不可用，本次写操作未执行",
        status_code=503,
        error_code="audit_unavailable",
    )


class RainSkillsAuditService(object):

    def begin(self, user: Any, tool_name: str, arguments: Dict[str, Any],
              request_meta: Any) -> Optional[RainSkillsAuditContext]:
        policy = classify_tool(tool_name)
        if policy.operation_class == "read":
            return None

        metadata = extract_operation_meta(request_meta)
        _audit_metric("metadata_present", present=metadata is not None)
        if metadata is None:
            if bool(getattr(settings, "RAINSKILLS_AUDIT_STRICT", False)):
                raise ServiceHandleException(
                    msg="RainSkills operation confirmation metadata is required",
                    msg_show="当前写操作需要新版 RainSkills 确认信息",
                    status_code=428,
                    error_code="operation_confirmation_required",
                )
            validated = None
            operation_id = str(uuid.uuid4())
            confirmation_type = "legacy_compat"
            _audit_metric("legacy_compat")
            skill_id = None
            root_skill_id = None
            skill_digest = None
        else:
            validated = validate_operation_meta(metadata)
            operation_id = validated["operation_id"]
            confirmation_type = validated["confirmation_type"]
            skill_id = validated["skill"]["id"]
            root_skill_id = validated["root_skill_id"]
            skill_digest = validated["skill"]["content_sha256"]

        enterprise_id = str(getattr(user, "enterprise_id", "") or "")
        digest = arguments_digest(arguments)
        try:
            existing = rainskills_audit_repo.get_operation(enterprise_id, operation_id)
            if existing is not None:
                self._reject_existing(existing, tool_name, digest, skill_id, skill_digest)

            snapshot = None
            if validated is not None:
                snapshot, _ = rainskills_audit_repo.get_or_create_snapshot(
                    enterprise_id, validated["skill"])
                _audit_metric("snapshot_verified")

            invocation = get_deployment_invocation()
            operation, owner = rainskills_audit_repo.begin_operation(
                enterprise_id=enterprise_id,
                operation_id=operation_id,
                user_id=str(getattr(user, "user_id", "") or ""),
                username=(getattr(user, "nick_name", None) or getattr(user, "username", None)),
                deploy_client=invocation.client,
                snapshot=snapshot,
                skill_id=skill_id,
                root_skill_id=root_skill_id,
                tool_name=tool_name,
                operation_class=policy.operation_class,
                risk=policy.risk,
                scope=policy.scope,
                arguments_digest=digest,
                input_json=_safe_input(arguments, digest),
                target_context=_target_context(arguments),
                confirmation_type=confirmation_type,
            )
            if not owner:
                self._reject_existing(operation, tool_name, digest, skill_id, skill_digest)
            return RainSkillsAuditContext(operation=operation)
        except ServiceHandleException:
            raise
        except Exception as exc:
            raise _audit_unavailable(exc)

    @staticmethod
    def _reject_existing(operation: Any, tool_name: str, digest: str,
                         skill_id: Optional[str], skill_digest: Optional[str]) -> None:
        if not rainskills_audit_repo.binding_matches(
                operation, tool_name, digest, skill_id, skill_digest):
            raise ServiceHandleException(
                msg="operation metadata conflicts with the existing operation",
                msg_show="操作标识与已有记录不一致",
                status_code=409,
                error_code="operation_conflict",
            )
        raise ServiceHandleException(
            msg="operation has already been recorded",
            msg_show="该操作已记录，不会重复执行",
            status_code=409,
            error_code="operation_already_recorded",
        )

    @staticmethod
    def finalize_success(context: Optional[RainSkillsAuditContext], result: Any) -> None:
        if context is None:
            return
        try:
            rainskills_audit_repo.finalize_operation(
                context.operation,
                status="succeeded",
                output_summary=_safe_summary(result),
            )
        except Exception:
            # The durable started row remains executing and is later materialized
            # as unknown. A successful Tool must never be replayed automatically.
            logger.exception("RainSkills terminal success audit persistence failed")

    @staticmethod
    def finalize_failure(context: Optional[RainSkillsAuditContext], exc: Exception) -> None:
        if context is None:
            return
        error_code = getattr(exc, "error_code", None) or exc.__class__.__name__.lower()
        reason = getattr(exc, "msg_show", None) or str(exc) or exc.__class__.__name__
        try:
            rainskills_audit_repo.finalize_operation(
                context.operation,
                status="failed",
                error_code=str(error_code)[:64],
                error_message=_safe_summary(reason),
            )
        except Exception:
            logger.exception("RainSkills terminal failure audit persistence failed")


rainskills_audit_service = RainSkillsAuditService()
