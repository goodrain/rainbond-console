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

django.setup()

from console.services.app_actions import app_manage_service  # noqa: E402

MODULE = "console.services.app_actions.app_manage"


class VerticalUpgradeGPUTests(TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_name="demo-team", enterprise_id="ent-id", creater=1)
        self.user = SimpleNamespace(nick_name="demo-user")
        self.service = SimpleNamespace(
            service_alias="demo-web",
            service_region="demo-region",
            create_status="complete",
            min_node=1,
            min_memory=2048,
            min_cpu=1000,
            container_gpu=0,
            save=mock.Mock(),
        )

    def _vertical_upgrade(self, **kwargs):
        with mock.patch(MODULE + ".check_account_quota", return_value=True), \
                mock.patch(MODULE + ".baseService.calculate_service_cpu", return_value=2000), \
                mock.patch(MODULE + ".region_api.vertical_upgrade") as region_mock:
            code, msg = app_manage_service.vertical_upgrade(self.tenant, self.service, self.user, oauth_instance=None, **kwargs)
        return code, msg, region_mock

    def test_omitted_gpu_keeps_current_value_instead_of_null(self):
        self.service.container_gpu = 512

        code, _, region_mock = self._vertical_upgrade(new_memory=4096, new_gpu=None, new_cpu=0)

        self.assertEqual(200, code)
        self.assertEqual(512, self.service.container_gpu)
        self.service.save.assert_called_once()
        body = region_mock.call_args[0][3]
        self.assertNotIn("container_gpu", body)

    def test_omitted_gpu_defaults_to_zero_when_current_is_none(self):
        self.service.container_gpu = None

        code, _, _ = self._vertical_upgrade(new_memory=4096, new_gpu=None, new_cpu=0)

        self.assertEqual(200, code)
        self.assertEqual(0, self.service.container_gpu)
        self.service.save.assert_called_once()

    def test_explicit_gpu_is_applied_and_sent_to_region(self):
        code, _, region_mock = self._vertical_upgrade(new_memory=4096, new_gpu=1024, new_cpu=0)

        self.assertEqual(200, code)
        self.assertEqual(1024, self.service.container_gpu)
        body = region_mock.call_args[0][3]
        self.assertEqual(1024, body["container_gpu"])
