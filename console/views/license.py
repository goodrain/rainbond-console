# coding:utf-8
import logging

from rest_framework.response import Response

from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message
from console.services.license import license_service

logger = logging.getLogger("default")


class LicenseLView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        authz_code, license = license_service.get_licenses(enterprise_id)
        if not authz_code or not license:
            result = general_message(400, "invalid authz code", "无效授权码", bean={"authz_code": authz_code})
            return Response(result, status=result["code"])
        result = general_message(200, "success", "查询成功", bean=license)
        return Response(result, status=result["code"])

    def post(self, request, enterprise_id, *args, **kwargs):
        authz_code = request.data.get("authz_code")
        config = license_service.update_license(enterprise_id, authz_code)
        result = general_message(200, "success", "更新成功", bean=config)
        return Response(result, status=result["code"])


class LicenseClusterIDView(JWTAuthApiView):
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
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
    def post(self, request, enterprise_id, region_name, *args, **kwargs):
        try:
            license_code = request.data.get("license")
            if not license_code:
                result = general_message(400, "error", "license field is required")
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
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
        try:
            body = license_service.get_license_status(enterprise_id, region_name)
            bean = body.get("bean", {}) if body else {}
            result = general_message(200, "success", "查询成功", bean=bean)
            return Response(result, status=200)
        except Exception as e:
            logger.exception("get license status error")
            result = general_message(500, "error", str(e))
            return Response(result, status=500)
