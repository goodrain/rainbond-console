# -*- coding: utf-8 -*-
import hashlib
import uuid
from datetime import datetime
from unittest.mock import patch

from django.test import TestCase

from console.repositories.rainskills_audit_repo import rainskills_audit_repo


class RainSkillsAuditRepositoryTests(TestCase):

    def setUp(self):
        self.content = "# Audited Skill\n"
        self.skill = {
            "id": "rainbond-fullstack-bootstrap",
            "profile": "cli",
            "package_version": "1.0.0",
            "source_revision": "revision-1",
            "content_sha256": hashlib.sha256(self.content.encode("utf-8")).hexdigest(),
            "bundle_sha256": "b" * 64,
            "content": self.content,
        }

    def _begin(self, enterprise_id="enterprise-1", operation_id=None, snapshot=None):
        return rainskills_audit_repo.begin_operation(
            enterprise_id=enterprise_id,
            operation_id=operation_id or str(uuid.uuid4()),
            user_id="42",
            username="operator",
            deploy_client="codex",
            snapshot=snapshot,
            skill_id=self.skill["id"] if snapshot else None,
            root_skill_id="rainbond-app-assistant" if snapshot else None,
            tool_name="rainbond_create_app",
            operation_class="write",
            risk="medium",
            scope="team",
            arguments_digest="a" * 64,
            input_json={"app_name": "demo"},
            target_context={"app_id": 7},
            confirmation_type="rainskills_cli" if snapshot else "legacy_compat",
        )

    def test_snapshot_deduplicates_within_enterprise_but_not_across_enterprises(self):
        first, first_created = rainskills_audit_repo.get_or_create_snapshot("enterprise-1", self.skill)
        second, second_created = rainskills_audit_repo.get_or_create_snapshot("enterprise-1", self.skill)
        isolated, isolated_created = rainskills_audit_repo.get_or_create_snapshot("enterprise-2", self.skill)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertTrue(isolated_created)
        self.assertEqual(first.pk, second.pk)
        self.assertNotEqual(first.pk, isolated.pk)

    def test_begin_is_idempotent_and_creates_only_one_started_event(self):
        snapshot, _ = rainskills_audit_repo.get_or_create_snapshot("enterprise-1", self.skill)
        operation_id = str(uuid.uuid4())

        first, owner = self._begin(operation_id=operation_id, snapshot=snapshot)
        second, second_owner = self._begin(operation_id=operation_id, snapshot=snapshot)

        self.assertTrue(owner)
        self.assertFalse(second_owner)
        self.assertEqual(first.pk, second.pk)
        events = rainskills_audit_repo.list_events("enterprise-1", after_cursor=0, limit=100)
        self.assertEqual([event.event_type for event in events], ["operation_started"])

    def test_events_are_enterprise_isolated_and_cursor_ordered(self):
        first, _ = self._begin(enterprise_id="enterprise-1")
        second, _ = self._begin(enterprise_id="enterprise-1")
        self._begin(enterprise_id="enterprise-2")
        rainskills_audit_repo.finalize_operation(first, status="succeeded", output_summary="ok")
        rainskills_audit_repo.finalize_operation(
            second, status="failed", error_code="conflict", error_message="failed")

        events = rainskills_audit_repo.list_events("enterprise-1", after_cursor=0, limit=100)
        event_ids = [event.id for event in events]
        self.assertEqual(event_ids, sorted(event_ids))
        self.assertTrue(all(event.enterprise_id == "enterprise-1" for event in events))
        self.assertEqual(len(events), 4)

        tail = rainskills_audit_repo.list_events("enterprise-1", after_cursor=event_ids[1], limit=100)
        self.assertEqual([event.id for event in tail], event_ids[2:])

    def test_snapshot_lookup_is_bound_to_enterprise_skill_and_profile(self):
        snapshot, _ = rainskills_audit_repo.get_or_create_snapshot("enterprise-1", self.skill)

        self.assertEqual(
            rainskills_audit_repo.get_snapshot(
                "enterprise-1", self.skill["id"], "cli", self.skill["content_sha256"]).pk,
            snapshot.pk,
        )
        self.assertIsNone(rainskills_audit_repo.get_snapshot(
            "enterprise-2", self.skill["id"], "cli", self.skill["content_sha256"]))

    def test_events_publish_asia_shanghai_rfc3339_timestamps(self):
        local_time = datetime(2026, 8, 19, 17, 55, 0)
        with patch(
                "console.repositories.rainskills_audit_repo.timezone.now",
                return_value=local_time):
            operation, _ = self._begin()
            rainskills_audit_repo.finalize_operation(operation, status="succeeded")

        events = rainskills_audit_repo.list_events("enterprise-1", after_cursor=0, limit=100)
        started_payload = events[0].payload
        finished_payload = events[1].payload

        self.assertEqual(started_payload["occurred_at"], "2026-08-19T17:55:00+08:00")
        self.assertEqual(
            started_payload["operation"]["started_at"],
            "2026-08-19T17:55:00+08:00",
        )
        self.assertEqual(
            finished_payload["operation"]["finished_at"],
            "2026-08-19T17:55:00+08:00",
        )
