# -*- coding: utf-8 -*-
import os
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration(object):
        def __init__(self):
            self.host = ""
            self.api_key = {}

    configuration_module.Configuration = _Configuration
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

from console.exception.bcode import ErrK8sComponentNameExists  # noqa: E402
from console.services import multi_app_service as multi_app_service_module  # noqa: E402


class MultiAppServiceTests(TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant-1")
        self.user = SimpleNamespace(pk=1, nick_name="admin")
        self.temporary_service = SimpleNamespace(
            service_id="temporary-service",
            service_alias="temporary-alias",
            code_from="git",
            clone_url="https://git.example.com/demo.git",
            git_project_id=1,
            code_version="main",
            server_type="git",
            oauth_service_id=None,
            git_full_name="demo/repository",
            open_webhooks=False,
        )

    @contextmanager
    def service_dependencies(self, duplicate=False):
        created_service = SimpleNamespace(
            service_id="created-service",
            create_status="creating",
            save=mock.Mock(),
        )
        with mock.patch.object(multi_app_service_module.service_source_repo, "get_service_source",
                               return_value=None), mock.patch.object(
                                   multi_app_service_module.app_service,
                                   "is_k8s_component_name_duplicate",
                                   return_value=duplicate) as duplicate_name, mock.patch.object(
                                       multi_app_service_module.app_service,
                                       "create_source_code_app",
                                       return_value=(200, "success", created_service)) as create_source, mock.patch.object(
                                           multi_app_service_module.group_service,
                                           "add_service_to_group",
                                           return_value=(200, "success")), mock.patch.object(
                                               multi_app_service_module.app_check_service,
                                               "save_service_info"), mock.patch.object(multi_app_service_module.app_service,
                                                                                       "create_region_service",
                                                                                       return_value=created_service):
            yield duplicate_name, create_source

    def save_services(self, service_infos):
        save_multi_services = multi_app_service_module.multi_app_service.save_multi_services.__wrapped__
        return save_multi_services(
            multi_app_service_module.multi_app_service,
            region_name="rainbond",
            tenant=self.tenant,
            group_id=12,
            service=self.temporary_service,
            user=self.user,
            service_infos=service_infos,
            host="https://console.example.com",
        )

    def test_passes_k8s_component_name_to_source_component_creation(self):
        service_info = {
            "cname": "Registry",
            "k8s_component_name": "pig-register",
            "arch": "arm64",
            "envs": [],
        }

        with self.service_dependencies() as (duplicate_name, create_source):
            service_ids = self.save_services([service_info])

        self.assertEqual(service_ids, ["created-service"])
        duplicate_name.assert_called_once_with(12, "pig-register")
        create_source.assert_called_once_with(
            "rainbond",
            self.tenant,
            self.user,
            "git",
            "Registry",
            "https://git.example.com/demo.git",
            1,
            "main",
            "git",
            oauth_service_id=None,
            git_full_name="demo/repository",
            k8s_component_name="pig-register",
            arch="arm64",
        )

    def test_rejects_duplicate_k8s_component_name_before_creation(self):
        service_info = {
            "cname": "Registry",
            "k8s_component_name": "pig-register",
            "arch": "amd64",
            "envs": [],
        }

        with self.service_dependencies(duplicate=True) as (duplicate_name, create_source):
            with self.assertRaises(ErrK8sComponentNameExists):
                self.save_services([service_info])

        duplicate_name.assert_called_once_with(12, "pig-register")
        create_source.assert_not_called()

    def test_missing_k8s_component_name_keeps_legacy_alias_generation(self):
        service_info = {
            "cname": "Registry",
            "arch": "amd64",
            "envs": [],
        }

        with self.service_dependencies() as (duplicate_name, create_source):
            self.save_services([service_info])

        duplicate_name.assert_not_called()
        self.assertEqual(create_source.call_args.kwargs["k8s_component_name"], "")
