# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.views.base import JWTAuthApiView
from console.services.platform_plugin_service import platform_plugin_service
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class PlatformPluginLView(JWTAuthApiView):
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
        try:
            plugins = platform_plugin_service.list_platform_plugins(enterprise_id, region_name)
            result = general_message(200, "success", "查询成功", list=plugins)
            return Response(result, status=200)
        except Exception as e:
            logger.exception("list platform plugins error")
            result = general_message(500, "error", str(e))
            return Response(result, status=500)
