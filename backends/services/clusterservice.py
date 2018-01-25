# -*- coding: utf8 -*-

from backends.models.main import RegionClusterInfo, RegionConfig
from backends.services.regionservice import region_service
import logging

logger = logging.getLogger("default")


class ClusterService(object):
    def get_all_clusters(self):
        cluster_list = RegionClusterInfo.objects.all()
        clusters = []
        for cluster in cluster_list:

            region = RegionConfig.objects.get(region_id=cluster.region_id)
            cluster_info = {}
            try:
                cluster_info["node_num"] = 0
                result = region_service.get_region_resource(region)
                cluster_info.update(result)
                cluster_info["status"] = "success"
            except Exception as e:
                cluster_info["status"] = "failure"
                logger.exception(e)

            cluster_info["cluster_name"] = cluster.cluster_name
            cluster_info["cluster_alias"] = cluster.cluster_alias
            cluster_info["region_id"] = cluster.region_id
            cluster_info["region_alias"] = region.region_alias
            cluster_info["cluster_id"] = cluster.ID

            clusters.append(cluster_info)
        return clusters

    def get_cluster_by_region(self, region_id):
        cluster_list = RegionClusterInfo.objects.filter(region_id=region_id)
        return cluster_list

    def add_cluster(self, region_id, cluster_id, cluster_name, cluster_alias, enable):
        cluster_info = RegionClusterInfo.objects.create(region_id=region_id,
                                                        cluster_id=cluster_id,
                                                        cluster_name=cluster_name,
                                                        cluster_alias=cluster_alias,
                                                        enable=enable)
        return cluster_info


cluster_service = ClusterService()
