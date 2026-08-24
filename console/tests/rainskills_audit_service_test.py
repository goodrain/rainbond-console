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
from console.services.rainskills_tool_audit_policy import classify_tool


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
    @patch("console.services.rainskills_audit_service.group_service_relation_repo.list_serivce_ids_by_app_id")
    @patch("console.services.rainskills_audit_service.service_repo.get_service_by_tenant_and_id")
    def test_component_target_context_resolves_navigation_alias(
            self, get_service, list_app_service_ids, get_team):
        get_team.return_value = SimpleNamespace(tenant_id="tenant-id-1")
        list_app_service_ids.return_value = ["8fdb8ad75494e14320a0ba0120e02326"]
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

    @patch("console.services.rainskills_audit_service.team_repo.get_team_by_team_name")
    @patch("console.services.rainskills_audit_service.group_service_relation_repo.list_serivce_ids_by_app_id")
    @patch("console.services.rainskills_audit_service.service_repo.get_services_by_service_ids")
    def test_component_target_context_resolves_multiple_targets_in_input_order(
            self, get_services, list_app_service_ids, get_team):
        get_team.return_value = SimpleNamespace(tenant_id="tenant-id-1")
        list_app_service_ids.return_value = ["service-1", "service-2"]
        get_services.return_value = [
            SimpleNamespace(
                tenant_id="tenant-id-1", service_id="service-2",
                service_alias="gr-two", service_cname="two"),
            SimpleNamespace(
                tenant_id="tenant-id-1", service_id="service-1",
                service_alias="gr-one", service_cname="one"),
        ]

        arguments = {
            "team_name": "demo-team",
            "region_name": "rainbond",
            "app_id": 12,
            "action": "restart",
            "service_ids": ["service-1", "service-2"],
        }
        context = _target_context(
            arguments, classify_tool("rainbond_operate_app", arguments),
            "rainbond_operate_app")

        self.assertEqual(context["service_ids"], ["service-1", "service-2"])
        self.assertEqual(context["operation_descriptor"], {
            "schema": "rainskills.audit-operation.v1",
            "effect": "write",
            "action": "restart",
            "resource_type": "component_runtime",
            "scope": "app",
            "target_mode": "multiple",
            "targets": [
                {"type": "component", "id": "service-1", "navigation_id": "gr-one", "name": "one"},
                {"type": "component", "id": "service-2", "navigation_id": "gr-two", "name": "two"},
            ],
        })

    def test_whole_app_operation_has_all_target_descriptor(self):
        arguments = {
            "team_name": "demo-team",
            "region_name": "rainbond",
            "app_id": 12,
            "action": "start",
        }
        context = _target_context(
            arguments, classify_tool("rainbond_operate_app", arguments),
            "rainbond_operate_app")

        self.assertEqual(context["operation_descriptor"]["scope"], "app")
        self.assertEqual(context["operation_descriptor"]["target_mode"], "all")
        self.assertEqual(context["operation_descriptor"]["targets"], [])

    @patch("console.services.rainskills_audit_service.team_repo.get_team_by_team_name")
    @patch("console.services.rainskills_audit_service.group_service_relation_repo.list_serivce_ids_by_app_id")
    @patch("console.services.rainskills_audit_service.service_repo.get_services_by_service_ids")
    def test_component_names_are_not_projected_across_app_boundaries(
            self, get_services, list_app_service_ids, get_team):
        get_team.return_value = SimpleNamespace(
            tenant_id="tenant-id-1", enterprise_id="enterprise-1")
        list_app_service_ids.return_value = ["service-in-app"]
        get_services.return_value = [SimpleNamespace(
            tenant_id="tenant-id-1", service_id="service-other-app",
            service_alias="gr-secret", service_cname="secret-component")]
        arguments = {
            "team_name": "demo-team", "region_name": "rainbond", "app_id": 12,
            "action": "restart", "service_ids": ["service-other-app"],
        }

        context = _target_context(
            arguments, classify_tool("rainbond_operate_app", arguments),
            "rainbond_operate_app", "enterprise-1")

        self.assertEqual(context["operation_descriptor"]["targets"], [
            {"type": "component", "id": "service-other-app"},
        ])
        self.assertNotIn("secret-component", str(context))

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

    @patch("console.services.rainskills_audit_service.rainskills_audit_repo")
    def test_read_variant_of_mixed_tool_bypasses_persistence(self, repo):
        context = rainskills_audit_service.begin(
            self.user,
            "rainbond_manage_component_envs",
            {"operation": "summary", "service_id": "service-1"},
            {},
        )

        self.assertIsNone(context)
        repo.begin_operation.assert_not_called()

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
