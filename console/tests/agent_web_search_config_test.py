# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate

from console.exception.main import ServiceHandleException
from console.services.agent_web_search_config_service import AgentWebSearchConfigService
from console.services.agent_web_search_service import AgentWebSearchService, agent_web_search_service


class AgentWebSearchConfigServiceTests(SimpleTestCase):

    def setUp(self):
        self.service = AgentWebSearchConfigService()

    def test_rejects_missing_api_key_when_enabled(self):
        with mock.patch.object(self.service, "_load_config", return_value={}):
            with self.assertRaises(ServiceHandleException) as context:
                self.service.update_config(
                    {"enabled": True, "provider": "deepseek", "max_results": 5})
        self.assertIn("API Key", context.exception.msg_show)

    def test_defaults_to_disabled_when_config_missing(self):
        with mock.patch.object(self.service, "_load_config", return_value={}):
            runtime = self.service.get_runtime_config()
        self.assertFalse(runtime["enabled"])

    def test_rejects_invalid_provider(self):
        with mock.patch.object(self.service, "_load_config", return_value={}):
            with self.assertRaises(ServiceHandleException) as context:
                self.service.update_config({"provider": "google", "api_key": "k"})
        self.assertIn("provider", context.exception.msg_show)

    def test_masks_api_key_without_encrypting_plain_text(self):
        with mock.patch.object(self.service, "_load_config", return_value={}), \
                mock.patch.object(self.service, "_save_config") as save:
            result = self.service.update_config(
                {"provider": "deepseek", "api_key": "ds-123456789", "max_results": 3})
        self.assertTrue(result["api_key_set"])
        self.assertNotIn("ds-123456789", str(result))
        stored = save.call_args[0][0]
        self.assertTrue(stored["api_key"].startswith("fernet:v1:"))

    def test_normalizes_legacy_provider_to_deepseek(self):
        with mock.patch.object(self.service, "_load_config",
                               return_value={"provider": "exa", "api_key": ""}):
            runtime = self.service.get_runtime_config()
            masked = self.service.get_masked_config()
        self.assertEqual("deepseek", runtime["provider"])
        self.assertEqual("deepseek", masked["provider"])

    def test_rejects_non_deepseek_provider(self):
        with mock.patch.object(self.service, "_load_config", return_value={}):
            with self.assertRaises(ServiceHandleException) as context:
                self.service.update_config(
                    {"provider": "exa", "api_key": "k", "max_results": 5})
        self.assertIn("deepseek", context.exception.msg_show)

    def test_allows_disabled_search_without_api_key(self):
        with mock.patch.object(self.service, "_load_config", return_value={}), \
                mock.patch.object(self.service, "_save_config"):
            result = self.service.update_config(
                {"enabled": False, "provider": "deepseek", "max_results": 5})
        self.assertFalse(result["enabled"])

    def test_accepts_deepseek_provider(self):
        with mock.patch.object(self.service, "_load_config", return_value={}), \
                mock.patch.object(self.service, "_save_config"):
            result = self.service.update_config(
                {"provider": "deepseek", "api_key": "ds-key", "max_results": 5})
        self.assertEqual("deepseek", result["provider"])


class AgentWebSearchServiceTests(SimpleTestCase):

    def test_exports_module_singleton_for_views(self):
        self.assertIsInstance(agent_web_search_service, AgentWebSearchService)

    def test_maps_deepseek_search_results(self):
        service = AgentWebSearchService()
        response = mock.Mock(
            status_code=200,
            content=b"{}",
            text="{}",
            json=lambda: {
                "results": [{
                    "title": "Rainbond",
                    "url": "https://www.rainbond.com/docs",
                    "summary": "Rainbond is a cloud native application platform",
                    "date": "2026-01-01",
                }]
            },
        )
        runtime = {
            "enabled": True,
            "provider": "deepseek",
            "api_key": "ds-key",
            "max_results": 5,
        }
        with mock.patch(
                "console.services.agent_web_search_service.agent_web_search_config_service.get_runtime_config",
                return_value=runtime), \
                mock.patch("console.services.agent_web_search_service.requests.post",
                           return_value=response) as post:
            result = service.search("Rainbond", 1, "deepseek-scope")

        self.assertEqual("deepseek", result["provider"])
        self.assertEqual([{
            "url": "https://www.rainbond.com/docs",
            "title": "Rainbond",
            "snippet": "Rainbond is a cloud native application platform",
            "publishedAt": "2026-01-01",
        }], result["sources"])
        args, kwargs = post.call_args
        self.assertEqual("https://api.deepseek.com/v1/tools/search", args[0])
        self.assertEqual({"query": "Rainbond", "count": 1, "need_content": False}, kwargs["json"])
        self.assertEqual("Bearer ds-key", kwargs["headers"]["Authorization"])

    def test_maps_deepseek_unauthorized_to_401(self):
        service = AgentWebSearchService()
        response = mock.Mock(status_code=401, content=b"{}", text="unauthorized")
        runtime = {
            "enabled": True,
            "provider": "deepseek",
            "api_key": "bad-key",
            "max_results": 5,
        }
        with mock.patch(
                "console.services.agent_web_search_service.agent_web_search_config_service.get_runtime_config",
                return_value=runtime), \
                mock.patch("console.services.agent_web_search_service.requests.post",
                           return_value=response):
            with self.assertRaises(ServiceHandleException) as context:
                service.search("q", 1, "deepseek-401-scope")
        self.assertEqual(401, context.exception.status_code)
        self.assertIn("API Key", context.exception.msg_show)


class AgentWebSearchRuntimeConfigViewTests(SimpleTestCase):

    def test_runtime_view_does_not_expose_api_key(self):
        from console.views.agent_web_search_config import AgentWebSearchRuntimeConfigView

        factory = APIRequestFactory()
        request = factory.get("/console/internal/agent-web-search-config/runtime")
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
        with mock.patch(
                "console.views.agent_web_search_config.agent_web_search_config_service.get_runtime_config",
                return_value={
                    "enabled": True,
                    "provider": "deepseek",
                    "api_key": "secret-key",
                    "max_results": 5,
                }):
            response = AgentWebSearchRuntimeConfigView.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertNotIn("api_key", response.data["data"]["bean"])
        self.assertTrue(response.data["data"]["bean"]["enabled"])
