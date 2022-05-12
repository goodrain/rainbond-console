from console.repositories.group import group_service_relation_repo
from console.repositories.region_repo import region_repo
from console.services.region_services import region_services


class Performance_overview(object):
    def get_performance_overview(self, enterprise_id):
        regions = region_repo.get_usable_regions(enterprise_id)

        performance_dict = {"cpu_use_sum": 0, "memory_use_sum": 0, "disk_use_sum": 0, "node_number": 0,
                            "service_number": 0}
        for region in regions:
            data = region_services.get_enterprise_region(enterprise_id, region.region_id, check_status="yes")
            region_node_number = data["manage_node"] + data["etcd_node"] + data["compute_node"] - data[
                "notready_manage_node"] - data["notready_etcd_node"] - data["notready_etcd_node"]
            performance_dict["cpu_use_sum"] += data["used_cpu"]
            performance_dict["memory_use_sum"] += data["used_memory"]
            performance_dict["disk_use_sum"] += data["used_disk"]
            performance_dict["node_number"] += region_node_number
            service_count = group_service_relation_repo.get_service_number(region.region_name)
            performance_dict["service_number"] += service_count
        return performance_dict


performance_overview = Performance_overview()
