# -*- coding: utf-8 -*-
"""
Platform storage resource views.
"""
import logging
from rest_framework.response import Response
from rest_framework import status

from console.views.base import JWTAuthApiView
from console.views.platform_resources.base import PlatformAdminRequiredMixin
from console.services.k8s_resource_service import k8s_resource_service

logger = logging.getLogger("default")


class StorageClassListView(PlatformAdminRequiredMixin, JWTAuthApiView):
    """
    List StorageClasses in the cluster.
    """
    def get(self, request, region_name):
        """
        GET /console/platform/regions/{region_name}/storageclasses
        """
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))

            data = k8s_resource_service.list_storage_classes(
                region_name=region_name,
                page=page,
                page_size=page_size
            )

            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"msg": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error listing storage classes")
            return Response(
                {"msg": "获取存储类列表失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StorageClassDetailView(PlatformAdminRequiredMixin, JWTAuthApiView):
    """
    Get StorageClass details.
    """
    def get(self, request, region_name, name):
        """
        GET /console/platform/regions/{region_name}/storageclasses/{name}
        """
        try:
            data = k8s_resource_service.get_storage_class(
                region_name=region_name,
                name=name
            )

            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"msg": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error getting storage class")
            return Response(
                {"msg": "获取存储类详情失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PersistentVolumeListView(PlatformAdminRequiredMixin, JWTAuthApiView):
    """
    List PersistentVolumes in the cluster.
    """
    def get(self, request, region_name):
        """
        GET /console/platform/regions/{region_name}/persistentvolumes
        """
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))

            data = k8s_resource_service.list_persistent_volumes(
                region_name=region_name,
                page=page,
                page_size=page_size
            )

            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"msg": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error listing persistent volumes")
            return Response(
                {"msg": "获取持久卷列表失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
