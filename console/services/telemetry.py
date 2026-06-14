# -*- coding: utf-8 -*-
import hashlib
import logging
import os
import re
import uuid

from django.utils import timezone

from console.models.main import ConsoleSysConfig


logger = logging.getLogger("default")

DEFAULT_POSTHOG_PROJECT_TOKEN = "phc_oCoPwcxutKCU9AZtUT63dMTNhWezUxCXCLtSZE6a4wvE"
DEFAULT_POSTHOG_SERVER_HOST = "https://posthog.goodrain.com"
INSTANCE_ID_KEY = "RBD_TELEMETRY_INSTANCE_ID"
REGISTERED_KEY = "RBD_TELEMETRY_REGISTERED"
FIRST_APP_KEY = "RBD_TEL_FIRST_APP_CREATED"
HEARTBEAT_KEY_PREFIX = "RBD_TEL_HB_"
REQUEST_TIMEOUT = 2

SENSITIVE_KEY_RE = re.compile(
    r"(token|password|secret|authorization|cookie|key|dsn|email|phone|git|repo|repository|url|domain|image|"
    r"app_name|service_name|component_name|team_name|user_name|nick_name)",
    re.I,
)
SENSITIVE_VALUE_RE = re.compile(
    r"\b((?:token|password|secret|authorization|cookie|dsn|api[_-]?key|access[_-]?key|secret[_-]?key|email|phone)"
    r"\s*[:=]\s*)(?:bearer\s+)?[^&\s\"'<>]+",
    re.I,
)
BEARER_VALUE_RE = re.compile(r"\b(bearer\s+)[a-z0-9._~+/=-]+", re.I)


def str_to_bool(value):
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    return value.lower() in ("true", "1", "yes", "on")


def hash_identifier(instance_id, identifier):
    raw = "{0}:{1}".format(instance_id or "", identifier)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sanitize_properties(value, depth=0):
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
                result[key] = sanitize_properties(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_properties(item, depth + 1) for item in list(value)[:20]]
    return value


def _utc_now():
    return timezone.now()


class NullTransport(object):
    def post(self, *args, **kwargs):
        raise RuntimeError("telemetry transport unavailable")


