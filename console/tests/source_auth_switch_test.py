# -*- coding: utf-8 -*-
import os
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.models.main import ServiceSourceInfo  # noqa: E402
from console.services import mcp_query_service as mcp_module  # noqa: E402
from console.services.mcp_query_service import mcp_query_service  # noqa: E402
from console.views import app_overview  # noqa: E402
from www.models.main import TenantServiceInfo  # noqa: E402


# capability_id: console.build-source.clear-oauth-on-explicit-git-switch
class SourceAuthSwitchTests(TestCase):
    def setUp(self):
        self.service = TenantServiceInfo.objects.create(
            service_id="auth-switch-component", tenant_id="auth-switch-team", service_key="application",
            service_alias="api", service_cname="API", service_region="region", category="application",
            version="1", image="", k8s_component_name="api", language="dockerfile", dockerfile="Dockerfile",
            service_source="source_code", server_type="git", code_from="oauth_github", oauth_service_id=7,
            git_url="https://example.invalid/repo.git", code_version="main", arch="amd64",
        )
        self.source = ServiceSourceInfo.objects.create(
            service=self.service, team_id=self.service.tenant_id, user_name="fixture-user",
            password="fixture-not-a-secret",
        )
        self.team = SimpleNamespace(tenant_id=self.service.tenant_id, tenant_name="fixture-team")
        self.app = SimpleNamespace(ID=1, region_name="region")
        self.user = SimpleNamespace(user_id=1, enterprise_id="fixture-enterprise", nick_name="fixture-operator")

    def mcp_update(self, **extra):
        arguments = {
            "team_name": "fixture-team", "region_name": "region", "app_id": 1,
            "service_id": self.service.service_id, "service_source": "source_code", "server_type": "git",
        }
        arguments.update(extra)
        with mock.patch.object(mcp_query_service, "_get_team_app_service_context",
                               return_value=(self.team, self.app, self.service)), \
                mock.patch.object(mcp_query_service, "_get_component_build_source_snapshot", return_value={}):
            return mcp_query_service.update_component_build_source(self.user, arguments)

    def web_update(self, **extra):
        payload = {"service_source": "source_code", "server_type": "git", "code_version": "main", "arch": "amd64"}
        payload.update(extra)
        view = app_overview.BuildSourceinfo()
        view.service, view.tenant, view.app, view.user, view.region_name = self.service, self.team, self.app, self.user, "region"
        request = view.initialize_request(APIRequestFactory().put("/build-source", payload, format="json"))
        request.user = self.user
        with mock.patch.object(app_overview.operation_log_service, "generate_component_comment", return_value="fixture"), \
                mock.patch.object(app_overview.operation_log_service, "create_component_log"), \
                mock.patch.object(app_overview.arch_service, "update_affinity_by_arch"):
            return view.put(request)

    def assert_git_saved(self):
        self.service.refresh_from_db()
        self.source.refresh_from_db()
        self.assertIsNone(self.service.oauth_service_id)
        self.assertEqual(self.service.code_from, "")
        self.assertEqual(self.service.git_url, "https://example.invalid/repo.git")
        self.assertEqual(self.service.code_version, "main")
        self.assertEqual(self.service.dockerfile, "Dockerfile")
        self.assertEqual(self.source.user_name, "fixture-user")
        self.assertEqual(self.source.password, "fixture-not-a-secret")

    def test_mcp_explicit_git_switch_clears_oauth_and_preserves_omitted_credentials(self):
        result = self.mcp_update(is_oauth=False)
        self.assertTrue(result["updated"])
        self.assert_git_saved()

    def test_mcp_repeat_git_save_repairs_stale_oauth_id(self):
        self.service.code_from = ""
        self.service.save()
        self.mcp_update(is_oauth=False, oauth_service_id="0")
        self.assert_git_saved()

    def test_mcp_omitted_auth_choice_keeps_existing_oauth_binding(self):
        self.mcp_update()
        self.service.refresh_from_db()
        self.assertEqual(self.service.oauth_service_id, 7)
        self.assertEqual(self.service.code_from, "oauth_github")

    def test_web_git_switch_without_new_url_clears_oauth_and_keeps_credentials(self):
        response = self.web_update(is_oauth=False)
        self.assertEqual(response.status_code, 200)
        self.assert_git_saved()

    def test_web_repeat_git_save_repairs_stale_oauth_id(self):
        self.service.code_from = ""
        self.service.save()
        response = self.web_update(is_oauth=False, git_url=self.service.git_url,
                                   user_name=self.source.user_name, password=self.source.password)
        self.assertEqual(response.status_code, 200)
        self.assert_git_saved()

    def test_explicit_git_switch_can_be_followed_by_valid_oauth_binding(self):
        self.mcp_update(is_oauth=False)
        instance = SimpleNamespace(is_git_oauth=lambda: True)
        with mock.patch.object(mcp_module.oauth_repo, "get_oauth_services_by_service_id",
                               return_value=SimpleNamespace(oauth_type="github")), \
                mock.patch.object(mcp_module.oauth_user_repo, "get_user_oauth_by_user_id", return_value=object()), \
                mock.patch.object(mcp_module, "get_oauth_instance", return_value=instance):
            result = self.mcp_update(is_oauth=True, oauth_service_id="9", full_name="fixture/repo")
        self.assertTrue(result["updated"])
        self.service.refresh_from_db()
        self.assertEqual(self.service.oauth_service_id, 9)
        self.assertEqual(self.service.code_from, "oauth_github")

    def test_web_oauth_binding_is_preserved_by_valid_oauth_update(self):
        instance = SimpleNamespace(is_git_oauth=lambda: True)
        with mock.patch.object(app_overview.oauth_repo, "get_oauth_services_by_service_id",
                               return_value=SimpleNamespace(oauth_type="github")), \
                mock.patch.object(app_overview.oauth_user_repo, "get_user_oauth_by_user_id", return_value=object()), \
                mock.patch.object(app_overview, "get_oauth_instance", return_value=instance):
            response = self.web_update(is_oauth=True, service_id="9", git_url=self.service.git_url,
                                       user_name=self.source.user_name, password=self.source.password)
        self.assertEqual(response.status_code, 200)
        self.service.refresh_from_db()
        self.assertEqual(self.service.oauth_service_id, 9)
        self.assertEqual(self.service.code_from, "oauth_github")
