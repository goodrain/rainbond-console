# -*- coding: utf-8 -*-
import json
import logging
import os
import re


SENSITIVE_KEY_RE = re.compile(r"(token|password|secret|authorization|cookie|key|dsn)", re.I)
SENSITIVE_VALUE_RE = re.compile(
    r"\b((?:token|password|secret|authorization|cookie|dsn|api[_-]?key|access[_-]?key|secret[_-]?key)\s*[:=]\s*)(?:bearer\s+)?[^&\s\"'<>]+",
    re.I,
)
BEARER_VALUE_RE = re.compile(r"\b(bearer\s+)[a-z0-9._~+/=-]+", re.I)
DEFAULT_TRACES_SAMPLE_RATE = 0.0
DEFAULT_POSTHOG_PROJECT_TOKEN = "phc_oCoPwcxutKCU9AZtUT63dMTNhWezUxCXCLtSZE6a4wvE"
DEFAULT_POSTHOG_API_HOST = "/console/posthog"
DEFAULT_POSTHOG_UI_HOST = "https://posthog.goodrain.com"
DEFAULT_POSTHOG_CONFIG_DATE = "2026-05-30"
DEFAULT_POSTHOG_PERSON_PROFILES = "identified_only"

# Official release images inject the public Sentry ingest DSN at build time.
# Source builds stay disabled until a DSN is provided.

def str_to_bool(value):
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    return value.lower() in ("true", "1", "yes", "on")


def parse_sample_rate(value):
    if value in (None, ""):
        return DEFAULT_TRACES_SAMPLE_RATE
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return DEFAULT_TRACES_SAMPLE_RATE
    if rate < 0:
        return DEFAULT_TRACES_SAMPLE_RATE
    if rate > 1:
        return 1.0
    return rate


def get_env_value(env, *keys):
    for key in keys:
        value = env.get(key)
        if value:
            return value
    return ""


def is_telemetry_disabled(env):
    return (
        str_to_bool(env.get("RAINBOND_TELEMETRY_DISABLED"))
        or str_to_bool(env.get("RAINBOND_ERROR_REPORTING_DISABLED"))
    )


def get_enabled(env, *scoped_keys):
    if is_telemetry_disabled(env):
        return False
    for scoped_key in scoped_keys:
        if scoped_key in env:
            return str_to_bool(env.get(scoped_key))
    if "RAINBOND_ERROR_REPORTING_ENABLED" in env:
        return str_to_bool(env.get("RAINBOND_ERROR_REPORTING_ENABLED"))
    if "SENTRY_ENABLED" in env:
        return str_to_bool(env.get("SENTRY_ENABLED"))
    return True


def get_sentry_config(env=None):
    env = env or os.environ
    dsn = get_env_value(
        env,
        "RAINBOND_ERROR_REPORTING_CONSOLE_DSN",
        "RAINBOND_ERROR_REPORTING_BACKEND_DSN",
        "RAINBOND_ERROR_REPORTING_DSN",
        "SENTRY_CONSOLE_DSN",
        "SENTRY_BACKEND_DSN",
        "SENTRY_DSN",
    )
    enabled = get_enabled(
        env,
        "RAINBOND_ERROR_REPORTING_CONSOLE_ENABLED",
        "RAINBOND_ERROR_REPORTING_BACKEND_ENABLED",
    ) and bool(dsn)
    return {
        "enabled": enabled,
        "dsn": dsn,
        "environment": get_env_value(env, "RAINBOND_ERROR_REPORTING_ENVIRONMENT", "SENTRY_ENVIRONMENT") or "production",
        "release": get_env_value(env, "RAINBOND_ERROR_REPORTING_RELEASE", "SENTRY_RELEASE", "RELEASE_DESC"),
        "traces_sample_rate": parse_sample_rate(env.get("SENTRY_TRACES_SAMPLE_RATE")),
    }


def get_frontend_sentry_config(env=None):
    env = env or os.environ
    dsn = get_env_value(
        env,
        "RAINBOND_ERROR_REPORTING_FRONTEND_DSN",
        "RAINBOND_ERROR_REPORTING_DSN",
        "SENTRY_FRONTEND_DSN",
        "SENTRY_DSN",
    )
    enabled = get_enabled(env, "RAINBOND_ERROR_REPORTING_FRONTEND_ENABLED") and bool(dsn)
    return {
        "enabled": enabled,
        "dsn": dsn if enabled else "",
        "environment": get_env_value(env, "RAINBOND_ERROR_REPORTING_ENVIRONMENT", "SENTRY_ENVIRONMENT") or "production",
        "release": get_env_value(env, "RAINBOND_ERROR_REPORTING_RELEASE", "SENTRY_RELEASE", "RELEASE_DESC"),
        "tracesSampleRate": parse_sample_rate(env.get("SENTRY_TRACES_SAMPLE_RATE")),
    }


