# -*- coding: utf-8 -*-
import json
import os
import sys
import time
from datetime import datetime
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
os.environ.setdefault("DISABLE_APP_SNAPSHOT_WORKER", "1")

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from console.models.main import ConsoleSysConfig  # noqa: E402
from console.services import app_version_auto_snapshot as snapshot_module  # noqa: E402
from www.models.main import ServiceGroup, ServiceGroupRelation  # noqa: E402


# capability_id: console.app-version.automatic-snapshots
class AutomaticAppSnapshotTests(TestCase):
    def setUp(self):
        self.service = snapshot_module.AppVersionAutoSnapshotService()
        self.tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team", enterprise_id="enterprise-1")
        self.region = SimpleNamespace(region_name="region")
        self.user = SimpleNamespace(user_id=1)
        self.app = ServiceGroup.objects.create(
            tenant_id=self.tenant.tenant_id, region_name=self.region.region_name,
            group_name="app", create_time=datetime.now(), update_time=datetime.now())
        self.events = [{"service_id": "s1", "event_id": "e1"}, {"service_id": "s2", "event_id": "e2"}]
        self.context_patch = mock.patch.object(
            self.service, "_context", return_value=(self.tenant, self.region, self.user))
        self.context_patch.start()
        self.addCleanup(self.context_patch.stop)
        self.ready_patch = mock.patch.object(self.service, "_ready", return_value=True)
        self.ready = self.ready_patch.start()
        self.addCleanup(self.ready_patch.stop)
        self.snapshot_patch = mock.patch.object(self.service, "_create_snapshot", return_value={"version_id": 10})
        self.create_snapshot = self.snapshot_patch.start()
        self.addCleanup(self.snapshot_patch.stop)
        self.api_patch = mock.patch.object(snapshot_module, "region_api")
        self.api = self.api_patch.start()
        self.addCleanup(self.api_patch.stop)
        self.api.get_tenant_events.return_value = {"list": [
            {"event_id": "e1", "status": "success"}, {"event_id": "e2", "status": "success"}]}

    def track(self, events=None):
        return self.service.track(self.tenant, self.region.region_name, self.user, self.app,
                                  self.events if events is None else events, "组件库部署成功，自动创建快照")

    def row(self):
        return ConsoleSysConfig.objects.get(key=self.service.key(self.app.ID))

    def reconcile(self):
        self.service.reconcile(self.service.key(self.app.ID))

    def test_success_creates_one_snapshot_and_duplicate_poll_is_noop(self):
        self.track()
        self.reconcile()
        self.reconcile()
        self.create_snapshot.assert_called_once()
        self.assertFalse(self.row().enable)
        self.assertEqual(json.loads(self.row().value)["status"], "success")

    def test_waits_for_every_event_and_for_runtime(self):
        self.track()
        self.api.get_tenant_events.return_value = {"list": [{"event_id": "e1", "status": "success"}]}
        self.reconcile()
        self.create_snapshot.assert_not_called()
        self.api.get_tenant_events.return_value = {"list": [
            {"event_id": "e1", "status": "success"}, {"event_id": "e2", "status": "success"}]}
        self.ready.return_value = False
        self.reconcile()
        self.create_snapshot.assert_not_called()
        self.assertTrue(self.row().enable)

    def test_failure_or_timeout_does_not_create_successful_snapshot(self):
        for status in ("failure", "timeout"):
            self.track()
            self.api.get_tenant_events.return_value = {"list": [{"event_id": "e1", "status": status}]}
            self.reconcile()
            self.create_snapshot.assert_not_called()
            self.assertFalse(self.row().enable)
            self.assertEqual(json.loads(self.row().value)["status"], "failure")

    def test_retry_replaces_failed_event_for_only_that_component(self):
        self.track()
        self.track([{"service_id": "s1", "event_id": "retry"}])
        self.assertEqual(json.loads(self.row().value)["events"], {"s1": "retry", "s2": "e2"})

    def test_empty_events_are_never_treated_as_success(self):
        self.track([])
        self.assertFalse(ConsoleSysConfig.objects.filter(key=self.service.key(self.app.ID)).exists())

    def test_transient_api_or_snapshot_error_leaves_durable_task_for_retry(self):
        self.track()
        self.create_snapshot.side_effect = RuntimeError("temporary")
        with self.assertRaises(RuntimeError):
            self.reconcile()
        self.assertTrue(self.row().enable)
        self.create_snapshot.side_effect = None
        self.reconcile()
        self.assertFalse(self.row().enable)

    def test_restart_resumes_persisted_task(self):
        self.track()
        restarted = snapshot_module.AppVersionAutoSnapshotService()
        with mock.patch.object(restarted, "_context", return_value=(self.tenant, self.region, self.user)), \
                mock.patch.object(restarted, "_ready", return_value=True), \
                mock.patch.object(restarted, "_create_snapshot") as create:
            restarted.run_once()
        create.assert_called_once()
        self.assertFalse(self.row().enable)

    def test_expired_task_cannot_create_snapshot(self):
        self.track()
        row = self.row()
        payload = json.loads(row.value)
        payload["deadline"] = time.time() - 1
        row.value = json.dumps(payload)
        row.save()
        self.reconcile()
        self.create_snapshot.assert_not_called()
        self.assertFalse(self.row().enable)

    def test_cancel_before_rollback_prevents_late_upgrade_snapshot(self):
        self.track()
        self.service.cancel(self.app.ID)
        self.reconcile()
        self.create_snapshot.assert_not_called()

    def test_new_deployment_does_not_inherit_cancelled_events(self):
        self.track()
        self.service.cancel(self.app.ID)
        self.track([{"service_id": "s1", "event_id": "after-rollback"}])
        self.assertEqual(json.loads(self.row().value)["events"], {"s1": "after-rollback"})

    def test_task_cannot_capture_another_tenants_application(self):
        self.track()
        ServiceGroup.objects.filter(ID=self.app.ID).update(tenant_id="another-tenant")
        self.reconcile()
        self.create_snapshot.assert_not_called()

    def test_final_status_failure_wins_over_success_status(self):
        self.assertFalse(self.service.events_succeeded(
            ["e1"], [{"event_id": "e1", "status": "success", "final_status": "failure"}]))
        self.assertFalse(self.service.events_succeeded([], []))
        self.assertTrue(self.service.events_succeeded(["e1"], [{"EventID": "e1", "Status": "success"}]))

    def test_region_complete_final_status_requires_successful_operation_status(self):
        self.assertTrue(self.service.events_succeeded(
            ["e1"], [{"event_id": "e1", "status": "success", "final_status": "complete"}]))
        self.assertFalse(self.service.events_succeeded(
            ["e1"], [{"event_id": "e1", "status": "checking", "final_status": "complete"}]))
        self.assertFalse(self.service.events_succeeded(
            ["e1"], [{"event_id": "e1", "status": "success", "final_status": "running"}]))

    def test_pending_deployment_blocks_upgrade_without_snapshotting_partial_state(self):
        self.track()
        self.api.get_tenant_events.return_value = {"list": []}
        with self.assertRaises(snapshot_module.ServiceHandleException):
            self.service.before_upgrade(self.tenant, self.region, self.user, self.app)
        self.create_snapshot.assert_not_called()

    def test_upgrade_baseline_is_captured_before_creating_successful_version(self):
        self.service.before_upgrade(self.tenant, self.region, self.user, self.app)
        self.create_snapshot.assert_called_once_with(self.tenant, self.region, self.user, self.app, "组件库升级前自动快照")

    def test_upgrade_dispatch_cannot_be_overwritten_by_ordinary_component_deployment(self):
        self.service.before_upgrade(self.tenant, self.region, self.user, self.app)
        self.track()
        self.assertEqual(json.loads(self.row().value)["status"], "dispatching")
        self.reconcile()
        self.assertEqual(self.create_snapshot.call_count, 1)

    def test_upgrade_dispatch_changes_to_pending_only_for_upgrade_events(self):
        self.service.before_upgrade(self.tenant, self.region, self.user, self.app)
        self.service.track(self.tenant, self.region.region_name, self.user, self.app,
                           self.events, "组件库升级成功，自动创建快照", upgrade=True)
        self.reconcile()
        self.assertEqual(self.create_snapshot.call_count, 2)

    def test_unrelated_failure_event_does_not_fail_task(self):
        self.track()
        self.api.get_tenant_events.return_value["list"].append({"event_id": "unrelated", "status": "failure"})
        self.reconcile()
        self.create_snapshot.assert_called_once()

    def test_status_exposes_only_public_state_and_cancelled_task_is_inactive(self):
        self.track()
        self.assertEqual(self.service.status(self.app), {"status": "pending"})
        self.service.cancel(self.app.ID)
        self.assertEqual(self.service.status(self.app), {})

    def test_bulk_component_deploy_tracks_only_market_components_in_their_current_application(self):
        ServiceGroupRelation.objects.create(service_id="s1", group_id=self.app.ID,
                                            tenant_id=self.tenant.tenant_id, region_name=self.region.region_name)
        market = SimpleNamespace(service_id="s1", service_source="market")
        source = SimpleNamespace(service_id="s2", service_source="source_code")
        self.service.safe_track_components(self.tenant, self.region.region_name, self.user, [market, source], self.events)
        self.assertEqual(json.loads(self.row().value)["events"], {"s1": "e1"})

    def test_snapshot_baseline_failure_does_not_leave_upgrade_dispatching(self):
        self.create_snapshot.side_effect = RuntimeError("temporary")
        with self.assertRaises(RuntimeError):
            self.service.before_upgrade(self.tenant, self.region, self.user, self.app)
        self.assertFalse(ConsoleSysConfig.objects.filter(key=self.service.key(self.app.ID), enable=True).exists())

    def test_unsupported_vm_snapshot_does_not_block_existing_upgrade_or_create_partial_snapshot(self):
        with mock.patch.object(self.service, "_components", return_value=[SimpleNamespace(service_source="vm_run")]):
            self.service.before_upgrade(self.tenant, self.region, self.user, self.app)
            self.track()
        self.create_snapshot.assert_not_called()
        self.assertFalse(ConsoleSysConfig.objects.filter(key=self.service.key(self.app.ID)).exists())

    def test_scan_continues_after_one_task_fails(self):
        self.track()
        with mock.patch.object(self.service, "reconcile", side_effect=RuntimeError("temporary")):
            self.service.run_once()
        self.assertTrue(self.row().enable)

    def test_noop_upgrade_releases_dispatch_without_claiming_a_new_version(self):
        self.service.before_upgrade(self.tenant, self.region, self.user, self.app)
        self.service.track(self.tenant, self.region.region_name, self.user, self.app, [], "noop", upgrade=True)
        self.assertFalse(self.row().enable)
        self.assertEqual(self.create_snapshot.call_count, 1)


# capability_id: console.app-version.automatic-snapshot-readiness
class AutomaticSnapshotReadinessTests(TestCase):
    def test_incomplete_or_missing_runtime_component_prevents_snapshot(self):
        service = snapshot_module.AppVersionAutoSnapshotService()
        tenant = SimpleNamespace(tenant_id="tenant", tenant_name="team", enterprise_id="enterprise")
        app = SimpleNamespace(ID=1, tenant_id="tenant", region_name="region")
        component = SimpleNamespace(service_id="s", tenant_id="tenant", service_region="region",
                                    create_status="complete", service_source="market")
        with mock.patch.object(service, "_components", return_value=[component]), \
                mock.patch.object(snapshot_module, "region_api") as api:
            api.service_status.return_value = {"list": []}
            self.assertFalse(service._ready(tenant, app))
            api.service_status.return_value = {"list": [{"service_id": "s", "status": "running"}]}
            self.assertTrue(service._ready(tenant, app))
            component.create_status = "creating"
            self.assertFalse(service._ready(tenant, app))
