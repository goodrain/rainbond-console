# -*- coding: utf-8 -*-
import logging
import os
import threading
import time
from datetime import datetime

import requests

from console.repositories.first_deploy_repo import enterprise_first_deploy_repo
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantEnterprise

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class EnterpriseFirstDeployService(object):
    REPORT_URL = os.getenv("FIRST_DEPLOY_REPORT_URL", "https://log.rainbond.com/api/enterprise/first-deploy")
    PAYLOAD_VERSION = 2
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"
    FINAL_STATUSES = {STATUS_SUCCESS, STATUS_FAILURE}
    POLL_INTERVAL = 5
    POLL_TIMEOUT = 60 * 20
    DEPLOY_TYPE_SOURCE_CODE = "source_code"
    DEPLOY_TYPE_APP_MARKET = "app_market"
    DEPLOY_TYPE_IMAGE = "image"
    FAILURE_STAGE_BUILD = "build"
    FAILURE_STAGE_RUNTIME = "runtime"
    FAILURE_STAGE_UNKNOWN = "unknown"
    MAX_FAILURE_EVENTS = 3
    MAX_FAILURE_LOG_LINES = 8
    MAX_FAILURE_LOG_LINE_LENGTH = 200
    MAX_FAILURE_REASON_LENGTH = 200
    BUILD_OPT_KEYWORDS = ("build", "slug", "package")
    RUNTIME_OPT_KEYWORDS = ("start", "deploy", "upgrade", "rollback", "restart", "run")

    def __init__(self):
        self._running_keys = set()
        self._lock = threading.Lock()

    def begin_tracking(self,
                       enterprise_id,
                       tenant_name,
                       region_name,
                       deploy_type,
                       operator="",
                       source_language=""):
        record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if record:
            payload = enterprise_first_deploy_repo.load_payload(record)
            if payload.get("status") == self.STATUS_PENDING and not payload.get("event_ids") and self._is_expired(payload):
                self._finalize_record(record, payload, self.STATUS_FAILURE)
            self._report_if_needed(record, payload)
            if payload.get("status") == self.STATUS_PENDING and payload.get("event_ids"):
                transaction.on_commit(lambda: self._start_sync_thread(record.key, tenant_name, region_name))
            return None

        payload = self._build_payload(
            enterprise_id=enterprise_id,
            tenant_name=tenant_name,
            region_name=region_name,
            deploy_type=deploy_type,
            operator=operator,
            source_language=source_language,
        )
        record, created = enterprise_first_deploy_repo.create_if_absent(enterprise_id, payload)
        if not created:
            existing = enterprise_first_deploy_repo.load_payload(record)
            if existing.get("status") == self.STATUS_PENDING and not existing.get("event_ids") and self._is_expired(existing):
                self._finalize_record(record, existing, self.STATUS_FAILURE)
            self._report_if_needed(record, existing)
            if existing.get("status") == self.STATUS_PENDING and existing.get("event_ids"):
                transaction.on_commit(lambda: self._start_sync_thread(record.key, tenant_name, region_name))
            return None
        return {
            "enterprise_id": enterprise_id,
            "key": record.key,
            "tenant_name": tenant_name,
            "region_name": region_name,
        }

    def bind_events(self, tracker, event_ids):
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_enterprise_id(tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return

        event_ids = [str(event_id) for event_id in (event_ids or []) if event_id]
        payload["event_ids"] = sorted(set(event_ids))
        if not payload["event_ids"]:
            self._finalize_record(record, payload, self.STATUS_SUCCESS)
            return

        enterprise_first_deploy_repo.update_payload(record, payload)
        transaction.on_commit(lambda: self._start_sync_thread(record.key, tracker["tenant_name"], tracker["region_name"]))

    def mark_success(self, tracker):
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_enterprise_id(tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return
        self._finalize_record(record, payload, self.STATUS_SUCCESS)

    def mark_failure(self, tracker, reason="", failure_stage=""):
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_enterprise_id(tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return
        self._set_failure_details(
            payload,
            tenant_name=payload.get("tenant_name"),
            region_name=payload.get("region_name"),
            reason=reason,
            failure_stage=failure_stage)
        self._finalize_record(record, payload, self.STATUS_FAILURE)

    def sync_once(self, enterprise_id, tenant_name, region_name):
        record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if not record:
            return None
        payload = enterprise_first_deploy_repo.load_payload(record)
        return self._sync_record(record, payload, tenant_name, region_name)

    def _build_payload(self, enterprise_id, tenant_name, region_name, deploy_type, operator="", source_language=""):
        enterprise = TenantEnterprise.objects.filter(enterprise_id=enterprise_id).first()
        payload = {
            "enterprise_id": enterprise_id,
            "enterprise_name": self._get_enterprise_name(enterprise),
            "deploy_type": deploy_type,
            "source_language": source_language if deploy_type == self.DEPLOY_TYPE_SOURCE_CODE else "",
            "payload_version": self.PAYLOAD_VERSION,
            "status": self.STATUS_PENDING,
            "reported": False,
            "reported_at": "",
            "started_at": self._now(),
            "finished_at": "",
            "tenant_name": tenant_name,
            "region_name": region_name,
            "operator": operator or "",
            "event_ids": [],
            "failure_stage": "",
            "failure_reason": "",
            "failure_events": [],
            "failure_logs": [],
        }
        return payload

    def _sync_record(self, record, payload, tenant_name, region_name):
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return payload.get("status")

        event_ids = payload.get("event_ids") or []
        if not event_ids:
            self._finalize_record(record, payload, self.STATUS_SUCCESS)
            return self.STATUS_SUCCESS

        try:
            body = region_api.get_tenant_events(region_name, tenant_name, event_ids)
        except Exception as e:
            logger.exception("sync first deploy status failed: %s", e)
            return None

        events = body.get("list") or []
        status_map = {}
        for event in events:
            event_id = event.get("EventID") or event.get("event_id")
            status = event.get("Status") or event.get("status")
            if event_id and status:
                status_map[str(event_id)] = status

        if not status_map:
            return None

        failed_events = [
            event for event in [self._normalize_event_data(event) for event in events]
            if event.get("status") in (self.STATUS_FAILURE, "timeout")
        ]
        if failed_events:
            self._set_failure_details(payload, tenant_name, region_name, failed_events=failed_events)
            self._finalize_record(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

        if len(status_map) < len(set(event_ids)):
            return None

        normalized = set(status_map.values())
        if normalized == {self.STATUS_SUCCESS}:
            self._finalize_record(record, payload, self.STATUS_SUCCESS)
            return self.STATUS_SUCCESS

        if "timeout" in normalized:
            self._set_failure_details(payload, tenant_name, region_name)
            self._finalize_record(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

        return None

    def _finalize_record(self, record, payload, status):
        payload["status"] = status
        payload["finished_at"] = self._now()
        enterprise_first_deploy_repo.update_payload(record, payload)
        self._report_if_needed(record, payload)

    def _report_if_needed(self, record, payload):
        if payload.get("status") not in self.FINAL_STATUSES or payload.get("reported"):
            return

        report_payload = {
            "eid": payload.get("enterprise_id"),
            "enterprise_name": payload.get("enterprise_name"),
            "deploy_type": payload.get("deploy_type"),
            "source_language": payload.get("source_language", ""),
            "is_success": payload.get("status") == self.STATUS_SUCCESS,
        }
        if payload.get("status") == self.STATUS_FAILURE:
            report_payload.update({
                "payload_version": payload.get("payload_version", self.PAYLOAD_VERSION),
                "failure_stage": payload.get("failure_stage", self.FAILURE_STAGE_UNKNOWN),
                "failure_reason": payload.get("failure_reason", ""),
                "failure_events": payload.get("failure_events") or [],
                "failure_logs": payload.get("failure_logs") or [],
            })

        for _ in range(3):
            try:
                response = requests.post(self.REPORT_URL, json=report_payload, timeout=5)
                if 200 <= response.status_code < 300:
                    payload["reported"] = True
                    payload["reported_at"] = self._now()
                    enterprise_first_deploy_repo.update_payload(record, payload)
                    return
            except Exception as e:
                logger.warning("report first deploy log failed: %s", e)
            time.sleep(1)

    def _start_sync_thread(self, key, tenant_name, region_name):
        with self._lock:
            if key in self._running_keys:
                return
            self._running_keys.add(key)

        worker = threading.Thread(target=self._poll_until_finished, args=(key, tenant_name, region_name))
        worker.daemon = True
        worker.start()

    def _poll_until_finished(self, key, tenant_name, region_name):
        try:
            deadline = time.time() + self.POLL_TIMEOUT
            while time.time() < deadline:
                record = enterprise_first_deploy_repo.get_by_key(key)
                if not record:
                    time.sleep(self.POLL_INTERVAL)
                    continue
                payload = enterprise_first_deploy_repo.load_payload(record)
                status = self._sync_record(record, payload, tenant_name, region_name)
                if status in self.FINAL_STATUSES:
                    return
                time.sleep(self.POLL_INTERVAL)

            record = enterprise_first_deploy_repo.get_by_key(key)
            if not record:
                return
            payload = enterprise_first_deploy_repo.load_payload(record)
            if payload.get("status") == self.STATUS_PENDING:
                self._finalize_record(record, payload, self.STATUS_FAILURE)
        finally:
            with self._lock:
                self._running_keys.discard(key)

    @staticmethod
    def _now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _day():
        return datetime.now().strftime("%Y%m%d")

    def _is_expired(self, payload):
        started_at = payload.get("started_at")
        if not started_at:
            return False
        try:
            started = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False
        return (datetime.now() - started).total_seconds() >= self.POLL_TIMEOUT

    @staticmethod
    def _get_enterprise_name(enterprise):
        if not enterprise:
            return ""
        return enterprise.enterprise_alias or enterprise.enterprise_name or ""

    def _set_failure_details(self, payload, tenant_name="", region_name="", failed_events=None, reason="", failure_stage=""):
        failed_events = failed_events or []
        payload["payload_version"] = self.PAYLOAD_VERSION
        payload["failure_events"] = self._shrink_failure_events(failed_events)
        payload["failure_stage"] = failure_stage or self._detect_failure_stage(payload.get("deploy_type"), failed_events)
        payload["failure_reason"] = self._shrink_text(
            reason or self._detect_failure_reason(failed_events),
            self.MAX_FAILURE_REASON_LENGTH)
        if payload["failure_stage"] == self.FAILURE_STAGE_BUILD:
            payload["failure_logs"] = self._collect_build_failure_logs(
                tenant_name or payload.get("tenant_name"),
                region_name or payload.get("region_name"),
                failed_events)
        else:
            payload["failure_logs"] = []

    def _detect_failure_stage(self, deploy_type, failed_events):
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

    @staticmethod
    def _detect_failure_reason(failed_events):
        for event in failed_events:
            if event.get("message"):
                return event["message"]
            if event.get("reason"):
                return event["reason"]
        return ""

    def _shrink_failure_events(self, failed_events):
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

    def _collect_build_failure_logs(self, tenant_name, region_name, failed_events):
        build_event = self._find_build_failure_event(failed_events)
        if not build_event or not tenant_name or not region_name:
            return []
        event_id = build_event.get("event_id")
        if not event_id:
            return []
        try:
            res, body = region_api.get_events_log(tenant_name, region_name, event_id)
        except Exception as e:
            logger.warning("get build failure logs failed: %s", e)
            return []
        if not self._is_success_response(res):
            return []
        lines, truncated = self._normalize_log_lines((body or {}).get("list") or [])
        if not lines:
            return []
        return [{
            "stage": self.FAILURE_STAGE_BUILD,
            "event_id": event_id,
            "source": "event_log",
            "truncated": truncated,
            "lines": lines,
        }]

    def _find_build_failure_event(self, failed_events):
        for event in failed_events:
            opt_type = (event.get("opt_type") or "").lower()
            if any(keyword in opt_type for keyword in self.BUILD_OPT_KEYWORDS):
                return event
        return failed_events[0] if failed_events else None

    def _normalize_log_lines(self, log_items):
        truncated = len(log_items) > self.MAX_FAILURE_LOG_LINES
        selected = log_items[-self.MAX_FAILURE_LOG_LINES:]
        lines = []
        for item in selected:
            if isinstance(item, dict):
                message = item.get("message") or item.get("Message") or ""
                line_time = item.get("time") or item.get("Time") or item.get("utime") or ""
            else:
                message = str(item)
                line_time = ""
            message, line_truncated = self._truncate_text(message, self.MAX_FAILURE_LOG_LINE_LENGTH)
            truncated = truncated or line_truncated
            if not message:
                continue
            lines.append({
                "time": line_time,
                "message": message,
            })
        return lines, truncated

    @staticmethod
    def _truncate_text(value, limit):
        value = value or ""
        if len(value) <= limit:
            return value, False
        return value[:limit], True

    def _shrink_text(self, value, limit):
        trimmed, _ = self._truncate_text(value, limit)
        return trimmed

    @staticmethod
    def _is_success_response(response):
        status = getattr(response, "status_code", None)
        if status is None:
            status = getattr(response, "status", None)
        try:
            return 200 <= int(status) < 300
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _normalize_event_data(event):
        return {
            "event_id": str(event.get("EventID") or event.get("event_id") or ""),
            "service_id": event.get("ServiceID") or event.get("service_id") or "",
            "opt_type": event.get("OptType") or event.get("opt_type") or "",
            "status": event.get("Status") or event.get("status") or "",
            "final_status": event.get("FinalStatus") or event.get("final_status") or "",
            "message": event.get("Message") or event.get("message") or "",
            "reason": event.get("Reason") or event.get("reason") or "",
            "start_time": event.get("StartTime") or event.get("start_time") or "",
            "end_time": event.get("EndTime") or event.get("end_time") or "",
        }

    def get_deploy_type(self, service_source):
        if service_source in ("source_code", "package_build"):
            return self.DEPLOY_TYPE_SOURCE_CODE
        if service_source == "market":
            return self.DEPLOY_TYPE_APP_MARKET
        return self.DEPLOY_TYPE_IMAGE


enterprise_first_deploy_service = EnterpriseFirstDeployService()
