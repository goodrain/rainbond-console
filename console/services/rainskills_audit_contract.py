# -*- coding: utf-8 -*-
import hashlib
import json
import re
import uuid
from typing import Any, Dict, Optional

from console.exception.main import ServiceHandleException

RAINSKILLS_META_NAMESPACE = "com.rainbond/rainskills"
OPERATION_META_SCHEMA = "rainskills.operation-meta.v1"
MAX_SKILL_CONTENT_BYTES = 128 * 1024
MAX_OPERATION_META_BYTES = 160 * 1024

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_TOP_LEVEL_FIELDS = frozenset({
    "schema",
    "operation_id",
    "cli_version",
    "confirmation_type",
    "root_skill_id",
    "skill",
})
_SKILL_FIELDS = frozenset({
    "id",
    "profile",
    "package_version",
    "source_revision",
    "content_sha256",
    "bundle_sha256",
    "content",
})


def _contract_error(message: str, msg_show: str = "RainSkills 操作元数据无效") -> ServiceHandleException:
    return ServiceHandleException(
        msg=message,
        msg_show=msg_show,
        status_code=400,
        error_code="invalid_operation_metadata",
    )


def _required_string(value: Any, field: str, max_length: int) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise _contract_error("{} must be a non-empty string no longer than {} characters".format(
            field, max_length))
    return value


def _skill_id(value: Any, field: str) -> str:
    normalized = _required_string(value, field, 128)
    if not _ID_PATTERN.fullmatch(normalized):
        raise _contract_error("{} has an invalid format".format(field))
    return normalized


def _sha256(value: Any, field: str) -> str:
    normalized = _required_string(value, field, 64)
    if not _SHA256_PATTERN.fullmatch(normalized):
        raise _contract_error("{} must be a lowercase SHA-256 digest".format(field))
    return normalized


def extract_operation_meta(request_meta: Any) -> Optional[Dict[str, Any]]:
    """Return the RainSkills namespace without trusting other MCP metadata."""
    if request_meta is None:
        return None
    if not isinstance(request_meta, dict):
        raise _contract_error("tools/call _meta must be an object")
    metadata = request_meta.get(RAINSKILLS_META_NAMESPACE)
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        raise _contract_error("RainSkills operation metadata must be an object")
    return metadata


def validate_operation_meta(metadata: Any) -> Dict[str, Any]:
    """Validate the client-owned correlation and immutable Skill snapshot fields.

    Actor, enterprise, policy, target and deployment origin are deliberately not
    part of this schema. The Console derives those values from authenticated and
    server-owned request context.
    """
    if not isinstance(metadata, dict):
        raise _contract_error("RainSkills operation metadata must be an object")

    try:
        encoded_metadata = json.dumps(
            metadata, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError):
        raise _contract_error("RainSkills operation metadata must be valid UTF-8 JSON")
    if len(encoded_metadata) > MAX_OPERATION_META_BYTES:
        raise _contract_error("RainSkills operation metadata exceeds {} bytes".format(MAX_OPERATION_META_BYTES))

    unknown_fields = set(metadata) - _TOP_LEVEL_FIELDS
    if unknown_fields:
        raise _contract_error("unsupported RainSkills operation metadata fields: {}".format(
            ",".join(sorted(unknown_fields))))

    if metadata.get("schema") != OPERATION_META_SCHEMA:
        raise _contract_error("unsupported RainSkills operation metadata schema")

    operation_id = _required_string(metadata.get("operation_id"), "operation_id", 64)
    try:
        parsed_operation_id = uuid.UUID(operation_id)
    except (AttributeError, TypeError, ValueError):
        raise _contract_error("operation_id must be a UUID")
    if str(parsed_operation_id) != operation_id.lower():
        raise _contract_error("operation_id must use canonical UUID form")

    cli_version = _required_string(metadata.get("cli_version"), "cli_version", 64)
    if metadata.get("confirmation_type") != "rainskills_cli":
        raise _contract_error("confirmation_type must be rainskills_cli")
    root_skill_id = _skill_id(metadata.get("root_skill_id"), "root_skill_id")

    skill = metadata.get("skill")
    if not isinstance(skill, dict):
        raise _contract_error("skill must be an object")
    unknown_skill_fields = set(skill) - _SKILL_FIELDS
    if unknown_skill_fields:
        raise _contract_error("unsupported RainSkills skill metadata fields: {}".format(
            ",".join(sorted(unknown_skill_fields))))

    skill_id = _skill_id(skill.get("id"), "skill.id")
    if skill.get("profile") != "cli":
        raise _contract_error("skill.profile must be cli")
    package_version = _required_string(skill.get("package_version"), "skill.package_version", 64)

    source_revision = skill.get("source_revision")
    if source_revision is not None:
        source_revision = _required_string(source_revision, "skill.source_revision", 128)

    content_sha256 = _sha256(skill.get("content_sha256"), "skill.content_sha256")
    bundle_sha256 = _sha256(skill.get("bundle_sha256"), "skill.bundle_sha256")
    content = skill.get("content")
    if not isinstance(content, str):
        raise _contract_error("skill.content must be a string")
    try:
        content_bytes = content.encode("utf-8")
    except UnicodeEncodeError:
        raise _contract_error("skill.content must be valid UTF-8")
    if len(content_bytes) > MAX_SKILL_CONTENT_BYTES:
        raise _contract_error("skill.content exceeds {} bytes".format(MAX_SKILL_CONTENT_BYTES))
    if hashlib.sha256(content_bytes).hexdigest() != content_sha256:
        raise ServiceHandleException(
            msg="Skill content digest does not match metadata",
            msg_show="Skill 内容摘要校验失败",
            status_code=422,
            error_code="skill_digest_mismatch",
        )

    return {
        "schema": OPERATION_META_SCHEMA,
        "operation_id": operation_id.lower(),
        "cli_version": cli_version,
        "confirmation_type": "rainskills_cli",
        "root_skill_id": root_skill_id,
        "skill": {
            "id": skill_id,
            "profile": "cli",
            "package_version": package_version,
            "source_revision": source_revision,
            "content_sha256": content_sha256,
            "bundle_sha256": bundle_sha256,
            "content": content,
        },
    }
