# -*- coding: utf8 -*-
from addict import Dict
from rest_framework.views import APIView
from www.utils.license import LICENSE
from rest_framework.response import Response
from www.utils.api import APISuccessResponseJson, APIErrResponseJson
import logging

logger = logging.getLogger('default')


class BaseAPIView(APIView):
    def __init__(self, *args, **kwargs):
        APIView.__init__(self, *args, **kwargs)
        self.report = Dict({"ok": True})


class LicenseView(BaseAPIView):

    allowed_methods = ('PUT', 'GET', )

    def put(self, request, format=None):
        try:
            license = request.data.get("license")
            ok = LICENSE.validation(license)
            if ok:
                LICENSE.set_license(license)
                return APISuccessResponseJson()
            return APIErrResponseJson("Illegal license", "非法的LICESE信息", 400)
        except Exception as e:
            logger.exception(e)
            return APIErrResponseJson(e.message, u"系统错误", 500)

    def get(self, request, format=None):
        try:
            license_data = LICENSE.get_license()
            return APISuccessResponseJson(bean=license_data)
        except Exception as e:
            logger.exception(e)
            return APIErrResponseJson(e.message, u"系统错误", 500)
