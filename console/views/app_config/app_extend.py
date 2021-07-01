# -*- coding: utf8 -*-
"""
  Created on 18/1/30.
"""

import logging

from console.services.app_config import extend_service
from console.views.app_config.base import AppBaseView
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class AppExtendView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件扩展方式
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
        """
        node_list, memory_list = extend_service.get_app_extend_method(self.service)
        bean = {
            "node_list": node_list,
            "memory_list": memory_list,
            "current_node": self.service.min_node,
            "current_memory": self.service.min_memory,
            "current_gpu": self.service.container_gpu,
            "extend_method": self.service.extend_method
        }
        result = general_message(200, "success", "操作成功", bean=bean)
        return Response(result, status=result["code"])
