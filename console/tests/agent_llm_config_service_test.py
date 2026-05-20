# -*- coding: utf-8 -*-
import json
from types import SimpleNamespace
from unittest import TestCase, mock

from django.core.exceptions import ObjectDoesNotExist

from console.services.agent_llm_config_service import agent_llm_config_service


class AgentLLMConfigServiceTests(TestCase):

    def setUp(self):
        self.saved = {}

    def _config_obj(self, value):
        obj = SimpleNamespace(value=value)

        def save(update_fields=None):
            self.saved["value"] = obj.value
            self.saved["update_fields"] = update_fields

        obj.save = save
        return obj

    def test_update_masks_and_runtime_decrypts_api_key(self):
        def create(**kwargs):
            self.saved.update(kwargs)
            return self._config_obj(kwargs["value"])

        with mock.patch("console.services.agent_llm_config_service.ConsoleSysConfig.objects.get",
                        side_effect=ObjectDoesNotExist), \
                mock.patch("console.services.agent_llm_config_service.ConsoleSysConfig.objects.create",
                           side_effect=create):
            masked = agent_llm_config_service.update_config({
                "openai_api_key": "sk-test-secret",
                "openai_model": "gpt-4o-mini",
                "openai_base_url": "https://api.openai.com/v1",
                "llm_thinking_enabled": True,
                "llm_reasoning_effort": "medium",
            }, updated_by="admin")

        self.assertTrue(masked["openai_api_key_set"])
        self.assertEqual("sk-****cret", masked["openai_api_key_masked"])
        stored = json.loads(self.saved["value"])
        self.assertNotEqual("sk-test-secret", stored["OPENAI_API_KEY"])

        with mock.patch("console.services.agent_llm_config_service.ConsoleSysConfig.objects.get",
                        return_value=self._config_obj(self.saved["value"])):
            runtime = agent_llm_config_service.get_runtime_config()

        self.assertEqual("sk-test-secret", runtime["OPENAI_API_KEY"])
        self.assertEqual("gpt-4o-mini", runtime["OPENAI_MODEL"])
        self.assertEqual("true", runtime["LLM_THINKING_ENABLED"])
        self.assertEqual("medium", runtime["LLM_REASONING_EFFORT"])

    def test_update_requires_api_key_and_all_config_values(self):
        with self.assertRaises(Exception) as cm:
            agent_llm_config_service.update_config({
                "openai_model": "new-model",
                "openai_base_url": "https://new.example/v1",
                "llm_thinking_enabled": False,
                "llm_reasoning_effort": "high",
            }, updated_by="admin")

        self.assertIn("OPENAI_API_KEY", getattr(cm.exception, "msg_show", ""))

    def test_invalid_values_raise_service_error(self):
        with self.assertRaises(Exception) as cm:
            agent_llm_config_service.update_config({
                "openai_base_url": "ftp://example.com",
                "llm_reasoning_effort": "extreme",
            })

        self.assertIn("OPENAI_BASE_URL", getattr(cm.exception, "msg_show", ""))
