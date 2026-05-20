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

from console.views.agent_llm_config import AgentLLMConfigView, AgentLLMRuntimeConfigView


class AgentLLMConfigViewTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.manage_view = AgentLLMConfigView.as_view()
        self.runtime_view = AgentLLMRuntimeConfigView.as_view()

    def _admin_user(self):
        return SimpleNamespace(user_id=1, nick_name="admin", enterprise_id="eid", is_authenticated=True)

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

    @override_settings(INTERNAL_API_TOKEN="token-1")
    def test_runtime_config_requires_internal_token_and_returns_runtime_values(self):
        request = self.factory.get(
            "/console/internal/agent-llm-config/runtime",
            HTTP_X_INTERNAL_TOKEN="token-1",
        )

        with mock.patch("console.services.auth.authentication.Users.objects.filter") as users_filter, \
                mock.patch("console.views.agent_llm_config.agent_llm_config_service.get_runtime_config",
                           return_value={"OPENAI_API_KEY": "sk-runtime", "OPENAI_MODEL": "gpt-4o-mini"}):
            users_filter.return_value.first.return_value = self._admin_user()
            response = self.runtime_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual("sk-runtime", response.data["data"]["bean"]["OPENAI_API_KEY"])

    @override_settings(INTERNAL_API_TOKEN="token-1")
    def test_runtime_config_rejects_missing_internal_token(self):
        request = self.factory.get("/console/internal/agent-llm-config/runtime")

        response = self.runtime_view(request)

        self.assertIn(response.status_code, (401, 403))
