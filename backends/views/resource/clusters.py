# -*- coding: utf8 -*-

import logging

from rest_framework.response import Response

from backends.services.clusterservice import cluster_service
from backends.services.regionservice import region_service
from backends.services.resultservice import *
from backends.views.base import BaseAPIView

logger = logging.getLogger("default")


class ClusterView(BaseAPIView):
    def get(self, request, region_id, *args, **kwargs):
        """
        获取数据中心下的集群信息
        ---

        """
        try:
            cluster_list = region_service.get_region_clusters(region_id)
            list = []
            for cluster in cluster_list:
                cluster_info = {}
                cluster_info['cluster_name'] = cluster.cluster_name
                cluster_info['cluster_alias'] = cluster.cluster_alias
                cluster_info['cluster_id'] = cluster.ID
                list.append(cluster_info)
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, list=list)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class AllClusterView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取所有集群的信息
        ---

        """
        try:
            cluster_list = cluster_service.get_all_clusters()
            result = generate_result("0000", "success", "查询成功", list=cluster_list)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class ClusterResourceView(BaseAPIView):
    def get(self, request, region_id, *args, **kwargs):
        """
        获取数据中心下所有集群的资源信息
        """
        try:
            resource_list = region_service.get_region_clusters_resources(region_id)
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, list=resource_list)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
