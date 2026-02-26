# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.exception.main import ServiceHandleException
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


class PlatformPluginInstallView(JWTAuthApiView):
    def post(self, request, enterprise_id, region_name, plugin_id, *args, **kwargs):
        try:
            data = platform_plugin_service.install_platform_plugin(
                enterprise_id, region_name, plugin_id, self.user)
            result = general_message(200, "success", "安装成功", bean=data)
            return Response(result, status=200)
        except ServiceHandleException as e:
            result = general_message(e.status_code, e.msg, e.msg_show)
            return Response(result, status=e.status_code)
        except Exception as e:
            logger.exception("install platform plugin error")
            result = general_message(500, "error", str(e))
            return Response(result, status=500)
