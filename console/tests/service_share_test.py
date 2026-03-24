# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import service_share  # noqa: E402
from console.views.service_share import ServiceShareRecordView  # noqa: E402


class ServiceShareRecordViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ServiceShareRecordView()
        self.view.team = mock.Mock(tenant_id=1, tenant_name="demo-team")
        self.view.tenant = mock.Mock(tenant_name="demo-team")
        self.view.user = mock.Mock(user_id=1)
        self.view.response_region = "demo-region"

    def make_request(self, payload):
        return self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/groups/30/share/record", payload, format="json"))

    def test_post_snapshot_mode_uses_hidden_template_app_id(self):
        request = self.make_request({"scope": "team", "snapshot_mode": True, "snapshot_app_id": "origin-app-id"})
        share_record = mock.Mock()
        share_record.to_dict.return_value = {"group_share_id": "share-uuid"}
        hidden_template = mock.Mock(app_id="hidden-app-id")

        with mock.patch.object(
                service_share.group_repo, "get_group_count_by_team_id_and_group_id", return_value=1), \
                mock.patch.object(service_share.share_service, "check_service_source", return_value=None), \
                mock.patch("console.services.group_service.group_service.get_group_or_404",
                           return_value=mock.Mock()) as get_group_mock, \
                mock.patch.object(
                    service_share.app_version_service,
                    "get_or_create_hidden_template",
                    return_value=(mock.Mock(), hidden_template)), \
                mock.patch.object(
                    service_share.share_service,
                    "create_service_share_record",
                    return_value=share_record) as create_record_mock, \
                mock.patch.object(service_share, "make_uuid", return_value="share-uuid"):
            response = self.view.post(request, "demo-team", "30")

        self.assertEqual(response.status_code, 200)
        get_group_mock.assert_called_once_with(self.view.tenant, self.view.response_region, 30)
        _, kwargs = create_record_mock.call_args
        self.assertEqual(kwargs["app_id"], "hidden-app-id")
        self.assertEqual(kwargs["group_share_id"], "share-uuid")

    def test_post_returns_500_response_for_unexpected_exception(self):
        request = self.make_request({"scope": "team"})

        with mock.patch.object(
                service_share.group_repo, "get_group_count_by_team_id_and_group_id", return_value=1), \
                mock.patch.object(service_share.share_service, "check_service_source", return_value=None), \
                mock.patch.object(
                    service_share.share_service,
                    "create_service_share_record",
                    side_effect=RuntimeError("boom")), \
                mock.patch.object(service_share, "make_uuid", return_value="share-uuid"):
            response = self.view.post(request, "demo-team", "30")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg"], "boom")
        self.assertEqual(response.data["msg_show"], "系统异常")
