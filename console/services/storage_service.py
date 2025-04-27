# -*- coding: utf-8 -*-
import logging
import os
import requests
from console.repositories.app import service_repo
from console.repositories.group import group_service_relation_repo
from console.repositories.region_app import region_app_repo

logger = logging.getLogger("default")


class StorageService(object):
    def __init__(self):
        """
        初始化存储服务，使用 Prometheus API
        """
        self.prometheus_url = os.environ.get("PROMETHEUS_URL", "http://rbd-monitor:9999")

    def get_storage_usage_by_service_id(self, service_id):
        try:
            if not service_id:
                return 0.0
            total_used_bytes = 0
            query = f'rainbond_storage_usage_bytes{{service_id="{service_id}"}}'
            response = requests.get(f"{self.prometheus_url}/api/v1/query", params={"query": query})
            result = response.json()
            if result['status'] == 'success' and result['data']['result']:
                total_used_bytes += float(result['data']['result'][0]['value'][1])
            return self._format_storage_size(total_used_bytes)  # 转换为字节
        except Exception as e:
            logger.warning(f"获取存储使用量失败: {e}")
            return 0.0

    def get_tenant_storage_usage(self, tenant_id):
        try:
            if not tenant_id:
                return 0.0
            total_used_bytes = 0
            query = f'sum(rainbond_storage_usage_bytes{{tenant_id="{tenant_id}"}}) by (tenant_id)'
            response = requests.get(f"{self.prometheus_url}/api/v1/query", params={"query": query})
            result = response.json()
            if result['status'] == 'success' and result['data']['result']:
                total_used_bytes += float(result['data']['result'][0]['value'][1])
            return self._format_storage_size(total_used_bytes)
        except Exception as e:
            logger.warning(f"获取租户存储使用量失败: {e}")
            return 0.0

    def get_app_storage_usage(self, region_name, app_id):
        try:
            if not app_id:
                return 0.0
            total_used_bytes = 0
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
            query = f'sum(rainbond_storage_usage_bytes{{app_id="{region_app_id}"}}) by (app_id)'
            response = requests.get(f"{self.prometheus_url}/api/v1/query", params={"query": query})
            result = response.json()
            if result['status'] == 'success' and result['data']['result']:
                total_used_bytes += float(result['data']['result'][0]['value'][1])
            return self._format_storage_size(total_used_bytes)
        except Exception as e:
            logger.warning(f"获取应用存储使用量失败: {e}")
            return 0.0

    def _format_storage_size(self, size_in_bytes):
        """
        格式化存储大小，自动选择合适的单位
        :param size_in_bytes: 字节大小
        :return: 包含数值和单位的字典
        """
        units = ['MB', 'GB', 'TB']
        size = float(size_in_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return {
            "value": round(size, 2),
            "unit": units[unit_index]
        }


storage_service = StorageService()
