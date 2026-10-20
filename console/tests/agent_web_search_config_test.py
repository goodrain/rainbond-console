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
