# -*- coding: utf-8 -*-
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest import mock

import urllib3
from django.test import SimpleTestCase, RequestFactory

from console.exception.main import ServiceHandleException
from console.services.ai_engine_service import AIEngineProxyService
from console.views import rbd_plugin


class AIEngineManagementProxyTests(SimpleTestCase):
    # capability_id: console.ai-engine.management-scope-rbac
    def setUp(self):
        self.service = AIEngineProxyService()
        self.user = SimpleNamespace(user_id=7, enterprise_id="enterprise-a")
        self.team = SimpleNamespace(tenant_name="team-a", tenant_id="tid-a", namespace="trusted-ns", creater=1)
        patches = {
            "team_services.get_enterprise_tenant_by_tenant_name": self.team,
            "team_repo.get_user_tenant_by_name": self.team,
            "enterprise_user_perm_repo.is_admin": False,
            "region_services.get_enterprise_region_by_region_name": SimpleNamespace(region_name="region-b"),
            "team_repo.get_team_region_by_name": [SimpleNamespace(is_active=True, is_init=True)],
            "optimized_role_perm_repo.get_user_team_all_perms": {
                "global_perms": [200001],
                "app_perms": {}
            },
        }
        self.mocks = {}
        for target, value in patches.items():
            module = "console.repositories.perm_repo." if target.startswith(
                "optimized_role_perm_repo.") else "console.services.ai_engine_service."
            patcher = mock.patch(module + target, return_value=value)
            self.mocks[target] = patcher.start()
            self.addCleanup(patcher.stop)

    def context(self, method="GET", path="api/v1/ai-engine/model-apis"):
        return self.service.management_context(self.user, "team-a", "region-b", method, path)

    def test_observer_reads_with_verified_context_and_actor(self):
        context = self.context()
        self.assertEqual(context.headers, {
            "X-AI-Team-Name": "team-a",
            "X-AI-Region-Name": "region-b",
            "X-AI-Team-Namespace": "trusted-ns",
            "X-AI-Actor-ID": "7",
        })

    def test_observer_cannot_mutate_or_read_plaintext_key(self):
        for method, path in (("POST", "model-apis"), ("PUT", "sources/a"), ("DELETE", "api-keys/1"), ("GET",
                                                                                                      "api-keys/1/secret")):
            with self.subTest(method=method, path=path), self.assertRaises(ServiceHandleException) as caught:
                self.context(method, "api/v1/ai-engine/" + path)
            self.assertEqual(caught.exception.status_code, 403)

    def test_custom_permissions_and_app_only_permissions_are_distinct(self):
        perms = self.mocks["optimized_role_perm_repo.get_user_team_all_perms"]
        perms.return_value = {"global_perms": [200001, 300003], "app_perms": {1: [300016]}}
        self.context("PUT", "api/v1/ai-engine/model-apis/a")
        for method, path in (("GET", "api-keys/1/secret"), ("POST", "api-keys"), ("POST", "api-keys/1/rotate")):
            with self.subTest(method=method, path=path), self.assertRaises(ServiceHandleException):
                self.context(method, "api/v1/ai-engine/" + path)
        perms.return_value["global_perms"].append(300016)
        self.context("GET", "api/v1/ai-engine/api-keys/1/secret")

    def test_scope_checks_reject_foreign_team_and_inactive_region(self):
        self.mocks["team_repo.get_user_tenant_by_name"].return_value = None
        with self.assertRaises(ServiceHandleException) as caught:
            self.context()
        self.assertEqual(caught.exception.status_code, 403)
        self.mocks["team_repo.get_user_tenant_by_name"].return_value = self.team
        for binding in ([], [SimpleNamespace(is_active=0, is_init=1)], [SimpleNamespace(is_active=1, is_init=0)]):
            self.mocks["team_repo.get_team_region_by_name"].return_value = binding
            with self.assertRaises(ServiceHandleException):
                self.context()

    def test_owner_and_enterprise_admin_reuse_privileged_roles(self):
        self.user.user_id = 1
        self.context("DELETE", "api/v1/ai-engine/api-keys/1")
        self.user.user_id = 7
        self.mocks["enterprise_user_perm_repo.is_admin"].return_value = True
        self.context("GET", "api/v1/ai-engine/api-keys/1/secret")

    def test_only_authorized_secret_reads_receive_engine_capability(self):
        for user_id, is_admin, permissions in ((1, False, []), (7, True, []), (7, False, [200001, 300016])):
            with self.subTest(user_id=user_id, is_admin=is_admin):
                self.user.user_id = user_id
                self.mocks["enterprise_user_perm_repo.is_admin"].return_value = is_admin
                self.mocks["optimized_role_perm_repo.get_user_team_all_perms"].return_value = {
                    "global_perms": permissions,
                    "app_perms": {}
                }
                context = self.context("GET", "api/v1/ai-engine/api-keys/1/secret")
                self.assertEqual(context.headers["X-AI-Can-Read-Secrets"], "true")
                self.assertNotIn("X-AI-Can-Read-Secrets", self.context().headers)
                self.assertNotIn("X-AI-Can-Read-Secrets",
                                 self.service._context(self.user, {
                                     "team_name": "team-a",
                                     "region_name": "region-b"
                                 }).headers)

    @mock.patch.object(rbd_plugin.JWTAuthApiView, "initial")
    def test_secret_capability_reaches_engine_gate_and_browser_cannot_forge_it(self, initial):
        received = []

        class EngineSecretHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                headers = {key.lower(): value for key, value in self.headers.items()}
                received.append(headers)
                # Match the actual aicontrol secret handler's two required headers.
                allowed = headers.get("x-ai-can-read-secrets") == "true" and bool(headers.get("x-ai-actor-id"))
                payload = json.dumps({"code": 200 if allowed else 403, "data": {"api_key": "fixture-key"}}).encode()
                self.send_response(200 if allowed else 403)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), EngineSecretHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        region = SimpleNamespace(url="http://127.0.0.1:{}".format(server.server_port), token="region-token")
        request = RequestFactory().get("/",
                                       HTTP_X_AI_TEAM_NAME="team-a",
                                       HTTP_X_AI_CAN_READ_SECRETS="true",
                                       HTTP_X_AI_ACTOR_ID="forged")
        kwargs = {
            "region_name": "region-b",
            "plugin_name": "rainbond-ai-engine",
            "file_path": "api/v1/ai-engine/api-keys/1/secret"
        }
        try:
            with mock.patch.object(rbd_plugin, "ai_engine_service", self.service), \
                    mock.patch("www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name",
                               return_value=region), \
                    mock.patch.object(rbd_plugin.region_api, "get_client", return_value=pool):
                for view_type in (rbd_plugin.RainbondPluginBackendView, rbd_plugin.RainbondPluginFullProxyView):
                    for user_id, is_admin, permissions in ((1, False, []), (7, True, []), (7, False, [200001, 300016])):
                        self.user.user_id = user_id
                        self.mocks["enterprise_user_perm_repo.is_admin"].return_value = is_admin
                        self.mocks["optimized_role_perm_repo.get_user_team_all_perms"].return_value = {
                            "global_perms": permissions,
                            "app_perms": {}
                        }
                        view = view_type()
                        view.user = self.user
                        view.initial(request, **kwargs)
                        response = view.get(request, **kwargs)
                        try:
                            self.assertEqual(response.status_code, 200)
                            self.assertEqual(json.loads(b"".join(response.streaming_content))["data"]["api_key"], "fixture-key")
                        finally:
                            response.close()
                        self.assertEqual(received[-1]["x-ai-actor-id"], str(user_id))
                self.user.user_id = 7
                self.mocks["enterprise_user_perm_repo.is_admin"].return_value = False
                self.mocks["optimized_role_perm_repo.get_user_team_all_perms"].return_value = {
                    "global_perms": [200001],
                    "app_perms": {}
                }
                count = len(received)
                view = rbd_plugin.RainbondPluginBackendView()
                view.user = self.user
                with self.assertRaises(ServiceHandleException):
                    view.initial(request, **kwargs)
                self.assertEqual(len(received), count)
                kwargs["file_path"] = "api/v1/ai-engine/api-keys"
                view.initial(request, **kwargs)
                response = view.get(request, **kwargs)
                try:
                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn("x-ai-can-read-secrets", received[-1])
                finally:
                    response.close()
        finally:
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(1)

    def test_ambiguous_paths_cannot_bypass_secret_permission(self):
        for path in ("api/v1/ai-engine/api-keys/1/%73ecret", "api/v1/ai-engine/api-keys/1/../1/secret",
                     "api/v1/ai-engine//api-keys/1/secret", "other/api"):
            with self.subTest(path=path), self.assertRaises(ServiceHandleException):
                self.context("GET", path)

    @mock.patch.object(rbd_plugin.region_api, "stream_proxy")
    @mock.patch.object(rbd_plugin.JWTAuthApiView, "initial")
    def test_backend_view_uses_selected_team_and_rewrites_scope(self, initial, proxy):
        request = RequestFactory().get("/",
                                       HTTP_X_AI_TEAM_NAME="team-a",
                                       HTTP_X_AI_TEAM_NAMESPACE="forged",
                                       HTTP_X_AI_ACTOR_ID="root")
        view = rbd_plugin.RainbondPluginBackendView()
        view.user = self.user
        kwargs = {"region_name": "region-b", "plugin_name": "rainbond-ai-engine", "file_path": "api/v1/ai-engine/model-apis"}
        with mock.patch.object(rbd_plugin, "ai_engine_service", self.service):
            view.initial(request, **kwargs)
            view.get(request, **kwargs)
        sent = proxy.call_args.kwargs["requests_args"]["headers"]
        self.assertEqual(sent["X-AI-Team-Namespace"], "trusted-ns")
        self.assertEqual(sent["X-AI-Actor-ID"], "7")

    @mock.patch.object(rbd_plugin.region_api, "stream_proxy")
    @mock.patch.object(rbd_plugin.JWTAuthApiView, "initial")
    def test_full_proxy_alias_has_same_ai_permissions(self, initial, proxy):
        request = RequestFactory().post("/", HTTP_X_AI_TEAM_NAME="team-a")
        view = rbd_plugin.RainbondPluginFullProxyView()
        view.user = self.user
        kwargs = {"region_name": "region-b", "plugin_name": "rainbond-ai-engine", "file_path": "api/v1/ai-engine/model-apis"}
        with mock.patch.object(rbd_plugin, "ai_engine_service", self.service), self.assertRaises(ServiceHandleException):
            view.initial(request, **kwargs)
        proxy.assert_not_called()
