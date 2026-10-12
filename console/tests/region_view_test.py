# coding: utf-8
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import region as region_view_module  # noqa: E402


class QueryRegionViewTests(TestCase):
    # capability_id: console.region.list-current-enterprise
    def test_get_uses_authenticated_users_enterprise_without_path_parameter(self):
        request = APIRequestFactory().get("/console/regions")
        view = region_view_module.QyeryRegionView()
        view.user = SimpleNamespace(enterprise_id="eid-1")
        region = mock.Mock()
        region.to_dict.return_value = {"region_name": "rainbond"}

        with mock.patch.object(
                region_view_module.region_services,
                "get_open_regions",
                return_value=[region],
        ) as get_open_regions:
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], [{"region_name": "rainbond"}])
        get_open_regions.assert_called_once_with("eid-1")
