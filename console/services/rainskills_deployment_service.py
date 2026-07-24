# -*- coding: utf-8 -*-
import datetime
import logging
import os
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, Iterable, NamedTuple, Optional, Tuple

import requests

from console.repositories.rainskills_deployment_repo import rainskills_deployment_repo
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger(__name__)


class DeploymentSpec(NamedTuple):
    deploy_stage: str
    trigger: str
    deploy_type: str
    resource_created: bool
    legacy_tracked: bool


class RainSkillsDeploymentService(object):
    DEFAULT_REPORT_URL = "https://log.rainbond.com/api/rainskills/deployments"
    POLL_WINDOW_SECONDS = 20 * 60
    POLL_INTERVAL_SECONDS = 5
    SWEEPER_INTERVAL_SECONDS = 15
    MAX_RETENTION_SECONDS = 7 * 24 * 60 * 60
    MAX_IDS = 50
    MAX_FAILURE_REASON_LENGTH = 1024
    LOCAL_STATE_AWAITING_RESULT = "awaiting_result"
    LOCAL_STATE_BOUND = "bound"

    CREATE_DEPLOYMENT_TOOLS = {
        "rainbond_create_component": DeploymentSpec(
            "initial", "image_create", "image", True, False),
        "rainbond_create_component_from_image": DeploymentSpec(
            "initial", "image_create", "image", True, False),
        "rainbond_create_component_from_source": DeploymentSpec(
            "initial", "source_create", "source_code", True, True),
        "rainbond_create_component_from_package": DeploymentSpec(
            "initial", "package_create", "package", True, True),
        "rainbond_create_component_from_local_package": DeploymentSpec(
            "initial", "package_create", "package", True, True),
        "rainbond_install_app_model": DeploymentSpec(
            "initial", "market_install", "app_market", True, True),
        "rainbond_install_app_by_market": DeploymentSpec(
            "initial", "market_install", "app_market", True, True),
        "rainbond_create_app_from_snapshot_version": DeploymentSpec(
            "initial", "snapshot_create", "app_market", True, True),
    }
    UNCONDITIONAL_DEPLOYMENT_TOOLS = {
        "rainbond_execute_app_upgrade_record": DeploymentSpec(
            "continuous", "execute_upgrade_record", "app_market", False,
            False),
        "rainbond_deploy_app_upgrade_record": DeploymentSpec(
            "continuous", "deploy_upgrade_record", "app_market", False,
            False),
        "rainbond_upgrade_app": DeploymentSpec(
            "continuous", "upgrade_app", "app_market", False, False),
        "rainbond_rollback_app_upgrade_record": DeploymentSpec(
            "rollback", "rollback_app_upgrade_record", "app_market", False,
            False),
        "rainbond_rollback_app_version_snapshot": DeploymentSpec(
            "rollback", "rollback_app_version_snapshot", "app_market", False,
            False),
    }
    DEPLOY_DEFAULTS = {
        "rainbond_install_app_by_market": False,
    }
    SOURCE_TYPE_MAP = {
        "source_code": "source_code",
        "docker_image": "image",
        "docker_run": "image",
        "docker_compose": "image",
        "package_build": "package",
    }

    REPORT_FIELDS = (
        "deploy_attempt_id",
        "eid",
        "deploy_client",
        "tool_name",
        "deploy_type",
        "deploy_stage",
        "trigger",
        "source_language",
        "resource_created",
        "app_id",
        "service_ids",
        "event_ids",
        "service_count",
        "event_count",
        "service_ids_truncated",
        "event_ids_truncated",
        "report_phase",
        "status",
        "deploy_result_at",
        "failure_stage",
        "failure_category",
        "failure_reason",
    )
    FINAL_STATUSES = ("success", "failure", "timeout")
    SUCCESS_STATUSES = ("success", "succeeded", "complete", "completed")
    FAILURE_STATUSES = ("failure", "failed", "error")
    TIMEOUT_STATUSES = ("timeout", "timedout", "timed_out")
    SENSITIVE_QUOTED_ASSIGNMENT_RE = re.compile(
        r"(?P<key_quote>[\"']?)(?P<key>password|passwd|pwd|token|secret|authorization|api[_-]?key)"
        r"(?P=key_quote)(?P<separator>\s*[:=]\s*)(?P<value_quote>[\"'])(?P<value>.*?)(?P=value_quote)",
        re.IGNORECASE)
    SENSITIVE_BARE_ASSIGNMENT_RE = re.compile(
        r"(?P<key_quote>[\"']?)(?P<key>password|passwd|pwd|token|secret|authorization|api[_-]?key)"
        r"(?P=key_quote)(?P<separator>\s*[:=]\s*)(?P<value>[^,\s\"';&]+)",
        re.IGNORECASE)
    AUTH_TOKEN_RE = re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+",
                               re.IGNORECASE)
    ACCESS_TOKEN_RE = re.compile(
        r"\b(access\s+token)\s+(?:<[A-Za-z0-9._~+/=-]+>|[A-Za-z0-9._~+/=-]+)",
        re.IGNORECASE)
    URL_CREDENTIAL_RE = re.compile(
        r"([A-Za-z][A-Za-z0-9+.-]*://)[^:/\s]*:[^@\s]+@", re.IGNORECASE)

    def classify_tool_call(self,
                           tool_name: str,
                           arguments: Any,
                           service_sources: Optional[Iterable[Any]] = None
                           ) -> Optional[DeploymentSpec]:
        arguments = arguments if isinstance(arguments, dict) else {}
        if tool_name in self.CREATE_DEPLOYMENT_TOOLS:
            default = self.DEPLOY_DEFAULTS.get(tool_name, True)
            if not self._parse_bool(arguments.get("is_deploy"), default):
                return None
            return self.CREATE_DEPLOYMENT_TOOLS[tool_name]
        if tool_name == "rainbond_build_component":
            if not self._parse_bool(arguments.get("is_deploy"), True):
                return None
            return DeploymentSpec("continuous", "build_component",
                                  self._classify_service_sources(
                                      service_sources), False, False)
        if tool_name == "rainbond_operate_app":
            action = str(arguments.get("action") or "").strip().lower()
            if action not in ("deploy", "upgrade"):
                return None
            return DeploymentSpec("continuous", "operate_app_{}".format(action),
                                  self._classify_service_sources(
                                      service_sources), False, False)
        return self.UNCONDITIONAL_DEPLOYMENT_TOOLS.get(tool_name)

    def normalize_tool_result(self, result: Any) -> dict:
        result = result if isinstance(result, dict) else {}
        result_is_deploy = result.get("is_deploy")
        if not isinstance(result_is_deploy, bool):
            result_is_deploy = None
        event_values = [result.get("event_id")]
        service_values = [result.get("service_id")]
        raw_event_ids = result.get("event_ids")
        if isinstance(raw_event_ids, (list, tuple)):
            for item in raw_event_ids:
                event_values.append(self._standard_id(item, "event_id"))
                if isinstance(item, dict):
                    service_values.append(
                        self._standard_id(item, "service_id"))
        raw_service_ids = result.get("service_ids")
        if isinstance(raw_service_ids, (list, tuple)):
            for item in raw_service_ids:
                service_values.append(self._standard_id(item, "service_id"))
        event_ids, event_count, events_truncated = self._normalize_ids(
            event_values)
        service_ids, service_count, services_truncated = self._normalize_ids(
            service_values)
        return {
            "app_id": self._normalize_app_id(result.get("app_id")),
            "is_deploy": result_is_deploy,
            "event_ids": event_ids,
            "event_count": event_count,
            "event_ids_truncated": events_truncated,
            "service_ids": service_ids,
            "service_count": service_count,
            "service_ids_truncated": services_truncated,
        }

    @classmethod
    def _classify_service_sources(
            cls, service_sources: Optional[Iterable[Any]]) -> str:
        def get_source(value: Any) -> Any:
            if isinstance(value, dict):
                return value.get("service_source")
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                return value
            return getattr(value, "service_source", None)

        deploy_types = {
            cls.SOURCE_TYPE_MAP.get(str(get_source(source) or "").strip().lower(),
                                    "mixed")
            for source in (service_sources or [])
        }
        if len(deploy_types) == 1:
            return next(iter(deploy_types))
        return "mixed"

    @staticmethod
    def _parse_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on")
        return bool(value)

    @staticmethod
    def _standard_id(value: Any, key: str) -> Any:
        if isinstance(value, dict):
            value = value.get(key)
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return None
        return value

    def __init__(self,
                 repo: Any = None,
                 region_api_client: Any = None,
                 transport: Any = None,
                 clock: Optional[Callable[[], datetime.datetime]] = None,
                 sleep: Optional[Callable[[float], None]] = None,
                 thread_factory: Any = None,
                 start_sweeper: Optional[bool] = None) -> None:
        self.repo = repo or rainskills_deployment_repo
        self.region_api = region_api_client or RegionInvokeApi()
        self.transport = transport or requests
        self.clock = clock or (
            lambda: datetime.datetime.now(datetime.timezone.utc))
        self.sleep = sleep or time.sleep
        self.thread_factory = thread_factory or threading.Thread
        self.report_url = os.getenv("RAINSKILLS_DEPLOY_REPORT_URL",
                                    self.DEFAULT_REPORT_URL)
        self._running_keys = set()
        self._lock = threading.Lock()
        if start_sweeper is None:
            start_sweeper = os.getenv("DISABLE_RAINSKILLS_DEPLOY_SWEEPER",
                                      "") != "1"
        if start_sweeper:
            self._start_sweeper()

    def begin_tracking(self,
                       client: str,
                       tool: str,
                       deploy_type: str,
                       deploy_stage: str,
                       trigger: str,
                       enterprise_id: str = "",
                       tenant_name: str = "",
                       region_name: str = "",
                       app_id: int = 0,
                       resource_created: bool = False,
                       source_language: str = "") -> dict:
        now = self._now()
        attempt_id = uuid.uuid4().hex
        eid = str(enterprise_id or "").strip() or self._fallback_eid(
            tenant_name, region_name)
        normalized_deploy_stage = str(
            deploy_stage).strip() if deploy_stage else "initial"
        if not normalized_deploy_stage:
            normalized_deploy_stage = "initial"
        payload = {
            "deploy_attempt_id": attempt_id,
            "eid": eid,
            "deploy_client": str(client or "unknown").strip() or "unknown",
            "tool_name": str(tool or "unknown").strip() or "unknown",
            "deploy_type": str(deploy_type or "mixed").strip() or "mixed",
            "deploy_stage": normalized_deploy_stage,
            "trigger": str(trigger or "unknown").strip() or "unknown",
            "source_language": str(source_language or "").strip(),
            "resource_created": bool(resource_created),
            "app_id": self._normalize_app_id(app_id),
            "service_ids": [],
            "event_ids": [],
            "service_count": 0,
            "event_count": 0,
            "service_ids_truncated": False,
            "event_ids_truncated": False,
            "report_phase": "dispatch",
            "status": "accepted",
            "deploy_result_at": now,
            "failure_stage": "",
            "failure_category": "",
            "failure_reason": "",
            "tenant_name": str(tenant_name or ""),
            "region_name": str(region_name or ""),
            "created_at": now,
            "local_state": self.LOCAL_STATE_AWAITING_RESULT,
        }
        record, _created = self.repo.create_attempt(eid, attempt_id, payload)
        return {"key": record.key, "deploy_attempt_id": attempt_id, "eid": eid}

    def safe_begin_tracking(self, *args: Any, **kwargs: Any) -> Optional[dict]:
        try:
            return self.begin_tracking(*args, **kwargs)
        except Exception as exc:
            logger.warning("begin RainSkills deployment tracking failed: %s",
                           exc)
            return None

    def bind_events(self, tracker: Optional[dict], event_ids: Iterable[Any],
                    service_ids: Iterable[Any]) -> None:
        record, payload = self._load_tracker(tracker)
        if not record:
            return
        events, event_count, events_truncated = self._normalize_ids(event_ids)
        services, service_count, services_truncated = self._normalize_ids(
            service_ids)
        self._bind_normalized_result(
            record, payload, {
                "app_id": 0,
                "event_ids": events,
                "event_count": event_count,
                "event_ids_truncated": events_truncated,
                "service_ids": services,
                "service_count": service_count,
                "service_ids_truncated": services_truncated,
            })

    def bind_tool_result(self, tracker: Optional[dict], result: Any) -> None:
        normalized = self.normalize_tool_result(result)
        if normalized["is_deploy"] is False:
            self.discard_tracking(tracker)
            return
        record, payload = self._load_tracker(tracker)
        if not record:
            return
        self._bind_normalized_result(record, payload, normalized)

    def safe_bind_tool_result(self, tracker: Optional[dict], result: Any) -> None:
        try:
            self.bind_tool_result(tracker, result)
        except Exception as exc:
            logger.warning("bind RainSkills deployment tool result failed: %s",
                           exc)

    def discard_tracking(self, tracker: Optional[dict]) -> None:
        record, payload = self._load_tracker(tracker)
        if record and payload.get(
                "local_state") == self.LOCAL_STATE_AWAITING_RESULT:
            self.repo.delete_payload(record)

    def safe_discard_tracking(self, tracker: Optional[dict]) -> None:
        try:
            self.discard_tracking(tracker)
        except Exception as exc:
            logger.warning("discard RainSkills deployment tracker failed: %s",
                           exc)

    def _bind_normalized_result(self, record: Any, payload: dict,
                                normalized: dict) -> None:
        app_id = self._normalize_app_id(normalized.get("app_id"))
        payload.update({
            "event_ids": normalized.get("event_ids") or [],
            "event_count": normalized.get("event_count") or 0,
            "event_ids_truncated": bool(
                normalized.get("event_ids_truncated")),
            "service_ids": normalized.get("service_ids") or [],
            "service_count": normalized.get("service_count") or 0,
            "service_ids_truncated": bool(
                normalized.get("service_ids_truncated")),
            "report_phase": "dispatch",
            "status": "accepted",
            "deploy_result_at": self._now(),
            "failure_stage": "",
            "failure_category": "",
            "failure_reason": "",
            "local_state": self.LOCAL_STATE_BOUND,
        })
        if app_id:
            payload["app_id"] = app_id
        self.repo.update_payload(record, payload)
        self._start_worker(record.key)

    def safe_bind_events(self, tracker: Optional[dict],
                         event_ids: Iterable[Any],
                         service_ids: Iterable[Any]) -> None:
        try:
            self.bind_events(tracker, event_ids, service_ids)
        except Exception as exc:
            logger.warning("bind RainSkills deployment events failed: %s", exc)

    def mark_failure(self,
                     tracker: Optional[dict],
                     reason: str = "",
                     failure_stage: str = "",
                     failure_category: str = "") -> None:
        record, payload = self._load_tracker(tracker)
        if not record:
            return
        self._set_final(
            record,
            payload,
            "failure",
            failure_stage=failure_stage or "unknown",
            failure_category=failure_category or "unknown",
            failure_reason=reason or "deployment failed",
        )
        self._start_worker(record.key)

    def safe_mark_failure(self,
                          tracker: Optional[dict],
                          reason: str = "",
                          failure_stage: str = "",
                          failure_category: str = "") -> None:
        try:
            self.mark_failure(tracker, reason, failure_stage, failure_category)
        except Exception as exc:
            logger.warning("mark RainSkills deployment failure failed: %s",
                           exc)

    def _load_tracker(self, tracker: Optional[dict]) -> Tuple[Any, dict]:
        key = tracker.get("key") if isinstance(tracker, dict) else ""
        record = self.repo.get_by_key(key)
        return record, self.repo.load_payload(record)

    def _start_worker(self, key: str) -> None:
        if not key:
            return
        with self._lock:
            if key in self._running_keys:
                return
            self._running_keys.add(key)
        try:
            worker = self.thread_factory(target=self._worker_entry,
                                         args=(key, ))
            worker.daemon = True
            worker.start()
        except Exception:
            with self._lock:
                self._running_keys.discard(key)
            raise

    def _worker_entry(self, key: str) -> None:
        try:
            self._poll_by_key(key)
        finally:
            with self._lock:
                self._running_keys.discard(key)

    def _poll_by_key(self, key: str) -> None:
        dispatch_attempted = False
        while True:
            record = self.repo.get_by_key(key)
            payload = self.repo.load_payload(record)
            if not record or not payload:
                return
            if payload.get("report_phase") == "final":
                self._report_final(record, payload)
                return
            if payload.get("local_state") != self.LOCAL_STATE_BOUND:
                return
            event_ids = payload.get("event_ids") or []
            if not dispatch_attempted:
                dispatch_sent = self._post_report_payload(payload)
                dispatch_attempted = True
                if not event_ids:
                    if dispatch_sent:
                        self.repo.delete_payload(record)
                    return
            if self._elapsed_seconds(
                    payload.get("created_at")) >= self.POLL_WINDOW_SECONDS:
                self._set_final(
                    record,
                    payload,
                    "timeout",
                    failure_stage="poll",
                    failure_category="poll_timeout",
                    failure_reason="deployment event polling timed out",
                )
                self._report_final(record, payload)
                return
            try:
                body = self.region_api.get_tenant_events(
                    payload.get("region_name", ""),
                    payload.get("tenant_name", ""),
                    event_ids,
                )
                status, failure = self._evaluate_events(body, event_ids)
            except Exception as exc:
                logger.warning("poll RainSkills deployment events failed: %s",
                               exc)
                self.sleep(self.POLL_INTERVAL_SECONDS)
                continue
            if status == "pending":
                self.sleep(self.POLL_INTERVAL_SECONDS)
                continue
            self._set_final(record, payload, status, **failure)
            self._report_final(record, payload)
            return

    def _evaluate_events(
            self, body: Any,
            event_ids: Iterable[str]) -> Tuple[str, Dict[str, str]]:
        events = body.get("list", []) if isinstance(body, dict) else []
        events = events if isinstance(events, list) else []
        expected_ids = set(event_ids)
        observed_ids = set()
        statuses = []
        for event in events:
            if not isinstance(event, dict):
                continue
            event_id = str(event.get("event_id") or event.get("EventID") or "")
            if event_id:
                observed_ids.add(event_id)
            status_value = event.get("status") or event.get("Status")
            status = str(status_value or "").strip().lower()
            statuses.append((status, event))
        for status, event in statuses:
            if status in self.FAILURE_STATUSES:
                return "failure", self._failure_details(event, "failure")
        for status, event in statuses:
            if status in self.TIMEOUT_STATUSES:
                return "timeout", self._failure_details(event, "timeout")
        if expected_ids and expected_ids.issubset(
                observed_ids) and statuses and all(
                    status in self.SUCCESS_STATUSES
                    for status, _event in statuses):
            return "success", {}
        return "pending", {}

    def _failure_details(self, event: dict, status: str) -> Dict[str, str]:
        opt_type_value = event.get("opt_type") or event.get("OptType")
        opt_type = str(opt_type_value or "").lower()
        stage_value = event.get("failure_stage") or event.get("stage")
        stage = str(stage_value or "").strip().lower()
        if not stage:
            if "build" in opt_type or "compile" in opt_type:
                stage = "build"
            elif "runtime" in opt_type or "container" in opt_type:
                stage = "runtime"
            else:
                stage = "poll"
        category_value = event.get("failure_category") or event.get("category")
        category = str(category_value or "").strip().lower()
        if not category:
            category = "event_timeout" if status == "timeout" else "event_failed"
        reason = event.get("reason") or event.get("Reason") or event.get(
            "message") or event.get("Message")
        failure_reason = reason or "deployment event {}".format(status)
        return {
            "failure_stage": self._sanitize_text(stage, 32),
            "failure_category": self._sanitize_text(category, 64),
            "failure_reason": self._sanitize_reason(failure_reason),
        }

    def _set_final(self,
                   record: Any,
                   payload: dict,
                   status: str,
                   failure_stage: str = "",
                   failure_category: str = "",
                   failure_reason: str = "") -> None:
        payload.update({
            "report_phase":
            "final",
            "status":
            status,
            "deploy_result_at":
            self._now(),
            "failure_stage":
            self._sanitize_text(failure_stage, 32)
            if status != "success" else "",
            "failure_category":
            self._sanitize_text(failure_category, 64)
            if status != "success" else "",
            "failure_reason":
            self._sanitize_reason(failure_reason)
            if status != "success" else "",
        })
        self.repo.update_payload(record, payload)

    def _report_final(self, record: Any, payload: dict) -> bool:
        if self._post_report_payload(payload):
            self.repo.delete_payload(record)
            return True
        return False

    def sweep_once(self) -> None:
        for record in list(self.repo.list_tracking_records()):
            try:
                payload = self.repo.load_payload(record)
                if self._elapsed_seconds(payload.get(
                        "created_at")) > self.MAX_RETENTION_SECONDS:
                    logger.warning(
                        "delete expired RainSkills deployment tracker: key=%s",
                        record.key)
                    self.repo.delete_payload(record)
                elif payload.get("report_phase") == "final" or payload.get(
                        "local_state") == self.LOCAL_STATE_BOUND:
                    self._start_worker(record.key)
            except Exception as exc:
                logger.warning(
                    "sweep RainSkills deployment tracker failed: key=%s error=%s",
                    record.key, exc)

    def _start_sweeper(self) -> None:
        worker = self.thread_factory(target=self._sweeper_loop)
        worker.daemon = True
        worker.start()

    def _sweeper_loop(self) -> None:
        while True:
            self.sleep(self.SWEEPER_INTERVAL_SECONDS)
            try:
                self.sweep_once()
            except Exception as exc:
                logger.warning("RainSkills deployment sweeper failed: %s", exc)

    def _post_report_payload(self, payload: dict) -> bool:
        report_payload = self._build_report_payload(payload)
        for attempt in range(3):
            try:
                response = self.transport.post(self.report_url,
                                               json=report_payload,
                                               timeout=5)
                if 200 <= int(response.status_code) < 300:
                    return True
                logger.warning(
                    "report RainSkills deployment failed: status=%s",
                    response.status_code)
            except Exception as exc:
                logger.warning("report RainSkills deployment failed: %s", exc)
            if attempt < 2:
                self.sleep(1)
        return False

    def _build_report_payload(self, payload: dict) -> dict:
        result = {field: payload.get(field) for field in self.REPORT_FIELDS}
        result["deploy_result_at"] = self._valid_report_time(
            result.get("deploy_result_at"))
        return result

    def _valid_report_time(self, value: Any) -> str:
        parsed = self._parse_time(value)
        if not parsed or parsed.year < 1000 or parsed.year > 9999:
            parsed = self.clock()
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.isoformat()

    def _elapsed_seconds(self, value: Any) -> float:
        parsed = self._parse_time(value)
        if not parsed:
            return self.MAX_RETENTION_SECONDS + 1
        now = self.clock()
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)
        return max(0.0, (now - parsed).total_seconds())

    @staticmethod
    def _parse_time(value: Any) -> Optional[datetime.datetime]:
        if isinstance(value, datetime.datetime):
            return value
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(
                str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None

    def _now(self) -> str:
        value = self.clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.isoformat()

    @staticmethod
    def _fallback_eid(tenant_name: str, region_name: str) -> str:
        seed = "{}|{}".format(
            str(tenant_name or "").strip(),
            str(region_name or "").strip())
        return uuid.uuid5(uuid.NAMESPACE_URL,
                          "rainskills-deployment:{}".format(seed)).hex

    @classmethod
    def _normalize_ids(cls, values: Iterable[Any]) -> Tuple[list, int, bool]:
        normalized = sorted({
            str(value).strip()
            for value in (values or [])
            if value is not None and str(value).strip()
        })
        count = len(normalized)
        return normalized[:cls.MAX_IDS], count, count > cls.MAX_IDS

    @staticmethod
    def _normalize_app_id(app_id: Any) -> int:
        try:
            return max(0, int(app_id or 0))
        except (TypeError, ValueError):
            return 0

    def _sanitize_reason(self, value: Any) -> str:
        return self._sanitize_text(value, self.MAX_FAILURE_REASON_LENGTH)

    def _sanitize_text(self, value: Any, limit: int) -> str:
        text = str(value or "")
        text = self.URL_CREDENTIAL_RE.sub(r"\1[Filtered]@", text)
        text = self.AUTH_TOKEN_RE.sub(r"\1 [Filtered]", text)
        text = self.ACCESS_TOKEN_RE.sub(r"\1 [Filtered]", text)
        text = self.SENSITIVE_QUOTED_ASSIGNMENT_RE.sub(
            self._redact_quoted_assignment, text)
        text = self.SENSITIVE_BARE_ASSIGNMENT_RE.sub(
            self._redact_bare_assignment, text)
        return self._bounded_text(text, limit)

    @staticmethod
    def _redact_quoted_assignment(match: Any) -> str:
        key_quote = match.group("key_quote")
        value_quote = match.group("value_quote")
        return "{}{}{}{}{}[Filtered]{}".format(
            key_quote,
            match.group("key"),
            key_quote,
            match.group("separator"),
            value_quote,
            value_quote,
        )

    @staticmethod
    def _redact_bare_assignment(match: Any) -> str:
        key_quote = match.group("key_quote")
        return "{}{}{}{}[Filtered]".format(
            key_quote,
            match.group("key"),
            key_quote,
            match.group("separator"),
        )

    @staticmethod
    def _bounded_text(value: Any, limit: int) -> str:
        return str(value or "").strip()[:limit]


rainskills_deployment_service = RainSkillsDeploymentService()
