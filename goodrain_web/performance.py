# -*- coding: utf-8 -*-
import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from urllib.parse import urlsplit

logger = logging.getLogger('default')

DEFAULT_SLOW_REQUEST_THRESHOLD_MS = 500.0
MAX_REGION_CALL_DETAILS = 100
PERFORMANCE_PATH_PREFIXES = ('/api/', '/console/', '/marketapi/', '/openapi/')

_performance_context = ContextVar('console_performance_context', default=None)


def get_performance_context():
    return _performance_context.get()


def _start_performance_context():
    context = {
        "request_id": uuid.uuid4().hex,
        "region_calls": [],
        "region_call_count": 0,
        "region_total_ms": 0.0,
        "region_max_ms": 0.0,
    }
    return _performance_context.set(context), context


def _slow_request_threshold_ms():
    try:
        return max(0.0, float(os.environ.get("CONSOLE_SLOW_REQUEST_THRESHOLD_MS", DEFAULT_SLOW_REQUEST_THRESHOLD_MS)))
    except (TypeError, ValueError):
        return DEFAULT_SLOW_REQUEST_THRESHOLD_MS


def _performance_logging_enabled():
    value = os.environ.get("CONSOLE_PERFORMANCE_LOG_ENABLED", "")
    return value.strip().lower() in ("1", "true", "yes", "on")


def _safe_url_path(url):
    try:
        return urlsplit(str(url)).path or "/"
    except (TypeError, ValueError):
        return "<invalid-url>"


def record_region_call(method, url, status, elapsed_ms):
    context = get_performance_context()
    if context is None:
        return

    elapsed_ms = round(float(elapsed_ms), 3)
    context["region_call_count"] += 1
    context["region_total_ms"] += elapsed_ms
    context["region_max_ms"] = max(context["region_max_ms"], elapsed_ms)
    if len(context["region_calls"]) < MAX_REGION_CALL_DETAILS:
        context["region_calls"].append({
            "method": str(method).upper(),
            "path": _safe_url_path(url),
            "status": status,
            "elapsed_ms": elapsed_ms,
        })


class PerformanceTimingMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(PERFORMANCE_PATH_PREFIXES):
            return self.get_response(request)

        token, context = _start_performance_context()
        started = time.monotonic()
        status = 500
        try:
            response = self.get_response(request)
            status = getattr(response, "status_code", 200)
            response["X-Request-ID"] = context["request_id"]
            return response
        finally:
            try:
                total_ms = round((time.monotonic() - started) * 1000, 3)
                if _performance_logging_enabled() and (status >= 500 or total_ms >= _slow_request_threshold_ms()):
                    payload = {
                        "event": "console_request_timing",
                        "request_id": context["request_id"],
                        "method": request.method,
                        "path": request.path,
                        "status": status,
                        "total_ms": total_ms,
                        "region_call_count": context["region_call_count"],
                        "region_total_ms": round(context["region_total_ms"], 3),
                        "region_max_ms": round(context["region_max_ms"], 3),
                        "non_region_ms": round(max(0.0, total_ms - context["region_total_ms"]), 3),
                        "region_calls": context["region_calls"],
                    }
                    try:
                        logger.info("PERF_REQUEST %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))
                    except Exception:
                        pass
            finally:
                _performance_context.reset(token)
