# -*- coding: utf-8 -*-
"""
Platform cluster resource views (Nodes).
"""
import logging
from rest_framework.response import Response
from rest_framework import status

from console.views.base import JWTAuthApiView
from console.views.platform_resources.base import PlatformAdminRequiredMixin
from console.services.k8s_resource_service import k8s_resource_service

logger = logging.getLogger("default")


class NodeListView(PlatformAdminRequiredMixin, JWTAuthApiView):
    """
    List Nodes in the cluster.
    """
    def get(self, request, region_name):
        """
        GET /console/platform/regions/{region_name}/nodes
        """
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))

            data = k8s_resource_service.list_nodes(
                region_name=region_name,
                page=page,
                page_size=page_size
            )

            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"msg": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error listing nodes")
            return Response(
                {"msg": "获取节点列表失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NodeDetailView(PlatformAdminRequiredMixin, JWTAuthApiView):
    """
    Get Node details.
    """
    def get(self, request, region_name, name):
        """
        GET /console/platform/regions/{region_name}/nodes/{name}
        """
        try:
            data = k8s_resource_service.get_node(
                region_name=region_name,
                name=name
            )

            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"msg": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error getting node")
            return Response(
                {"msg": "获取节点详情失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
