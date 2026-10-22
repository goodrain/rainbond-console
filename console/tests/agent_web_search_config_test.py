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

from console.exception.main import ServiceHandleException
from console.services.agent_web_search_config_service import AgentWebSearchConfigService
from console.services.agent_web_search_service import AgentWebSearchService


class AgentWebSearchConfigServiceTests(SimpleTestCase):

    def setUp(self):
        self.service = AgentWebSearchConfigService()

    def test_rejects_missing_api_key(self):
        with mock.patch.object(self.service, "_load_config", return_value={}):
            with self.assertRaises(ServiceHandleException) as context:
                self.service.update_config({"provider": "exa", "max_results": 5})
        self.assertIn("API Key", context.exception.msg_show)

    def test_rejects_invalid_provider(self):
        with mock.patch.object(self.service, "_load_config", return_value={}):
            with self.assertRaises(ServiceHandleException) as context:
                self.service.update_config({"provider": "google", "api_key": "k"})
        self.assertIn("provider", context.exception.msg_show)

    def test_masks_api_key_without_encrypting_plain_text(self):
        with mock.patch.object(self.service, "_load_config", return_value={}), \
                mock.patch.object(self.service, "_save_config") as save:
            result = self.service.update_config(
                {"provider": "exa", "api_key": "exa-123456789", "max_results": 3})
        self.assertTrue(result["api_key_set"])
        self.assertNotIn("exa-123456789", str(result))
        stored = save.call_args[0][0]
        self.assertTrue(stored["api_key"].startswith("fernet:v1:"))

    def test_accepts_deepseek_provider(self):
        with mock.patch.object(self.service, "_load_config", return_value={}), \
                mock.patch.object(self.service, "_save_config"):
            result = self.service.update_config(
                {"provider": "deepseek", "api_key": "ds-key", "max_results": 5})
        self.assertEqual("deepseek", result["provider"])


class AgentWebSearchServiceTests(SimpleTestCase):

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
            "fetch_timeout_ms": 15000,
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
            "fetch_timeout_ms": 15000,
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
