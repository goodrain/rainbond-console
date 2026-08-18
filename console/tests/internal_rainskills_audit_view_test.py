# -*- coding: utf-8 -*-
import hashlib
import uuid

from django.test import TestCase, override_settings
from django.urls import resolve
from rest_framework.test import APIRequestFactory

from console.repositories.rainskills_audit_repo import rainskills_audit_repo
from console.views.internal_rainskills_audit import (
    InternalRainSkillsAuditEventsView,
    InternalRainSkillsSkillSnapshotView,
)
from www.models.main import TenantEnterprise, Users


@override_settings(INTERNAL_API_TOKEN="legacy-global-internal-token")
class InternalRainSkillsAuditViewTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = Users.objects.create(
            email="admin@example.com",
            nick_name="admin",
            password="unused",
            is_active=True,
            sys_admin=True,
            enterprise_id="enterprise-1",
        )
        for enterprise_id in ("enterprise-1", "enterprise-2"):
            TenantEnterprise.objects.create(
                enterprise_id=enterprise_id,
                enterprise_name=enterprise_id,
            )
        content = "# Enterprise Skill\n"
        self.skill = {
            "id": "rainbond-fullstack-bootstrap",
            "profile": "cli",
            "package_version": "1.0.0",
            "source_revision": None,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "bundle_sha256": "b" * 64,
            "content": content,
        }
        self.snapshot, _ = rainskills_audit_repo.get_or_create_snapshot("enterprise-1", self.skill)
        rainskills_audit_repo.begin_operation(
            enterprise_id="enterprise-1",
            operation_id=str(uuid.uuid4()),
            user_id=str(self.admin.user_id),
            username="admin",
            deploy_client="codex",
            snapshot=self.snapshot,
            skill_id=self.skill["id"],
            root_skill_id="rainbond-app-assistant",
            tool_name="rainbond_create_app",
            operation_class="write",
            risk="medium",
            scope="team",
            arguments_digest="a" * 64,
            input_json={"app_name": "demo"},
            target_context={"app_id": 7},
            confirmation_type="rainskills_cli",
        )

    def _get(self, path, token="enterprise-1", remote_addr="10.0.0.12", **headers):
        return self.factory.get(
            path,
            HTTP_X_INTERNAL_TOKEN=token,
            REMOTE_ADDR=remote_addr,
            **headers
        )

    def test_enterprise_token_reads_only_its_cursor_events_without_snapshot_content(self):
        view = InternalRainSkillsAuditEventsView.as_view()
        response = view(self._get(
            "/console/internal/agent-rainskills-audit/events?after_cursor=0&limit=100"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        event = response.data["data"][0]["event"]
        self.assertEqual(event["operation"]["enterprise_id"], "enterprise-1")
        self.assertNotIn("content", event["skill"])
        self.assertFalse(response.data["meta"]["has_more"])

    def test_global_token_and_proxied_request_are_rejected(self):
        view = InternalRainSkillsAuditEventsView.as_view()

        global_response = view(self._get(
            "/console/internal/agent-rainskills-audit/events",
            token="legacy-global-internal-token",
        ))
        proxy_response = view(self._get(
            "/console/internal/agent-rainskills-audit/events",
            HTTP_X_FORWARDED_FOR="203.0.113.8",
        ))

        self.assertEqual(global_response.status_code, 401)
        self.assertEqual(proxy_response.status_code, 401)

    def test_snapshot_lookup_is_enterprise_bound_and_returns_plain_content(self):
        path = (
            "/console/internal/agent-rainskills-audit/skill-snapshots/{}"
            "?skill_id={}&profile=cli"
        ).format(self.skill["content_sha256"], self.skill["id"])
        view = InternalRainSkillsSkillSnapshotView.as_view()

        found = view(self._get(path), content_sha256=self.skill["content_sha256"])
        hidden = view(
            self._get(path, token="enterprise-2"),
            content_sha256=self.skill["content_sha256"],
        )

        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.data["data"]["content"], self.skill["content"])
        self.assertEqual(hidden.status_code, 404)

    def test_invalid_cursor_and_limit_are_rejected(self):
        view = InternalRainSkillsAuditEventsView.as_view()
        for query in ("after_cursor=-1", "after_cursor=bad", "limit=0", "limit=501"):
            with self.subTest(query=query):
                response = view(self._get(
                    "/console/internal/agent-rainskills-audit/events?{}".format(query)))
                self.assertEqual(response.status_code, 400)

    def test_internal_urls_resolve_to_enterprise_bound_views(self):
        events = resolve("/console/internal/agent-rainskills-audit/events")
        snapshot = resolve(
            "/console/internal/agent-rainskills-audit/skill-snapshots/{}".format("a" * 64))
        self.assertIs(events.func.view_class, InternalRainSkillsAuditEventsView)
        self.assertIs(snapshot.func.view_class, InternalRainSkillsSkillSnapshotView)
