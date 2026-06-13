# -*- coding: utf8 -*-
"""
  Created on 18/1/30.
"""

import logging

from console.services.app_config import extend_service
from www.apiclient.regionapi import RegionInvokeApi
from console.views.app_config.base import AppBaseView
from console.utils.cache_decorators import never_cache
from rest_framework.response import Response
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


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
        hot_update_capability = {
            "cpu_hot_update_supported": False,
            "memory_hot_update_supported": False,
            "hot_update_reason": ""
        }
        if self.service.extend_method == "vm" and self.service.create_status == "complete":
            try:
                _, body = region_api.get_vm_live_update_capability(
                    self.service.service_region,
                    self.tenant.tenant_name,
                    self.service.service_alias
                )
                bean = body.get("bean", {}) if isinstance(body, dict) else {}
                if isinstance(bean, dict):
                    hot_update_capability.update(bean)
            except Exception as e:
                logger.exception(e)
                hot_update_capability["hot_update_reason"] = "当前暂时无法判断虚拟机是否支持热更新，请稍后重试。"
        bean = {
            "node_list": node_list,
            "memory_list": memory_list,
            "current_node": self.service.min_node,
            "current_memory": self.service.min_memory,
            "current_gpu": self.service.container_gpu,
            "extend_method": self.service.extend_method,
            "current_cpu": self.service.min_cpu,
            **hot_update_capability
        }
        result = general_message(200, "success", "操作成功", bean=bean)
        return Response(result, status=result["code"])
