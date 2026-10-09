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

from console.views import app_manage as app_manage_view  # noqa: E402


class BatchActionViewTestCase(TestCase):
    # capability_id: console.component-batch-action.missing-app
    def test_post_keeps_batch_action_successful_when_component_has_no_app(self):
        view = app_manage_view.BatchActionView()
        view.region_name = "region-a"
        view.tenant = mock.Mock()
        view.user = mock.Mock(enterprise_id="enterprise-id")
        view.team_name = "demo-team"
        view.oauth_instance = None
        request = view.initialize_request(
            APIRequestFactory().post(
                "/console/teams/demo-team/batch_actions",
                {"action": "restart", "service_ids": "service-1"},
                format="json",
            )
        )
        service = mock.Mock(service_cname="api", service_alias="grapi")

        with mock.patch.object(app_manage_view.group_service, "get_service_group_info", return_value=None), \
                mock.patch.object(
                    app_manage_view.app_manage_service,
                    "batch_action",
                    return_value=(200, "success", [service]),
                ), mock.patch.object(
                    app_manage_view.operation_log_service,
                    "process_component_name",
                    return_value="api",
                ), mock.patch.object(app_manage_view.operation_log_service, "create_log") as create_log:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "操作成功")
        self.assertIn("未分组", create_log.call_args.kwargs["comment"])
        self.assertEqual(create_log.call_args.kwargs["app_id"], 0)
