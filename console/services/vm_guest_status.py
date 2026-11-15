"""Normalize the current guest-agent observation without guessing OS readiness."""

_RULES = {
    ("responding", "agent_connected"): True,
    ("unconfirmed", "agent_disconnected"): False,
    ("unconfirmed", "agent_not_reported"): None,
    ("powered_off", "vm_stopped"): None,
    ("paused", "vm_paused"): None,
    ("starting", "vm_starting"): None,
    ("unavailable", "read_failed"): None,
    ("unavailable", "instance_not_created"): None,
    ("unavailable", "instance_not_running"): None,
    ("unavailable", "backend_unsupported"): None,
    ("unavailable", "invalid_response"): None,
}


def _unavailable(reason):
    return {"status": "unavailable", "agent_connected": None, "reason": reason}


def normalize_vm_guest_status(payload, fallback_reason="backend_unsupported"):
    """Keep true, false and unavailable separate; expose only finite status codes."""
    if payload is None:
        return _unavailable(fallback_reason if fallback_reason in ("backend_unsupported", "read_failed")
                            else "invalid_response")
    if not isinstance(payload, dict):
        return _unavailable("invalid_response")
    status, reason = payload.get("status"), payload.get("reason")
    if not isinstance(status, str) or not isinstance(reason, str):
        return _unavailable("invalid_response")
    key = (status, reason)
    if key not in _RULES or "agent_connected" not in payload:
        return _unavailable("invalid_response")
    connected = payload["agent_connected"]
    if connected is not _RULES[key]:
        return _unavailable("invalid_response")
    result = {"status": status, "agent_connected": connected, "reason": reason}
    if connected is True and isinstance(payload.get("os"), dict):
        result["os"] = {
            name: value.strip()[:256]
            for name, value in payload["os"].items()
            if name in ("name", "version", "kernel_release") and isinstance(value, str)
            and not any(ord(char) < 32 or ord(char) == 127 for char in value)
        }
    return result
