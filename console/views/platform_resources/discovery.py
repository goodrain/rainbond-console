# -*- coding: utf-8 -*-
"""
Platform service discovery views.
"""
import logging
from rest_framework.response import Response
from rest_framework import status

from console.views.base import JWTAuthApiView
from console.views.platform_resources.base import TeamResourceViewMixin
from console.services.k8s_resource_service import k8s_resource_service

logger = logging.getLogger("default")


class ServiceListView(TeamResourceViewMixin, JWTAuthApiView):
    """
    List Services in a team namespace.
    """
    def get(self, request, team_name, region_name):
        """
        GET /console/teams/{team_name}/regions/{region_name}/services
        """
        try:
            # Validate team and region access
            result = self.get_team_and_region(request, team_name, region_name)
            if isinstance(result, Response):
                return result
            team, region = result

            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))

            # Use team UUID as namespace
            namespace = team.tenant_id

            data = k8s_resource_service.list_services(
                region_name=region_name,
                namespace=namespace,
                page=page,
                page_size=page_size
            )

            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"msg": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error listing services")
            return Response(
                {"msg": "获取服务列表失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
