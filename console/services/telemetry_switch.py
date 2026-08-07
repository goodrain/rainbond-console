# -*- coding: utf-8 -*-
import logging
import os
import threading
import time

from console.utils.offline import is_external_telemetry_disabled


logger = logging.getLogger("default")

EXTERNAL_TELEMETRY_ENABLED_KEY = "EXTERNAL_TELEMETRY_ENABLED"
EXTERNAL_TELEMETRY_CACHE_TTL = 5

_cache_lock = threading.Lock()
_cached_enabled = None
_cache_expires_at = 0


def _load_external_telemetry_setting():
    from console.models.main import ConsoleSysConfig

    return ConsoleSysConfig.objects.filter(
        key=EXTERNAL_TELEMETRY_ENABLED_KEY,
    ).first()


def invalidate_external_telemetry_cache():
    global _cached_enabled, _cache_expires_at
    with _cache_lock:
        _cached_enabled = None
        _cache_expires_at = 0


def get_external_telemetry_enabled(env=None):
    global _cached_enabled, _cache_expires_at
    source = os.environ if env is None else env
    if is_external_telemetry_disabled(source):
        return False

    use_cache = source is os.environ
    now = time.time()
    if use_cache:
        with _cache_lock:
            if _cached_enabled is not None and now < _cache_expires_at:
                return _cached_enabled

    try:
        config = _load_external_telemetry_setting()
        enabled = True if config is None else bool(config.enable)
    except Exception as exc:
        logger.warning("failed to read external telemetry setting: %s", exc)
        enabled = False

    if use_cache:
        with _cache_lock:
            _cached_enabled = enabled
            _cache_expires_at = now + EXTERNAL_TELEMETRY_CACHE_TTL
    return enabled


def set_external_telemetry_enabled(enabled):
    from console.models.main import ConsoleSysConfig

    config, _ = ConsoleSysConfig.objects.update_or_create(
        key=EXTERNAL_TELEMETRY_ENABLED_KEY,
        defaults={
            "type": "boolean",
            "value": "",
            "desc": "Console external telemetry switch",
            "enable": bool(enabled),
            "enterprise_id": "",
        },
    )
    invalidate_external_telemetry_cache()
    return config
