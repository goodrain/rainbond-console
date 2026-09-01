from typing import Any


GATEWAY_MONITORING_PLUGIN_BASE_IDS = frozenset([
    "rainbond-observability",
])

PLUGIN_ARCH_SUFFIXES = ("-AMD64", "-ARM64")


def normalize_plugin_base_id(plugin_name: Any) -> str:
    normalized = str(plugin_name or "").strip()
    for suffix in PLUGIN_ARCH_SUFFIXES:
        if normalized.endswith(suffix):
            return normalized[:-len(suffix)]
    return normalized


def is_gateway_monitoring_plugin(plugin_name: Any) -> bool:
    return normalize_plugin_base_id(plugin_name) in GATEWAY_MONITORING_PLUGIN_BASE_IDS
