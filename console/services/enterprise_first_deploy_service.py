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
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"
    FINAL_STATUSES = {STATUS_SUCCESS, STATUS_FAILURE}
    POLL_INTERVAL = 5
    POLL_TIMEOUT = 60 * 20
    DEPLOY_TYPE_SOURCE_CODE = "source_code"
    DEPLOY_TYPE_APP_MARKET = "app_market"
    DEPLOY_TYPE_IMAGE = "image"

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

    def mark_failure(self, tracker):
        if not tracker:
            return
        record = enterprise_first_deploy_repo.get_by_enterprise_id(tracker["enterprise_id"])
        if not record:
            return
        payload = enterprise_first_deploy_repo.load_payload(record)
        if payload.get("status") in self.FINAL_STATUSES:
            self._report_if_needed(record, payload)
            return
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
            "status": self.STATUS_PENDING,
            "reported": False,
            "reported_at": "",
            "started_at": self._now(),
            "finished_at": "",
            "tenant_name": tenant_name,
            "region_name": region_name,
            "operator": operator or "",
            "event_ids": [],
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

        if any(status == self.STATUS_FAILURE for status in status_map.values()):
            self._finalize_record(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

        if len(status_map) < len(set(event_ids)):
            return None

        normalized = set(status_map.values())
        if normalized == {self.STATUS_SUCCESS}:
            self._finalize_record(record, payload, self.STATUS_SUCCESS)
            return self.STATUS_SUCCESS

        if "timeout" in normalized:
            self._finalize_record(record, payload, self.STATUS_FAILURE)
            return self.STATUS_FAILURE

        if self.STATUS_FAILURE in normalized:
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

    def get_deploy_type(self, service_source):
        if service_source in ("source_code", "package_build"):
            return self.DEPLOY_TYPE_SOURCE_CODE
        if service_source == "market":
            return self.DEPLOY_TYPE_APP_MARKET
        return self.DEPLOY_TYPE_IMAGE


enterprise_first_deploy_service = EnterpriseFirstDeployService()
