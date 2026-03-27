from unittest import TestCase
from unittest.mock import patch

from console.services import app_check_service as app_check_service_module
from console.services.app_check_service import AppCheckService


class DummyTenant(object):
    tenant_id = "team-1"
    tenant_name = "team-a"


class DummyService(object):
    def __init__(self, build_strategy=""):
        self.service_cname = "demo"
        self.language = ""
        self.build_strategy = build_strategy
        self.min_memory = 0
        self.min_cpu = 0
        self.extend_method = "stateless_multiple"
        self.cmd = ""
        self.image = ""
        self.version = ""


class AppCheckServiceBuildStrategyTests(TestCase):
    def setUp(self):
        self.service_helper = AppCheckService()
        self.tenant = DummyTenant()

    def patch_side_effects(self):
        return patch.multiple(
            self.service_helper,
            _AppCheckService__save_compile_env=lambda *args, **kwargs: None,
            _AppCheckService__save_env=lambda *args, **kwargs: None,
            _AppCheckService__save_port=lambda *args, **kwargs: None,
            _AppCheckService__save_volume=lambda *args, **kwargs: None,
            sync_cnb_build_envs=lambda *args, **kwargs: None,
        )

    def test_save_service_info_defaults_supported_language_to_cnb(self):
        service = DummyService()

        with self.patch_side_effects():
            self.service_helper.save_service_info(self.tenant, service, {
                "language": "Java-maven",
                "memory": 256,
            })

        self.assertEqual(service.build_strategy, "cnb")

    def test_save_service_info_keeps_explicit_slug_strategy(self):
        service = DummyService(build_strategy="slug")

        with self.patch_side_effects():
            self.service_helper.save_service_info(self.tenant, service, {
                "language": "Python",
                "memory": 256,
            })

        self.assertEqual(service.build_strategy, "slug")

    def test_supports_cnb_build_strategy_falls_back_when_helper_symbol_is_missing(self):
        with patch.object(app_check_service_module.cnb_build_utils, "supports_cnb_build_strategy", None):
            self.assertTrue(app_check_service_module.supports_cnb_build_strategy("Python"))
            self.assertFalse(app_check_service_module.supports_cnb_build_strategy("dockerfile"))

    def test_resolve_lang_update_build_strategy_falls_back_when_helper_symbol_is_missing(self):
        with patch.object(app_check_service_module.cnb_build_utils, "resolve_lang_update_build_strategy", None):
            self.assertEqual(
                app_check_service_module.resolve_lang_update_build_strategy("Java-maven", ""),
                "cnb")
            self.assertEqual(
                app_check_service_module.resolve_lang_update_build_strategy("java-maven", "slug"),
                "slug")
