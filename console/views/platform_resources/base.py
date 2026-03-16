# -*- coding: utf-8 -*-
"""
Platform resources base views and mixins.
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from console.views.base import JWTAuthApiView


class PlatformAdminRequiredMixin(object):
    """
    Mixin to ensure user has platform admin privileges.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"msg": "用户未认证"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not request.user.is_sys_admin:
            return Response(
                {"msg": "需要平台管理员权限"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super(PlatformAdminRequiredMixin, self).dispatch(request, *args, **kwargs)


class TeamResourceViewMixin(object):
    """
    Mixin for team-scoped resource views with permission and feature flag checks.
    """
    def get_team_and_region(self, request, team_name, region_name):
        """
        Get team and region objects, validate access.

        Args:
            request: HTTP request object
            team_name: Team name to retrieve
            region_name: Region name to retrieve

        Returns:
            tuple: (team, region) objects

        Raises:
            NotFound: If team or region not found
            PermissionDenied: If user lacks access to team
        """
        from console.repositories.team_repo import team_repo
        from console.repositories.region_repo import region_repo
        from console.services.team_services import team_services

        team = team_repo.get_team_by_team_name(team_name)
        if not team:
            raise NotFound("团队不存在")

        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise NotFound("集群不存在")

        # Check user has access to team
        if not team_services.user_is_exist_in_team(user=request.user, tenant_name=team_name):
            raise PermissionDenied("无权限访问该团队")

        return team, region

    def check_feature_flag(self, feature_name, team_id=None):
        """
        Check if a feature flag is enabled.

        Args:
            feature_name: Name of the feature to check
            team_id: Optional team ID for team-scoped features

        Returns:
            bool: True if feature is enabled, False otherwise
        """
        from console.repositories.platform_resources_repo import platform_resources_repo

        try:
            flag = platform_resources_repo.get_feature_flag(feature_name, team_id)
            return flag.enabled if flag else False
        except Exception:
            return False
