# -*- coding: utf8 -*-

from rest_framework.response import Response

from console.views.base import EnterpriseAdminView
from console.services.plugin_service import rbd_plugin_service
from www.utils.return_message import general_message


class RainbondPluginLView(EnterpriseAdminView):
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
        plugins = rbd_plugin_service.list_plugins(enterprise_id, region_name)
        return Response(general_message(200, "success", "查询成功", list=plugins))
