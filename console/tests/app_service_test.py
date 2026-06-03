# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest.mock import call, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client_module = sys.modules.setdefault("openapi_client", ModuleType("openapi_client"))
configuration_module = ModuleType("openapi_client.configuration")
rest_module = ModuleType("openapi_client.rest")


class _DummyConfiguration(object):
    def __init__(self):
        self.client_side_validation = False
        self.host = ""
        self.api_key = {}


class _DummyApiException(Exception):
    status = 500
    body = ""


configuration_module.Configuration = _DummyConfiguration
rest_module.ApiException = _DummyApiException
openapi_client_module.configuration = configuration_module
openapi_client_module.rest = rest_module
sys.modules.setdefault("openapi_client.configuration", configuration_module)
sys.modules.setdefault("openapi_client.rest", rest_module)
openssl_module = ModuleType("OpenSSL")
openssl_crypto_module = ModuleType("OpenSSL.crypto")
openssl_module.crypto = openssl_crypto_module
sys.modules.setdefault("OpenSSL", openssl_module)
sys.modules.setdefault("OpenSSL.crypto", openssl_crypto_module)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AppServiceTests(SimpleTestCase):

    def test_get_component_source_default_resources_for_source_code(self):
        from console.services.app import app_service

        resources = app_service.get_component_source_default_resources("region-a", "source_code")

        self.assertEqual(resources["min_memory"], 128)
        self.assertEqual(resources["min_cpu"], 20)
        self.assertEqual(resources["total_memory"], 128)

    def test_get_component_source_default_resources_for_package_build(self):
        from console.services.app import app_service

        resources = app_service.get_component_source_default_resources("region-a", "package_build")

        self.assertEqual(resources["min_memory"], 128)
        self.assertEqual(resources["min_cpu"], 20)
        self.assertEqual(resources["total_memory"], 128)

    def test_get_component_source_default_resources_for_docker_image(self):
        from console.services.app import app_service

        resources = app_service.get_component_source_default_resources("region-a", "docker_image")

        self.assertEqual(resources["min_memory"], 512)
        self.assertEqual(resources["min_cpu"], 0)
        self.assertEqual(resources["total_memory"], 512)

    @patch("console.services.app.env_var_repo")
    def test_ensure_source_build_default_locale_envs_adds_missing_values(self, mock_env_repo):
        from console.services.app import app_service

        tenant = Obj(tenant_id="tenant-1")
        service = Obj(service_id="service-1")
        mock_env_repo.get_service_env_by_attr_name.return_value = None

        app_service.ensure_source_build_default_locale_envs(tenant, service)

        self.assertEqual(mock_env_repo.get_service_env_by_attr_name.call_args_list, [
            call("tenant-1", "service-1", "LANG"),
            call("tenant-1", "service-1", "LC_ALL"),
            call("tenant-1", "service-1", "TZ"),
        ])
        self.assertEqual(mock_env_repo.add_service_env.call_args_list, [
            call(
                tenant_id="tenant-1",
                service_id="service-1",
                container_port=0,
                name="LANG",
                attr_name="LANG",
                attr_value="C.UTF-8",
                is_change=True,
                scope="inner",
            ),
            call(
                tenant_id="tenant-1",
                service_id="service-1",
                container_port=0,
                name="LC_ALL",
                attr_name="LC_ALL",
                attr_value="C.UTF-8",
                is_change=True,
                scope="inner",
            ),
            call(
                tenant_id="tenant-1",
                service_id="service-1",
                container_port=0,
                name="TZ",
                attr_name="TZ",
                attr_value="Asia/Shanghai",
                is_change=True,
                scope="inner",
            ),
        ])

    @patch("console.services.app.env_var_repo")
    def test_ensure_source_build_default_locale_envs_preserves_existing_values(self, mock_env_repo):
        from console.services.app import app_service

        tenant = Obj(tenant_id="tenant-1")
        service = Obj(service_id="service-1")
        mock_env_repo.get_service_env_by_attr_name.side_effect = lambda tenant_id, service_id, name: Obj(
            attr_name=name) if name == "LANG" else None

        app_service.ensure_source_build_default_locale_envs(tenant, service)

        self.assertEqual(mock_env_repo.add_service_env.call_args_list, [
            call(
                tenant_id="tenant-1",
                service_id="service-1",
                container_port=0,
                name="LC_ALL",
                attr_name="LC_ALL",
                attr_value="C.UTF-8",
                is_change=True,
                scope="inner",
            ),
            call(
                tenant_id="tenant-1",
                service_id="service-1",
                container_port=0,
                name="TZ",
                attr_name="TZ",
                attr_value="Asia/Shanghai",
                is_change=True,
                scope="inner",
            ),
        ])

    @patch("console.services.app.gitHubClient.createReposHook")
    def test_init_repositories_defaults_missing_github_project_id_to_zero(self, mock_create_hook):
        from console.services.app import app_service

        service = Obj()
        service.save = lambda: None
        user = Obj(github_token="token-1")

        code, msg = app_service.init_repositories(
            service,
            user,
            "github",
            "https://github.com/goodrain/rainbond.git",
            None,
            "main",
            None,
            None,
            None,
            None,
        )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        self.assertEqual(service.git_project_id, 0)
        self.assertEqual(service.git_url, "https://github.com/goodrain/rainbond.git")
        self.assertEqual(service.code_from, "github")
        self.assertEqual(service.code_version, "main")
        mock_create_hook.assert_called_once_with("goodrain", "rainbond", "token-1")

    @patch("console.services.app.gitHubClient.createReposHook")
    def test_init_repositories_skips_github_hook_without_github_token(self, mock_create_hook):
        from console.services.app import app_service

        service = Obj()
        service.save = lambda: None
        user = Obj()

        code, msg = app_service.init_repositories(
            service,
            user,
            "github",
            "https://github.com/goodrain/rainbond.git",
            None,
            "main",
            None,
            None,
            None,
            None,
        )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        self.assertEqual(service.git_project_id, 0)
        mock_create_hook.assert_not_called()
