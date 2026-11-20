# -*- coding: utf-8 -*-
from typing import Any, Dict


def normalize_template_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1"):
            return True
        if normalized in ("false", "0"):
            return False
    return default


def normalize_template_port_service_flags(port: Dict[str, Any], default_inner_service: bool = True) -> Dict[str, Any]:
    normalized_port = port.copy()
    is_outer_service = normalize_template_bool(port.get("is_outer_service"), False)
    normalized_port["is_outer_service"] = is_outer_service
    normalized_port["is_inner_service"] = normalize_template_bool(
        port.get("is_inner_service"), default_inner_service) or is_outer_service
    return normalized_port
