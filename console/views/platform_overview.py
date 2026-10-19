# -*- coding: utf-8 -*-
from typing import Any

from console.services.platform_overview_service import (PlatformOverviewRegionNotFound, platform_overview_service)
from console.views.base import EnterpriseAdminView
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from www.utils.return_message import general_message


class PlatformOverviewBaseView(EnterpriseAdminView):
    def _ensure_enterprise_access(self, enterprise_id: str) -> None:
        if str(getattr(self.user, "enterprise_id", "") or "") != str(enterprise_id):
            raise PermissionDenied("enterprise access denied")
        if not self.is_enterprise_admin:
            raise PermissionDenied("enterprise administrator access required")

    @staticmethod
    def _success(data: dict) -> Response:
        return Response(general_message(200, "success", "查询成功", bean=data), status=200)

    @staticmethod
    def _not_found() -> Response:
        return Response(general_message(404, "region not found", "集群不存在"), status=404)


class PlatformOverviewShellView(PlatformOverviewBaseView):
    def get(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        self._ensure_enterprise_access(enterprise_id)
        return self._success(platform_overview_service.get_shell(enterprise_id))


class PlatformOverviewRuntimeView(PlatformOverviewBaseView):
    def get(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        self._ensure_enterprise_access(enterprise_id)
        return self._success(platform_overview_service.get_runtime(enterprise_id))


class PlatformOverviewSnapshotView(PlatformOverviewBaseView):
    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        self._ensure_enterprise_access(enterprise_id)
        try:
            data = platform_overview_service.get_cluster_overview(enterprise_id, region_name)
        except PlatformOverviewRegionNotFound:
            return self._not_found()
        return self._success(data)


class PlatformOverviewMetricsView(PlatformOverviewBaseView):
    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        self._ensure_enterprise_access(enterprise_id)
        metric = request.GET.get("metric", "cpu")
        time_range = request.GET.get("range", "6h")
        if metric not in platform_overview_service.METRIC_QUERIES or time_range not in platform_overview_service.RANGE_CONFIG:
            return Response(general_message(400, "invalid metric parameters", "不支持的监控指标或时间范围"), status=400)
        try:
            data = platform_overview_service.get_metrics(enterprise_id, region_name, metric, time_range)
        except PlatformOverviewRegionNotFound:
            return self._not_found()
        return self._success(data)