class RainbondTelemetryService(object):
    def __init__(self, env=None, transport=None, now=None):
        self.env = env or os.environ
        self.transport = transport or self._load_default_transport()
        self.now = now or _utc_now

    @staticmethod
    def _load_default_transport():
        try:
            import requests
            return requests
        except Exception:
            return NullTransport()

    def is_enabled(self):
        if str_to_bool(self.env.get("RAINBOND_TELEMETRY_DISABLED")):
            return False
        if str_to_bool(self.env.get("RAINBOND_POSTHOG_DISABLED")) or str_to_bool(self.env.get("POSTHOG_DISABLED")):
            return False
        if "RAINBOND_POSTHOG_ENABLED" in self.env:
            return str_to_bool(self.env.get("RAINBOND_POSTHOG_ENABLED"))
        if "POSTHOG_ENABLED" in self.env:
            return str_to_bool(self.env.get("POSTHOG_ENABLED"))
        return True

    def get_project_token(self):
        return DEFAULT_POSTHOG_PROJECT_TOKEN

    def get_server_host(self):
        for key in (
            "RAINBOND_POSTHOG_SERVER_HOST",
            "RAINBOND_POSTHOG_PROXY_TARGET",
            "RAINBOND_POSTHOG_API_HOST",
            "POSTHOG_HOST",
            "POSTHOG_API_HOST",
            "RAINBOND_POSTHOG_UI_HOST",
        ):
            value = self.env.get(key)
            if value and value.startswith("http"):
                return value.rstrip("/")
        return DEFAULT_POSTHOG_SERVER_HOST

    def get_or_create_instance_id(self):
        record = ConsoleSysConfig.objects.filter(key=INSTANCE_ID_KEY, enable=True).first()
        if record and record.value:
            return record.value
        instance_id = uuid.uuid4().hex
        record, created = ConsoleSysConfig.objects.get_or_create(
            key=INSTANCE_ID_KEY,
            defaults={
                "type": "string",
                "value": instance_id,
                "desc": "Rainbond telemetry anonymous instance id",
                "enable": True,
            },
        )
        if not created and not record.value:
            record.value = instance_id
            record.enable = True
            record.save(update_fields=["value", "enable"])
        return record.value

    def get_install_time(self):
        record = ConsoleSysConfig.objects.filter(key=INSTANCE_ID_KEY, enable=True).first()
        if not record or not record.create_time:
            return ""
        return record.create_time.isoformat()

    def get_days_since_install(self):
        record = ConsoleSysConfig.objects.filter(key=INSTANCE_ID_KEY, enable=True).first()
        if not record or not record.create_time:
            return 0
        now = self.now()
        create_time = record.create_time
        if timezone.is_naive(now) != timezone.is_naive(create_time):
            if timezone.is_naive(now):
                now = timezone.make_aware(now, timezone.utc)
            if timezone.is_naive(create_time):
                create_time = timezone.make_aware(create_time, timezone.utc)
        return max((now - create_time).days, 0)

    def get_instance_properties(self):
        console_version = ""
        try:
            from django.conf import settings
            console_version = getattr(settings, "VERSION", "") or ""
        except Exception:
            console_version = ""
        instance_id = self.get_or_create_instance_id()
        return {
            "instance_id": instance_id,
            "console_version": console_version,
            "rainbond_version": self.env.get("RAINBOND_VERSION", "") or self.env.get("RELEASE_DESC", "") or "",
            "edition": self.env.get("ENTERPRISE_EDITION", "") or self.env.get("RAINBOND_EDITION", "") or "",
            "install_time": self.get_install_time(),
            "days_since_install": self.get_days_since_install(),
        }

    def build_payload(self, event_name, properties=None, distinct_id=None):
        merged_properties = self.get_instance_properties()
        merged_properties.update(properties or {})
        return {
            "api_key": self.get_project_token(),
            "batch": [{
                "event": event_name,
                "distinct_id": distinct_id or merged_properties["instance_id"],
                "timestamp": self.now().isoformat(),
                "properties": sanitize_properties(merged_properties),
            }],
        }

    def capture(self, event_name, properties=None, distinct_id=None):
        if not event_name or not self.is_enabled():
            return False
        try:
            self.transport.post(
                self.get_server_host() + "/batch/",
                json=self.build_payload(event_name, properties, distinct_id),
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            return True
        except Exception as exc:
            logger.debug("posthog telemetry capture failed: %s", exc)
            return False

    def _create_flag_if_absent(self, key):
        _, created = ConsoleSysConfig.objects.get_or_create(
            key=key,
            defaults={
                "type": "string",
                "value": "true",
                "desc": "Rainbond telemetry marker",
                "enable": True,
            },
        )
        return created

    def track_instance_registered(self):
        try:
            if not self._create_flag_if_absent(REGISTERED_KEY):
                return False
            return self.capture("rainbond_instance_registered")
        except Exception as exc:
            logger.debug("posthog telemetry registration failed: %s", exc)
            return False

    def track_instance_heartbeat(self):
        try:
            day_key = HEARTBEAT_KEY_PREFIX + self.now().strftime("%Y%m%d")
            if not self._create_flag_if_absent(day_key):
                return False
            return self.capture("rainbond_instance_heartbeat")
        except Exception as exc:
            logger.debug("posthog telemetry heartbeat failed: %s", exc)
            return False

    def track_app_created(self, tenant=None, region_name="", app=None, source="rainbond"):
        try:
            is_first_app = self._create_flag_if_absent(FIRST_APP_KEY)
            return self.capture("rainbond_app_created", {
                "region_name": region_name,
                "source": source,
                "app_type": getattr(app, "app_type", "") if app is not None else "",
                "is_first_app": is_first_app,
                "days_since_install": self.get_days_since_install(),
            })
        except Exception as exc:
            logger.debug("posthog telemetry app event failed: %s", exc)
            return False

    def track_component_created(self, tenant=None, region_name="", component=None, source_type=""):
        try:
            return self.capture("rainbond_component_created", {
                "region_name": region_name,
                "source_type": source_type or getattr(component, "service_source", "") or "",
                "category": getattr(component, "category", "") if component is not None else "",
                "service_type": getattr(component, "service_type", "") if component is not None else "",
                "language": getattr(component, "language", "") if component is not None else "",
                "arch": getattr(component, "arch", "") if component is not None else "",
            })
        except Exception as exc:
            logger.debug("posthog telemetry component event failed: %s", exc)
            return False

    def track_market_app_installed(self, tenant=None, region_name="", app_model_version="", market_type=""):
        try:
            return self.capture("rainbond_market_app_installed", {
                "region_name": region_name,
                "app_model_version": app_model_version,
                "market_type": market_type,
            })
        except Exception as exc:
            logger.debug("posthog telemetry market event failed: %s", exc)
            return False

    def track_version_upgraded(self,
                               tenant=None,
                               region_name="",
                               from_version="",
                               to_version="",
                               upgrade_type="app",
                               upgrade_count=0):
        try:
            return self.capture("rainbond_version_upgraded", {
                "region_name": region_name,
                "from_version": from_version,
                "to_version": to_version,
                "upgrade_type": upgrade_type,
                "upgrade_count": upgrade_count,
            })
        except Exception as exc:
            logger.debug("posthog telemetry upgrade event failed: %s", exc)
            return False

    def boot(self):
        try:
            self.track_instance_registered()
            self.track_instance_heartbeat()
        except Exception as exc:
            logger.debug("posthog telemetry boot failed: %s", exc)


telemetry_service = RainbondTelemetryService()
