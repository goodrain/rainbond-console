# -*- coding: utf-8 -*-
"""
K8s resource service for platform resource management.
"""
import logging
from console.repositories.region_repo import region_repo

logger = logging.getLogger("default")


class K8sResourceService(object):
    """
    Service for managing Kubernetes resources via region API.
    """

    def list_storage_classes(self, region_name, page=1, page_size=10):
        """
        List StorageClasses in the cluster.

        Args:
            region_name: Region name
            page: Page number
            page_size: Items per page

        Returns:
            dict: {
                "list": [...],
                "total": int,
                "page": int,
                "page_size": int
            }
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/storageclasses"
            params = {"page": page, "page_size": page_size}
            res, body = region.api.get(url, params=params)

            if res.status != 200:
                logger.error("Failed to list storage classes: {}".format(body))
                raise Exception("获取存储类列表失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error listing storage classes")
            raise e

    def get_storage_class(self, region_name, name):
        """
        Get StorageClass details.

        Args:
            region_name: Region name
            name: StorageClass name

        Returns:
            dict: StorageClass details
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/storageclasses/{}".format(name)
            res, body = region.api.get(url)

            if res.status != 200:
                logger.error("Failed to get storage class: {}".format(body))
                raise Exception("获取存储类详情失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error getting storage class")
            raise e

    def list_persistent_volumes(self, region_name, page=1, page_size=10):
        """
        List PersistentVolumes in the cluster.

        Args:
            region_name: Region name
            page: Page number
            page_size: Items per page

        Returns:
            dict: {
                "list": [...],
                "total": int,
                "page": int,
                "page_size": int
            }
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/persistentvolumes"
            params = {"page": page, "page_size": page_size}
            res, body = region.api.get(url, params=params)

            if res.status != 200:
                logger.error("Failed to list persistent volumes: {}".format(body))
                raise Exception("获取持久卷列表失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error listing persistent volumes")
            raise e

    def list_nodes(self, region_name, page=1, page_size=10):
        """
        List Nodes in the cluster.

        Args:
            region_name: Region name
            page: Page number
            page_size: Items per page

        Returns:
            dict: {
                "list": [...],
                "total": int,
                "page": int,
                "page_size": int
            }
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/nodes"
            params = {"page": page, "page_size": page_size}
            res, body = region.api.get(url, params=params)

            if res.status != 200:
                logger.error("Failed to list nodes: {}".format(body))
                raise Exception("获取节点列表失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error listing nodes")
            raise e

    def get_node(self, region_name, name):
        """
        Get Node details.

        Args:
            region_name: Region name
            name: Node name

        Returns:
            dict: Node details
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/nodes/{}".format(name)
            res, body = region.api.get(url)

            if res.status != 200:
                logger.error("Failed to get node: {}".format(body))
                raise Exception("获取节点详情失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error getting node")
            raise e

    def list_services(self, region_name, namespace, page=1, page_size=10):
        """
        List Services in a namespace.

        Args:
            region_name: Region name
            namespace: Namespace name
            page: Page number
            page_size: Items per page

        Returns:
            dict: {
                "list": [...],
                "total": int,
                "page": int,
                "page_size": int
            }
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/namespaces/{}/services".format(namespace)
            params = {"page": page, "page_size": page_size}
            res, body = region.api.get(url, params=params)

            if res.status != 200:
                logger.error("Failed to list services: {}".format(body))
                raise Exception("获取服务列表失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error listing services")
            raise e

    def get_cluster_scoped_resource_types(self, region_name):
        """
        Get cluster-scoped resource types.

        Args:
            region_name: Region name

        Returns:
            dict: Resource types information
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/cluster-scoped-resource-types"
            res, body = region.api.get(url)

            if res.status != 200:
                logger.error("Failed to get cluster scoped resource types: {}".format(body))
                raise Exception("获取集群范围资源类型失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error getting cluster scoped resource types")
            raise e

    def list_cluster_resources(self, region_name, resource_type, page=1, page_size=10):
        """
        List cluster resources by type.

        Args:
            region_name: Region name
            resource_type: Resource type (e.g., 'nodes', 'storageclasses')
            page: Page number
            page_size: Items per page

        Returns:
            dict: {
                "list": [...],
                "total": int,
                "page": int,
                "page_size": int
            }
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/cluster-resources/{}".format(resource_type)
            params = {"page": page, "page_size": page_size}
            res, body = region.api.get(url, params=params)

            if res.status != 200:
                logger.error("Failed to list cluster resources: {}".format(body))
                raise Exception("获取集群资源列表失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error listing cluster resources")
            raise e

    def get_cluster_resource(self, region_name, resource_type, resource_name):
        """
        Get a specific cluster resource.

        Args:
            region_name: Region name
            resource_type: Resource type (e.g., 'nodes', 'storageclasses')
            resource_name: Resource name

        Returns:
            dict: Resource details
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/cluster-resources/{}/{}".format(resource_type, resource_name)
            res, body = region.api.get(url)

            if res.status != 200:
                logger.error("Failed to get cluster resource: {}".format(body))
                raise Exception("获取集群资源详情失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error getting cluster resource")
            raise e

    def get_storage_overview(self, region_name):
        """
        Get storage overview information.

        Args:
            region_name: Region name

        Returns:
            dict: Storage overview data
        """
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ValueError("集群不存在")

        try:
            url = "/v2/platform/storage-overview"
            res, body = region.api.get(url)

            if res.status != 200:
                logger.error("Failed to get storage overview: {}".format(body))
                raise Exception("获取存储概览失败")

            return body.get("data", {})
        except Exception as e:
            logger.exception("Error getting storage overview")
            raise e


k8s_resource_service = K8sResourceService()
