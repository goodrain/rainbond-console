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
    FAILURE_STAGE_BUILD = "build"
    FAILURE_STAGE_RUNTIME = "runtime"
    FAILURE_STAGE_UNKNOWN = "unknown"
    MAX_FAILURE_EVENTS = 3
    MAX_FAILURE_LOG_LINES = 8
    MAX_FAILURE_LOG_LINE_LENGTH = 200
    MAX_FAILURE_REASON_LENGTH = 200
    RUNTIME_OBSERVE_WINDOW = 60
    RUNTIME_EVENT_QUERY_SIZE = 20
    BUILD_OPT_KEYWORDS = ("build", "slug", "package")
    RUNTIME_OPT_KEYWORDS = ("start", "deploy", "upgrade", "rollback", "restart", "run")
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

    def __init__(self):
        self._running_keys = set()
        self._lock = threading.Lock()

    def begin_tracking(self,
                       enterprise_id,
                       tenant_name,
                       region_name,
                       deploy_type,
                       operator="",
                       source_language="",
                       service_id=""):
        record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if record:
            payload = enterprise_first_deploy_repo.load_payload(record)
            if payload.get("status") == self.STATUS_PENDING and not payload.get("event_ids") and self._is_expired(payload):
                self._set_stage_failure(payload, self.FAILURE_STAGE_BUILD)
                self._complete_tracking(record, payload, self.STATUS_FAILURE)
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_BUILD)
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_RUNTIME)
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
            service_id=service_id,
        )
        record, created = enterprise_first_deploy_repo.create_if_absent(enterprise_id, payload)
        if not created:
            existing = enterprise_first_deploy_repo.load_payload(record)
            if existing.get("status") == self.STATUS_PENDING and not existing.get("event_ids") and self._is_expired(existing):
                self._set_stage_failure(existing, self.FAILURE_STAGE_BUILD)
                self._complete_tracking(record, existing, self.STATUS_FAILURE)
            self._report_stage_if_needed(record, existing, self.FAILURE_STAGE_BUILD)
            self._report_stage_if_needed(record, existing, self.FAILURE_STAGE_RUNTIME)
            if existing.get("status") == self.STATUS_PENDING and existing.get("event_ids"):
                transaction.on_commit(lambda: self._start_sync_thread(record.key, tenant_name, region_name))
            return None
        return {
            "enterprise_id": enterprise_id,
            "key": record.key,
            "tenant_name": tenant_name,
            "region_name": region_name,
            "service_id": service_id or "",
        }

    def bind_events(self, tracker, event_ids):
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_enterprise_id(tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_BUILD)
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_RUNTIME)
            return

        event_ids = [str(event_id) for event_id in (event_ids or []) if event_id]
        payload["event_ids"] = sorted(set(event_ids))
        if event_ids:
            payload["build_event_id"] = event_ids[0]
        tracker_service_id = tracker.get("service_id")
        if tracker_service_id and tracker_service_id not in payload.get("service_ids", []):
            payload.setdefault("service_ids", []).append(tracker_service_id)
        if not payload["event_ids"]:
            self._mark_stage_success(payload, self.FAILURE_STAGE_BUILD, service_id=tracker_service_id)
            self._mark_stage_success(payload, self.FAILURE_STAGE_RUNTIME, service_id=tracker_service_id)
            self._complete_tracking(record, payload, self.STATUS_SUCCESS)
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
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_BUILD)
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_RUNTIME)
            return
        self._mark_stage_success(payload, self.FAILURE_STAGE_BUILD)
        self._mark_stage_success(payload, self.FAILURE_STAGE_RUNTIME)
        self._complete_tracking(record, payload, self.STATUS_SUCCESS)

    def mark_failure(self, tracker, reason="", failure_stage=""):
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_enterprise_id(tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_BUILD)
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_RUNTIME)
            return
        stage = self._normalize_stage(failure_stage)
        self._set_stage_failure(
            payload,
            stage,
            tenant_name=payload.get("tenant_name"),
            region_name=payload.get("region_name"),
            reason=reason)
        self._complete_tracking(record, payload, self.STATUS_FAILURE)

    def sync_once(self, enterprise_id, tenant_name, region_name):
        record = enterprise_first_deploy_repo.get_by_enterprise_id(enterprise_id)
        if not record:
            return None
        payload = enterprise_first_deploy_repo.load_payload(record)
        return self._sync_record(record, payload, tenant_name, region_name)

    def _build_payload(self, enterprise_id, tenant_name, region_name, deploy_type, operator="", source_language="", service_id=""):
        enterprise = TenantEnterprise.objects.filter(enterprise_id=enterprise_id).first()
        payload = {
            "enterprise_id": enterprise_id,
            "enterprise_name": self._get_enterprise_name(enterprise),
            "deploy_type": deploy_type,
            "source_language": source_language if deploy_type == self.DEPLOY_TYPE_SOURCE_CODE else "",
            "payload_version": self.PAYLOAD_VERSION,
            "status": self.STATUS_PENDING,
            "started_at": self._now(),
            "finished_at": "",
            "tenant_name": tenant_name,
            "region_name": region_name,
            "operator": operator or "",
            "event_ids": [],
            "service_ids": [service_id] if service_id else [],
            "build_status": self.STAGE_STATUS_PENDING,
            "build_reported": False,
            "build_reported_at": "",
            "build_started_at": self._now(),
            "build_finished_at": "",
            "build_event_id": "",
            "build_failure_reason": "",
            "build_failure_events": [],
            "build_failure_logs": [],
            "runtime_status": self.STAGE_STATUS_PENDING,
            "runtime_reported": False,
            "runtime_reported_at": "",
            "runtime_started_at": "",
            "runtime_finished_at": "",
            "runtime_event_id": "",
            "runtime_failure_reason": "",
            "runtime_failure_events": [],
            "runtime_failure_logs": [],
            "runtime_watch_started_at": "",
        }
        return payload

    def _sync_record(self, record, payload, tenant_name, region_name):
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_BUILD)
            self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_RUNTIME)
            return payload.get("status")

        event_ids = payload.get("event_ids") or []
        if not event_ids:
            return None

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
            self._set_stage_failure(payload, self.FAILURE_STAGE_BUILD, tenant_name, region_name, failed_events=failed_events)
            self._complete_tracking(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

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
                self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_BUILD)
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
            self._set_stage_failure(payload, self.FAILURE_STAGE_BUILD, tenant_name, region_name, stage_status=self.STAGE_STATUS_TIMEOUT)
            self._complete_tracking(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

        return None

    def _complete_tracking(self, record, payload, status):
        payload["status"] = status
        payload["finished_at"] = self._now()
        enterprise_first_deploy_repo.update_payload(record, payload)
        self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_BUILD)
        self._report_stage_if_needed(record, payload, self.FAILURE_STAGE_RUNTIME)

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
                stage = self.FAILURE_STAGE_BUILD if payload.get("build_status") == self.STAGE_STATUS_PENDING else self.FAILURE_STAGE_RUNTIME
                self._set_stage_failure(payload, stage, stage_status=self.STAGE_STATUS_TIMEOUT)
                self._complete_tracking(record, payload, self.STATUS_FAILURE)
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

    def _merge_service_ids(self, payload, tracked_events):
        service_ids = payload.get("service_ids") or []
        for event in tracked_events or []:
            service_id = (event.get("ServiceID") or event.get("service_id") or "")
            if service_id and service_id not in service_ids:
                service_ids.append(service_id)
        payload["service_ids"] = service_ids
        return service_ids[0] if service_ids else ""

    def _mark_stage_success(self, payload, stage, event_id="", service_id=""):
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

    def _set_stage_failure(self, payload, stage, tenant_name="", region_name="", failed_events=None, reason="", stage_status=""):
        failed_events = failed_events or []
        now = self._now()
        payload["payload_version"] = self.PAYLOAD_VERSION
        payload["{}_status".format(stage)] = stage_status or self.STATUS_FAILURE
        payload["{}_finished_at".format(stage)] = now
        if not payload.get("{}_started_at".format(stage)):
            payload["{}_started_at".format(stage)] = now
        compact_events = self._shrink_failure_events(failed_events)
        payload["{}_failure_events".format(stage)] = compact_events
        payload["{}_failure_reason".format(stage)] = self._shrink_text(
            reason or self._detect_failure_reason(failed_events),
            self.MAX_FAILURE_REASON_LENGTH)
        if compact_events:
            payload["{}_event_id".format(stage)] = compact_events[0].get("event_id", "")
            service_id = compact_events[0].get("service_id", "")
            if service_id and service_id not in payload.get("service_ids", []):
                payload.setdefault("service_ids", []).append(service_id)
        payload["{}_failure_logs".format(stage)] = self._collect_failure_logs(
            tenant_name or payload.get("tenant_name"),
            region_name or payload.get("region_name"),
            failed_events,
            stage)

    def _inspect_runtime_status(self, record, payload, tenant_name, region_name):
        runtime_watch_started_at = payload.get("runtime_watch_started_at")
        if not runtime_watch_started_at:
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
            self._mark_stage_success(
                payload,
                self.FAILURE_STAGE_RUNTIME,
                event_id="",
                service_id=(payload.get("service_ids") or [""])[0])
            return self.STATUS_SUCCESS
        return None

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

    def _normalize_stage(self, stage):
        if stage == self.FAILURE_STAGE_RUNTIME:
            return self.FAILURE_STAGE_RUNTIME
        return self.FAILURE_STAGE_BUILD

    @staticmethod
    def _detect_failure_reason(failed_events):
        for event in failed_events:
            if event.get("message"):
                return event["message"]
            if event.get("reason"):
                return event["reason"]
        return ""

    def _report_stage_if_needed(self, record, payload, stage):
        stage_status = payload.get("{}_status".format(stage))
        if stage_status not in self.STAGE_FINAL_STATUSES or payload.get("{}_reported".format(stage)):
            return

        service_ids = payload.get("service_ids") or []
        report_payload = {
            "eid": payload.get("enterprise_id"),
            "enterprise_name": payload.get("enterprise_name"),
            "deploy_type": payload.get("deploy_type"),
            "source_language": payload.get("source_language", ""),
            "payload_version": payload.get("payload_version", self.PAYLOAD_VERSION),
            "stage": stage,
            "status": stage_status,
            "is_success": stage_status == self.STATUS_SUCCESS,
            "event_id": payload.get("{}_event_id".format(stage), ""),
            "service_id": service_ids[0] if service_ids else "",
            "started_at": payload.get("{}_started_at".format(stage), ""),
            "finished_at": payload.get("{}_finished_at".format(stage), ""),
        }
        if stage_status != self.STATUS_SUCCESS:
            report_payload.update({
                "failure_reason": payload.get("{}_failure_reason".format(stage), ""),
                "failure_events": payload.get("{}_failure_events".format(stage)) or [],
                "failure_logs": payload.get("{}_failure_logs".format(stage)) or [],
            })

        for _ in range(3):
            try:
                response = requests.post(self.REPORT_URL, json=report_payload, timeout=5)
                if 200 <= response.status_code < 300:
                    payload["{}_reported".format(stage)] = True
                    payload["{}_reported_at".format(stage)] = self._now()
                    enterprise_first_deploy_repo.update_payload(record, payload)
                    return
            except Exception as e:
                logger.warning("report first deploy %s stage failed: %s", stage, e)
            time.sleep(1)

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

    def _collect_failure_logs(self, tenant_name, region_name, failed_events, failure_stage):
        failure_event = self._select_failure_log_event(failed_events, failure_stage)
        if not failure_event or not tenant_name or not region_name:
            return []
        event_id = failure_event.get("event_id")
        if not event_id:
            return []
        try:
            res, body = region_api.get_events_log(tenant_name, region_name, event_id)
        except Exception as e:
            logger.warning("get %s failure logs failed: %s", failure_stage, e)
            return []
        if not self._is_success_response(res):
            return []
        lines, truncated = self._normalize_log_lines((body or {}).get("list") or [])
        if not lines:
            return []
        return [{
            "stage": failure_stage,
            "event_id": event_id,
            "source": "event_log",
            "truncated": truncated,
            "lines": lines,
        }]

    def _select_failure_log_event(self, failed_events, failure_stage):
        for event in failed_events:
            opt_type = (event.get("opt_type") or "").lower()
            if failure_stage == self.FAILURE_STAGE_BUILD and any(keyword in opt_type for keyword in self.BUILD_OPT_KEYWORDS):
                return event
            if failure_stage == self.FAILURE_STAGE_RUNTIME and self._is_runtime_failure_event(event):
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

    def _list_runtime_failure_events(self, tenant_name, region_name, service_ids, runtime_watch_started_at):
        failed_events = []
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

    def _is_runtime_failure_event(self, event):
        if event.get("status") != self.STATUS_FAILURE:
            return False
        opt_type = (event.get("opt_type") or "").lower()
        if opt_type in self.RUNTIME_FAILURE_OPT_TYPES:
            return True
        target = (event.get("target") or "").lower()
        return target == "pod"

    def _event_in_runtime_window(self, event, runtime_watch_started_at):
        event_time = self._parse_time(
            event.get("create_time") or event.get("start_time") or event.get("end_time"))
        watch_time = self._parse_time(runtime_watch_started_at)
        if not event_time or not watch_time:
            return True
        return event_time >= watch_time

    def _runtime_window_elapsed(self, runtime_watch_started_at):
        watch_time = self._parse_time(runtime_watch_started_at)
        current_time = self._parse_time(self._now())
        if not watch_time or not current_time:
            return True
        return (current_time - watch_time).total_seconds() >= self.RUNTIME_OBSERVE_WINDOW

    @staticmethod
    def _parse_time(value):
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S+08:00", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def get_deploy_type(self, service_source):
        if service_source in ("source_code", "package_build"):
            return self.DEPLOY_TYPE_SOURCE_CODE
        if service_source == "market":
            return self.DEPLOY_TYPE_APP_MARKET
        return self.DEPLOY_TYPE_IMAGE


enterprise_first_deploy_service = EnterpriseFirstDeployService()
