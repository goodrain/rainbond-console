# coding:utf-8
import logging
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.views.base import JWTAuthApiView
from console.exception.main import ServiceHandleException
from www.utils.return_message import general_message
from console.services.license import license_service

logger = logging.getLogger("default")


class LicenseLView(JWTAuthApiView):
    def get(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        authz_code, license = license_service.get_licenses(enterprise_id)
        if not authz_code or not license:
            result = general_message(400, "invalid authz code", "无效授权码", bean={"authz_code": authz_code})
            return Response(result, status=result["code"])
        result = general_message(200, "success", "查询成功", bean=license)
        return Response(result, status=result["code"])

    def post(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        authz_code = request.data.get("authz_code")
        try:
            # NOTE: authz_code is Optional; service expects str (legacy mismatch, backlog).
            config = license_service.update_license(enterprise_id, authz_code)  # type: ignore[arg-type]
        except ServiceHandleException as e:
            result = general_message(e.status_code, "error", e.msg_show)
            return Response(result, status=e.status_code)
        result = general_message(200, "success", "更新成功", bean=config)
        return Response(result, status=result["code"])


class LicenseClusterIDView(JWTAuthApiView):
    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        try:
            body = license_service.get_cluster_id(enterprise_id, region_name)
            bean = body.get("bean", {}) if body else {}
            result = general_message(200, "success", "查询成功", bean=bean)
            return Response(result, status=200)
        except Exception as e:
            logger.exception("get cluster id error")
            result = general_message(500, "error", str(e))
            return Response(result, status=500)


class LicenseActivateView(JWTAuthApiView):
    def post(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        try:
            license_code = request.data.get("license_code")
            if not license_code:
                result = general_message(400, "error", "license_code field is required")
                return Response(result, status=400)
            body = license_service.activate_license(enterprise_id, region_name, license_code)
            bean = body.get("bean", {}) if body else {}
            result = general_message(200, "success", "激活成功", bean=bean)
            return Response(result, status=200)
        except Exception as e:
            logger.exception("activate license error")
            result = general_message(500, "error", str(e))
            return Response(result, status=500)


class LicenseStatusView(JWTAuthApiView):
    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        try:
            body = license_service.get_license_status(enterprise_id, region_name)
            bean = body.get("bean", {}) if body else {}
            result = general_message(200, "success", "查询成功", bean=bean)
            return Response(result, status=200)
        except Exception as e:
            logger.exception("get license status error")
            result = general_message(500, "error", str(e))
            return Response(result, status=500)
