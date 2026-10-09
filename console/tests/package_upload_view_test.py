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

from console.views.app_create import source_code as source_code_module  # noqa: E402


class UploadRecordLastViewTests(TestCase):
    # capability_id: console.package-upload.last-record-empty
    def test_get_returns_empty_result_without_logging_when_record_is_missing(self):
        view = source_code_module.UploadRecordLastView()
        request = view.initialize_request(
            APIRequestFactory().get(
                "/console/teams/demo/apps/package_build/last-record",
                {"region": "rainbond"},
            )
        )

        with mock.patch.object(
                source_code_module.package_upload_service,
                "get_last_upload_record",
                return_value=None,
        ), mock.patch.object(source_code_module.logger, "exception") as log_exception:
            response = view.get(request, "demo")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "暂无记录")
        self.assertEqual(response.data["data"]["bean"], {})
        log_exception.assert_not_called()

    # capability_id: console.package-upload.last-record-empty
    def test_get_keeps_existing_upload_record_response(self):
        view = source_code_module.UploadRecordLastView()
        request = view.initialize_request(
            APIRequestFactory().get(
                "/console/teams/demo/apps/package_build/last-record",
                {"region": "rainbond"},
            )
        )
        record = SimpleNamespace(source_dir="['demo.zip']", event_id="event-1")

        with mock.patch.object(
                source_code_module.package_upload_service,
                "get_last_upload_record",
                return_value=record,
        ):
            response = view.get(request, "demo")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], {
            "source_dir": ["demo.zip"],
            "event_id": "event-1",
        })


class PackageCreateViewTests(TestCase):
    def _request(self, view, method, data):
        request_factory = APIRequestFactory()
        request = getattr(request_factory, method)(
            "/console/teams/demo/apps/package_build",
            data,
            format="json",
        )
        return view.initialize_request(request)

    # capability_id: console.package-upload.missing-event-record
    def test_post_returns_404_before_creating_component_when_upload_record_is_missing(self):
        view = source_code_module.PackageCreateView()
        view.team_name = "demo"
        request = self._request(view, "post", {
            "group_id": 1,
            "region": "rainbond",
            "event_id": "missing-event",
            "service_cname": "demo",
        })

        with mock.patch.object(
                source_code_module.package_upload_service,
                "get_upload_record",
                return_value=None,
        ), mock.patch.object(source_code_module.app_service, "create_package_upload_info") as create_component, \
                mock.patch.object(source_code_module.logger, "exception") as log_exception:
            response = view.post(request, "demo")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "上传记录不存在")
        create_component.assert_not_called()
        log_exception.assert_not_called()

    # capability_id: console.package-upload.missing-event-record
    def test_put_returns_404_before_updating_component_when_upload_record_is_missing(self):
        view = source_code_module.PackageCreateView()
        view.team_name = "demo"
        request = self._request(view, "put", {
            "region": "rainbond",
            "event_id": "missing-event",
            "service_id": "service-id",
        })

        with mock.patch.object(
                source_code_module.package_upload_service,
                "get_upload_record",
                return_value=None,
        ), mock.patch.object(source_code_module.app_service, "change_package_upload_info") as update_component, \
                mock.patch.object(source_code_module.logger, "exception") as log_exception:
            response = view.put(request, "demo")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "上传记录不存在")
        update_component.assert_not_called()
        log_exception.assert_not_called()
