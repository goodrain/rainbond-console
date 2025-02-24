# -*- coding: utf-8 -*-
import logging
import os
from prometheus_api_client import PrometheusConnect
from rest_framework.response import Response
from console.views.base import AlowAnyApiView
from www.utils.return_message import general_message
from console.repositories.app import service_repo

logger = logging.getLogger("default")


class PrometheusClient:
    def __init__(self, prometheus_url):
        self.api = PrometheusConnect(url=prometheus_url, disable_ssl=True)

    def get_storage_usage_by_service_aliases(self, service_aliases: list, duration_minutes: int = 5) -> float:
        """
        根据service_alias列表查询存储使用量
        :param service_aliases: service_alias列表
        :param duration_minutes: 时间范围（分钟）
        :return: 存储使用量（字节）
        """
        try:
            if not service_aliases:
                return 0.0
                
            # 构造查询语句，使用正则表达式匹配多个service_alias
            service_aliases_str = "|".join(service_aliases)
            query = f'sum(avg_over_time(kubelet_volume_stats_used_bytes{{persistentvolumeclaim=~"({service_aliases_str})"}}[{duration_minutes}m]))'
            
            # 执行查询
            result = self.api.custom_query(query)
            
            # 解析结果
            if result and isinstance(result, list) and len(result) > 0:
                return float(result[0]['value'][1])
            
            return 0.0
        except Exception as e:
            logger.warning(f"获取存储使用量失败: {e}")
            return 0.0


class StorageStatistics(AlowAnyApiView):
    def __init__(self):
        super().__init__()
        # 从环境变量获取Prometheus URL，默认为 http://rbd-monitor:9999
        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://rbd-monitor:9999")
        self.prom_client = PrometheusClient(prometheus_url)

    def _format_storage_size(self, size_in_bytes):
        """
        格式化存储大小，自动选择合适的单位
        :param size_in_bytes: 字节大小
        :return: 包含数值和单位的字典
        """
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_in_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return {
            "value": round(size, 2),
            "unit": units[unit_index]
        }

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
            
            # 根据不同的查询条件获取service_aliases
            service_aliases = []
            if service_id:
                # 查询单个组件
                service = service_repo.get_service_by_service_id(service_id)
                if service:
                    service_aliases.append(service.service_alias)
            elif app_id:
                # 查询应用下的所有组件
                services = service_repo.get_services_by_group_id(app_id)
                service_aliases = [s.service_alias for s in services]
            elif tenant_id:
                # 查询团队下的所有组件
                services = service_repo.get_service_by_tenant(tenant_id)
                service_aliases = [s.service_alias for s in services]
            
            # 获取5分钟内的平均使用量
            used_bytes = self.prom_client.get_storage_usage_by_service_aliases(
                service_aliases=service_aliases,
                duration_minutes=5
            )
            
            storage_stats = {
                "used_storage": self._format_storage_size(used_bytes)
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
