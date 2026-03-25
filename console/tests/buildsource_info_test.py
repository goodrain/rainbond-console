import importlib
import sys
import types
from unittest import TestCase
from unittest.mock import MagicMock


class DummyService(object):
    def __init__(self):
        self.service_id = "svc-1"
        self.service_source = "source_code"
        self.image = ""
        self.cmd = ""
        self.code_from = "gitlab"
        self.version = "v1"
        self.docker_cmd = ""
        self.create_time = "2026-03-24"
        self.git_url = "https://example.com/demo.git"
        self.code_version = "main"
        self.server_type = "source"
        self.language = "Python"
        self.build_strategy = "cnb"
        self.oauth_service_id = ""
        self.git_full_name = "demo/demo"
        self.service_region = "region-a"


class DummyTenant(object):
    enterprise_id = "eid"
    tenant_id = "team-1"


class DummyRegionInvokeApi(object):
    pass


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class BuildSourceInfoServiceTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.exception.main",
            "console.repositories.app",
            "console.repositories.service_repo",
            "console.services.region_lang_version",
            "console.services.service_services",
            "console.utils.oauth.oauth_types",
            "www.apiclient.regionapi",
            "www.db.base",
        ):
            sys.modules.pop(module_name, None)

    def import_service_module(self):
        service_repo = MagicMock()
        service_repo.list_by_component_ids.return_value = [DummyService()]

        service_source_repo = MagicMock()
        service_source_repo.get_service_sources.return_value = []
        env_var_repo = MagicMock()
        env_var_repo.get_build_envs.return_value = {
            "BUILD_TYPE": "cnb",
            "BUILD_RUNTIMES": "3.11"
        }

        install_stub(
            "console.exception.main",
            AbortRequest=Exception,
            RbdAppNotFound=Exception,
            ServiceHandleException=Exception,
        )
        install_stub("console.repositories.app", service_repo=service_repo, service_source_repo=service_source_repo)
        install_stub("console.repositories.service_repo", service_repo=service_repo)
        install_stub("console.repositories.app_config", env_var_repo=env_var_repo)
        install_stub("console.utils.oauth.oauth_types", support_oauth_type={})
        install_stub("www.apiclient.regionapi", RegionInvokeApi=DummyRegionInvokeApi)
        install_stub("www.db.base", BaseConnection=object)
        install_stub(
            "console.services.region_lang_version",
            region_lang_version=types.SimpleNamespace(show_long_version=MagicMock(return_value={
                "list": [{
                    "lang": "python",
                    "version": "python-3.11.9",
                    "build_strategy": "cnb",
                    "show": True,
                    "is_allowed": True,
                    "first_choice": True
                }]
            })),
            region_cnb_config=types.SimpleNamespace(show_cnb_versions=MagicMock(return_value={"list": []})),
        )
        service_module = importlib.import_module("console.services.service_services")
        service_module.service_source_repo = service_source_repo
        service_module.env_var_repo = env_var_repo
        return service_module

    def test_build_infos_attach_cnb_version_policy(self):
        service_module = self.import_service_module()

        build_infos = service_module.base_service.get_build_infos(DummyTenant(), ["svc-1"])

        self.assertEqual(build_infos["svc-1"]["cnb_version_policy"], {
            "python": {
                "cpython": {
                    "visible_versions": ["3.11"],
                    "allowed_versions": ["3.11"],
                    "default_version": "3.11"
                }
            }
        })
        self.assertEqual(build_infos["svc-1"]["builder_image"], "registry.cn-hangzhou.aliyuncs.com/goodrain/ubuntu-noble-builder:0.0.72")
        self.assertEqual(build_infos["svc-1"]["start_command_source"], "buildpack-default")
        self.assertEqual(build_infos["svc-1"]["yaml_observable"]["annotations"]["rainbond.io/cnb-language"], "python")
