# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
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

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException

    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.app_config_group import AppConfigGroupView  # noqa: E402


class AppConfigGroupViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppConfigGroupView()
        self.view.region_name = "demo-region"
        self.view.tenant_name = "demo-team"
        self.view.app = SimpleNamespace(app_name="Demo App", app_id="app-1")

    def test_delete_reads_config_group_before_deleting_it(self):
        request = self.factory.delete("/console/apps/app-1/config-groups/demo-config")
        config_group = {
            "config_group_name": "demo-config",
            "enable": True,
            "services": [{
                "service_cname": "Demo Service"
            }],
            "config_items": [{
                "item_key": "LOG_LEVEL",
                "item_value": "info"
            }],
        }
        state = {"deleted": False}

        def get_config_group_side_effect(*args):
            if state["deleted"]:
                raise AssertionError("config group was read after deletion")
            return config_group

        def delete_config_group_side_effect(*args):
            state["deleted"] = True

        with (
                mock.patch(
                    "console.views.app_config_group.app_config_group_service.get_config_group",
                    side_effect=get_config_group_side_effect,
                ) as get_config_group,
                mock.patch(
                    "console.views.app_config_group.app_config_group_service.delete_config_group",
                    side_effect=delete_config_group_side_effect,
                ) as delete_config_group,
                mock.patch(
                    "console.views.app_config_group.app_config_group_service.json_config_groups",
                    return_value="old-information",
                ) as json_config_groups,
                mock.patch(
                    "console.views.app_config_group.operation_log_service.process_app_name",
                    return_value="Demo App",
                ),
                mock.patch("console.views.app_config_group.operation_log_service.create_app_log") as create_app_log,
        ):
            response = self.view.delete(request, team_name="demo-team", app_id="app-1", name="demo-config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], config_group)
        get_config_group.assert_called_once_with("demo-region", "app-1", "demo-config")
        delete_config_group.assert_called_once_with("demo-region", "demo-team", "app-1", "demo-config")
        json_config_groups.assert_called_once_with(
            config_group_name="demo-config",
            config_items=[{
                "变量名": "LOG_LEVEL",
                "变量值": "info"
            }],
            enable=True,
            services_names=["Demo Service"],
        )
        create_app_log.assert_called_once_with(
            self.view,
            "删除了应用 Demo App 的配置组 demo-config",
            format_app=False,
            old_information="old-information",
        )
