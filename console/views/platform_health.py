# -*- coding: utf-8 -*-
"""
平台健康检测视图
提供平台基础设施和关键资源的健康状态查询接口
"""
import logging

from console.services.platform_health_service import platform_health_service
from console.views.base import AlowAnyApiView
from rest_framework.response import Response
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class PlatformHealthCheckView(AlowAnyApiView):
    """
    平台健康检测接口
    GET /console/api/v1/platform/health
    """

    def get(self, request, *args, **kwargs):
        """
        获取平台健康状态
        ---
        获取所有集群的平台基础设施和关键资源的健康状态，包括：
        - 数据库、Kubernetes集群、镜像仓库、对象存储
        - 磁盘空间、计算资源、节点状态

        返回格式：
        {
            "regions": {
                "region_name_1": {
                    "status": "healthy|warning|unhealthy",
                    "total_issues": 0,
                    "issues": [
                        {
                            "priority": "P0",
                            "category": "database",
                            "name": "MySQL数据库",
                            "instance": "rbd-db-region",
                            "status": "down",
                            "message": "数据库不可达",
                            "metric": "mysql_up",
                            "value": 0
                        }
                    ]
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
            health_data = platform_health_service.get_platform_health()
            result = general_message(200, "success", "查询成功", bean=health_data)
        except Exception as e:
            logger.error(f"获取平台健康状态失败: {e}")
            result = general_message(500, "failed", f"查询失败: {str(e)}")

        return Response(result, status=result["code"])
