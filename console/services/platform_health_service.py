# -*- coding: utf-8 -*-
import logging

from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.region_repo import region_repo

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class PlatformHealthService(object):
    """
    平台健康检测服务
    通过调用 Rainbond API 获取平台基础设施和关键资源的健康状态
    支持多集群健康检查
    """

    def __init__(self):
        pass

    def get_platform_health(self):
        """
        获取平台整体健康状态
        通过调用 Rainbond API 获取所有集群的健康状态

        返回格式：
        {
            "regions": {
                "region_name_1": {
                    "status": "healthy|warning|unhealthy",
                    "total_issues": 0,
                    "issues": []
                },
                "region_name_2": {
                    "status": "healthy|warning|unhealthy",
                    "total_issues": 0,
                    "issues": []
                }
            }
        }
        """
        try:
            # 获取企业信息
            enterprises = enterprise_repo.list_all(None)
            if not enterprises or len(enterprises) == 0:
                logger.error("No enterprise found")
                return {"regions": {}}

            enterprise_id = enterprises[0].enterprise_id

            # 获取所有集群
            regions = region_repo.get_all_regions()
            if not regions or len(regions) == 0:
                logger.error("No region found")
                return {"regions": {}}

            # 遍历所有集群，获取每个集群的健康状态
            result = {"regions": {}}
            for region in regions:
                region_name = region.region_name
                try:
                    # 调用 Rainbond API 获取平台健康状态
                    res, body = region_api.get_platform_health(enterprise_id, region_name)

                    if res.get("status") == 200:
                        # API 返回成功，存储该集群的健康状态数据
                        result["regions"][region_name] = body.get("bean", {})
                    else:
                        # API 返回错误，记录错误信息
                        error_msg = body.get("msg_show", body.get("msg", "获取平台健康状态失败"))
                        logger.error(f"Failed to get platform health for region {region_name}: {error_msg}")
                        result["regions"][region_name] = self._error_response(f"API 调用失败: {error_msg}")
                except Exception as e:
                    # 单个集群查询失败，记录日志但继续查询其他集群
                    logger.exception(f"Failed to get platform health for region {region_name}: {e}")
                    result["regions"][region_name] = self._error_response(f"获取集群健康状态异常: {str(e)}")

            return result

        except Exception as e:
            logger.exception(f"Failed to get platform health: {e}")
            return {"regions": {}}

    def _error_response(self, message):
        """返回错误响应"""
        return {
            "status": "unhealthy",
            "total_issues": 1,
            "issues": [{
                "priority": "P0",
                "category": "api",
                "name": "API调用",
                "instance": "console",
                "status": "down",
                "message": message,
                "solution": "1. 检查 Rainbond API 服务是否正常运行\n2. 检查网络连接是否正常\n3. 查看 API 服务日志排查问题\n4. 确认集群配置正确",
                "metric": "api_call",
                "value": 0
            }]
        }


platform_health_service = PlatformHealthService()
