from console.repositories.group import group_service_relation_repo
from console.repositories.region_repo import region_repo
from console.services.region_services import region_services

import logging

logger = logging.getLogger("default")

class Performance_overview(object):
    def get_performance_overview(self, enterprise_id):
        regions = region_repo.get_usable_regions(enterprise_id)

        performance_dict = {"cpu_use_sum": 0, "memory_use_sum": 0, "disk_use_sum": 0, "node_number": 0,
                            "service_number": 0}
        for region in regions:
            try:
                data = region_services.get_enterprise_region(enterprise_id, region.region_id, check_status="yes")
                # 确保data不为None
                if not data:
                    continue
                
                # 修复KeyError：使用实际可用的节点字段
                # 使用node_ready（就绪节点数）作为可用节点数量，如果没有则使用all_nodes（总节点数）
                region_node_number = data.get("node_ready", data.get("all_nodes", 0))
                
                # 安全地获取资源使用数据，确保都是数字类型
                cpu_used = data.get("used_cpu", 0)
                memory_used = data.get("used_memory", 0) 
                disk_used = data.get("used_disk", 0)
                
                # 确保所有值都是数字类型
                if isinstance(cpu_used, (int, float)):
                    performance_dict["cpu_use_sum"] += cpu_used
                if isinstance(memory_used, (int, float)):
                    performance_dict["memory_use_sum"] += memory_used
                if isinstance(disk_used, (int, float)):
                    performance_dict["disk_use_sum"] += disk_used
                if isinstance(region_node_number, (int, float)):
                    performance_dict["node_number"] += region_node_number
                
                service_count = group_service_relation_repo.get_service_number(region.region_name)
                if isinstance(service_count, (int, float)):
                    performance_dict["service_number"] += service_count
                    
            except Exception as e:
                # 记录错误但不中断整个流程
                logger.warning(f"Error getting performance data for region {region.region_id}: {str(e)}")
                continue
                
        return performance_dict


performance_overview = Performance_overview()
