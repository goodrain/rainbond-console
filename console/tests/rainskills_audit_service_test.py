# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from console.exception.main import ServiceHandleException
from console.services.rainskills_audit_service import (
    RainSkillsAuditContext,
    _safe_input,
    _safe_summary,
    _target_context,
    rainskills_audit_service,
)


class RainSkillsAuditServiceSafetyTests(SimpleTestCase):

    def setUp(self):
        self.user = SimpleNamespace(
            enterprise_id="enterprise-1",
            user_id=7,
            nick_name="operator",
        )

    def test_sensitive_arguments_and_terminal_text_are_redacted(self):
        safe_input = _safe_input({
            "password": "password-value",
            "api_key": "api-key-value",
            "cookie": "cookie-value",
            "kubeconfig": "kubeconfig-value",
            "certificate": "certificate-value",
            "nested": {"private_key": "private-key-value"},
            "app_name": "demo",
        }, "a" * 64)

        self.assertEqual(safe_input["app_name"], "demo")
        for key in ("password", "api_key", "cookie", "kubeconfig", "certificate"):
            self.assertEqual(safe_input[key], "[REDACTED]")
        self.assertEqual(safe_input["nested"]["private_key"], "[REDACTED]")

        summary = _safe_summary(
            "password=one api_key=two cookie=three kubeconfig=four certificate=five")
        for secret in ("one", "two", "three", "four", "five"):
            self.assertNotIn(secret, summary)

    @patch("console.services.rainskills_audit_service.team_repo.get_team_by_team_name")
    @patch("console.services.rainskills_audit_service.service_repo.get_service_by_tenant_and_id")
    def test_component_target_context_resolves_navigation_alias(self, get_service, get_team):
        get_team.return_value = SimpleNamespace(tenant_id="tenant-id-1")
        get_service.return_value = SimpleNamespace(
            service_alias="gr-api",
            service_cname="api",
        )

        context = _target_context({
            "team_name": "demo-team",
            "region_name": "rainbond",
            "app_id": 12,
            "service_id": "8fdb8ad75494e14320a0ba0120e02326",
        })

        get_team.assert_called_once_with("demo-team")
        get_service.assert_called_once_with(
            "tenant-id-1", "8fdb8ad75494e14320a0ba0120e02326")
        self.assertEqual(context["service_id"], "8fdb8ad75494e14320a0ba0120e02326")
        self.assertEqual(context["service_alias"], "gr-api")
        self.assertEqual(context["service_cname"], "api")

    @patch("console.services.rainskills_audit_service.get_deployment_invocation")
    @patch("console.services.rainskills_audit_service.rainskills_audit_repo")
    def test_legacy_write_begins_durable_audit_with_server_owned_context(self, repo, invocation):
        operation = SimpleNamespace(pk=1)
        invocation.return_value = SimpleNamespace(client="api")
        repo.get_operation.return_value = None
        repo.begin_operation.return_value = (operation, True)

        context = rainskills_audit_service.begin(
            self.user,
            "rainbond_create_app",
            {"app_name": "demo", "token": "secret-value"},
            {},
        )

        self.assertEqual(context, RainSkillsAuditContext(operation=operation))
        values = repo.begin_operation.call_args.kwargs
        self.assertEqual(values["enterprise_id"], "enterprise-1")
        self.assertEqual(values["deploy_client"], "api")
        self.assertEqual(values["confirmation_type"], "legacy_compat")
        self.assertEqual(values["input_json"]["token"], "[REDACTED]")
        self.assertEqual(values["tool_name"], "rainbond_create_app")

    @override_settings(RAINSKILLS_AUDIT_STRICT=True)
    def test_strict_mode_rejects_write_without_confirmation_metadata(self):
        with self.assertRaises(ServiceHandleException) as raised:
            rainskills_audit_service.begin(
                self.user,
                "rainbond_create_app",
                {"app_name": "demo"},
                {},
            )

        self.assertEqual(raised.exception.status_code, 428)
        self.assertEqual(raised.exception.error_code, "operation_confirmation_required")

    def test_read_and_empty_terminal_contexts_bypass_persistence(self):
        self.assertIsNone(rainskills_audit_service.begin(
            self.user,
            "rainbond_get_current_user",
            {},
            {},
        ))
        rainskills_audit_service.finalize_success(None, {"user_id": 7})
        rainskills_audit_service.finalize_failure(None, RuntimeError("unused"))

    @patch("console.services.rainskills_audit_service.rainskills_audit_repo")
    def test_started_persistence_failure_is_fail_closed(self, repo):
        repo.get_operation.side_effect = RuntimeError("database unavailable")

        with self.assertRaises(ServiceHandleException) as raised:
            rainskills_audit_service.begin(
                self.user,
                "rainbond_create_app",
                {"app_name": "demo"},
                {},
            )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.error_code, "audit_unavailable")

    @patch("console.services.rainskills_audit_service.rainskills_audit_repo")
    def test_existing_operation_is_not_replayed(self, repo):
        repo.get_operation.return_value = SimpleNamespace(pk=1)
        repo.binding_matches.return_value = True

        with self.assertRaises(ServiceHandleException) as raised:
            rainskills_audit_service.begin(
                self.user,
                "rainbond_create_app",
                {"app_name": "demo"},
                {},
            )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.error_code, "operation_already_recorded")

    @patch("console.services.rainskills_audit_service.rainskills_audit_repo")
    def test_terminal_results_are_redacted_and_persisted(self, repo):
        operation = SimpleNamespace(pk=1)
        context = RainSkillsAuditContext(operation=operation)

        rainskills_audit_service.finalize_success(
            context, {"token": "secret-value", "app_id": 7})
        success_values = repo.finalize_operation.call_args.kwargs
        self.assertEqual(success_values["status"], "succeeded")
        self.assertNotIn("secret-value", success_values["output_summary"])

        failure = ServiceHandleException(
            msg="conflict",
            msg_show="password=secret-value",
            status_code=409,
            error_code="resource_conflict",
        )
        rainskills_audit_service.finalize_failure(context, failure)
        failure_values = repo.finalize_operation.call_args.kwargs
        self.assertEqual(failure_values["status"], "failed")
        self.assertEqual(failure_values["error_code"], "resource_conflict")
        self.assertNotIn("secret-value", failure_values["error_message"])
