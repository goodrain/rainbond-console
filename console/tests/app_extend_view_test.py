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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.app_config.app_extend import AppExtendView  # noqa: E402


class AppExtendViewVMLiveUpdateCapabilityTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppExtendView()
        self.view.tenant = SimpleNamespace(tenant_name="demo-team")
        self.view.service = SimpleNamespace(
            service_alias="demo-vm",
            service_region="demo-region",
            extend_method="vm",
            create_status="complete",
            min_node=1,
            min_memory=12288,
            container_gpu=0,
            min_cpu=6000
        )

    def test_get_includes_vm_live_update_capability_for_vm(self):
        request = self.factory.get("/console/teams/demo-team/apps/demo-vm/extend_method")

        with mock.patch("console.views.app_config.app_extend.extend_service.get_app_extend_method", return_value=([1], [12288])), \
                mock.patch("console.views.app_config.app_extend.region_api.get_vm_live_update_capability", return_value=(None, {
                    "bean": {
                        "cpu_hot_update_supported": True,
                        "memory_hot_update_supported": True,
                        "hot_update_reason": ""
                    }
                })) as capability_mock:
            response = self.view.get(request)

        self.assertEqual(200, response.status_code)
        bean = response.data["data"]["bean"]
        self.assertTrue(bean["cpu_hot_update_supported"])
        self.assertTrue(bean["memory_hot_update_supported"])
        self.assertEqual("", bean["hot_update_reason"])
        capability_mock.assert_called_once_with("demo-region", "demo-team", "demo-vm")

    def test_get_skips_capability_lookup_for_non_vm(self):
        request = self.factory.get("/console/teams/demo-team/apps/demo-web/extend_method")
        self.view.service.extend_method = "stateless_multiple"

        with mock.patch("console.views.app_config.app_extend.extend_service.get_app_extend_method", return_value=([1], [512])), \
                mock.patch("console.views.app_config.app_extend.region_api.get_vm_live_update_capability") as capability_mock:
            response = self.view.get(request)

        self.assertEqual(200, response.status_code)
        bean = response.data["data"]["bean"]
        self.assertFalse(bean["cpu_hot_update_supported"])
        self.assertFalse(bean["memory_hot_update_supported"])
        self.assertEqual("", bean["hot_update_reason"])
        capability_mock.assert_not_called()

    def test_get_returns_fallback_reason_when_capability_lookup_fails(self):
        request = self.factory.get("/console/teams/demo-team/apps/demo-vm/extend_method")

        with mock.patch("console.views.app_config.app_extend.extend_service.get_app_extend_method", return_value=([1], [12288])), \
                mock.patch("console.views.app_config.app_extend.region_api.get_vm_live_update_capability", side_effect=Exception("boom")):
            response = self.view.get(request)

        self.assertEqual(200, response.status_code)
        bean = response.data["data"]["bean"]
        self.assertFalse(bean["cpu_hot_update_supported"])
        self.assertFalse(bean["memory_hot_update_supported"])
        self.assertEqual("当前暂时无法判断虚拟机是否支持热更新，请稍后重试。", bean["hot_update_reason"])
