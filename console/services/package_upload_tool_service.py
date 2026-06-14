# -*- coding: utf-8 -*-
import logging
import os
import tempfile
import zipfile
from typing import Any, Dict, Optional, Tuple

import requests

from console.exception.main import ServiceHandleException
from console.services.app import package_upload_service
from console.services.app_import_and_export_service import import_service
from console.services.package_component_service import package_component_service
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class PackageUploadToolService(object):
    SUPPORTED_FILE_SUFFIXES = (".zip", ".jar", ".war", ".tar", ".tar.gz")

    @staticmethod
    def _build_local_path_error_details(local_path: Any, normalized_path: Optional[str] = None) -> Dict[str, Any]:
        return {
            "field": "local_path",
            "provided_value": local_path,
            "normalized_path": normalized_path,
            "path_scope": "server_side",
            "suggestion": "请确认该路径位于 rainbond-console 进程所在机器或容器可见的挂载目录中，而不是 MCP 客户端本机路径。",
        }

    def init_upload(self, team_name: str, region_name: str, component_id: str = "") -> Dict[str, Any]:
        event_id = make_uuid()
        try:
            region_api.create_upload_file_dir(region_name, team_name, event_id)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="create upload dir failed",
                msg_show="初始化软件包上传目录失败",
                status_code=getattr(e, "status", 500) or 500,
            )

        upload_record = package_upload_service.create_upload_record(
            event_id=event_id,
            status="unfinished",
            source_dir="",
            team_name=team_name,
            region=region_name,
            component_id=component_id or "",
        )
        upload_url = import_service.get_upload_package_url(region_name, event_id)
        return {
            "event_id": upload_record.event_id,
            "status": upload_record.status,
            "team_name": upload_record.team_name,
            "region_name": upload_record.region,
            "component_id": component_id or "",
            "upload_url": upload_url,
        }

    def upload_package(self, team_name: str, region_name: str, event_id: str, local_path: str, archive_name: str = "") -> Dict[str, Any]:
        upload_record = package_upload_service.get_upload_record(team_name, region_name, event_id)
        if not upload_record:
            raise ServiceHandleException(
                msg="upload record not found",
                msg_show="未找到软件包上传记录，请先初始化上传",
                status_code=404,
            )

        archive_path, should_cleanup = self._prepare_upload_archive(local_path, archive_name)
        upload_url = import_service.get_upload_package_url(region_name, event_id)

        try:
            with open(archive_path, "rb") as archive_file:
                response = requests.post(
                    upload_url,
                    files={"packageTarFile": (os.path.basename(archive_path), archive_file)},
                    timeout=300,
                )
            if response.status_code < 200 or response.status_code >= 300:
                raise ServiceHandleException(
                    msg="package upload failed",
                    msg_show="上传软件包失败: {0}".format(getattr(response, "text", "")),
                    status_code=response.status_code,
                )
            return self.get_upload_status(team_name, region_name, event_id)
        except requests.RequestException as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="package upload failed",
                msg_show="上传软件包失败: {0}".format(e),
                status_code=500,
            )
        finally:
            if should_cleanup and archive_path and os.path.exists(archive_path):
                os.remove(archive_path)

    def get_upload_status(self, team_name: str, region_name: str, event_id: str) -> Dict[str, Any]:
        try:
            _, body = region_api.get_upload_file_dir(region_name, team_name, event_id)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="query upload status failed",
                msg_show="查询软件包上传状态失败",
                status_code=getattr(e, "status", 500) or 500,
            )
        packages = body.get("bean", {}).get("packages", []) or []  # type: ignore[union-attr]  # NOTE: body may be None if region_api returns (status, None); caller guards via CallApiError
        package_upload_service.update_upload_record(team_name, event_id, source_dir=packages)
        return {
            "event_id": event_id,
            "uploaded_packages": packages,
            "uploaded": bool(packages),
        }

    def delete_upload(self, team_name: str, region_name: str, event_id: str) -> Dict[str, Any]:
        try:
            region_api.delete_upload_file_dir(region_name, team_name, event_id)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="delete upload failed",
                msg_show="删除软件包上传内容失败",
                status_code=getattr(e, "status", 500) or 500,
            )
        package_upload_service.update_upload_record(team_name, event_id, status="deleted", source_dir=[])
        return {
            "event_id": event_id,
            "deleted": True,
        }

    def auto_create_component_from_local_path(
            self,
            team: Any,
            app: Any,
            user: Any,
            local_path: str,
            service_cname: str,
            k8s_component_name: str = "",
            arch: str = "amd64",
            is_deploy: bool = True,
            archive_name: str = "") -> Dict[str, Any]:
        upload_info = self.init_upload(team.tenant_name, app.region_name, "")
        event_id = upload_info["event_id"]
        self.upload_package(team.tenant_name, app.region_name, event_id, local_path, archive_name)
        upload_status = self.get_upload_status(team.tenant_name, app.region_name, event_id)
        if not upload_status.get("uploaded_packages"):
            raise ServiceHandleException(
                msg="package not uploaded",
                msg_show="软件包未上传完成",
                status_code=400,
            )
        result = package_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            event_id=event_id,
            service_cname=service_cname,
            k8s_component_name=k8s_component_name,
            arch=arch,
            is_deploy=is_deploy,
        )
        result["upload_event_id"] = event_id
        result["uploaded_packages"] = upload_status["uploaded_packages"]
        result["local_path"] = os.path.abspath(local_path)
        return result

    def _prepare_upload_archive(self, local_path: str, archive_name: str = "") -> Tuple[str, bool]:
        normalized_path = self._normalize_local_path(local_path)
        if os.path.isfile(normalized_path):
            if not self._is_supported_package_file(normalized_path):
                raise ServiceHandleException(
                    msg="unsupported package file",
                    msg_show="仅支持上传 .zip、.jar、.war、.tar、.tar.gz 文件",
                    status_code=400,
                )
            return normalized_path, False
        return self._zip_directory(normalized_path, archive_name)

    @staticmethod
    def _normalize_local_path(local_path: Any) -> str:
        if not local_path or not isinstance(local_path, str):
            raise ServiceHandleException(
                msg="local path required",
                msg_show="本地路径不能为空",
                status_code=400,
                details=PackageUploadToolService._build_local_path_error_details(local_path, None),
            )
        normalized_path = os.path.abspath(local_path)
        if not os.path.exists(normalized_path):
            raise ServiceHandleException(
                msg="local path not found",
                msg_show="本地路径不存在",
                status_code=404,
                details=PackageUploadToolService._build_local_path_error_details(local_path, normalized_path),
            )
        if not os.path.isfile(normalized_path) and not os.path.isdir(normalized_path):
            raise ServiceHandleException(
                msg="invalid local path",
                msg_show="本地路径必须是文件或目录",
                status_code=400,
                details=PackageUploadToolService._build_local_path_error_details(local_path, normalized_path),
            )
        return normalized_path

    def _zip_directory(self, directory_path: str, archive_name: str = "") -> Tuple[str, bool]:
        archive_basename = os.path.basename(archive_name.strip()) if archive_name else os.path.basename(
            os.path.normpath(directory_path)
        )
        archive_basename = archive_basename or "package"
        if not archive_basename.endswith(".zip"):
            archive_basename = "{0}.zip".format(archive_basename)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_path = temp_file.name
        temp_file.close()

        archive_path = os.path.join(os.path.dirname(temp_path), archive_basename)
        file_count = 0
        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for root, _, files in os.walk(directory_path):
                    for file_name in sorted(files):
                        absolute_file = os.path.join(root, file_name)
                        relative_file = os.path.relpath(absolute_file, directory_path)
                        archive.write(absolute_file, relative_file)
                        file_count += 1
            if file_count == 0:
                raise ServiceHandleException(msg="empty local directory", msg_show="待上传目录为空，无法创建软件包", status_code=400)
            os.replace(temp_path, archive_path)
            return archive_path, True
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(archive_path):
                os.remove(archive_path)
            raise

    def _is_supported_package_file(self, file_path: str) -> bool:
        lower_path = file_path.lower()
        return lower_path.endswith(self.SUPPORTED_FILE_SUFFIXES)


package_upload_tool_service = PackageUploadToolService()
