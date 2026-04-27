# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
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

from console.views.app_config.app_volume import AppVolumeManageView  # noqa: E402


class AppVolumeManageViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppVolumeManageView()
        self.view.tenant = mock.Mock(tenant_name="demo-team")
        self.view.service = mock.Mock(
            create_status="complete",
            service_region="region-1",
            service_alias="demo-service",
            service_cname="Demo Service",
        )
        self.view.user = mock.Mock(nick_name="demo-user", enterprise_id="enterprise-1")
        self.view.app = mock.Mock(ID=1)

    # capability_id: console.component.storage-update-capacity
    def test_put_allows_updating_volume_capacity_without_path_change(self):
        request = self.factory.put(
            "/console/teams/demo-team/apps/demo-service/volumes/1",
            {"new_volume_path": "/data", "volume_capacity": 20},
            format="json",
        )
        request.data = {"new_volume_path": "/data", "volume_capacity": 20}
        volume = mock.Mock(
            volume_name="data",
            volume_path="/data",
            volume_type="share-file",
            volume_capacity=10,
            mode=None,
        )

        with mock.patch("console.views.app_config.app_volume.volume_repo.get_service_volume_by_pk", return_value=volume):
            with mock.patch("console.views.app_config.app_volume.volume_repo.get_service_config_file", return_value=None):
                with mock.patch(
                    "console.views.app_config.app_volume.volume_service.json_service_volume", return_value="{}"
                ):
                    with mock.patch(
                        "console.views.app_config.app_volume.region_api.upgrade_service_volumes",
                        return_value=(mock.Mock(status=200), {}),
                    ) as mock_region:
                        with mock.patch(
                            "console.views.app_config.app_volume.operation_log_service.generate_component_comment",
                            return_value="comment",
                        ):
                            with mock.patch("console.views.app_config.app_volume.operation_log_service.create_component_log"):
                                response = self.view.put(request, volume_id="1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(volume.volume_capacity, 20)
        volume.save.assert_called_once_with()
        self.assertEqual(mock_region.call_args[0][3]["volume_capacity"], 20)
