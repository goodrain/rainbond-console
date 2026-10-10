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

from console.views.app_create import source_code as source_code_view_module  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.package-create.group-id-validation
class PackageCreateViewGroupIdTests(TestCase):
    def setUp(self):
        self.view = source_code_view_module.PackageCreateView()
        self.view.team_name = "demo-team"
        self.view.response_region = "demo-region"
        self.view.tenant = Obj(tenant_id="tenant-id")
        self.view.user = Obj(user_id=1)

    def test_post_rejects_invalid_group_id_before_package_lookup(self):
        for group_id in (None, "", "abc", True, 0, -1):
            with self.subTest(group_id=group_id), mock.patch.object(
                    source_code_view_module.package_upload_service,
                    "get_upload_record",
            ) as get_upload_record:
                response = self.view.post(
                    Obj(data={"group_id": group_id}, META={}),
                    tenantName="demo-team",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["msg_show"], "应用 ID 无效")
            get_upload_record.assert_not_called()

    def test_post_normalizes_numeric_group_id_before_service_calls(self):
        package_record = Obj(create_time="2026-10-08T00:00:00Z")
        service = Obj(service_id="service-1", to_dict=lambda: {"service_id": "service-1"})
        request = Obj(data={
            "group_id": "42",
            "region": "demo-region",
            "event_id": "event-1",
            "service_cname": "demo",
            "k8s_component_name": "demo",
        }, META={})

        with mock.patch.object(
                source_code_view_module.app_service,
                "is_k8s_component_name_duplicate",
                return_value=False,
        ) as duplicate_check, mock.patch.object(
                source_code_view_module.package_upload_service,
                "get_upload_record",
                return_value=package_record,
        ), mock.patch.object(
                source_code_view_module.app_service,
                "create_package_upload_info",
                return_value=service,
        ), mock.patch.object(
                source_code_view_module.package_upload_service,
                "update_upload_record",
        ), mock.patch.object(
                source_code_view_module.group_service,
                "add_service_to_group",
                return_value=(200, "success"),
        ) as add_to_group:
            response = self.view.post(request, tenantName="demo-team")

        self.assertEqual(response.status_code, 200)
        duplicate_check.assert_called_once_with("42", "demo")
        add_to_group.assert_called_once_with(
            self.view.tenant,
            "demo-region",
            42,
            "service-1",
        )
