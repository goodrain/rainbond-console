# -*- coding: utf-8 -*-
import logging
from rest_framework.response import Response
from console.views.base import AlowAnyApiView
from www.utils.return_message import general_message
from console.services.storage_service import storage_service

logger = logging.getLogger("default")


class StorageStatistics(AlowAnyApiView):
    def get(self, request):
        """
        获取存储使用统计
        ---
        parameters:
            - name: tenant_id
              description: 团队ID
              required: false
              type: string
              paramType: query
            - name: app_id
              description: 应用ID
              required: false
              type: string
              paramType: query
            - name: service_id
              description: 组件ID
              required: false
              type: string
              paramType: query
        """
        try:
            tenant_id = request.GET.get("tenant_id", "")
            app_id = request.GET.get("app_id", "")
            service_id = request.GET.get("service_id", "")
            region_name = request.GET.get("region_name", "")
            
            # 根据不同的查询条件获取存储使用量
            if service_id:
                # 查询单个组件
                storage_stats = {
                    "used_storage": storage_service.get_storage_usage_by_service_id(service_id)
                }
            elif app_id:
                # 查询应用下的所有组件
                storage_stats = {
                    "used_storage": storage_service.get_app_storage_usage(region_name, app_id)
                }
            elif tenant_id:
                # 查询团队下的所有组件
                storage_stats = {
                    "used_storage": storage_service.get_tenant_storage_usage(tenant_id)
                }
            else:
                storage_stats = {
                    "used_storage": {"value": 0, "unit": "B"}
                }

            result = general_message(
                200,
                "success",
                "获取存储统计成功",
                bean=storage_stats
            )
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "获取存储统计失败", "系统异常")
            return Response(result, status=500)
