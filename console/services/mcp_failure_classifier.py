# -*- coding: utf-8 -*-
"""Rule-based classifier for component operation failures.

Pure, dependency-free functions that map K8s pod Warning events (and, as a
fallback, event-log tail lines) to a stable machine-readable
``classified_reason``. The MCP tool ``get_operation_failure_context`` exposes
this enum so rainagent can route directly into the matching troubleshooter
blocker branch instead of blindly retrying a failed operation.

Discipline: when no rule matches, return ``"unknown"``. Never guess.
"""
import re
from typing import Any, List, Optional, Set, Tuple

# classified_reason enum values, highest match priority first.
CONFIG_FILE_CONFIGMAP_MISSING = "config_file_configmap_missing"
VOLUME_MOUNT_FAILED = "volume_mount_failed"
IMAGE_PULL_FAILED = "image_pull_failed"
CRASH_LOOP = "crash_loop"
PROBE_FAILED = "probe_failed"
UNSCHEDULABLE = "unschedulable"
K8S_API_REJECTED = "k8s_api_rejected"
UNKNOWN = "unknown"

# Pod-warning rules, evaluated top to bottom; the first match wins. Each rule is
# (enum, reason_substrings, message_regex). ``reason_substrings`` may be empty,
# meaning "match on message regex regardless of reason".
_FAILED_MOUNT_REASONS = ("failedmount", "failedattachvolume")
_CONFIGMAP_MISSING_RE = re.compile(r"configmap\s+.*not\s+found", re.IGNORECASE)
_IMAGE_PULL_RE = re.compile(
    r"imagepullbackoff|errimagepull|back-?off\s+pulling|pull.*(timed?\s*out|timeout)", re.IGNORECASE)
_CRASH_LOOP_RE = re.compile(r"crashloopbackoff|back-?off", re.IGNORECASE)
_PROBE_RE = re.compile(r"(readiness|liveness|startup)\s+probe", re.IGNORECASE)
_UNSCHEDULABLE_REASONS = ("failedscheduling", "unschedulable")
_UNSCHEDULABLE_RE = re.compile(r"failedscheduling|unschedulable|insufficient", re.IGNORECASE)
_PROBE_REASONS = ("unhealthy",)

# Event-log fallback (only consulted when no pod warning matches).
_K8S_API_REJECTED_RE = re.compile(
    r"(patch|apply).*(failure|failed|forbidden|denied)|namespace\s+failure", re.IGNORECASE)


def _normalize_warnings(pod_warnings: Any) -> List[Tuple[str, str]]:
    normalized: List[Tuple[str, str]] = []
    for warning in pod_warnings or []:
        if not isinstance(warning, dict):
            continue
        reason = str(warning.get("reason") or "")
        message = str(warning.get("message") or "")
        normalized.append((reason.lower(), reason + " " + message))
    return normalized


def _normalize_log_lines(log_tail: Any) -> List[str]:
    lines: List[str] = []
    for entry in log_tail or []:
        if isinstance(entry, dict):
            message = entry.get("message")
            lines.append(str(message) if message is not None else "")
        elif isinstance(entry, str):
            lines.append(entry)
        else:
            lines.append(str(entry))
    return lines


def _classify_one_warning(reason_lower: str, haystack: str) -> Optional[str]:
    """Classify a single warning. Returns an enum or None if no rule matches."""
    is_mount = any(token in reason_lower for token in _FAILED_MOUNT_REASONS)
    if is_mount or "failedmount" in haystack.lower():
        if _CONFIGMAP_MISSING_RE.search(haystack):
            return CONFIG_FILE_CONFIGMAP_MISSING
        return VOLUME_MOUNT_FAILED
    if _CONFIGMAP_MISSING_RE.search(haystack):
        return CONFIG_FILE_CONFIGMAP_MISSING
    if _IMAGE_PULL_RE.search(haystack):
        return IMAGE_PULL_FAILED
    if _CRASH_LOOP_RE.search(haystack):
        return CRASH_LOOP
    if "unhealthy" in reason_lower or _PROBE_RE.search(haystack):
        return PROBE_FAILED
    if any(token in reason_lower for token in _UNSCHEDULABLE_REASONS) or _UNSCHEDULABLE_RE.search(haystack):
        return UNSCHEDULABLE
    return None


# Enum precedence used to pick the highest-priority match when several pod
# warnings classify differently (e.g. an image-pull warning and a crash-loop
# warning in the same pod).
#
# K8S_API_REJECTED is intentionally NOT in this table: it is never produced by a
# pod warning, only by the event-log fallback path below. Do not "fix" it by
# adding it here.
_PRIORITY = (
    CONFIG_FILE_CONFIGMAP_MISSING,
    VOLUME_MOUNT_FAILED,
    IMAGE_PULL_FAILED,
    CRASH_LOOP,
    PROBE_FAILED,
    UNSCHEDULABLE,
)


def classify_failure(pod_warnings: Any, log_tail: Any) -> str:
    """Map pod warnings + event-log tail to a stable classified_reason enum.

    Pod-warning evidence is authoritative and always outranks the event-log
    fallback. Among multiple pod warnings the highest-priority match wins,
    independent of list order. Returns ``"unknown"`` when nothing matches.
    """
    matches: Set[str] = set()
    for reason_lower, haystack in _normalize_warnings(pod_warnings):
        result = _classify_one_warning(reason_lower, haystack)
        if result is not None:
            matches.add(result)

    for enum_value in _PRIORITY:
        if enum_value in matches:
            return enum_value

    # Event-log fallback: only consulted when no pod warning classified.
    for line in _normalize_log_lines(log_tail):
        if _K8S_API_REJECTED_RE.search(line):
            return K8S_API_REJECTED

    return UNKNOWN
