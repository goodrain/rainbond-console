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
