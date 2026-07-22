# -*- coding: utf-8 -*-
import json
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

django.setup()

from console.views.agent_llm_config import (AgentLLMConfigView, AgentLLMRuntimeConfigView,
                                            AgentMCPDelegatedCredentialsView,
                                            AgentMCPRuntimeCredentialsView)


class AgentLLMConfigViewTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.manage_view = AgentLLMConfigView.as_view()
        self.runtime_view = AgentLLMRuntimeConfigView.as_view()
        self.mcp_credentials_view = AgentMCPRuntimeCredentialsView.as_view()
        self.delegated_credentials_view = AgentMCPDelegatedCredentialsView.as_view()

    def _admin_user(self):
        return SimpleNamespace(
            user_id=1, nick_name="admin", enterprise_id="eid", is_authenticated=True, sys_admin=False)

    def _normal_user(self):
        return SimpleNamespace(user_id=2, nick_name="user", enterprise_id="eid", is_authenticated=True)

    def test_get_returns_masked_config_for_enterprise_admin(self):
        request = self.factory.get("/console/enterprise/eid/agent-llm-config")
        force_authenticate(request, user=self._admin_user())

        with mock.patch("console.views.base.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=True), \
                mock.patch("console.views.base.user_services.list_roles", return_value=[]), \
                mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]), \
                mock.patch("console.views.agent_llm_config.agent_llm_config_service.get_masked_config",
                           return_value={"openai_api_key_set": True, "openai_api_key_masked": "sk-****abcd"}):
            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            response = self.manage_view(request, eid="eid")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["bean"]["openai_api_key_set"])
        self.assertNotIn("OPENAI_API_KEY", json.dumps(response.data))

    def test_get_returns_masked_config_for_non_admin_user(self):
        request = self.factory.get("/console/enterprise/eid/agent-llm-config")
        force_authenticate(request, user=self._normal_user())

        with mock.patch("console.views.base.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=False), \
                mock.patch("console.views.base.user_services.list_roles", return_value=[]), \
                mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]), \
                mock.patch("console.views.agent_llm_config.agent_llm_config_service.get_masked_config",
                           return_value={"openai_api_key_set": True, "openai_api_key_masked": "sk-****abcd"}):
            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            response = self.manage_view(request, eid="eid")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["bean"]["openai_api_key_set"])
        self.assertNotIn("OPENAI_API_KEY", json.dumps(response.data))

    def test_put_requires_enterprise_admin(self):
        request = self.factory.put(
            "/console/enterprise/eid/agent-llm-config",
            data=json.dumps({"openai_model": "gpt-4o-mini"}),
            content_type="application/json",
        )
        force_authenticate(request, user=self._admin_user())

        with mock.patch("console.views.base.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=False), \
                mock.patch("console.views.base.user_services.list_roles", return_value=[]), \
                mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]):
            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            response = self.manage_view(request, eid="eid")

        self.assertEqual(response.status_code, 403)

    def test_delete_clears_config_for_enterprise_admin(self):
        request = self.factory.delete("/console/enterprise/eid/agent-llm-config")
        force_authenticate(request, user=self._admin_user())

        with mock.patch("console.views.base.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=True), \
                mock.patch("console.views.base.user_services.list_roles", return_value=[]), \
                mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]), \
                mock.patch("console.views.agent_llm_config.agent_llm_config_service.clear_config",
                           return_value={"openai_api_key_set": False, "openai_api_key_masked": ""}) as clear_config:
            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            response = self.manage_view(request, eid="eid")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["bean"]["openai_api_key_set"])
        clear_config.assert_called_once()

    def test_delete_requires_enterprise_admin(self):
        request = self.factory.delete("/console/enterprise/eid/agent-llm-config")
        force_authenticate(request, user=self._admin_user())

        with mock.patch("console.views.base.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=False), \
                mock.patch("console.views.base.user_services.list_roles", return_value=[]), \
                mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]):
            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            response = self.manage_view(request, eid="eid")

        self.assertEqual(response.status_code, 403)

    def test_runtime_config_accepts_agent_service_jwt(self):
        request = self.factory.get(
            "/console/internal/agent-llm-config/runtime",
            HTTP_AUTHORIZATION="GRJWT service-token",
        )
        force_authenticate(request, user=self._admin_user(), token="service-token")

        with mock.patch("console.views.agent_llm_config.jwt_issuer.decode_jwt",
                        return_value={"token_purpose": "agent_service", "enterprise_id": "eid"}), \
                mock.patch("console.views.agent_llm_config.agent_llm_config_service.get_runtime_config",
                           return_value={"OPENAI_API_KEY": "sk-runtime", "OPENAI_MODEL": "gpt-4o-mini"}):
            response = self.runtime_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual("sk-runtime", response.data["data"]["bean"]["OPENAI_API_KEY"])

    def test_runtime_config_rejects_enterprise_id_as_token(self):
        request = self.factory.get(
            "/console/internal/agent-llm-config/runtime",
            HTTP_X_INTERNAL_TOKEN="5ae43b0db81042d0ba8005386022d1c5",
        )

        response = self.runtime_view(request)
        self.assertIn(response.status_code, (401, 403))

    def test_runtime_config_rejects_request_through_public_gateway(self):
        request = self.factory.get(
            "/console/internal/agent-llm-config/runtime",
            HTTP_X_INTERNAL_TOKEN="5ae43b0db81042d0ba8005386022d1c5",
            HTTP_X_FORWARDED_FOR="203.0.113.7",
        )

        response = self.runtime_view(request)

        self.assertIn(response.status_code, (401, 403))

    def test_runtime_config_rejects_public_source_ip(self):
        request = self.factory.get(
            "/console/internal/agent-llm-config/runtime",
            HTTP_X_INTERNAL_TOKEN="5ae43b0db81042d0ba8005386022d1c5",
            REMOTE_ADDR="8.8.8.8",
        )

        response = self.runtime_view(request)

        self.assertIn(response.status_code, (401, 403))

    def test_runtime_config_rejects_unknown_token(self):
        request = self.factory.get(
            "/console/internal/agent-llm-config/runtime",
            HTTP_X_INTERNAL_TOKEN="not-an-enterprise-id",
        )

        response = self.runtime_view(request)

        self.assertIn(response.status_code, (401, 403))

    def test_runtime_config_rejects_missing_internal_token(self):
        request = self.factory.get("/console/internal/agent-llm-config/runtime")

        response = self.runtime_view(request)

        self.assertIn(response.status_code, (401, 403))

    def test_mcp_runtime_credentials_generates_console_jwt_headers(self):
        request = self.factory.get(
            "/console/internal/agent-mcp-credentials/runtime",
            HTTP_AUTHORIZATION="GRJWT service-token",
        )
        force_authenticate(request, user=self._admin_user(), token="service-token")

        with mock.patch("console.views.agent_llm_config.jwt_issuer.decode_jwt",
                        return_value={"token_purpose": "agent_service", "enterprise_id": "eid"}), \
                mock.patch("console.views.agent_llm_config.jwt_issuer.issue_jwt", return_value="jwt-token"):
            response = self.mcp_credentials_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual("GRJWT jwt-token", response.data["data"]["bean"]["authorization"])
        self.assertEqual("token=jwt-token", response.data["data"]["bean"]["cookie"])

    @override_settings(INTERNAL_API_TOKEN="legacy-internal-token")
    def test_delegated_credentials_use_bound_enterprise_admin_identity(self):
        request = self.factory.post(
            "/console/internal/agent-mcp-credentials/delegated",
            data=json.dumps({"enterprise_id": "eid", "user_id": "7"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="GRJWT service-token",
        )
        force_authenticate(request, user=self._admin_user(), token="service-token")
        delegated_user = SimpleNamespace(
            user_id=7,
            nick_name="bound-admin",
            email="admin@example.com",
            is_authenticated=True,
        )

        with mock.patch("console.views.agent_llm_config.jwt_issuer.decode_jwt",
                        return_value={"token_purpose": "agent_service", "enterprise_id": "eid"}), \
                mock.patch("console.views.agent_llm_config.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.agent_llm_config.EnterpriseUserPerm.objects.filter") as perm_filter, \
                mock.patch("console.views.agent_llm_config.Users.objects.filter") as users_filter, \
                mock.patch("console.views.agent_llm_config.jwt_issuer.issue_short_lived_jwt",
                           return_value="delegated-jwt") as issue_jwt:
            enterprise_filter.return_value.exists.return_value = True
            perm_filter.return_value.exists.return_value = True
            perm_filter.return_value.first.return_value = SimpleNamespace(identity="admin")
            users_filter.return_value.first.return_value = delegated_user
            response = self.delegated_credentials_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual("GRJWT delegated-jwt", response.data["data"]["bean"]["authorization"])
        self.assertEqual("token=delegated-jwt", response.data["data"]["bean"]["cookie"])
        self.assertEqual("7", response.data["data"]["bean"]["user_id"])
        self.assertEqual(perm_filter.call_args_list, [
            mock.call(enterprise_id="eid", user_id=1, identity="admin"),
            mock.call(enterprise_id="eid", user_id=7, identity="admin"),
        ])
        issue_jwt.assert_called_once_with(delegated_user, lifetime_seconds=300)

    def test_delegated_credentials_reject_cross_enterprise_and_non_admin(self):
        cross_enterprise = self.factory.post(
            "/console/internal/agent-mcp-credentials/delegated",
            data=json.dumps({"enterprise_id": "other", "user_id": "7"}),
            content_type="application/json",
            HTTP_X_INTERNAL_TOKEN="eid",
        )
        force_authenticate(cross_enterprise, user=self._admin_user())
        self.assertEqual(self.delegated_credentials_view(cross_enterprise).status_code, 403)

        non_admin = self.factory.post(
            "/console/internal/agent-mcp-credentials/delegated",
            data=json.dumps({"enterprise_id": "eid", "user_id": "7"}),
            content_type="application/json",
            HTTP_X_INTERNAL_TOKEN="eid",
        )
        force_authenticate(non_admin, user=self._admin_user())
        with mock.patch("console.views.agent_llm_config.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.agent_llm_config.EnterpriseUserPerm.objects.filter") as perm_filter:
            enterprise_filter.return_value.exists.return_value = True
            perm_filter.return_value.first.return_value = None
            response = self.delegated_credentials_view(non_admin)
        self.assertEqual(response.status_code, 403)

    def test_delegated_credentials_reject_enterprise_id_as_service_token(self):
        request = self.factory.post(
            "/console/internal/agent-mcp-credentials/delegated",
            data=json.dumps({"enterprise_id": "eid", "user_id": "7"}),
            content_type="application/json",
            HTTP_X_INTERNAL_TOKEN="eid",
        )

        with mock.patch("console.views.agent_llm_config.TenantEnterprise.objects.filter") as enterprise_filter, \
                mock.patch("console.views.agent_llm_config.EnterpriseUserPerm.objects.filter") as perm_filter, \
                mock.patch("console.views.agent_llm_config.Users.objects.filter") as users_filter, \
                mock.patch("console.views.agent_llm_config.jwt_issuer.issue_short_lived_jwt",
                           return_value="delegated-jwt"):
            enterprise_filter.return_value.exists.return_value = True
            perm_filter.return_value.exists.return_value = True
            perm_filter.return_value.first.return_value = SimpleNamespace(identity="admin")
            users_filter.return_value.first.return_value = self._admin_user()
            response = self.delegated_credentials_view(request)

        self.assertIn(response.status_code, (401, 403))

    def test_delegated_credentials_reject_invalid_user_id_types(self):
        for invalid_user_id in (None, [], {}, True, "not-a-number"):
            request = self.factory.post(
                "/console/internal/agent-mcp-credentials/delegated",
                data=json.dumps({"enterprise_id": "eid", "user_id": invalid_user_id}),
                content_type="application/json",
                HTTP_AUTHORIZATION="GRJWT service-token",
            )
            force_authenticate(request, user=self._admin_user(), token="service-token")
            with mock.patch("console.views.agent_llm_config.jwt_issuer.decode_jwt",
                            return_value={"token_purpose": "agent_service", "enterprise_id": "eid"}):
                response = self.delegated_credentials_view(request)
            self.assertEqual(response.status_code, 400)
