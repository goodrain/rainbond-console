# -*- coding: utf-8 -*-
import os
import shutil
import sys
import tempfile
import zipfile
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class PackageUploadToolServiceTests(SimpleTestCase):

    # capability_id: console.package-upload.archive-reuse
    def test_prepare_upload_archive_reuses_supported_package_file(self):
        from console.services.package_upload_tool_service import package_upload_tool_service

        with tempfile.NamedTemporaryFile(suffix=".war") as temp_file:
            archive_path, should_cleanup = package_upload_tool_service._prepare_upload_archive(temp_file.name, "")

            self.assertEqual(archive_path, temp_file.name)
            self.assertFalse(should_cleanup)

    # capability_id: console.package-upload.archive-zip-dir
    def test_prepare_upload_archive_zips_directory(self):
        from console.services.package_upload_tool_service import package_upload_tool_service

        temp_dir = tempfile.mkdtemp(prefix="pkg-upload-")
        archive_path = ""
        try:
            os.makedirs(os.path.join(temp_dir, "dist"))
            with open(os.path.join(temp_dir, "dist", "index.html"), "w") as handle:
                handle.write("<html></html>")
            with open(os.path.join(temp_dir, "README.txt"), "w") as handle:
                handle.write("demo")

            archive_path, should_cleanup = package_upload_tool_service._prepare_upload_archive(temp_dir, "demo-package")

            self.assertTrue(should_cleanup)
            self.assertTrue(archive_path.endswith(".zip"))
            self.assertTrue(os.path.exists(archive_path))

            with zipfile.ZipFile(archive_path, "r") as archive:
                self.assertEqual(sorted(archive.namelist()), ["README.txt", "dist/index.html"])
        finally:
            if archive_path and os.path.exists(archive_path):
                os.remove(archive_path)
            shutil.rmtree(temp_dir)

    @patch("console.services.package_upload_tool_service.import_service.get_upload_package_url")
    @patch("console.services.package_upload_tool_service.package_upload_service.create_upload_record")
    @patch("console.services.package_upload_tool_service.region_api.create_upload_file_dir")
    @patch("console.services.package_upload_tool_service.make_uuid")
    # capability_id: console.package-upload.init-flow
    def test_init_upload_creates_remote_dir_and_record(
            self,
            mock_make_uuid,
            mock_create_dir,
            mock_create_record,
            mock_get_upload_url):
        from console.services.package_upload_tool_service import package_upload_tool_service

        mock_make_uuid.return_value = "evt-upload-1"
        mock_create_dir.return_value = (None, {"bean": {"path": "/grdata/package_build/temp/events/evt-upload-1"}})
        mock_create_record.return_value = Obj(
            event_id="evt-upload-1",
            status="unfinished",
            team_name="demo-team",
            region="rainbond",
            component_id=""
        )
        mock_get_upload_url.return_value = "http://region-ws/package_build/component/events/evt-upload-1"

        result = package_upload_tool_service.init_upload("demo-team", "rainbond", "")

        self.assertEqual(result["event_id"], "evt-upload-1")
        self.assertEqual(result["upload_url"], "http://region-ws/package_build/component/events/evt-upload-1")
        mock_create_record.assert_called_once()

    @patch("console.services.package_upload_tool_service.package_upload_tool_service.get_upload_status")
    @patch("console.services.package_upload_tool_service.requests.post")
    @patch("console.services.package_upload_tool_service.package_upload_service.get_upload_record")
    @patch("console.services.package_upload_tool_service.import_service.get_upload_package_url")
    # capability_id: console.package-upload.upload-flow
    def test_upload_package_uploads_archive_and_returns_status(
            self,
            mock_get_upload_url,
            mock_get_upload_record,
            mock_requests_post,
            mock_get_upload_status):
        from console.services.package_upload_tool_service import package_upload_tool_service

        temp_dir = tempfile.mkdtemp(prefix="pkg-upload-")
        try:
            with open(os.path.join(temp_dir, "main.py"), "w") as handle:
                handle.write("print('ok')\n")

            mock_get_upload_url.return_value = "http://region-ws/package_build/component/events/evt-upload-1"
            mock_get_upload_record.return_value = Obj(event_id="evt-upload-1")
            mock_requests_post.return_value = Obj(status_code=200, text="ok")
            mock_get_upload_status.return_value = {
                "event_id": "evt-upload-1",
                "uploaded_packages": ["demo-package.zip"],
                "uploaded": True,
            }

            result = package_upload_tool_service.upload_package(
                "demo-team", "rainbond", "evt-upload-1", temp_dir, "demo-package"
            )

            self.assertTrue(result["uploaded"])
            self.assertEqual(
                mock_requests_post.call_args[0][0],
                "http://region-ws/package_build/component/events/evt-upload-1",
            )
            upload_file = mock_requests_post.call_args[1]["files"]["packageTarFile"]
            self.assertEqual(upload_file[0], "demo-package.zip")
        finally:
            shutil.rmtree(temp_dir)

    @patch("console.services.package_upload_tool_service.package_upload_service.update_upload_record")
    @patch("console.services.package_upload_tool_service.region_api.get_upload_file_dir")
    # capability_id: console.package-upload.status-flow
    def test_get_upload_status_reads_packages_and_updates_record(self, mock_get_upload_dir, mock_update_record):
        from console.services.package_upload_tool_service import package_upload_tool_service

        mock_get_upload_dir.return_value = (None, {"bean": {"packages": ["demo.zip"]}})

        result = package_upload_tool_service.get_upload_status("demo-team", "rainbond", "evt-upload-1")

        self.assertEqual(result["uploaded_packages"], ["demo.zip"])
        self.assertTrue(result["uploaded"])
        mock_update_record.assert_called_once_with("demo-team", "evt-upload-1", source_dir=["demo.zip"])

    @patch("console.services.package_upload_tool_service.package_upload_service.update_upload_record")
    @patch("console.services.package_upload_tool_service.region_api.delete_upload_file_dir")
    # capability_id: console.package-upload.delete-flow
    def test_delete_upload_cleans_remote_dir_and_marks_record(self, mock_delete_dir, mock_update_record):
        from console.services.package_upload_tool_service import package_upload_tool_service

        mock_delete_dir.return_value = (None, {"bean": {"res": "ok"}})

        result = package_upload_tool_service.delete_upload("demo-team", "rainbond", "evt-upload-1")

        self.assertTrue(result["deleted"])
        mock_update_record.assert_called_once_with("demo-team", "evt-upload-1", status="deleted", source_dir=[])

    @patch("console.services.package_upload_tool_service.package_component_service.auto_create_component")
    @patch("console.services.package_upload_tool_service.package_upload_tool_service.get_upload_status")
    @patch("console.services.package_upload_tool_service.package_upload_tool_service.upload_package")
    @patch("console.services.package_upload_tool_service.package_upload_tool_service.init_upload")
    # capability_id: console.package-upload.local-package-flow
    def test_auto_create_component_from_local_path_runs_full_flow(
            self,
            mock_init_upload,
            mock_upload_package,
            mock_get_upload_status,
            mock_create_component):
        from console.services.package_upload_tool_service import package_upload_tool_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_name="demo-team", tenant_id="team-1")
        app = Obj(ID=12, region_name="rainbond")

        mock_init_upload.return_value = {
            "event_id": "evt-upload-1",
            "upload_url": "http://region-ws/package_build/component/events/evt-upload-1"
        }
        mock_upload_package.return_value = {"event_id": "evt-upload-1", "uploaded_packages": ["demo.zip"], "uploaded": True}
        mock_get_upload_status.return_value = {"event_id": "evt-upload-1", "uploaded_packages": ["demo.zip"], "uploaded": True}
        mock_create_component.return_value = {"service_id": "svc-local-pkg-1", "built": True, "upload_event_id": "evt-upload-1"}

        result = package_upload_tool_service.auto_create_component_from_local_path(
            team=team,
            app=app,
            user=user,
            local_path="/tmp/demo-app",
            service_cname="demo-app",
            k8s_component_name="demo-app",
            arch="arm64",
            is_deploy=False,
            archive_name="demo-package",
        )

        self.assertTrue(result["built"])
        mock_init_upload.assert_called_once_with("demo-team", "rainbond", "")
        mock_upload_package.assert_called_once_with("demo-team", "rainbond", "evt-upload-1", "/tmp/demo-app", "demo-package")
        mock_get_upload_status.assert_called_once_with("demo-team", "rainbond", "evt-upload-1")
        mock_create_component.assert_called_once_with(
            team=team,
            app=app,
            user=user,
            event_id="evt-upload-1",
            service_cname="demo-app",
            k8s_component_name="demo-app",
            arch="arm64",
            is_deploy=False,
        )