def get_frontend_sentry_config_json(env=None):
    return (
        json.dumps(get_frontend_sentry_config(env), separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def get_posthog_enabled(env, project_token):
    if is_telemetry_disabled(env) or str_to_bool(env.get("RAINBOND_POSTHOG_DISABLED")) or str_to_bool(env.get("POSTHOG_DISABLED")):
        return False
    if "RAINBOND_POSTHOG_ENABLED" in env:
        return str_to_bool(env.get("RAINBOND_POSTHOG_ENABLED")) and bool(project_token)
    if "POSTHOG_ENABLED" in env:
        return str_to_bool(env.get("POSTHOG_ENABLED")) and bool(project_token)
    return bool(project_token)


def get_frontend_posthog_config(env=None):
    env = env or os.environ
    project_token = DEFAULT_POSTHOG_PROJECT_TOKEN
    enabled = get_posthog_enabled(env, project_token)
    return {
        "enabled": enabled,
        "projectToken": project_token if enabled else "",
        "apiHost": get_env_value(env, "RAINBOND_POSTHOG_API_HOST", "POSTHOG_API_HOST") or DEFAULT_POSTHOG_API_HOST,
        "uiHost": get_env_value(env, "RAINBOND_POSTHOG_UI_HOST", "POSTHOG_UI_HOST") or DEFAULT_POSTHOG_UI_HOST,
        "defaults": get_env_value(env, "RAINBOND_POSTHOG_DEFAULTS", "POSTHOG_DEFAULTS") or DEFAULT_POSTHOG_CONFIG_DATE,
        "personProfiles": get_env_value(env, "RAINBOND_POSTHOG_PERSON_PROFILES", "POSTHOG_PERSON_PROFILES") or DEFAULT_POSTHOG_PERSON_PROFILES,
        "autocapture": not str_to_bool(env.get("RAINBOND_POSTHOG_AUTOCAPTURE_DISABLED") or env.get("POSTHOG_AUTOCAPTURE_DISABLED")),
        "sessionRecording": str_to_bool(env.get("RAINBOND_POSTHOG_SESSION_RECORDING") or env.get("POSTHOG_SESSION_RECORDING")),
        "maskAllText": str_to_bool(env.get("RAINBOND_POSTHOG_MASK_ALL_TEXT") or env.get("POSTHOG_MASK_ALL_TEXT")),
        "maskAllElementAttributes": not str_to_bool(env.get("RAINBOND_POSTHOG_UNMASK_ELEMENT_ATTRIBUTES") or env.get("POSTHOG_UNMASK_ELEMENT_ATTRIBUTES")),
        "capturePageleave": str_to_bool(env.get("RAINBOND_POSTHOG_CAPTURE_PAGELEAVE") or env.get("POSTHOG_CAPTURE_PAGELEAVE")),
        "disableFlags": not str_to_bool(env.get("RAINBOND_POSTHOG_ENABLE_FLAGS") or env.get("POSTHOG_ENABLE_FLAGS")),
        "debug": str_to_bool(env.get("RAINBOND_POSTHOG_DEBUG") or env.get("POSTHOG_DEBUG")),
    }


def get_frontend_posthog_config_json(env=None):
    return (
        json.dumps(get_frontend_posthog_config(env), separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def sanitize_value(value, depth=0):
    if depth > 4:
        return "[MaxDepth]"
    if isinstance(value, str):
        return BEARER_VALUE_RE.sub(r"\1[Filtered]", SENSITIVE_VALUE_RE.sub(r"\1[Filtered]", value))
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                result[key] = "[Filtered]"
            else:
                result[key] = sanitize_value(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_value(item, depth + 1) for item in list(value)[:20]]
    return value


def before_send(event, hint):
    event.pop("user", None)
    request = event.get("request")
    if request:
        event["request"] = {
            "method": request.get("method"),
        }
    return sanitize_value(event)


def init_sentry():
    config = get_sentry_config()
    if not config["enabled"]:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        return False

    sentry_sdk.init(
        dsn=config["dsn"],
        integrations=[DjangoIntegration(), LoggingIntegration(event_level=logging.ERROR)],
        environment=config["environment"],
        release=config["release"] or None,
        traces_sample_rate=config["traces_sample_rate"],
        send_default_pii=False,
        before_send=before_send,
    )
    return True
