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
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.urls import resolve  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import enterprise  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.lang-version.proxy-upload
class UploadLongVersionProxyViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = enterprise.UploadLongVersion()

    # capability_id: console.lang-version.proxy-upload
    def test_legacy_upload_route_is_registered(self):
        match = resolve("/console/enterprise/lg_pack_operate")

        self.assertIs(match.func.view_class, enterprise.UploadLongVersion)

    # capability_id: console.lang-version.proxy-upload
    def test_post_proxies_upload_to_region_websocket_endpoint(self):
        upload_file = SimpleUploadedFile("demo.jar", b"PK\x03\x04demo", content_type="application/java-archive")
        request = self.view.initialize_request(
            self.factory.post(
                "/console/enterprise/lg_pack_operate",
                {"enterprise_id": "eid-1", "region_id": "region-1", "file": upload_file},
                format="multipart",
                HTTP_AUTHORIZATION="JWT demo-token",
            )
        )
        proxy_response = mock.Mock(status_code=200)
        proxy_response.json.return_value = {
            "code": 200,
            "message": "successful",
            "bean": {"event_id": "evt-1", "file_name": "demo.jar"},
        }

        with mock.patch.object(enterprise.region_repo, "get_region_by_id", return_value=Obj(wsurl="wss://region.example.com/ws")), \
                mock.patch.object(enterprise.requests, "post", return_value=proxy_response) as post_mock:
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["bean"]["event_id"], "evt-1")
        post_mock.assert_called_once()
        target_url = post_mock.call_args[0][0]
        files = post_mock.call_args[1]["files"]
        headers = post_mock.call_args[1]["headers"]
        self.assertEqual(target_url, "https://region.example.com/ws/lg_pack_operate/upload")
        self.assertEqual(headers, {"Authorization": "JWT demo-token"})
        self.assertEqual(files["file"][0], "demo.jar")
        self.assertEqual(files["file"][1], b"PK\x03\x04demo")
        self.assertEqual(files["file"][2], "application/java-archive")

    # capability_id: console.lang-version.proxy-upload
    def test_post_requires_file(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/enterprise/lg_pack_operate",
                {"enterprise_id": "eid-1", "region_id": "region-1"},
                format="multipart",
            )
        )

        response = self.view.post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "获取文件失败")

    # capability_id: console.lang-version.proxy-upload
    def test_post_returns_not_found_when_region_is_missing(self):
        upload_file = SimpleUploadedFile("demo.jar", b"PK\x03\x04demo", content_type="application/java-archive")
        request = self.view.initialize_request(
            self.factory.post(
                "/console/enterprise/lg_pack_operate",
                {"enterprise_id": "eid-1", "region_id": "missing-region", "file": upload_file},
                format="multipart",
            )
        )

        with mock.patch.object(enterprise.region_repo, "get_region_by_id", return_value=None):
            response = self.view.post(request)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "数据中心不存在")

    # capability_id: console.lang-version.proxy-upload
    def test_options_is_supported_for_legacy_preflight_requests(self):
        request = self.factory.options("/console/enterprise/lg_pack_operate")

        response = enterprise.UploadLongVersion.as_view()(request)

        self.assertEqual(response.status_code, 200)
