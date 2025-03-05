# -*- coding: utf-8 -*-
import logging
import os
import volcenginesdkcore
import volcenginesdkfilenas
from volcenginesdkcore.rest import ApiException
from console.repositories.app import service_repo
from console.repositories.group import group_service_relation_repo

logger = logging.getLogger("default")


class StorageService(object):
    def __init__(self):
        """
        初始化存储服务，使用火山云 SDK 配置
        """
        # 从环境变量获取 AK、SK 和区域信息
        self.ak = os.environ.get("VOLCENGINES_AK", "")
        self.sk = os.environ.get("VOLCENGINES_SK", "")
        self.region = os.environ.get("VOLCENGINES_REGION", "cn-beijing")

        # 配置火山云 SDK
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = self.ak
        configuration.sk = self.sk
        configuration.region = self.region
        volcenginesdkcore.Configuration.set_default(configuration)

        self.api_instance = volcenginesdkfilenas.FILENASApi()

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

            tag_filters_list = []
            for service_alias in service_aliases:
                tag_filters_list.append(
                    volcenginesdkfilenas.TagFilterForDescribeFileSystemsInput(
                        key="service_alias",
                        value=service_alias,
                    )
                )

            describe_file_systems_request = volcenginesdkfilenas.DescribeFileSystemsRequest(
                tag_filters=tag_filters_list,
                page_size=100,
                page_number=1,
            )
            # 获取火山云文件系统使用情况
            file_systems = self.api_instance.describe_file_systems(describe_file_systems_request)
            # 解析返回结果中的存储使用量
            total_used_bytes = 0
            for fs in file_systems.file_systems:
                if fs.file_system_name in service_aliases:
                    total_used_bytes += fs.capacity.used  # 假设返回的结果包含 'used_size' 字段，单位为字节
            return total_used_bytes

        except ApiException as e:
            logger.warning(f"获取存储使用量失败: {e}")
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

    def get_app_storage_usage(self, app_id: int) -> dict:
        """
        获取应用的存储使用量
        :param app_id: 应用ID
        :return: 格式化后的存储使用量
        """
        group_services = group_service_relation_repo.get_services_by_group(int(app_id))
        services = service_repo.get_services_by_service_ids(group_services.values_list("service_id", flat=True))
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
