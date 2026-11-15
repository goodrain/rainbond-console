"""Public, advisory storage snapshot evidence. Region remains mutation authority."""
import re
from typing import Any, Dict


def project_snapshot_capability(value: Any) -> Dict[str, Any]:
    value = value if isinstance(value, dict) else {}
    status = value.get("status")
    if status not in ("supported", "unsupported", "unknown") or value.get("supported") is not (status == "supported"):
        status = "unknown"
    reason = value.get("reason_code")
    return {
        "supported": status == "supported",
        "status": status,
        "reason_code": reason if isinstance(reason, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", reason) else ""
    }


def project_creation_storage_option(value: Dict[str, Any]) -> Dict[str, Any]:
    # Do not forward driver parameters, credentials or arbitrary upstream text.
    return {
        key: value[key]
        for key in ("volume_type", "name_show", "enable") if key in value
    } | {
        "snapshot_capability": project_snapshot_capability(value.get("snapshot_capability")),
        "managed_snapshot_capability": project_snapshot_capability(value.get("managed_snapshot_capability"))
    }
