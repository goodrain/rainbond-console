# -*- coding: utf-8 -*-
import logging
import os
from prometheus_api_client import PrometheusConnect
from console.repositories.app import service_repo

logger = logging.getLogger("default")


class StorageService(object):
    def __init__(self):
        """
        初始化存储服务
        """
        # 从环境变量获取Prometheus URL，默认为 http://rbd-monitor:9999
        self.prometheus_url = os.environ.get("PROMETHEUS_URL", "http://rbd-monitor:9999")
        self.prom_client = PrometheusConnect(url=self.prometheus_url, disable_ssl=True)

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
            result = self.prom_client.custom_query(query)
            
            # 解析结果
            if result and isinstance(result, list) and len(result) > 0:
                return float(result[0]['value'][1])
            
            return 0.0
        except Exception as e:
            logger.warning(f"获取存储使用量失败: {e}")
            return 0.0

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

    def get_tenant_storage_usage(self, tenant_id: str) -> dict:
        """
        获取团队的存储使用量
        :param tenant_id: 团队ID
        :return: 格式化后的存储使用量
        """
        services = service_repo.get_service_by_tenant(tenant_id)
        service_aliases = [s.service_alias for s in services]
        used_bytes = self.get_storage_usage_by_service_aliases(service_aliases)
        return self._format_storage_size(used_bytes)

    def get_app_storage_usage(self, app_id: str) -> dict:
        """
        获取应用的存储使用量
        :param app_id: 应用ID
        :return: 格式化后的存储使用量
        """
        services = service_repo.get_services_by_group_id(app_id)
        service_aliases = [s.service_alias for s in services]
        used_bytes = self.get_storage_usage_by_service_aliases(service_aliases)
        return self._format_storage_size(used_bytes)

    def get_service_storage_usage(self, service_id: str) -> dict:
        """
        获取组件的存储使用量
        :param service_id: 组件ID
        :return: 格式化后的存储使用量
        """
        service = service_repo.get_service_by_service_id(service_id)
        if service:
            used_bytes = self.get_storage_usage_by_service_aliases([service.service_alias])
            return self._format_storage_size(used_bytes)
        return {"value": 0, "unit": "B"}


storage_service = StorageService()
