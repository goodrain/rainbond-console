# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import group_service as group_service_module  # noqa: E402
from console.services.group_service import group_service  # noqa: E402


# capability_id: console.app-status.region-status-typeddict
class GroupAppStatusTypedDictTest(TestCase):
    def _tenant(self):
        return mock.Mock(tenant_name="demo-team", enterprise_id="ent-1")

    def test_returns_empty_dict_when_region_status_is_none(self):
        # region get_app_status payload may be null; the caller must not deref None.
        with mock.patch.object(group_service_module.region_app_repo, "get_region_app_id", return_value="ra-1"), \
                mock.patch.object(group_service_module.region_api, "get_app_status", return_value=None), \
                mock.patch.object(group_service_module.group_repo, "get_group_by_id", return_value=None):
            status = group_service.get_app_status(self._tenant(), "demo-region", 1)
        self.assertEqual(status, {})

    def test_normalizes_nil_status_and_overrides(self):
        region_status = {"status": "NIL", "overrides": ["A=1", "B=2"], "k8s_app": "demo"}
        with mock.patch.object(group_service_module.region_app_repo, "get_region_app_id", return_value="ra-1"), \
                mock.patch.object(group_service_module.region_api, "get_app_status", return_value=region_status), \
                mock.patch.object(group_service_module.group_repo, "get_group_by_id", return_value=None):
            status = group_service.get_app_status(self._tenant(), "demo-region", 1)
        self.assertIsNone(status["status"])
        self.assertEqual(status["overrides"], [{"A": "1"}, {"B": "2"}])
        self.assertEqual(status["k8s_app"], "demo")
