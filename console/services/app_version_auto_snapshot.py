# -*- coding: utf-8 -*-
"""Durable, application-scoped snapshots after successful market deployments."""
import json
import logging
import os
import threading
import time

from django.db import close_old_connections, connections, transaction

from console.exception.main import ServiceHandleException
from console.models.main import ConsoleSysConfig, RegionConfig
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroup, ServiceGroupRelation, Tenants, Users

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppVersionAutoSnapshotService:
    PREFIX = "APP_SNAPSHOT_"
    DESC = "application automatic snapshot"
    INTERVAL = 10
    TIMEOUT = 20 * 60

    def __init__(self, start_worker=False):
        if start_worker and os.getenv("DISABLE_APP_SNAPSHOT_WORKER") != "1":
            worker = threading.Thread(target=self._run, name="app-version-snapshots", daemon=True)
            worker.start()

    @classmethod
    def key(cls, app_id):
        return "{}{}".format(cls.PREFIX, app_id)

    @staticmethod
    def _event_result(item):
        status = item.get("status") or item.get("Status")
        final = item.get("final_status") or item.get("FinalStatus")
        if status in ("failure", "timeout") or final in ("failure", "timeout"):
            return "failure"
        if status == "success" and final in (None, "", "success", "complete", "emptycomplete"):
            return "success"
        return None

    @classmethod
    def events_succeeded(cls, event_ids, events):
        statuses = {}
        for item in events:
            event_id = item.get("event_id") or item.get("EventID")
            statuses.setdefault(event_id, []).append(cls._event_result(item))
        return bool(event_ids) and all(statuses.get(event_id) and all(value == "success" for value in statuses[event_id])
                                       for event_id in event_ids)

    def track(self, tenant, region_name, user, app, events, description, upgrade=False):
        if not self._supported(app):
            return
        event_map = {str(item["service_id"]): str(item["event_id"]) for item in events
                     if item.get("service_id") and item.get("event_id")}
        if not event_map:
            if upgrade:
                self.cancel(app.ID)
            return
        with transaction.atomic():
            ServiceGroup.objects.select_for_update().get(ID=app.ID, tenant_id=tenant.tenant_id, region_name=region_name)
            row = ConsoleSysConfig.objects.filter(key=self.key(app.ID)).first()
            previous = json.loads(row.value) if row and row.value else {}
            if row and row.enable and previous.get("status") == "dispatching" and not upgrade:
                return
            if previous.get("status") in ("pending", "failure"):
                event_map = dict(previous.get("events") or {}, **event_map)
            payload = {
                "app_id": app.ID, "tenant_id": tenant.tenant_id, "region_name": region_name,
                "user_id": user.user_id, "events": event_map, "description": description,
                "deadline": time.time() + self.TIMEOUT, "status": "pending",
            }
            ConsoleSysConfig.objects.update_or_create(key=self.key(app.ID), defaults={
                "type": "json", "value": json.dumps(payload, ensure_ascii=False),
                "desc": self.DESC, "enable": True, "enterprise_id": tenant.enterprise_id or "",
            })

    def safe_track_components(self, tenant, region_name, user, services, events):
        """Also cover installing without deployment, followed by component/batch deployment."""
        market_ids = {service.service_id for service in services if service.service_source == "market"}
        if not market_ids:
            return
        try:
            relations = ServiceGroupRelation.objects.filter(tenant_id=tenant.tenant_id, service_id__in=market_ids)
            by_app = {}
            for relation in relations:
                by_app.setdefault(relation.group_id, set()).add(relation.service_id)
            for app in ServiceGroup.objects.filter(ID__in=by_app, tenant_id=tenant.tenant_id, region_name=region_name):
                app_events = [item for item in events if item.get("service_id") in by_app[app.ID]]
                self.track(tenant, region_name, user, app, app_events, "组件库组件部署成功，自动创建快照")
        except Exception:
            # The deployment was already accepted by Region. Never report it as failed because of bookkeeping.
            logger.exception("could not register automatic application snapshot")

    def before_upgrade(self, tenant, region, user, app):
        if not self._supported(app):
            return
        with transaction.atomic():
            ServiceGroup.objects.select_for_update().get(
                ID=app.ID, tenant_id=tenant.tenant_id, region_name=region.region_name)
            self.reconcile(self.key(app.ID))
            if ConsoleSysConfig.objects.filter(key=self.key(app.ID), enable=True).exists():
                raise ServiceHandleException("application deployment pending", "应用仍在部署中，请等待部署完成后再升级", status_code=409)
            self._create_snapshot(tenant, region, user, app, "组件库升级前自动快照")
            ConsoleSysConfig.objects.update_or_create(key=self.key(app.ID), defaults={
                "type": "json", "desc": self.DESC, "enable": True, "enterprise_id": tenant.enterprise_id or "",
                "value": json.dumps({
                    "app_id": app.ID, "tenant_id": tenant.tenant_id, "region_name": region.region_name,
                    "user_id": user.user_id, "events": {}, "status": "dispatching",
                    "deadline": time.time() + self.TIMEOUT,
                }),
            })

    def cancel(self, app_id):
        with transaction.atomic():
            ServiceGroup.objects.select_for_update().filter(ID=app_id).first()
            row = ConsoleSysConfig.objects.filter(key=self.key(app_id), desc=self.DESC).first()
            if row:
                self._finish(row, json.loads(row.value), "cancelled")

    def status(self, app):
        row = ConsoleSysConfig.objects.filter(key=self.key(app.ID), desc=self.DESC).first()
        if not row or not row.value:
            return {}
        payload = json.loads(row.value)
        if payload.get("tenant_id") != app.tenant_id or payload.get("region_name") != app.region_name:
            return {}
        state = payload.get("status")
        if state in ("pending", "dispatching") and not row.enable:
            return {}
        return {"status": state} if state in ("pending", "dispatching", "success", "failure", "expired") else {}

    @staticmethod
    def _context(payload):
        return (
            Tenants.objects.get(tenant_id=payload["tenant_id"]),
            RegionConfig.objects.get(region_name=payload["region_name"]),
            Users.objects.get(user_id=payload["user_id"]),
        )

    @staticmethod
    def _components(app):
        from console.services.group_service import group_service
        return list(group_service.get_group_services(app.ID))

    def _supported(self, app):
        # These workloads retain their existing specialized backup/rollback paths.
        return not any(item.service_source in ("vm_run", "kubeblocks") for item in self._components(app))

    def acknowledge_manual_snapshot(self, app, captured_service_ids):
        if not captured_service_ids:
            return
        with transaction.atomic():
            locked_app = ServiceGroup.objects.select_for_update().filter(
                ID=app.ID, tenant_id=app.tenant_id, region_name=app.region_name).first()
            if not locked_app:
                return
            row = ConsoleSysConfig.objects.filter(key=self.key(app.ID), desc=self.DESC, enable=False).first()
            if not row:
                return
            try:
                payload = json.loads(row.value)
            except (TypeError, ValueError):
                return
            if not isinstance(payload, dict) or payload.get("status") not in ("failure", "expired"):
                return
            if (payload.get("app_id") != app.ID or payload.get("tenant_id") != app.tenant_id
                    or payload.get("region_name") != app.region_name):
                return
            expected = {item.service_id for item in self._components(locked_app)
                        if item.service_source not in ("third_party", "kubeblocks")}
            if expected and expected.issubset(set(captured_service_ids)):
                self._finish(row, payload, "cancelled")

    def _ready(self, tenant, app, required_running=None):
        components = self._components(app)
        if not components or any(item.create_status != "complete" or item.tenant_id != tenant.tenant_id
                                 or item.service_region != app.region_name for item in components):
            return False
        components = [item for item in components if item.service_source != "third_party"]
        service_ids = {item.service_id for item in components}
        required_running = service_ids if required_running is None else set(required_running)
        if not service_ids or not required_running.issubset(service_ids):
            return False
        body = region_api.service_status(app.region_name, tenant.tenant_name, {
            "service_ids": sorted(service_ids), "enterprise_id": tenant.enterprise_id,
        }) or {}
        statuses = {item.get("service_id"): item.get("status") for item in body.get("list") or []}
        return all(statuses.get(item.service_id) == "running" or (
            item.service_id not in required_running and statuses.get(item.service_id) == "closed"
            and bool(getattr(item, "deploy_version", ""))) for item in components)

    @staticmethod
    def _create_snapshot(tenant, region, user, app, description):
        from console.services.app_version_service import app_version_service
        return app_version_service.create_snapshot(
            tenant, region, user, app, app_version_info=description, require_complete=True)

    @staticmethod
    def _finish(row, payload, status):
        payload["status"] = status
        row.value = json.dumps(payload, ensure_ascii=False)
        row.enable = False
        row.save(update_fields=["value", "enable"])

    def reconcile(self, key):
        row = ConsoleSysConfig.objects.filter(key=key, desc=self.DESC, enable=True).first()
        if not row:
            return
        payload = json.loads(row.value)
        with transaction.atomic():
            app = ServiceGroup.objects.select_for_update().filter(
                ID=payload["app_id"], tenant_id=payload["tenant_id"], region_name=payload["region_name"]).first()
            # Re-read after acquiring the app lock: another process may have completed/replaced the task.
            row = ConsoleSysConfig.objects.filter(key=key, desc=self.DESC, enable=True).first()
            if not row:
                return
            payload = json.loads(row.value)
            if not app or payload["deadline"] < time.time():
                self._finish(row, payload, "expired")
                return
            if payload.get("status") == "dispatching":
                return
            tenant, region, user = self._context(payload)
            event_ids = list(payload["events"].values())
            body = region_api.get_tenant_events(region.region_name, tenant.tenant_name, event_ids) or {}
            events = body.get("list") or []
            failures = [item for item in events if (item.get("event_id") or item.get("EventID")) in event_ids
                        and self._event_result(item) == "failure"]
            if failures:
                self._finish(row, payload, "failure")
                return
            if not self.events_succeeded(event_ids, events) or not self._ready(tenant, app, set(payload["events"])):
                return
            self._create_snapshot(tenant, region, user, app, payload["description"])
            self._finish(row, payload, "success")

    def run_once(self):
        keys = list(ConsoleSysConfig.objects.filter(
            desc=self.DESC, enable=True, key__startswith=self.PREFIX).values_list("key", flat=True)[:100])
        for key in keys:
            try:
                self.reconcile(key)
            except Exception:
                logger.exception("automatic application snapshot will be retried: %s", key)

    def _run(self):
        while True:
            time.sleep(self.INTERVAL)
            try:
                close_old_connections()
                self.run_once()
            except Exception:
                logger.exception("automatic application snapshot scan failed")
            finally:
                connections.close_all()


# Retain the legacy service for compatibility without resuming template-triggered snapshot jobs.
app_version_auto_snapshot_service = AppVersionAutoSnapshotService()
