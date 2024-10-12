# coding:utf-8
import logging
import os

from rest_framework.response import Response

from console.views.base import AlowAnyApiView
from www.utils.return_message import general_message
from console.services.license import license_service

logger = logging.getLogger("default")


class LicenseLView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        resp = license_service.get_licenses()
        invalid_code = os.getenv("INVALID_AUTHZ_CODE", "123456789")
        if resp["authz_code"] == invalid_code:
            result = general_message(400, "invalid authz code", "无效授权码", bean={"authz_code": resp["authz_code"]})
            return Response(result, status=result["code"])
        result = general_message(200, "success", "查询成功", bean=resp)
        return Response(result, status=result["code"])

    def post(self, request, enterprise_id, *args, **kwargs):
        authz_code = request.data.get("authz_code")
        config = license_service.update_license(enterprise_id, authz_code)
        result = general_message(200, "success", "更新成功", bean=config)
        return Response(result, status=result["code"])

