import importlib
import sys
import types
from unittest import TestCase
from unittest.mock import MagicMock


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class RegionLongVersionServiceTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.repositories.app_config",
            "console.services.region_lang_version",
            "www.apiclient.regionapi",
        ):
            sys.modules.pop(module_name, None)

    def import_service_module(self):
        compile_env_repo = MagicMock()
        compile_env_repo.get_lang_version_in_use.return_value = []
        install_stub("console.repositories.app_config", compile_env_repo=compile_env_repo)

        class DummyRegionInvokeApi(object):
            def __init__(self):
                self.get_lang_version = MagicMock(return_value={"list": []})
                self.create_lang_version = MagicMock(return_value={"bean": {}})
                self.update_lang_version = MagicMock(return_value={"bean": {}})
                self.delete_lang_version = MagicMock(return_value={})

        install_stub("www.apiclient.regionapi", RegionInvokeApi=DummyRegionInvokeApi)
        return importlib.import_module("console.services.region_lang_version")

    def test_show_long_version_passes_strategy_and_defaults_missing_fields(self):
        service_module = self.import_service_module()
        service_module.region_api.get_lang_version.return_value = {
            "list": [{
                "lang": "python",
                "version": "3.11"
            }]
        }

        result = service_module.region_lang_version.show_long_version("eid", "region-a", "python", "cnb")

        service_module.region_api.get_lang_version.assert_called_once_with("eid", "region-a", "python", "", "cnb")
        self.assertEqual(result["list"][0]["build_strategy"], "slug")
        self.assertTrue(result["list"][0]["is_allowed"])

    def test_create_long_version_defaults_slug_and_allowed(self):
        service_module = self.import_service_module()

        service_module.region_lang_version.create_long_version(
            "eid", "region-a", "python", "3.11", "event-1", "Python3.11.tar.gz")

        service_module.region_api.create_lang_version.assert_called_once_with(
            "eid", "region-a", {
                "lang": "python",
                "version": "3.11",
                "event_id": "event-1",
                "file_name": "Python3.11.tar.gz",
                "show": True,
                "build_strategy": "slug",
                "is_allowed": True,
            })

    def test_update_long_version_only_sends_optional_strategy_fields_when_given(self):
        service_module = self.import_service_module()

        service_module.region_lang_version.update_long_version(
            "eid", "region-a", "python", "3.11", False, True)
        service_module.region_api.update_lang_version.assert_called_once_with(
            "eid", "region-a", {
                "lang": "python",
                "version": "3.11",
                "show": False,
                "first_choice": True
            })

        service_module.region_api.update_lang_version.reset_mock()
        service_module.region_lang_version.update_long_version(
            "eid", "region-a", "python", "3.11", True, False, build_strategy="cnb", is_allowed=False)
        service_module.region_api.update_lang_version.assert_called_once_with(
            "eid", "region-a", {
                "lang": "python",
                "version": "3.11",
                "show": True,
                "first_choice": False,
                "build_strategy": "cnb",
                "is_allowed": False,
            })

