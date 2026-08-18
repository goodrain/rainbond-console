# -*- coding: utf-8 -*-
import json
import os
import sys
from contextvars import Context
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402
from django.urls import resolve  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.deployment_invocation import (  # noqa: E402
    DeploymentInvocation,
    deployment_invocation_context,
    get_deployment_invocation,
    is_rainskills_invocation,
)
from console.services.rainskills_deployment_service import DeploymentSpec  # noqa: E402
from console.services.mcp_query_service import mcp_query_service  # noqa: E402
from console.views.mcp_query import MCPQueryHTTPView  # noqa: E402


class DeploymentInvocationContextTests(SimpleTestCase):
    def test_default_invocation_is_unknown(self):
        self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="unknown", client="unknown"))
        self.assertFalse(is_rainskills_invocation())

    def test_nested_contexts_restore_the_previous_invocation(self):
        with deployment_invocation_context("rainskills", "codex"):
            self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="rainskills", client="codex"))
            self.assertTrue(is_rainskills_invocation())

            with deployment_invocation_context("api", "unknown"):
                self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="api", client="unknown"))
                self.assertFalse(is_rainskills_invocation())

            self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="rainskills", client="codex"))

        self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="unknown", client="unknown"))

    def test_context_restores_after_an_exception(self):
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with deployment_invocation_context("rainskills", "claude_code"):
                raise RuntimeError("boom")

        self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="unknown", client="unknown"))

    def test_rainskills_origin_match_is_exact(self):
        for origin in ("RainSkills", "rainskills ", "api"):
            with self.subTest(origin=origin):
                with deployment_invocation_context(origin, "codex"):
                    self.assertFalse(is_rainskills_invocation())

    def test_context_value_is_isolated_from_a_fresh_context(self):
        fresh_context = Context()

        with deployment_invocation_context("rainskills", "codex"):
            self.assertEqual(get_deployment_invocation().client, "codex")
            self.assertEqual(
                fresh_context.run(get_deployment_invocation),
                DeploymentInvocation(origin="unknown", client="unknown"),
            )


class MCPDeploymentInvocationTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(user_id=1, is_authenticated=True, nick_name="tester")
        audit_begin = patch("console.views.mcp_query.rainskills_audit_service.begin", return_value=None)
        audit_begin.start()
        self.addCleanup(audit_begin.stop)

    def _request(self, arguments=None, tool_name="rainbond_test_tool"):
        request = self.factory.post(
            "/console/mcp/query",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {},
                },
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        force_authenticate(request, user=self.user)
        return request

    def test_configured_and_generic_views_expose_fixed_invocation_to_tool_calls(self):
        cases = (
            ({}, DeploymentInvocation(origin="unknown", client="unknown")),
            ({
                "deploy_origin": "rainskills",
                "deploy_client": "codex"
            }, DeploymentInvocation(origin="rainskills", client="codex")),
            ({
                "deploy_origin": "rainskills",
                "deploy_client": "claude_code"
            }, DeploymentInvocation(origin="rainskills", client="claude_code")),
        )

        for view_kwargs, expected in cases:
            with self.subTest(view_kwargs=view_kwargs):
                observed = []

                def call_tool(user, tool_name, arguments):
                    observed.append(get_deployment_invocation())
                    return {"ok": True}

                view = MCPQueryHTTPView.as_view(**view_kwargs)
                with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=call_tool):
                    response = view(self._request())

                self.assertEqual(response.status_code, 200)
                self.assertEqual(observed, [expected])
                self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="unknown", client="unknown"))

    def test_request_arguments_cannot_override_fixed_invocation(self):
        observed = []

        def call_tool(user, tool_name, arguments):
            observed.append((get_deployment_invocation(), arguments))
            return {"ok": True}

        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="codex")
        arguments = {
            "deploy_origin": "forged-origin",
            "deploy_client": "forged-client",
        }
        with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=call_tool):
            response = view(self._request(arguments=arguments))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed, [(DeploymentInvocation(origin="rainskills", client="codex"), arguments)])

    def test_service_exception_is_handled_inside_context_and_context_is_restored(self):
        observed = []

        def call_tool(user, tool_name, arguments):
            observed.append(get_deployment_invocation())
            raise ServiceHandleException(msg="failed", msg_show="failed", status_code=400)

        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="codex")
        with deployment_invocation_context("outer", "outer"):
            with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=call_tool):
                response = view(self._request())
            self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="outer", client="outer"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["result"]["isError"])
        self.assertEqual(observed, [DeploymentInvocation(origin="rainskills", client="codex")])

    def test_unexpected_exception_is_handled_inside_context_and_context_is_restored(self):
        observed = []

        def call_tool(user, tool_name, arguments):
            observed.append(get_deployment_invocation())
            raise RuntimeError("unexpected")

        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="claude_code")
        with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=call_tool):
            response = view(self._request())

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["result"]["isError"])
        self.assertEqual(observed, [DeploymentInvocation(origin="rainskills", client="claude_code")])
        self.assertEqual(get_deployment_invocation(), DeploymentInvocation(origin="unknown", client="unknown"))

    def test_rainskills_urls_resolve_to_http_view_with_fixed_configuration(self):
        cases = (
            ("/console/mcp/rainskills/codex/query", "codex"),
            ("/console/mcp/rainskills/claude-code/query", "claude_code"),
            ("/console/mcp/rainskills/api/query", "api"),
        )

        for path, client in cases:
            with self.subTest(path=path):
                match = resolve(path)
                self.assertIs(match.func.view_class, MCPQueryHTTPView)
                self.assertEqual(match.func.view_initkwargs, {"deploy_origin": "rainskills", "deploy_client": client})

                observed = []

                def call_tool(user, tool_name, arguments):
                    observed.append(get_deployment_invocation())
                    return {"ok": True}

                with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=call_tool):
                    response = match.func(self._request())

                self.assertEqual(response.status_code, 200)
                self.assertEqual(observed, [DeploymentInvocation(origin="rainskills", client=client)])

    def test_rainskills_api_hidden_tool_is_rejected_before_tracking_or_execution(self):
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="api")

        with patch(
                "console.views.mcp_query.rainskills_deployment_service.classify_tool_call",
                return_value=DeploymentSpec("initial", "source_create", "source_code", True, True)):
            with patch("console.views.mcp_query.rainskills_deployment_service.safe_begin_tracking") as begin:
                with patch.object(mcp_query_service, "create_component_from_local_package") as handler:
                    response = view(self._request(
                        tool_name="rainbond_create_component_from_local_package",
                        arguments={"team_name": "team-a", "region_name": "region-a", "app_id": 7},
                    ))

        self.assertEqual(response.status_code, 200)
        result = response.data["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["status_code"], 404)
        begin.assert_not_called()
        handler.assert_not_called()

    def test_rainskills_deployment_starts_and_binds_independent_tracker(self):
        spec = DeploymentSpec("initial", "source_create", "source_code", True, True)
        tracker = {"key": "RAINSKILLS_DEPLOY_test"}
        result = {"app_id": 7, "event_ids": ["event-1"], "service_ids": ["service-1"]}
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="codex")

        with patch(
                "console.views.mcp_query.rainskills_deployment_service.classify_tool_call",
                return_value=spec) as classify:
            with patch(
                    "console.views.mcp_query.rainskills_deployment_service.safe_begin_tracking",
                    return_value=tracker) as begin:
                with patch(
                        "console.views.mcp_query.rainskills_deployment_service.safe_bind_tool_result",
                        side_effect=RuntimeError("bind telemetry unavailable")) as bind:
                    with patch("console.views.mcp_query.mcp_query_service.call_tool", return_value=result):
                        response = view(self._request(
                            arguments={
                                "team_name": "team-a",
                                "region_name": "region-a",
                                "app_id": 7,
                                "language": "Go",
                            },
                            tool_name="rainbond_create_component_from_source"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result"]["structuredContent"], result)
        classify.assert_called_once_with(
            "rainbond_create_component_from_source", {
                "team_name": "team-a",
                "region_name": "region-a",
                "app_id": 7,
                "language": "Go",
            }, service_sources=None)
        begin.assert_called_once_with(
            client="codex",
            tool="rainbond_create_component_from_source",
            deploy_type="source_code",
            deploy_stage="initial",
            trigger="source_create",
            enterprise_id="",
            tenant_name="team-a",
            region_name="region-a",
            app_id=7,
            resource_created=True,
            source_language="Go",
        )
        bind.assert_called_once_with(tracker, result)

    def test_generic_route_never_starts_rainskills_tracker(self):
        result = {"event_id": "event-1"}
        view = MCPQueryHTTPView.as_view()

        with patch("console.views.mcp_query.rainskills_deployment_service.classify_tool_call") as classify:
            with patch("console.views.mcp_query.rainskills_deployment_service.safe_begin_tracking") as begin:
                with patch("console.views.mcp_query.mcp_query_service.call_tool", return_value=result):
                    response = view(self._request(
                        arguments={"is_deploy": True},
                        tool_name="rainbond_create_component_from_image"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result"]["structuredContent"], result)
        classify.assert_not_called()
        begin.assert_not_called()

    def test_rainskills_tool_failure_marks_tracker_without_changing_error_contract(self):
        spec = DeploymentSpec("continuous", "build_component", "source_code", False, False)
        tracker = {"key": "RAINSKILLS_DEPLOY_test"}
        failure = ServiceHandleException(msg="failed", msg_show="same failure", status_code=409)
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="claude_code")

        with patch(
                "console.views.mcp_query.rainskills_deployment_service.classify_tool_call",
                return_value=spec):
            with patch(
                    "console.views.mcp_query.mcp_query_service.resolve_deployment_service_sources",
                    return_value=[SimpleNamespace(service_source="source_code")]):
                with patch(
                        "console.views.mcp_query.rainskills_deployment_service.safe_begin_tracking",
                        return_value=tracker):
                    with patch(
                            "console.views.mcp_query.rainskills_deployment_service.safe_mark_failure",
                            side_effect=RuntimeError("failure telemetry unavailable")) as mark:
                        with patch("console.views.mcp_query.mcp_query_service.call_tool", side_effect=failure):
                            response = view(self._request(
                                arguments={
                                    "team_name": "team-a",
                                    "region_name": "region-a",
                                    "app_id": 7,
                                    "service_id": "service-1",
                                },
                                tool_name="rainbond_build_component"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["result"]["isError"])
        self.assertEqual(response.data["result"]["structuredContent"]["status_code"], 409)
        self.assertEqual(response.data["result"]["structuredContent"]["msg_show"], "same failure")
        mark.assert_called_once_with(
            tracker,
            reason="same failure",
            failure_stage="tool",
            failure_category="servicehandleexception",
        )

    def test_telemetry_failures_do_not_change_successful_tool_response(self):
        spec = DeploymentSpec("initial", "image_create", "image", True, False)
        result = {"app_id": 3, "event_id": "event-3"}
        view = MCPQueryHTTPView.as_view(deploy_origin="rainskills", deploy_client="codex")

        with patch(
                "console.views.mcp_query.rainskills_deployment_service.classify_tool_call",
                return_value=spec):
            with patch(
                    "console.views.mcp_query.rainskills_deployment_service.safe_begin_tracking",
                    side_effect=RuntimeError("telemetry unavailable")):
                with patch("console.views.mcp_query.mcp_query_service.call_tool", return_value=result) as call_tool:
                    response = view(self._request(
                        arguments={"is_deploy": True},
                        tool_name="rainbond_create_component_from_image"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result"]["structuredContent"], result)
        call_tool.assert_called_once()
