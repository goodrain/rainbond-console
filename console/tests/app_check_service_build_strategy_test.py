from unittest import TestCase
from unittest.mock import patch, Mock

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
        self.service_source = "source_code"
        self.oauth_service_id = ""
        self.service_region = "region-a"
        self.code_version = "main"
        self.git_url = "https://example.com/demo.git"
        self.tenant_id = "team-1"
        self.service_id = "service-1"
        self.create_status = "complete"

    def save(self):
        return None

    def to_dict(self):
        return {}


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

    @patch.object(app_check_service_module, "service_source_repo")
    @patch.object(app_check_service_module, "region_api")
    def test_check_service_forwards_build_strategy_in_source_body(self, region_api, service_source_repo):
        service = DummyService(build_strategy="cnb")
        region_api.service_source_check.return_value = (
            None,
            {"bean": {"check_uuid": "chk-1", "event_id": "evt-1"}},
        )
        service_source_repo.get_service_source.return_value = None

        code, msg, _ = self.service_helper.check_service(self.tenant, service, False, "evt-1", user=Mock(user_id="u-1"))

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        args, _ = region_api.service_source_check.call_args
        request_body = args[2]
        self.assertIn("source_body", request_body)
        source_body = request_body["source_body"]
        self.assertIn('"build_strategy": "cnb"', source_body)
