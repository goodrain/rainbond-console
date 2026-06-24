# -*- coding: utf-8 -*-
import logging
import os
import re
import uuid
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple

import requests

from console.models.main import ConsoleSysConfig
from console.repositories.first_deploy_repo import enterprise_first_deploy_repo
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantEnterprise

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class EnterpriseFirstDeployService(object):
    REPORT_URL = os.getenv("FIRST_DEPLOY_REPORT_URL", "https://log.rainbond.com/api/enterprise/first-deploy")
    PAYLOAD_VERSION = 3
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"
    FINAL_STATUSES = {STATUS_SUCCESS, STATUS_FAILURE}
    STAGE_STATUS_PENDING = "pending"
    STAGE_STATUS_TIMEOUT = "timeout"
    STAGE_STATUS_SKIPPED = "skipped"
    STAGE_FINAL_STATUSES = {STATUS_SUCCESS, STATUS_FAILURE, STAGE_STATUS_TIMEOUT, STAGE_STATUS_SKIPPED}
    POLL_INTERVAL = 5
    POLL_TIMEOUT = 60 * 20
    DEPLOY_TYPE_SOURCE_CODE = "source_code"
    DEPLOY_TYPE_APP_MARKET = "app_market"
    DEPLOY_TYPE_IMAGE = "image"
    FAILURE_STAGE_SOURCE_CHECK = "source_check"
    FAILURE_STAGE_BUILD = "build"
    FAILURE_STAGE_RUNTIME = "runtime"
    FAILURE_STAGE_UNKNOWN = "unknown"
    FAILURE_CATEGORY_SOURCE_FETCH_TIMEOUT = "source_fetch_timeout"
    FAILURE_CATEGORY_SOURCE_AUTH_FAILED = "source_auth_failed"
    FAILURE_CATEGORY_SOURCE_REPO_UNREACHABLE = "source_repo_unreachable"
    FAILURE_CATEGORY_SOURCE_BRANCH_MISSING = "source_branch_missing"
    FAILURE_CATEGORY_COMPILE_FAILED = "compile_failed"
    FAILURE_CATEGORY_IMAGE_PULL_FAILED = "image_pull_failed"
    FAILURE_CATEGORY_IMAGE_PUSH_FAILED = "image_push_failed"
    FAILURE_CATEGORY_VERSION_INFO_FAILED = "version_info_failed"
    FAILURE_CATEGORY_RUNTIME_TIMEOUT = "runtime_timeout"
    FAILURE_CATEGORY_POD_CRASH_LOOP = "pod_crash_loop"
    FAILURE_CATEGORY_NO_AVAILABLE_NODES = "no_available_nodes"
    FAILURE_CATEGORY_UNKNOWN = "unknown"
    LOG_COLLECT_STATUS_COLLECTED = "event_log_collected"
    LOG_COLLECT_STATUS_EMPTY_AFTER_RETRY = "event_log_empty_after_retry"
    LOG_COLLECT_STATUS_API_ERROR = "event_log_api_error"
    LOG_COLLECT_STATUS_NO_EVENT_ID = "no_event_id"
    LOG_COLLECT_STATUS_PROVIDED = "provided"
    EVENT_LOG_FALLBACK_LEVELS = ("debug", "info", "error")
    MAX_FAILURE_EVENTS = 20
    MAX_FAILURE_LOG_LINES = 50
    MAX_BUILD_FAILURE_LOG_LINES = 1000
    MAX_FAILURE_LOG_LINE_LENGTH = 4096
    MAX_FAILURE_REASON_LENGTH = 1024
    RUNTIME_OBSERVE_WINDOW = 60
    READINESS_FINAL_OBSERVE_WINDOW = 180
    BUILD_FAILURE_LOG_WAIT_WINDOW = 60
    COMPILE_FAILURE_LOG_WAIT_WINDOW = 180
    BUILD_FAILURE_LOG_RETRY_INTERVAL = 5
    RUNTIME_EVENT_QUERY_SIZE = 20
    RESUME_INTERVAL = 15
    BUILD_OPT_KEYWORDS = ("build", "slug", "package")
    RUNTIME_OPT_KEYWORDS = ("start", "deploy", "upgrade", "rollback", "restart", "run")
    POD_RUNTIME_FAILURE_REASONS = {
        "imagepullbackoff",
        "errimagepull",
        "crashloopbackoff",
        "createcontainerconfigerror",
        "oomkilled",
        "containerexiterror",
        "abnormalexited",
        "readinessprobefailed",
        "livenessprobefailed",
        "startupprobefailure",
        "failedscheduling",
    }
    # Probe/readiness failures during startup are transient — wait for the observe window before reporting
    SOFT_FAILURE_OPT_TYPES = {
        "readinessprobefailed",
        "livenessprobefailed",
        "startupprobefailure",
        "containersnotready",
    }
    RUNTIME_FAILURE_OPT_TYPES = {
        "containerexiterror",
        "crashloopbackoff",
        "oomkilled",
        "abnormalexited",
        "livenessprobefailed",
        "readinessprobefailed",
        "imagepullbackoff",
        "createcontainerconfigerror",
        "evicted",
        "readinessunhealthy",
        "startupprobefailure",
        "livenessrestart",
        "initiating",
    }
    SENSITIVE_QUOTED_ASSIGNMENT_RE = re.compile(
        r"\b((?:password|passwd|pwd|token|secret|authorization|api[_-]?key))(\s*[:=]\s*)([\"'])(.*?)(\3)",
        re.IGNORECASE)
    SENSITIVE_BARE_ASSIGNMENT_RE = re.compile(
        r"\b((?:password|passwd|pwd|token|secret|authorization|api[_-]?key))(\s*[:=]\s*)([^,\s\"';&]+)",
        re.IGNORECASE)
    AUTH_TOKEN_RE = re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
    URL_CREDENTIAL_RE = re.compile(r"(https?://)[^:/\s]+:[^@\s]+@", re.IGNORECASE)

    def __init__(self) -> None:
        self._running_keys = set()  # type: set
        self._reporting_keys = set()  # type: set
        self._lock = threading.Lock()
        self.report_async = True
        if os.getenv("DISABLE_FIRST_DEPLOY_SWEEPER") != "1":
            sweeper = threading.Thread(target=self._resume_pending_trackers_loop)
            sweeper.daemon = True
            sweeper.start()

    def begin_tracking(self,
                       enterprise_id: str,
                       tenant_name: str,
                       region_name: str,
                       deploy_type: str,
                       operator: str = "",
                       source_language: str = "",
                       service_id: str = "",
                       service_alias: str = "",
                       service: Any = None,
                       trigger: str = "",
                       app_context: Optional[dict] = None,
                       workload_context: Optional[dict] = None) -> Optional[dict]:
        existing_record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if existing_record:
            existing = enterprise_first_deploy_repo.load_payload(existing_record)
            if self._first_deploy_finished(existing):
                self._report_if_needed(existing_record, existing, async_report=True)
                return None
            if existing.get("status") == self.STATUS_PENDING and not existing.get("event_ids") and self._is_expired(existing):
                self._set_stage_failure(existing, self.FAILURE_STAGE_BUILD)
                self._complete_tracking(existing_record, existing, self.STATUS_FAILURE)
            self._report_if_needed(existing_record, existing, async_report=True)
            if existing.get("status") == self.STATUS_PENDING and existing.get("event_ids"):
                transaction.on_commit(lambda: self._start_sync_thread(existing_record.key, tenant_name, region_name))
            return None

        payload = self._build_payload(
            enterprise_id=enterprise_id,
            tenant_name=tenant_name,
            region_name=region_name,
            deploy_type=deploy_type,
            operator=operator,
            source_language=source_language,
            service_id=service_id,
            service_alias=service_alias,
            service=service,
            trigger=trigger,
            app_context=app_context,
            workload_context=workload_context,
        )
        record, created = enterprise_first_deploy_repo.create_if_absent(enterprise_id, payload)
        if not created:
            existing = enterprise_first_deploy_repo.load_payload(record)
            if self._first_deploy_finished(existing):
                self._report_if_needed(record, existing, async_report=True)
                return None
            if existing.get("status") == self.STATUS_PENDING and not existing.get("event_ids") and self._is_expired(existing):
                self._set_stage_failure(existing, self.FAILURE_STAGE_BUILD)
                self._complete_tracking(record, existing, self.STATUS_FAILURE)
            self._report_if_needed(record, existing, async_report=True)
            if existing.get("status") == self.STATUS_PENDING and existing.get("event_ids"):
                transaction.on_commit(lambda: self._start_sync_thread(record.key, tenant_name, region_name))
            return None
        tracker = {
            "enterprise_id": enterprise_id,
            "key": record.key,
            "tenant_name": tenant_name,
            "region_name": region_name,
            "service_id": payload.get("deployment_context", {}).get("service_id") or "",
            "service_alias": payload.get("deployment_context", {}).get("service_alias") or "",
        }
        transaction.on_commit(lambda: self._start_environment_collect_thread(record.key, enterprise_id, region_name))
        return tracker

    def safe_begin_tracking(self, *args: Any, **kwargs: Any) -> Optional[dict]:
        try:
            return self.begin_tracking(*args, **kwargs)
        except Exception as exc:
            logger.debug("begin deploy diagnostic tracking failed: %s", exc)
            return None

    def safe_bind_events(self, tracker: Optional[dict], *args: Any, **kwargs: Any) -> None:
        try:
            self.bind_events(tracker, *args, **kwargs)
        except Exception as exc:
            logger.debug("bind deploy diagnostic events failed: %s", exc)

    def safe_mark_success(self, tracker: Optional[dict]) -> None:
        try:
            self.mark_success(tracker)
        except Exception as exc:
            logger.debug("mark deploy diagnostic success failed: %s", exc)

    def safe_mark_failure(self, tracker: Optional[dict], reason: str = "", failure_stage: str = "") -> None:
        try:
            self.mark_failure(tracker, reason=reason, failure_stage=failure_stage)
        except Exception as exc:
            logger.debug("mark deploy diagnostic failure failed: %s", exc)

    def safe_report_source_check_failure(self, *args: Any, **kwargs: Any) -> None:
        try:
            kwargs.setdefault("async_report", True)
            self.report_source_check_failure(*args, **kwargs)
        except Exception as exc:
            logger.debug("report source check diagnostic failed: %s", exc)

    def report_source_check_failure(
            self,
            enterprise_id: str,
            tenant_name: str,
            region_name: str,
            reason: str,
            service: Any = None,
            operator: str = "",
            app_context: Optional[dict] = None,
            source_context: Optional[dict] = None,
            async_report: bool = False) -> None:
        existing_record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if existing_record:
            existing = enterprise_first_deploy_repo.load_payload(existing_record)
            if self._first_deploy_finished(existing):
                self._report_if_needed(existing_record, existing, async_report=async_report)
                return
            record = existing_record
        else:
            record = None
        payload = self._build_payload(
            enterprise_id=enterprise_id,
            tenant_name=tenant_name,
            region_name=region_name,
            deploy_type=self.DEPLOY_TYPE_SOURCE_CODE,
            operator=operator,
            source_language=getattr(service, "language", "") or "",
            service_id=getattr(service, "service_id", "") or "",
            service_alias=getattr(service, "service_alias", "") or "",
            service=service,
            trigger=self.FAILURE_STAGE_SOURCE_CHECK,
            app_context=self._merge_source_context(enterprise_id, app_context or {}, source_context or {}),
        )
        source_check_id = (source_context or {}).get("check_uuid")
        if source_check_id:
            payload["deployment_context"]["deploy_attempt_id"] = str(source_check_id)
        failed_event = self._build_source_check_event(payload, reason, source_context or {})
        payload["event_ids"] = [failed_event["event_id"]] if failed_event.get("event_id") else []
        payload["service_ids"] = [failed_event["service_id"]] if failed_event.get("service_id") else payload.get("service_ids", [])
        self._set_stage_failure(
            payload,
            self.FAILURE_STAGE_SOURCE_CHECK,
            failed_events=[failed_event],
            reason=reason,
            failure_logs=[self._build_source_check_diagnostic_log(payload, failed_event, reason)])
        payload["status"] = self.STATUS_FAILURE
        payload["finished_at"] = self._now()
        if record is None:
            record, created = enterprise_first_deploy_repo.create_if_absent(enterprise_id, payload)
            if not created:
                existing = enterprise_first_deploy_repo.load_payload(record)
                if self._first_deploy_finished(existing):
                    return
        else:
            enterprise_first_deploy_repo.update_payload(record, payload)
        self._report_if_needed(record, payload, async_report=async_report)

    def _resume_legacy_enterprise_record(self, enterprise_id: str, tenant_name: str, region_name: str) -> None:
        record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") == self.STATUS_PENDING and not payload.get("event_ids") and self._is_expired(payload):
            self._set_stage_failure(payload, self.FAILURE_STAGE_BUILD)
            self._complete_tracking(record, payload, self.STATUS_FAILURE)
        self._report_if_needed(record, payload, async_report=True)
        if payload.get("status") == self.STATUS_PENDING and payload.get("event_ids"):
            transaction.on_commit(lambda: self._start_sync_thread(record.key, tenant_name, region_name))

    def _first_deploy_finished(self, payload: dict) -> bool:
        return payload.get("status") in self.FINAL_STATUSES

    def bind_events(self,
                    tracker: Optional[dict],
                    event_ids: Any,
                    service_ids: Any = None,
                    service_alias: Optional[str] = None,
                    service_aliases: Any = None) -> None:
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_key(tracker.get("key")) or enterprise_first_deploy_repo.get_by_enterprise_id(
            tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return

        event_ids = [str(event_id) for event_id in (event_ids or []) if event_id]
        payload["event_ids"] = sorted(set(event_ids))
        if event_ids:
            payload["build_event_id"] = event_ids[0]
        tracker_service_id = tracker.get("service_id")
        if tracker_service_id and tracker_service_id not in payload.get("service_ids", []):
            payload.setdefault("service_ids", []).append(tracker_service_id)
        for sid in (service_ids or []):
            sid = str(sid)
            if sid and sid not in payload.get("service_ids", []):
                payload.setdefault("service_ids", []).append(sid)
        if service_alias and not payload.get("service_alias"):
            payload["service_alias"] = service_alias
        if service_aliases and not payload.get("service_aliases"):
            payload["service_aliases"] = [str(a) for a in service_aliases if a]
        if not payload["event_ids"]:
            self._mark_stage_success(payload, self.FAILURE_STAGE_BUILD, service_id=tracker_service_id)
            self._mark_stage_success(payload, self.FAILURE_STAGE_RUNTIME, service_id=tracker_service_id)
            self._complete_tracking(record, payload, self.STATUS_SUCCESS)
            return

        enterprise_first_deploy_repo.update_payload(record, payload)
        transaction.on_commit(lambda: self._start_sync_thread(record.key, tracker["tenant_name"], tracker["region_name"]))

    def mark_success(self, tracker: Optional[dict]) -> None:
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_key(tracker.get("key")) or enterprise_first_deploy_repo.get_by_enterprise_id(
            tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return
        self._mark_stage_success(payload, self.FAILURE_STAGE_BUILD)
        self._mark_stage_success(payload, self.FAILURE_STAGE_RUNTIME)
        self._complete_tracking(record, payload, self.STATUS_SUCCESS)

    def mark_failure(self, tracker: Optional[dict], reason: str = "", failure_stage: str = "") -> None:
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_key(tracker.get("key")) or enterprise_first_deploy_repo.get_by_enterprise_id(
            tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return
        stage = self._normalize_stage(failure_stage)
        self._set_stage_failure(
            payload,
            stage,
            tenant_name=payload.get("tenant_name"),
            region_name=payload.get("region_name"),
            reason=reason)
        self._complete_tracking(record, payload, self.STATUS_FAILURE)

    def sync_once(self, enterprise_id: str, tenant_name: str, region_name: str) -> Optional[str]:
        record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if not record:
            return None
        payload = enterprise_first_deploy_repo.load_payload(record)
        return self._sync_record(record, payload, tenant_name, region_name)

    def _build_payload(self,
                       enterprise_id: str,
                       tenant_name: str,
                       region_name: str,
                       deploy_type: str,
                       operator: str = "",
                       source_language: str = "",
                       service_id: str = "",
                       service_alias: str = "",
                       service: Any = None,
                       trigger: str = "",
                       app_context: Optional[dict] = None,
                       environment_context: Optional[dict] = None,
                       workload_context: Optional[dict] = None) -> dict:
        enterprise = TenantEnterprise.objects.filter(enterprise_id=enterprise_id).first()
        service_id = service_id or getattr(service, "service_id", "") or ""
        service_alias = service_alias or getattr(service, "service_alias", "") or ""
        service_source = getattr(service, "service_source", "") or self._service_source_from_deploy_type(deploy_type)
        component_name = getattr(service, "service_cname", "") or ""
        built_app_context = self._build_app_context(enterprise_id, app_context or {}, component_name)
        built_workload_context = self._build_workload_context(service, workload_context or {})
        payload = {
            "enterprise_id": enterprise_id,
            "enterprise_name": self._get_enterprise_name(enterprise),
            "deploy_type": deploy_type,
            "source_language": source_language if deploy_type == self.DEPLOY_TYPE_SOURCE_CODE else "",
            "payload_version": self.PAYLOAD_VERSION,
            "deployment_context": {
                "deploy_attempt_id": uuid.uuid4().hex,
                "trigger": trigger or "deploy",
                "deploy_type": deploy_type,
                "service_source": service_source,
                "service_id": service_id,
                "service_alias": service_alias,
                "component_name_hash": self._hash_identifier(enterprise_id, component_name) if component_name else "",
            },
            "app_context": built_app_context,
            "environment_context": environment_context or {"collect_status": "pending"},
            "workload_context": built_workload_context,
            "status": self.STATUS_PENDING,
            "reported": False,
            "reported_at": "",
            "started_at": self._now(),
            "finished_at": "",
            "tenant_name": tenant_name,
            "region_name": region_name,
            "operator": operator or "",
            "event_ids": [],
            "service_ids": [service_id] if service_id else [],
            "service_alias": service_alias or "",
            "service_aliases": [],
            "build_status": self.STAGE_STATUS_PENDING,
            "build_started_at": self._now(),
            "build_finished_at": "",
            "build_event_id": "",
            "build_failure_reason": "",
            "build_failure_events": [],
            "build_failure_logs": [],
            "runtime_status": self.STAGE_STATUS_PENDING,
            "runtime_started_at": "",
            "runtime_finished_at": "",
            "runtime_event_id": "",
            "runtime_failure_reason": "",
            "runtime_failure_events": [],
            "runtime_failure_logs": [],
            "runtime_watch_started_at": "",
            "failure_stage": "",
            "failure_reason": "",
            "failure_category": "",
            "log_collect_status": "",
            "failure_events": [],
            "failure_logs": [],
        }
        return payload

    def _merge_source_context(self, enterprise_id: str, app_context: dict, source_context: dict) -> dict:
        if not source_context:
            return app_context
        merged = dict(app_context or {})
        merged["source_context"] = self._sanitize_source_context(enterprise_id, source_context)
        return merged

    def _sanitize_source_context(self, enterprise_id: str, source_context: dict) -> dict:
        git_url = source_context.get("git_url") or ""
        parsed = urlparse(git_url)
        sanitized = {
            "server_type": source_context.get("server_type", ""),
            "code_version": source_context.get("code_version", ""),
            "check_uuid": source_context.get("check_uuid", ""),
            "repo_host": parsed.hostname or parsed.netloc or "",
        }
        if git_url:
            sanitized["repo_url_hash"] = self._hash_identifier(enterprise_id, git_url)
        return sanitized

    def _build_source_check_event(self, payload: dict, reason: str, source_context: dict) -> dict:
        deployment_context = payload.get("deployment_context") or {}
        source_context = self._sanitize_source_context(payload.get("enterprise_id") or "", source_context)
        return {
            "event_id": source_context.get("check_uuid") or deployment_context.get("deploy_attempt_id", ""),
            "service_id": deployment_context.get("service_id", ""),
            "opt_type": "source-check",
            "status": self.STATUS_FAILURE,
            "final_status": "complete",
            "message": self._shrink_text(reason, self.MAX_FAILURE_REASON_LENGTH),
            "reason": self._shrink_text(reason, self.MAX_FAILURE_REASON_LENGTH),
            "start_time": payload.get("started_at", ""),
            "end_time": self._now(),
            "source_context": source_context,
        }

    def _build_source_check_diagnostic_log(self, payload: dict, event: dict, reason: str) -> dict:
        deployment_context = payload.get("deployment_context") or {}
        source_context = event.get("source_context") or {}
        parts = [
            "failure_stage={}".format(self.FAILURE_STAGE_SOURCE_CHECK),
            "failure_category={}".format(self._detect_source_check_category(reason)),
            "component_alias={}".format(deployment_context.get("service_alias", "")),
            "repo_host={}".format(source_context.get("repo_host", "")),
            "code_version={}".format(source_context.get("code_version", "")),
            "reason={}".format(self._shrink_text(reason, self.MAX_FAILURE_REASON_LENGTH)),
        ]
        return {
            "stage": self.FAILURE_STAGE_SOURCE_CHECK,
            "event_id": event.get("event_id", ""),
            "source": "source_check",
            "failure_category": self._detect_source_check_category(reason),
            "log_collect_status": self.LOG_COLLECT_STATUS_PROVIDED,
            "truncated": False,
            "lines": [{"time": "", "message": "; ".join(parts)}],
        }

    def _sync_record(self, record: ConsoleSysConfig, payload: dict, tenant_name: str,
                     region_name: str) -> Optional[str]:
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return payload.get("status")

        event_ids = payload.get("event_ids") or []  # type: list
        if not event_ids:
            return None

        try:
            body = region_api.get_tenant_events(region_name, tenant_name, event_ids)
        except Exception as e:
            logger.exception("sync first deploy status failed: %s", e)
            return None

        # NOTE: potential latent None-bug — region_api.get_tenant_events returns
        # Optional[Dict]; if body is None this raises AttributeError at runtime
        # (currently unguarded). Preserving behavior, not fixing.
        events = body.get("list") or []  # type: ignore[union-attr]
        status_map = {}  # type: Dict[str, Any]
        for event in events:
            event_id = event.get("EventID") or event.get("event_id")
            status = event.get("Status") or event.get("status")
            if event_id and status:
                status_map[str(event_id)] = status

        failed_events = [
            event for event in [self._normalize_event_data(event) for event in events]
            if event.get("status") in (self.STATUS_FAILURE, "timeout")
        ]
        if failed_events:
            self._set_stage_failure(payload, self.FAILURE_STAGE_BUILD, tenant_name, region_name, failed_events=failed_events)
            self._complete_tracking(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

        if not status_map:
            if payload.get("build_status") == self.STATUS_SUCCESS:
                runtime_status = self._inspect_runtime_status(record, payload, tenant_name, region_name)
                if runtime_status == self.STATUS_FAILURE:
                    self._complete_tracking(record, payload, self.STATUS_FAILURE)
                    return self.STATUS_FAILURE
                if runtime_status == self.STATUS_SUCCESS:
                    self._complete_tracking(record, payload, self.STATUS_SUCCESS)
                    return self.STATUS_SUCCESS
            return None

        if len(status_map) < len(set(event_ids)):
            return None

        normalized = set(status_map.values())
        if normalized == {self.STATUS_SUCCESS}:
            build_service_id = self._merge_service_ids(payload, events)
            if payload.get("build_status") == self.STAGE_STATUS_PENDING:
                self._mark_stage_success(
                    payload,
                    self.FAILURE_STAGE_BUILD,
                    event_id=payload.get("build_event_id") or (event_ids[0] if event_ids else ""),
                    service_id=build_service_id)
                payload["runtime_started_at"] = self._now()
                payload["runtime_watch_started_at"] = payload["runtime_started_at"]
                enterprise_first_deploy_repo.update_payload(record, payload)
                return None

            runtime_status = self._inspect_runtime_status(record, payload, tenant_name, region_name)
            if runtime_status == self.STATUS_FAILURE:
                self._complete_tracking(record, payload, self.STATUS_FAILURE)
                return self.STATUS_FAILURE
            if runtime_status is None:
                return None
            self._complete_tracking(record, payload, self.STATUS_SUCCESS)
            return self.STATUS_SUCCESS

        if "timeout" in normalized:
            self._set_stage_failure(
                payload, self.FAILURE_STAGE_BUILD, tenant_name, region_name, stage_status=self.STAGE_STATUS_TIMEOUT)
            self._complete_tracking(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

        return None

    def _complete_tracking(self, record: ConsoleSysConfig, payload: dict, status: str) -> None:
        payload["status"] = status
        payload["finished_at"] = self._now()
        enterprise_first_deploy_repo.update_payload(record, payload)
        self._report_if_needed(record, payload, async_report=True)

    def _start_sync_thread(self, key: str, tenant_name: str, region_name: str) -> None:
        with self._lock:
            if key in self._running_keys:
                return
            self._running_keys.add(key)

        worker = threading.Thread(target=self._poll_until_finished, args=(key, tenant_name, region_name))
        worker.daemon = True
        worker.start()

    def _resume_pending_trackers_loop(self) -> None:
        while True:
            try:
                self._resume_pending_trackers_once()
            except Exception as e:
                logger.exception("resume first deploy trackers failed: %s", e)
            time.sleep(self.RESUME_INTERVAL)

    def _resume_pending_trackers_once(self) -> None:
        for record in enterprise_first_deploy_repo.list_tracking_records():
            payload = enterprise_first_deploy_repo.load_payload(record)
            if payload.get("status") != self.STATUS_PENDING:
                continue
            tenant_name = payload.get("tenant_name")
            region_name = payload.get("region_name")
            if not tenant_name or not region_name:
                continue
            if not payload.get("event_ids") and not payload.get("runtime_watch_started_at"):
                continue
            self._start_sync_thread(record.key, tenant_name, region_name)

    def _poll_until_finished(self, key: str, tenant_name: str, region_name: str) -> None:
        try:
            deadline = time.time() + self.POLL_TIMEOUT
            while time.time() < deadline:
                record = enterprise_first_deploy_repo.get_by_key(key)
                if not record:
                    time.sleep(self.POLL_INTERVAL)
                    continue
                payload = enterprise_first_deploy_repo.load_payload(record)
                try:
                    status = self._sync_record(record, payload, tenant_name, region_name)
                except Exception as e:
                    logger.exception("poll first deploy status failed: %s", e)
                    time.sleep(self.POLL_INTERVAL)
                    continue
                if status in self.FINAL_STATUSES:
                    return
                time.sleep(self.POLL_INTERVAL)

            record = enterprise_first_deploy_repo.get_by_key(key)
            if not record:
                return
            payload = enterprise_first_deploy_repo.load_payload(record)
            if payload.get("status") == self.STATUS_PENDING:
                stage = (
                    self.FAILURE_STAGE_BUILD
                    if payload.get("build_status") == self.STAGE_STATUS_PENDING else self.FAILURE_STAGE_RUNTIME)
                self._set_stage_failure(payload, stage, stage_status=self.STAGE_STATUS_TIMEOUT)
                self._complete_tracking(record, payload, self.STATUS_FAILURE)
        finally:
            with self._lock:
                self._running_keys.discard(key)

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _day() -> str:
        return datetime.now().strftime("%Y%m%d")

    def _is_expired(self, payload: dict) -> bool:
        started_at = payload.get("started_at")
        if not started_at:
            return False
        try:
            started = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False
        return (datetime.now() - started).total_seconds() >= self.POLL_TIMEOUT

    @staticmethod
    def _get_enterprise_name(enterprise: Optional[TenantEnterprise]) -> str:
        if not enterprise:
            return ""
        return enterprise.enterprise_alias or enterprise.enterprise_name or ""

    def _merge_service_ids(self, payload: dict, tracked_events: Any) -> str:
        service_ids = payload.get("service_ids") or []
        for event in tracked_events or []:
            service_id = (event.get("ServiceID") or event.get("service_id") or "")
            if service_id and service_id not in service_ids:
                service_ids.append(service_id)
        payload["service_ids"] = service_ids
        return service_ids[0] if service_ids else ""

    def _mark_stage_success(self, payload: dict, stage: str, event_id: str = "",
                            service_id: Optional[str] = "") -> None:
        now = self._now()
        payload["payload_version"] = self.PAYLOAD_VERSION
        payload["{}_status".format(stage)] = self.STATUS_SUCCESS
        payload["{}_finished_at".format(stage)] = now
        if not payload.get("{}_started_at".format(stage)):
            payload["{}_started_at".format(stage)] = now
        if event_id:
            payload["{}_event_id".format(stage)] = event_id
        if service_id and service_id not in payload.get("service_ids", []):
            payload.setdefault("service_ids", []).append(service_id)
        payload["{}_failure_reason".format(stage)] = ""
        payload["{}_failure_events".format(stage)] = []
        payload["{}_failure_logs".format(stage)] = []

    def _set_stage_failure(self,
                           payload: dict,
                           stage: str,
                           tenant_name: Optional[str] = "",
                           region_name: Optional[str] = "",
                           failed_events: Any = None,
                           reason: str = "",
                           stage_status: str = "",
                           failure_logs: Any = None) -> None:
        failed_events = failed_events or []
        now = self._now()
        payload["payload_version"] = self.PAYLOAD_VERSION
        payload["{}_status".format(stage)] = stage_status or self.STATUS_FAILURE
        payload["{}_finished_at".format(stage)] = now
        if not payload.get("{}_started_at".format(stage)):
            payload["{}_started_at".format(stage)] = now
        compact_events = self._shrink_failure_events(failed_events)
        payload["{}_failure_events".format(stage)] = compact_events
        payload["{}_failure_reason".format(stage)] = self._failure_reason_or_default(stage, failed_events, reason)
        failure_category = self._detect_failure_category(stage, compact_events, payload["{}_failure_reason".format(stage)])
        payload["{}_failure_category".format(stage)] = failure_category
        if compact_events:
            for event in compact_events:
                event["failure_category"] = failure_category
            payload["{}_event_id".format(stage)] = compact_events[0].get("event_id", "")
            service_id = compact_events[0].get("service_id", "")
            if service_id and service_id not in payload.get("service_ids", []):
                payload.setdefault("service_ids", []).append(service_id)
        if failure_logs is not None:
            payload["{}_failure_logs".format(stage)] = failure_logs
            payload["{}_log_collect_status".format(stage)] = self.LOG_COLLECT_STATUS_PROVIDED
        else:
            logs, log_collect_status = self._collect_failure_logs_with_status(
                tenant_name or payload.get("tenant_name"),
                region_name or payload.get("region_name"),
                failed_events,
                stage,
                failure_category,
                payload["{}_failure_reason".format(stage)],
                payload)
            payload["{}_failure_logs".format(stage)] = logs
            payload["{}_log_collect_status".format(stage)] = log_collect_status
        payload["failure_stage"] = stage
        payload["failure_reason"] = payload["{}_failure_reason".format(stage)]
        payload["failure_category"] = payload["{}_failure_category".format(stage)]
        payload["log_collect_status"] = payload["{}_log_collect_status".format(stage)]
        payload["failure_events"] = payload["{}_failure_events".format(stage)]
        payload["failure_logs"] = payload["{}_failure_logs".format(stage)]

    def _inspect_runtime_status(self, _record: ConsoleSysConfig, payload: dict, tenant_name: str,
                                region_name: str) -> Optional[str]:
        runtime_watch_started_at = payload.get("runtime_watch_started_at")
        if not runtime_watch_started_at:
            return None

        runtime_pod_status = self._inspect_runtime_pods(payload, tenant_name, region_name, runtime_watch_started_at)
        if runtime_pod_status == self.STATUS_FAILURE:
            return self.STATUS_FAILURE
        if runtime_pod_status == self.STATUS_SUCCESS:
            self._mark_stage_success(
                payload,
                self.FAILURE_STAGE_RUNTIME,
                service_id=(payload.get("service_ids") or [""])[0])
            return self.STATUS_SUCCESS
        if payload.get("service_alias") or payload.get("service_aliases"):
            if self._runtime_window_elapsed(runtime_watch_started_at):
                if self._is_soft_runtime_failure(payload) and not self._readiness_final_window_elapsed(runtime_watch_started_at):
                    return None
                failed_events, failure_logs, timeout_reason = self._collect_runtime_timeout_snapshot(
                    payload, tenant_name, region_name, runtime_watch_started_at)
                self._set_stage_failure(
                    payload,
                    self.FAILURE_STAGE_RUNTIME,
                    failed_events=payload.get("runtime_failure_events") or failed_events,
                    reason=payload.get("runtime_failure_reason") or timeout_reason,
                    stage_status=self.STAGE_STATUS_TIMEOUT,
                    failure_logs=payload.get("runtime_failure_logs") or failure_logs)
                return self.STATUS_FAILURE
            return None

        runtime_failed_events = self._list_runtime_failure_events(
            tenant_name,
            region_name,
            payload.get("service_ids") or [],
            runtime_watch_started_at)
        if runtime_failed_events:
            self._set_stage_failure(
                payload,
                self.FAILURE_STAGE_RUNTIME,
                tenant_name=tenant_name,
                region_name=region_name,
                failed_events=runtime_failed_events)
            return self.STATUS_FAILURE

        if self._runtime_window_elapsed(runtime_watch_started_at):
            failed_events, failure_logs, timeout_reason = self._collect_runtime_timeout_snapshot(
                payload, tenant_name, region_name, runtime_watch_started_at)
            self._set_stage_failure(
                payload,
                self.FAILURE_STAGE_RUNTIME,
                failed_events=payload.get("runtime_failure_events") or failed_events,
                reason=payload.get("runtime_failure_reason") or timeout_reason,
                stage_status=self.STAGE_STATUS_TIMEOUT,
                failure_logs=payload.get("runtime_failure_logs") or failure_logs)
            return self.STATUS_FAILURE
        return None

    def _collect_runtime_timeout_snapshot(self, payload: dict, tenant_name: str, region_name: str,
                                          runtime_watch_started_at: str) -> Tuple[list, list, str]:
        aliases = self._runtime_service_aliases(payload)
        service_id = self._first_service_id(payload)
        lines = []  # type: List[Dict[str, Any]]
        runtime_failed_events = self._list_runtime_failure_events(
            tenant_name,
            region_name,
            payload.get("service_ids") or [],
            runtime_watch_started_at)
        observed_pods = False
        missing_pods = False
        not_running = False
        containers_not_ready = False
        detail_unavailable = False

        if not aliases:
            reason = "runtime timeout: no service alias configured"
            lines.append({"time": "", "message": reason})
            return (
                [self._build_runtime_timeout_event(service_id, reason, runtime_watch_started_at)],
                self._build_runtime_snapshot_logs(lines),
                reason,
            )

        for service_alias in aliases:
            pods = self._get_service_pods_for_runtime(payload, tenant_name, region_name, service_alias)
            if not pods:
                missing_pods = True
                lines.append({
                    "time": "",
                    "message": "runtime timeout: no pods observed for service_alias {}".format(service_alias),
                })
                continue
            observed_pods = True
            candidate_pods = [pod for pod in pods if pod.get("_group") == "new_pods"] or pods
            for pod in candidate_pods:
                pod_name = pod.get("pod_name") or ""
                pod_status = pod.get("pod_status") or ""
                pod_detail = self._get_runtime_pod_detail(region_name, tenant_name, service_alias, pod_name)
                if not pod_detail:
                    detail_unavailable = True
                status_info = (pod_detail or {}).get("status") or {}
                detail_status = status_info.get("type_str") or ""
                status_reason = status_info.get("reason") or ""
                status_message = status_info.get("message") or ""
                if pod_status.upper() != "RUNNING" or (detail_status and detail_status.upper() != "RUNNING"):
                    not_running = True
                if self._is_soft_runtime_text(status_reason) or self._is_soft_runtime_text(status_message):
                    containers_not_ready = True
                lines.append({
                    "time": "",
                    "message": self._runtime_pod_snapshot_message(
                        service_alias, pod_name, pod_status, detail_status, status_reason, status_message),
                })
                self._append_runtime_detail_snapshot_lines(lines, service_alias, pod_name, pod_detail)

        if not observed_pods:
            reason = "runtime timeout: no pods observed"
        elif missing_pods:
            reason = "runtime timeout: some components have no pods observed"
        elif containers_not_ready:
            reason = "runtime timeout: containers not ready"
        elif not_running:
            reason = "runtime timeout: pods not running"
        elif detail_unavailable:
            reason = "runtime timeout: pod detail unavailable"
        else:
            reason = "runtime timeout: no diagnostic failure observed"
        self._append_runtime_event_snapshot_lines(lines, runtime_failed_events)
        return (
            runtime_failed_events or [self._build_runtime_timeout_event(service_id, reason, runtime_watch_started_at)],
            self._build_runtime_snapshot_logs(lines),
            reason,
        )

    def _runtime_service_aliases(self, payload: dict) -> list:
        aliases = []
        primary = payload.get("service_alias")
        if primary:
            aliases.append(primary)
        for alias in payload.get("service_aliases") or []:
            if alias and alias not in aliases:
                aliases.append(alias)
        return aliases

    @staticmethod
    def _first_service_id(payload: dict) -> str:
        return (payload.get("service_ids") or [""])[0]

    def _build_runtime_timeout_event(self, service_id: str, reason: str,
                                     runtime_watch_started_at: str) -> dict:
        now = self._now()
        return {
            "event_id": "runtime-timeout",
            "service_id": service_id or "",
            "opt_type": "RuntimeVerificationTimeout",
            "status": self.STAGE_STATUS_TIMEOUT,
            "final_status": "complete",
            "message": self._shrink_text(reason, self.MAX_FAILURE_REASON_LENGTH),
            "reason": self._shrink_text(reason, self.MAX_FAILURE_REASON_LENGTH),
            "start_time": runtime_watch_started_at or "",
            "end_time": now,
        }

    def _build_runtime_snapshot_logs(self, lines: list) -> list:
        normalized_lines, truncated = self._normalize_log_lines(lines)
        if not normalized_lines:
            return []
        return [{
            "stage": self.FAILURE_STAGE_RUNTIME,
            "event_id": "runtime-timeout",
            "source": "runtime_snapshot",
            "truncated": truncated,
            "lines": normalized_lines,
        }]

    def _runtime_pod_snapshot_message(self, service_alias: str, pod_name: str, pod_status: str, detail_status: str,
                                      status_reason: str, status_message: str) -> str:
        message = "service_alias {} pod {}: pod_status={}, detail_status={}".format(
            service_alias, pod_name or "-", pod_status or "-", detail_status or "-")
        if status_reason:
            message = "{} reason={}".format(message, status_reason)
        if status_message:
            message = "{} message={}".format(message, status_message)
        return message

    def _append_runtime_detail_snapshot_lines(self, lines: list, service_alias: str, pod_name: str,
                                              pod_detail: Any) -> None:
        for event in ((pod_detail or {}).get("events") or [])[:5]:
            message = event.get("message") or ""
            if message:
                lines.append({
                    "time": event.get("age") or "",
                    "message": "service_alias {} pod {} event {}: {}".format(
                        service_alias, pod_name or "-", event.get("reason") or "-", message),
                })
        for container_group in ("init_containers", "containers"):
            for container in ((pod_detail or {}).get(container_group) or [])[:5]:
                state = container.get("state") or container.get("status") or ""
                reason = container.get("reason") or ""
                image = container.get("image") or ""
                exit_code = container.get("exit_code")
                message = container.get("message") or ""
                if not state and not reason and not image and exit_code in (None, "") and not message:
                    continue
                details = [
                    "state={}".format(state or "-"),
                    "reason={}".format(reason or "-"),
                ]
                if image:
                    details.append("image={}".format(image))
                if exit_code not in (None, ""):
                    details.append("exit_code={}".format(exit_code))
                if message:
                    details.append("message={}".format(message))
                lines.append({
                    "time": "",
                    "message": "service_alias {} pod {} {} {}: {}".format(
                        service_alias, pod_name or "-", container_group, container.get("container_name") or "-",
                        ", ".join(details)),
                })

    def _append_runtime_event_snapshot_lines(self, lines: list, events: Any) -> None:
        for event in events or []:
            message = event.get("message") or event.get("reason") or ""
            if not message:
                continue
            lines.append({
                "time": event.get("create_time") or event.get("start_time") or event.get("end_time") or "",
                "message": "runtime event {} service_id={} target={}: {}".format(
                    event.get("opt_type") or "-",
                    event.get("service_id") or "-",
                    event.get("target") or "-",
                    self._redact_log_message(message)),
            })

    def _is_soft_runtime_failure(self, payload: dict) -> bool:
        opt_type = (payload.get("runtime_failure_opt_type") or "").lower()
        if opt_type in self.SOFT_FAILURE_OPT_TYPES:
            return True
        if self._is_soft_runtime_text(payload.get("runtime_failure_reason")):
            return True
        for failure_log in payload.get("runtime_failure_logs") or []:
            for line in failure_log.get("lines") or []:
                if self._is_soft_runtime_text(line.get("message")):
                    return True
        return False

    @staticmethod
    def _is_soft_runtime_text(value: Optional[str]) -> bool:
        value = (value or "").lower()
        if not value:
            return False
        return (
            "readiness" in value or
            "就绪" in value or
            "containersnotready" in value or
            "liveness" in value or
            "startup" in value
        )

    def _detect_failure_stage(self, deploy_type: str, failed_events: Any) -> str:
        for event in failed_events:
            opt_type = (event.get("opt_type") or "").lower()
            if any(keyword in opt_type for keyword in self.BUILD_OPT_KEYWORDS):
                return self.FAILURE_STAGE_BUILD
            if any(keyword in opt_type for keyword in self.RUNTIME_OPT_KEYWORDS):
                return self.FAILURE_STAGE_RUNTIME
        if deploy_type == self.DEPLOY_TYPE_SOURCE_CODE and failed_events:
            return self.FAILURE_STAGE_BUILD
        if failed_events:
            return self.FAILURE_STAGE_RUNTIME
        return self.FAILURE_STAGE_UNKNOWN

    def _normalize_stage(self, stage: str) -> str:
        if stage == self.FAILURE_STAGE_RUNTIME:
            return self.FAILURE_STAGE_RUNTIME
        return self.FAILURE_STAGE_BUILD

    @staticmethod
    def _detect_failure_reason(failed_events: Any) -> str:
        for event in failed_events:
            if event.get("message"):
                return event["message"]
            if event.get("reason"):
                return event["reason"]
        return ""

    def _failure_reason_or_default(self, failure_stage: str, failed_events: Any, reason: str) -> str:
        detected_reason = reason or self._detect_failure_reason(failed_events)
        if detected_reason:
            return self._shrink_text(detected_reason, self.MAX_FAILURE_REASON_LENGTH)
        return "{} failure: no failure reason reported".format(
            failure_stage or self.FAILURE_STAGE_UNKNOWN)

    def _start_report_thread(self, key: str) -> None:
        with self._lock:
            if key in self._reporting_keys:
                return
            self._reporting_keys.add(key)

        worker = threading.Thread(target=self._report_by_key, args=(key,))
        worker.daemon = True
        worker.start()

    def _report_by_key(self, key: str) -> None:
        try:
            record = enterprise_first_deploy_repo.get_by_key(key)
            if not record:
                return
            payload = enterprise_first_deploy_repo.load_payload(record)
            self._report_if_needed(record, payload, async_report=False)
        finally:
            with self._lock:
                self._reporting_keys.discard(key)

    def _report_if_needed(self, record: ConsoleSysConfig, payload: dict, async_report: bool = False) -> None:
        if payload.get("status") not in self.FINAL_STATUSES or payload.get("reported"):
            return
        if async_report and self.report_async:
            self._start_report_thread(record.key)
            return

        report_payload = self._build_report_payload(payload)
        if self._post_report_payload(report_payload):
            payload["reported"] = True
            payload["reported_at"] = self._now()
            enterprise_first_deploy_repo.update_payload(record, payload)

    def _build_report_payload(self, payload: dict) -> dict:
        report_payload = {
            "eid": payload.get("enterprise_id"),
            "enterprise_name": payload.get("enterprise_name"),
            "deploy_type": payload.get("deploy_type"),
            "source_language": payload.get("source_language", ""),
            "is_success": payload.get("status") == self.STATUS_SUCCESS,
        }
        if payload.get("payload_version", 1) >= 3:
            report_payload.update({
                "payload_version": payload.get("payload_version", self.PAYLOAD_VERSION),
                "deployment_context": payload.get("deployment_context") or {},
                "app_context": payload.get("app_context") or {},
                "environment_context": payload.get("environment_context") or {},
                "workload_context": payload.get("workload_context") or {},
            })
        if payload.get("status") == self.STATUS_FAILURE:
            report_payload.update({
                "payload_version": payload.get("payload_version", self.PAYLOAD_VERSION),
                "failure_stage": payload.get("failure_stage", self.FAILURE_STAGE_UNKNOWN),
                "failure_reason": payload.get("failure_reason", ""),
                "failure_category": payload.get("failure_category", self.FAILURE_CATEGORY_UNKNOWN),
                "log_collect_status": payload.get("log_collect_status", ""),
                "failure_events": payload.get("failure_events") or [],
                "failure_logs": payload.get("failure_logs") or [],
            })
        return report_payload

    def _post_report_payload(self, report_payload: dict) -> bool:
        for _ in range(3):
            try:
                response = requests.post(self.REPORT_URL, json=report_payload, timeout=5)
                if 200 <= response.status_code < 300:
                    return True
            except Exception as e:
                logger.warning("report first deploy log failed: %s", e)
            time.sleep(1)
        return False

    def _start_environment_collect_thread(self, key: str, enterprise_id: str, region_name: str) -> None:
        worker = threading.Thread(target=self._collect_environment_by_key, args=(key, enterprise_id, region_name))
        worker.daemon = True
        worker.start()

    def _collect_environment_by_key(self, key: str, enterprise_id: str, region_name: str) -> None:
        try:
            record = enterprise_first_deploy_repo.get_by_key(key)
            if not record:
                return
            environment_context = self._collect_environment_context(enterprise_id, region_name)
            record = enterprise_first_deploy_repo.get_by_key(key)
            if not record:
                return
            payload = enterprise_first_deploy_repo.load_payload(record)
            if payload.get("status") in self.FINAL_STATUSES:
                return
            payload["environment_context"] = environment_context
            enterprise_first_deploy_repo.update_payload(record, payload)
        except Exception as exc:
            logger.debug("collect deployment diagnostic environment failed: %s", exc)

    def _collect_environment_context(self, enterprise_id: str, region_name: str) -> dict:
        context: Dict[str, Any] = {
            "collect_status": "success",
            "region_name": region_name,
        }
        try:
            _, body = region_api.get_region_resources(enterprise_id, region=region_name)
            bean = (body or {}).get("bean") or {}
            context.update({
                "total_memory": bean.get("cap_mem", 0),
                "used_memory": bean.get("req_mem", 0),
                "total_cpu": bean.get("cap_cpu", 0),
                "used_cpu": bean.get("req_cpu", 0),
                "total_disk": bean.get("cap_disk", 0),
                "used_disk": bean.get("req_disk", 0),
                "rbd_version": bean.get("rbd_version", ""),
                "k8s_version": bean.get("k8s_version", ""),
                "node_count": bean.get("all_node", 0),
                "ready_nodes": bean.get("node_ready", 0),
                "run_pod_number": bean.get("run_pod_number", 0),
                "resource_proxy_status": bean.get("resource_proxy_status", False),
            })
        except Exception as exc:
            context["collect_status"] = "failed"
            context["error"] = self._shrink_text(str(exc), self.MAX_FAILURE_REASON_LENGTH)
            return context
        try:
            _, arch_body = region_api.get_cluster_nodes_arch(region_name)
            context["arch"] = (arch_body or {}).get("list") or []
        except Exception as exc:
            context["arch_collect_status"] = "failed"
            context["arch_collect_error"] = self._shrink_text(str(exc), self.MAX_FAILURE_REASON_LENGTH)
        return context

    @staticmethod
    def _service_source_from_deploy_type(deploy_type: str) -> str:
        if deploy_type == EnterpriseFirstDeployService.DEPLOY_TYPE_SOURCE_CODE:
            return "source_code"
        if deploy_type == EnterpriseFirstDeployService.DEPLOY_TYPE_APP_MARKET:
            return "market"
        if deploy_type == EnterpriseFirstDeployService.DEPLOY_TYPE_IMAGE:
            return "image"
        return deploy_type or ""

    def _build_app_context(self, enterprise_id: str, app_context: dict, component_name: str = "") -> dict:
        result = {}
        for key, value in (app_context or {}).items():
            if key in ("app_name", "component_name", "service_name"):
                hash_key = "{}_hash".format(key)
                result[hash_key] = self._hash_identifier(enterprise_id, value)
                continue
            result[key] = value
        if component_name and "component_name_hash" not in result:
            result["component_name_hash"] = self._hash_identifier(enterprise_id, component_name)
        return result

    @staticmethod
    def _build_workload_context(service: Any = None, workload_context: Optional[dict] = None) -> dict:
        result = dict(workload_context or {})
        if service is None:
            return result
        field_map = {
            "service_source": "service_source",
            "language": "language",
            "arch": "arch",
            "build_strategy": "build_strategy",
            "min_memory": "min_memory",
            "min_cpu": "min_cpu",
            "min_node": "min_node",
            "total_memory": "total_memory",
            "service_type": "service_type",
            "category": "category",
        }
        for target_key, attr in field_map.items():
            value = getattr(service, attr, None)
            if value not in (None, ""):
                result.setdefault(target_key, value)
        return result

    def build_service_app_context(self, app: Any = None, component_count: int = 1) -> dict:
        context = {
            "component_count": component_count,
        }
        if app is None:
            return context
        app_id = getattr(app, "ID", None) or getattr(app, "app_id", "")
        app_name = getattr(app, "group_name", None) or getattr(app, "app_name", "")
        if app_id:
            context["app_id"] = app_id
        if app_name:
            context["app_name"] = app_name
        return context

    @staticmethod
    def build_market_app_context(app: Any,
                                 market_app: Any,
                                 app_model_key: str,
                                 version: str,
                                 market_name: str,
                                 install_from_cloud: bool,
                                 app_template: Optional[dict] = None) -> dict:
        context = {}
        app_id = getattr(app, "app_id", None) or getattr(app, "ID", "")
        app_name = getattr(app, "group_name", None) or getattr(app, "app_name", "")
        if app_id:
            context["app_id"] = app_id
        if app_name:
            context["app_name"] = app_name
        market_app_name = getattr(market_app, "app_name", "")
        if market_app_name:
            context["market_app_name"] = market_app_name
        if app_model_key:
            context["app_model_key"] = app_model_key
        if version:
            context["app_model_version"] = version
        if market_name:
            context["market_name"] = market_name
        context["install_from_cloud"] = bool(install_from_cloud)
        if app_template:
            apps = app_template.get("apps") or []
            plugins = app_template.get("plugins") or []
            context["component_count"] = len(apps)
            if plugins:
                context["plugin_count"] = len(plugins)
            governance_mode = app_template.get("governance_mode") or app_template.get("goavernance_mode")
            if governance_mode:
                context["governance_mode"] = governance_mode
            arch = app_template.get("arch")
            if arch:
                context["template_arch"] = arch
        return context

    @staticmethod
    def build_market_workload_context(app_template: Optional[dict] = None) -> dict:
        if not app_template:
            return {}
        apps = app_template.get("apps") or []
        total_memory = 0
        min_memory = None
        total_cpu = 0
        min_cpu = None
        min_node = 0
        for app in apps:
            memory = app.get("memory") or app.get("container_memory") or 0
            cpu = app.get("container_cpu") or app.get("cpu") or 0
            replicas = app.get("min_node") or app.get("replicas") or 1
            try:
                memory_value = int(memory)
            except (TypeError, ValueError):
                memory_value = 0
            try:
                cpu_value = int(cpu)
            except (TypeError, ValueError):
                cpu_value = 0
            try:
                replicas_value = int(replicas)
            except (TypeError, ValueError):
                replicas_value = 1
            total_memory += memory_value * replicas_value
            total_cpu += cpu_value * replicas_value
            min_node += replicas_value
            if memory_value and (min_memory is None or memory_value < min_memory):
                min_memory = memory_value
            if cpu_value and (min_cpu is None or cpu_value < min_cpu):
                min_cpu = cpu_value
        context = {
            "component_count": len(apps),
            "total_memory": total_memory,
            "total_cpu": total_cpu,
            "min_node": min_node,
        }
        if min_memory is not None:
            context["min_memory"] = min_memory
        if min_cpu is not None:
            context["min_cpu"] = min_cpu
        template_arch = app_template.get("arch")
        if template_arch:
            context["template_arch"] = template_arch
        return context

    @staticmethod
    def _hash_identifier(instance_id: str, value: Any) -> str:
        import hashlib
        if value in (None, ""):
            return ""
        raw = "{}:{}".format(instance_id or "", value)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _shrink_failure_events(self, failed_events: Any) -> list:
        compact_events = []
        for event in (failed_events or [])[:self.MAX_FAILURE_EVENTS]:
            compact_events.append({
                "event_id": event.get("event_id", ""),
                "service_id": event.get("service_id", ""),
                "opt_type": event.get("opt_type", ""),
                "status": event.get("status", ""),
                "final_status": event.get("final_status", ""),
                "message": self._shrink_text(event.get("message", ""), self.MAX_FAILURE_REASON_LENGTH),
                "reason": self._shrink_text(event.get("reason", ""), self.MAX_FAILURE_REASON_LENGTH),
                "start_time": event.get("start_time", ""),
                "end_time": event.get("end_time", ""),
            })
        return compact_events

    def _collect_failure_logs(self, tenant_name: str, region_name: str, failed_events: Any,
                              failure_stage: str) -> list:
        logs, _ = self._collect_failure_logs_with_status(
            tenant_name,
            region_name,
            failed_events,
            failure_stage,
            self.FAILURE_CATEGORY_UNKNOWN,
            self._detect_failure_reason(failed_events),
            None)
        return logs

    def _collect_failure_logs_with_status(
            self, tenant_name: Optional[str], region_name: Optional[str], failed_events: Any,
            failure_stage: str, failure_category: str, reason: str, payload: Optional[dict] = None) -> Tuple[list, str]:
        failure_event = self._select_failure_log_event(failed_events, failure_stage)
        if not failure_event or not tenant_name or not region_name:
            return (
                [self._build_failure_diagnostic_log(
                    failure_stage, failure_category, self.LOG_COLLECT_STATUS_NO_EVENT_ID, failed_events, reason)],
                self.LOG_COLLECT_STATUS_NO_EVENT_ID,
            )
        event_id = failure_event.get("event_id")
        if not event_id:
            return (
                [self._build_failure_diagnostic_log(
                    failure_stage, failure_category, self.LOG_COLLECT_STATUS_NO_EVENT_ID, failed_events, reason)],
                self.LOG_COLLECT_STATUS_NO_EVENT_ID,
            )
        candidate_events = self._failure_log_candidate_events(failed_events, failure_stage, payload)
        attempts = self._failure_log_collect_attempts(failure_stage, failure_category)
        max_lines = self.MAX_BUILD_FAILURE_LOG_LINES if failure_stage == self.FAILURE_STAGE_BUILD else self.MAX_FAILURE_LOG_LINES
        had_api_error = False
        diagnostic_details = []  # type: List[str]
        for attempt in range(attempts):
            for candidate_event in candidate_events:
                event_id = candidate_event.get("event_id")
                try:
                    res, body = region_api.get_events_log(tenant_name, region_name, event_id)
                except Exception as e:
                    logger.warning("get %s failure logs failed: %s", failure_stage, e)
                    res, body = None, None
                    had_api_error = True
                    self._append_diagnostic_detail(
                        diagnostic_details, "event_log_exception={} event_id={}".format(
                            self._shrink_text(str(e), self.MAX_FAILURE_REASON_LENGTH), event_id))
                if self._is_success_response(res):
                    lines, truncated = self._normalize_log_lines(self._extract_event_log_items(body), max_lines=max_lines)
                    if lines:
                        return [{
                            "stage": failure_stage,
                            "event_id": event_id,
                            "source": "event_log",
                            "failure_category": failure_category,
                            "log_collect_status": self.LOG_COLLECT_STATUS_COLLECTED,
                            "truncated": truncated,
                            "lines": lines,
                        }], self.LOG_COLLECT_STATUS_COLLECTED
                    self._append_diagnostic_detail(diagnostic_details, "event_log_empty=true event_id={}".format(event_id))
                elif res is not None:
                    had_api_error = True
                    self._append_diagnostic_detail(
                        diagnostic_details, "event_log_status={} event_id={}".format(self._response_status(res), event_id))
            if attempt < attempts - 1:
                time.sleep(self.BUILD_FAILURE_LOG_RETRY_INTERVAL)
        for candidate_event in candidate_events:
            fallback_logs, fallback_details, fallback_had_api_error = self._collect_service_event_logs(
                tenant_name,
                region_name,
                candidate_event.get("event_id"),
                failure_stage,
                failure_category,
                max_lines,
                payload)
            if fallback_logs:
                return fallback_logs, self.LOG_COLLECT_STATUS_COLLECTED
            had_api_error = had_api_error or fallback_had_api_error
            for detail in fallback_details:
                self._append_diagnostic_detail(diagnostic_details, detail)
        status = self.LOG_COLLECT_STATUS_API_ERROR if had_api_error else self.LOG_COLLECT_STATUS_EMPTY_AFTER_RETRY
        return (
            [self._build_failure_diagnostic_log(
                failure_stage, failure_category, status, failed_events, reason, diagnostic_details)],
            status,
        )

    def _failure_log_candidate_events(self, failed_events: Any, failure_stage: str, payload: Optional[dict]) -> list:
        candidates = []  # type: List[dict]
        selected = self._select_failure_log_event(failed_events, failure_stage)
        self._append_failure_log_candidate(candidates, selected)
        if failure_stage == self.FAILURE_STAGE_BUILD and payload:
            self._append_failure_log_candidate(
                candidates,
                {"event_id": payload.get("build_event_id", ""), "opt_type": "build-service"})
            for event_id in payload.get("event_ids") or []:
                self._append_failure_log_candidate(candidates, {"event_id": event_id})
        for event in failed_events or []:
            self._append_failure_log_candidate(candidates, event)
        return candidates

    @staticmethod
    def _append_failure_log_candidate(candidates: List[dict], event: Optional[dict]) -> None:
        if not event:
            return
        event_id = event.get("event_id")
        if not event_id:
            return
        for candidate in candidates:
            if candidate.get("event_id") == event_id:
                return
        candidates.append(event)

    def _collect_service_event_logs(self, tenant_name: str, region_name: str, event_id: str, failure_stage: str,
                                    failure_category: str, max_lines: int,
                                    payload: Optional[dict]) -> Tuple[list, List[str], bool]:
        details = []  # type: List[str]
        if failure_stage != self.FAILURE_STAGE_BUILD or not payload:
            return [], details, False
        service_alias = payload.get("service_alias") or (payload.get("deployment_context") or {}).get("service_alias")
        if not service_alias:
            details.append("service_event_log_skipped=no_service_alias")
            return [], details, False
        had_api_error = False
        for level in self.EVENT_LOG_FALLBACK_LEVELS:
            request_body = {
                "event_id": event_id,
                "level": level,
                "enterprise_id": payload.get("enterprise_id", ""),
            }
            try:
                res, body = region_api.get_event_log(region_name, tenant_name, service_alias, request_body)
            except Exception as e:
                logger.warning("get %s service event logs failed: %s", failure_stage, e)
                had_api_error = True
                details.append("service_event_log_exception={} level={} service_alias={}".format(
                    self._shrink_text(str(e), self.MAX_FAILURE_REASON_LENGTH), level, service_alias))
                continue
            if not self._is_success_response(res):
                had_api_error = True
                details.append("service_event_log_status={} level={} service_alias={}".format(
                    self._response_status(res), level, service_alias))
                continue
            lines, truncated = self._normalize_log_lines(self._extract_event_log_items(body), max_lines=max_lines)
            if not lines:
                details.append("service_event_log_empty=true level={} service_alias={}".format(level, service_alias))
                continue
            return [{
                "stage": failure_stage,
                "event_id": event_id,
                "source": "service_event_log",
                "failure_category": failure_category,
                "log_collect_status": self.LOG_COLLECT_STATUS_COLLECTED,
                "truncated": truncated,
                "lines": lines,
            }], details, had_api_error
        return [], details, had_api_error

    def _extract_event_log_items(self, body: Any) -> list:
        if not body:
            return []
        if isinstance(body, list):
            return body
        if not isinstance(body, dict):
            return [body]
        for key in ("list", "bean", "data"):
            value = body.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = self._extract_event_log_items(value)
                if nested:
                    return nested
            if value:
                return [value]
        return []

    def _build_failure_diagnostic_log(self, failure_stage: str, failure_category: str, log_collect_status: str,
                                      failed_events: Any, reason: str,
                                      diagnostic_details: Optional[List[str]] = None) -> dict:
        event = self._select_failure_log_event(failed_events, failure_stage) or {}
        diagnostic = {
            "stage": failure_stage,
            "event_id": event.get("event_id", ""),
            "source": "diagnostic_summary",
            "failure_category": failure_category,
            "log_collect_status": log_collect_status,
            "truncated": False,
            "lines": [{
                "time": "",
                "message": self._failure_diagnostic_message(
                    failure_stage, failure_category, log_collect_status, event, reason, diagnostic_details),
            }],
        }
        return diagnostic

    def _failure_diagnostic_message(self, failure_stage: str, failure_category: str, log_collect_status: str,
                                    event: dict, reason: str,
                                    diagnostic_details: Optional[List[str]] = None) -> str:
        parts = [
            "failure_stage={}".format(failure_stage or self.FAILURE_STAGE_UNKNOWN),
            "failure_category={}".format(failure_category or self.FAILURE_CATEGORY_UNKNOWN),
            "log_collect_status={}".format(log_collect_status),
        ]
        if event.get("event_id"):
            parts.append("event_id={}".format(event.get("event_id")))
        if event.get("opt_type"):
            parts.append("opt_type={}".format(event.get("opt_type")))
        if reason:
            parts.append("reason={}".format(self._shrink_text(reason, self.MAX_FAILURE_REASON_LENGTH)))
        event_reason = event.get("reason") or ""
        if event_reason and event_reason != reason:
            parts.append("event_reason={}".format(self._shrink_text(event_reason, self.MAX_FAILURE_REASON_LENGTH)))
        for detail in diagnostic_details or []:
            if detail:
                parts.append(detail)
        return self._shrink_text("; ".join(parts), self.MAX_FAILURE_LOG_LINE_LENGTH)

    @staticmethod
    def _append_diagnostic_detail(details: List[str], detail: str) -> None:
        if detail and detail not in details:
            details.append(detail)

    @staticmethod
    def _response_status(response: Any) -> str:
        status = EnterpriseFirstDeployService._extract_response_status(response)
        if status is None:
            return "unknown"
        return str(status)

    @staticmethod
    def _extract_response_status(response: Any) -> Any:
        if response is None:
            return None
        if isinstance(response, dict):
            status = response.get("status")
            if status is not None:
                return status
            status = response.get("status_code")
            if status is not None:
                return status
        status = getattr(response, "status", None)
        if status is not None:
            return status
        return getattr(response, "status_code", None)

    def _detect_failure_category(self, failure_stage: str, failed_events: Any, reason: str) -> str:
        event_text = " ".join([
            "{} {}".format(event.get("message") or "", event.get("reason") or "")
            for event in failed_events or []
        ])
        reason_text = "{} {}".format(reason or self._detect_failure_reason(failed_events) or "", event_text).lower()
        opt_types = " ".join([(event.get("opt_type") or "") for event in failed_events or []]).lower()
        if failure_stage == self.FAILURE_STAGE_SOURCE_CHECK:
            return self._detect_source_check_category(reason_text)
        if ("拉取镜像失败" in reason_text or "failed to pull image" in reason_text or
                "imagepull" in opt_types or "errimagepull" in opt_types or
                "imagepullbackoff" in reason_text or "errimagepull" in reason_text):
            return self.FAILURE_CATEGORY_IMAGE_PULL_FAILED
        if "推送镜像" in reason_text or "push image" in reason_text:
            return self.FAILURE_CATEGORY_IMAGE_PUSH_FAILED
        if "版本信息" in reason_text or "version info" in reason_text:
            return self.FAILURE_CATEGORY_VERSION_INFO_FAILED
        if failure_stage == self.FAILURE_STAGE_BUILD:
            if "编译失败" in reason_text or "build failed" in reason_text or "构建镜像失败" in reason_text:
                return self.FAILURE_CATEGORY_COMPILE_FAILED
            return self.FAILURE_CATEGORY_UNKNOWN
        if "crashloopbackoff" in opt_types or "back-off restarting" in reason_text:
            return self.FAILURE_CATEGORY_POD_CRASH_LOOP
        if "没有可用节点" in reason_text or "nodes are available" in reason_text:
            return self.FAILURE_CATEGORY_NO_AVAILABLE_NODES
        if "runtimeverificationtimeout" in opt_types or "runtime timeout" in reason_text:
            return self.FAILURE_CATEGORY_RUNTIME_TIMEOUT
        return self.FAILURE_CATEGORY_UNKNOWN

    def _detect_source_check_category(self, reason: str) -> str:
        reason_text = (reason or "").lower()
        if "超时" in reason_text or "timeout" in reason_text or "timed out" in reason_text:
            return self.FAILURE_CATEGORY_SOURCE_FETCH_TIMEOUT
        if ("认证" in reason_text or "鉴权" in reason_text or "权限" in reason_text or
                "authentication" in reason_text or "unauthorized" in reason_text or "permission denied" in reason_text):
            return self.FAILURE_CATEGORY_SOURCE_AUTH_FAILED
        if ("分支" in reason_text or "branch" in reason_text or "revision" in reason_text or
                "reference not found" in reason_text):
            return self.FAILURE_CATEGORY_SOURCE_BRANCH_MISSING
        if ("仓库" in reason_text or "repo" in reason_text or "repository" in reason_text or
                "could not resolve host" in reason_text or "connection refused" in reason_text or
                "not found" in reason_text):
            return self.FAILURE_CATEGORY_SOURCE_REPO_UNREACHABLE
        return self.FAILURE_CATEGORY_UNKNOWN

    def _failure_log_collect_attempts(self, failure_stage: str, failure_category: str = "") -> int:
        if failure_stage != self.FAILURE_STAGE_BUILD:
            return 1
        retry_interval = max(int(self.BUILD_FAILURE_LOG_RETRY_INTERVAL), 1)
        if failure_category == self.FAILURE_CATEGORY_COMPILE_FAILED:
            wait_window = max(int(self.COMPILE_FAILURE_LOG_WAIT_WINDOW), 0)
        else:
            wait_window = max(int(self.BUILD_FAILURE_LOG_WAIT_WINDOW), 0)
        return max(int(wait_window / retry_interval) + 1, 1)

    def _select_failure_log_event(self, failed_events: Any, failure_stage: str) -> Optional[dict]:
        for event in failed_events:
            opt_type = (event.get("opt_type") or "").lower()
            if failure_stage == self.FAILURE_STAGE_BUILD and any(keyword in opt_type for keyword in self.BUILD_OPT_KEYWORDS):
                return event
            if failure_stage == self.FAILURE_STAGE_RUNTIME and self._is_runtime_failure_event(event):
                return event
        return failed_events[0] if failed_events else None

    def _normalize_log_lines(self, log_items: Any, max_lines: Optional[int] = None) -> Tuple[list, bool]:
        max_lines = max_lines or self.MAX_FAILURE_LOG_LINES
        truncated = len(log_items) > max_lines
        selected = log_items[-max_lines:]
        lines = []  # type: List[Dict[str, Any]]
        for item in selected:
            if isinstance(item, dict):
                message = item.get("message") or item.get("Message") or ""
                line_time = item.get("time") or item.get("Time") or item.get("utime") or ""
            else:
                message = str(item)
                line_time = ""
            message = self._redact_log_message(message)
            message, line_truncated = self._truncate_text(message, self.MAX_FAILURE_LOG_LINE_LENGTH)
            truncated = truncated or line_truncated
            if not message:
                continue
            lines.append({
                "time": line_time,
                "message": message,
            })
        return lines, truncated

    def _redact_log_message(self, message: Any) -> str:
        message = str(message or "")
        message = self.URL_CREDENTIAL_RE.sub(r"\1<redacted>@", message)
        message = self.AUTH_TOKEN_RE.sub(r"\1 <redacted>", message)
        message = self.SENSITIVE_QUOTED_ASSIGNMENT_RE.sub(self._redact_quoted_sensitive_assignment, message)
        return self.SENSITIVE_BARE_ASSIGNMENT_RE.sub(self._redact_bare_sensitive_assignment, message)

    @staticmethod
    def _redact_quoted_sensitive_assignment(match: Any) -> str:
        quote = match.group(3)
        return "{}{}{}<redacted>{}".format(match.group(1), match.group(2), quote, quote)

    @staticmethod
    def _redact_bare_sensitive_assignment(match: Any) -> str:
        return "{}{}<redacted>".format(
            match.group(1),
            match.group(2))

    @staticmethod
    def _truncate_text(value: Optional[str], limit: int) -> Tuple[str, bool]:
        value = value or ""
        if len(value) <= limit:
            return value, False
        return value[:limit], True

    def _shrink_text(self, value: Optional[str], limit: int) -> str:
        trimmed, _ = self._truncate_text(value, limit)
        return trimmed

    @staticmethod
    def _is_success_response(response: Any) -> bool:
        status = EnterpriseFirstDeployService._extract_response_status(response)
        try:
            # NOTE: status may be None; int(None) is caught by the except below (intentional).
            return 200 <= int(status) < 300  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _normalize_event_data(event: dict) -> dict:
        return {
            "event_id": str(event.get("EventID") or event.get("event_id") or ""),
            "service_id": event.get("ServiceID") or event.get("service_id") or "",
            "target": event.get("Target") or event.get("target") or "",
            "target_id": event.get("TargetID") or event.get("target_id") or "",
            "opt_type": event.get("OptType") or event.get("opt_type") or "",
            "status": event.get("Status") or event.get("status") or "",
            "final_status": event.get("FinalStatus") or event.get("final_status") or "",
            "message": event.get("Message") or event.get("message") or "",
            "reason": event.get("Reason") or event.get("reason") or "",
            "create_time": event.get("CreateTime") or event.get("create_time") or "",
            "start_time": event.get("StartTime") or event.get("start_time") or "",
            "end_time": event.get("EndTime") or event.get("end_time") or "",
        }

    def _inspect_runtime_pods(self, payload: dict, tenant_name: str, region_name: str,
                              runtime_watch_started_at: str) -> Optional[str]:
        aliases = []
        primary = payload.get("service_alias")
        if primary:
            aliases.append(primary)
        for alias in payload.get("service_aliases") or []:
            if alias and alias not in aliases:
                aliases.append(alias)
        if not aliases:
            return None

        all_running = True
        for service_alias in aliases:
            result = self._inspect_service_pods(payload, tenant_name, region_name, runtime_watch_started_at, service_alias)
            if result == self.STATUS_FAILURE:
                return self.STATUS_FAILURE
            if result is None:
                all_running = False
        return self.STATUS_SUCCESS if all_running else None

    def _inspect_service_pods(self, payload: dict, tenant_name: str, region_name: str,
                              runtime_watch_started_at: str, service_alias: str) -> Optional[str]:
        pods = self._get_service_pods_for_runtime(payload, tenant_name, region_name, service_alias)
        if not pods:
            return None

        candidate_pods = [pod for pod in pods if pod.get("_group") == "new_pods"] or pods
        all_running = True
        for pod in candidate_pods:
            pod_name = pod.get("pod_name")
            pod_detail = self._get_runtime_pod_detail(region_name, tenant_name, service_alias, pod_name)
            failure = self._extract_runtime_failure_from_pod(payload, pod, pod_detail)
            if failure:
                opt_type = (failure["event"].get("opt_type") or "").lower()
                is_soft = opt_type in self.SOFT_FAILURE_OPT_TYPES
                if is_soft:
                    all_running = False
                    # Probe/readiness failures can be transient. Keep the first snapshot, but only finalize
                    # after the extended readiness window.
                    payload["runtime_failure_opt_type"] = opt_type
                    payload["runtime_failure_reason"] = self._shrink_text(failure["reason"], self.MAX_FAILURE_REASON_LENGTH)
                    if not payload.get("runtime_failure_logs"):
                        payload["runtime_failure_logs"] = failure["logs"]
                    if not self._readiness_final_window_elapsed(runtime_watch_started_at):
                        continue
                self._set_stage_failure(
                    payload,
                    self.FAILURE_STAGE_RUNTIME,
                    failed_events=[failure["event"]],
                    reason=failure["reason"],
                    failure_logs=failure["logs"])
                return self.STATUS_FAILURE

            pod_status = (pod.get("pod_status") or "").upper()
            detail_status = ((pod_detail or {}).get("status") or {}).get("type_str", "")
            if pod_status != "RUNNING" or (detail_status and detail_status.upper() != "RUNNING"):
                all_running = False
                pod_status_info = (pod_detail or {}).get("status") or {}
                status_message = (pod_status_info.get("message") or pod_status_info.get("reason") or
                                  pod_status or detail_status or "runtime verification timeout")
                payload["runtime_failure_opt_type"] = pod_status_info.get("reason") or pod_status or detail_status
                payload["runtime_failure_reason"] = self._shrink_text(status_message, self.MAX_FAILURE_REASON_LENGTH)
                if not payload.get("runtime_failure_logs"):
                    pod_events = (pod_detail or {}).get("events") or []
                    candidate_logs = self._build_runtime_pod_logs(pod_name, pod_events, pod_status_info, pod_detail)
                    if candidate_logs:
                        payload["runtime_failure_logs"] = candidate_logs
        return self.STATUS_SUCCESS if all_running else None

    def _get_service_pods_for_runtime(self, payload: dict, tenant_name: str, region_name: str,
                                      service_alias: str) -> list:
        try:
            # NOTE: payload always carries enterprise_id (set in _build_payload); .get
            # widens to Optional but the invariant holds at runtime.
            data = region_api.get_service_pods(
                region_name, tenant_name, service_alias,
                payload.get("enterprise_id"))  # type: ignore[arg-type]
        except Exception as e:
            logger.warning("get service pods failed for %s: %s", service_alias, e)
            return []
        return self._extract_component_pods(data)

    @staticmethod
    def _extract_component_pods(pods_data: Any) -> list:
        if not isinstance(pods_data, dict):
            return []
        pod_groups = {}  # type: dict
        if isinstance(pods_data.get("bean"), dict):
            pod_groups = pods_data.get("bean") or {}
        elif isinstance(pods_data.get("list"), dict):
            pod_groups = pods_data.get("list") or {}
        pods = []
        for group_name in ("new_pods", "old_pods"):
            group_items = pod_groups.get(group_name) or []
            if not isinstance(group_items, list):
                continue
            for pod in group_items:
                if not isinstance(pod, dict):
                    continue
                pod_copy = dict(pod)
                pod_copy["_group"] = group_name
                pods.append(pod_copy)
        return pods

    def _get_runtime_pod_detail(self, region_name: str, tenant_name: str, service_alias: str,
                                pod_name: str) -> Any:
        if not pod_name:
            return {}
        try:
            data = region_api.pod_detail(region_name, tenant_name, service_alias, pod_name)
        except Exception as e:
            logger.warning("get pod detail failed for %s: %s", pod_name, e)
            return {}
        return self._extract_region_pod_detail(data)

    @staticmethod
    def _extract_region_pod_detail(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload or {}
        bean = payload.get("bean")
        if isinstance(bean, dict):
            return bean
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("bean"), dict):
            return data.get("bean")
        return payload

    def _extract_runtime_failure_from_pod(self, payload: dict, pod: dict, pod_detail: Any) -> Optional[dict]:
        pod_name = pod.get("pod_name") or (pod_detail or {}).get("name") or ""
        service_id = (payload.get("service_ids") or [""])[0]
        status = (pod_detail or {}).get("status") or {}
        events = (pod_detail or {}).get("events") or []
        container_reason = self._find_runtime_container_reason(pod_detail)
        event_message = self._find_runtime_event_message(events)
        if container_reason:
            reason_text = event_message or status.get("message") or container_reason
            return {
                "reason": self._shrink_text(reason_text, self.MAX_FAILURE_REASON_LENGTH),
                "event": {
                    "event_id": pod_name,
                    "service_id": service_id,
                    "opt_type": container_reason,
                    "status": self.STATUS_FAILURE,
                    "final_status": "complete",
                    "message": self._shrink_text(reason_text, self.MAX_FAILURE_REASON_LENGTH),
                    "reason": container_reason,
                    "start_time": "",
                    "end_time": "",
                },
                "logs": self._build_runtime_pod_logs(pod_name, events, status, pod_detail),
            }
        status_type = (status.get("type_str") or "").upper()
        if status_type in ("ABNORMAL", "UNHEALTHY") and (status.get("message") or status.get("reason")):
            reason_text = status.get("message") or status.get("reason")
            return {
                "reason": self._shrink_text(reason_text, self.MAX_FAILURE_REASON_LENGTH),
                "event": {
                    "event_id": pod_name,
                    "service_id": service_id,
                    "opt_type": status.get("reason") or status_type,
                    "status": self.STATUS_FAILURE,
                    "final_status": "complete",
                    "message": self._shrink_text(reason_text, self.MAX_FAILURE_REASON_LENGTH),
                    "reason": status.get("reason") or status_type,
                    "start_time": "",
                    "end_time": "",
                },
                "logs": self._build_runtime_pod_logs(pod_name, events, status, pod_detail),
            }
        return None

    def _find_runtime_container_reason(self, pod_detail: Any) -> str:
        for container_group in ((pod_detail or {}).get("init_containers") or [], (pod_detail or {}).get("containers") or []):
            for container in container_group:
                reason = (container.get("reason") or "").lower()
                if reason in self.POD_RUNTIME_FAILURE_REASONS:
                    return container.get("reason")
        return ""

    def _find_runtime_event_message(self, events: Any) -> str:
        for event in events or []:
            message = event.get("message") or ""
            reason = (event.get("reason") or "").lower()
            if "imagepullbackoff" in message.lower() or "errimagepull" in message.lower():
                return message
            if reason in ("failed", "backoff") and message:
                return message
        return ""

    def _build_runtime_pod_logs(self, pod_name: str, events: Any, status: Any,
                                pod_detail: Any = None) -> list:
        lines = []  # type: List[Dict[str, Any]]
        for event in events or []:
            message = event.get("message") or ""
            if not message:
                continue
            lines.append({
                "time": event.get("age") or "",
                "message": self._shrink_text(self._redact_log_message(message), self.MAX_FAILURE_LOG_LINE_LENGTH),
            })
        for container_group in ("init_containers", "containers"):
            for container in ((pod_detail or {}).get(container_group) or [])[:5]:
                state = container.get("state") or container.get("status") or ""
                reason = container.get("reason") or ""
                image = container.get("image") or ""
                exit_code = container.get("exit_code")
                message = container.get("message") or ""
                if not state and not reason and not image and exit_code in (None, "") and not message:
                    continue
                details = [
                    "state={}".format(state or "-"),
                    "reason={}".format(reason or "-"),
                ]
                if image:
                    details.append("image={}".format(image))
                if exit_code not in (None, ""):
                    details.append("exit_code={}".format(exit_code))
                if message:
                    details.append("message={}".format(message))
                lines.append({
                    "time": "",
                    "message": self._shrink_text(
                        self._redact_log_message("{} {}: {}".format(
                            container_group, container.get("container_name") or "-", ", ".join(details))),
                        self.MAX_FAILURE_LOG_LINE_LENGTH),
                })
        if not lines and status:
            message = status.get("message") or status.get("reason") or ""
            if message:
                lines.append({
                    "time": "",
                    "message": self._shrink_text(self._redact_log_message(message), self.MAX_FAILURE_LOG_LINE_LENGTH),
                })
        if not lines:
            return []
        return [{
            "stage": self.FAILURE_STAGE_RUNTIME,
            "event_id": pod_name,
            "source": "pod_event",
            "truncated": False,
            "lines": lines[:self.MAX_FAILURE_LOG_LINES],
        }]

    def _list_runtime_failure_events(self, tenant_name: str, region_name: str, service_ids: Any,
                                     runtime_watch_started_at: str) -> list:
        failed_events = []  # type: List[dict]
        for service_id in service_ids or []:
            try:
                res, body = region_api.get_target_events_list(
                    region_name, tenant_name, "service", service_id, 1, self.RUNTIME_EVENT_QUERY_SIZE)
            except Exception as e:
                logger.warning("list runtime events failed for service %s: %s", service_id, e)
                continue
            if not self._is_success_response(res):
                continue
            for event in (body or {}).get("list") or []:
                normalized_event = self._normalize_event_data(event)
                if not self._is_runtime_failure_event(normalized_event):
                    continue
                if not self._event_in_runtime_window(normalized_event, runtime_watch_started_at):
                    continue
                failed_events.append(normalized_event)
        return failed_events

    def _is_runtime_failure_event(self, event: dict) -> bool:
        if event.get("status") != self.STATUS_FAILURE:
            return False
        opt_type = (event.get("opt_type") or "").lower()
        if opt_type in self.RUNTIME_FAILURE_OPT_TYPES:
            return True
        target = (event.get("target") or "").lower()
        return target == "pod"

    def _event_in_runtime_window(self, event: dict, runtime_watch_started_at: str) -> bool:
        event_time = self._parse_time(
            event.get("create_time") or event.get("start_time") or event.get("end_time"))
        watch_time = self._parse_time(runtime_watch_started_at)
        if not event_time or not watch_time:
            return True
        return event_time >= watch_time

    def _runtime_window_elapsed(self, runtime_watch_started_at: str) -> bool:
        watch_time = self._parse_time(runtime_watch_started_at)
        current_time = self._parse_time(self._now())
        if not watch_time or not current_time:
            return True
        return (current_time - watch_time).total_seconds() >= self.RUNTIME_OBSERVE_WINDOW

    def _readiness_final_window_elapsed(self, runtime_watch_started_at: str) -> bool:
        watch_time = self._parse_time(runtime_watch_started_at)
        current_time = self._parse_time(self._now())
        if not watch_time or not current_time:
            return True
        final_window = max(self.RUNTIME_OBSERVE_WINDOW, self.READINESS_FINAL_OBSERVE_WINDOW)
        return (current_time - watch_time).total_seconds() >= final_window

    @staticmethod
    def _parse_time(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S+08:00", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def get_deploy_type(self, service_source: str) -> str:
        if service_source in ("source_code", "package_build"):
            return self.DEPLOY_TYPE_SOURCE_CODE
        if service_source == "market":
            return self.DEPLOY_TYPE_APP_MARKET
        return self.DEPLOY_TYPE_IMAGE


enterprise_first_deploy_service = EnterpriseFirstDeployService()
