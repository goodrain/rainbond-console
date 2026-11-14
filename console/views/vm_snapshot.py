# -*- coding: utf-8 -*-
"""Scoped snapshot reads and durable enqueue; only the worker submits Region commands."""
from typing import Any

from rest_framework.request import Request
from console.services.vm_snapshot_create import vm_snapshot_create_service
from console.services.vm_snapshot_read import vm_snapshot_read_service
from console.services.operation_log import OperationType, operation_log_service
from console.utils.cache_decorators import never_cache
from console.views.app_config.base import AppBaseView
from rest_framework.response import Response
from www.utils.return_message import general_message


class VMSnapshotReadView(AppBaseView):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        # AppBaseView's legacy initial chain does not invoke APIView.initial.
        self.perform_authentication(request)
        self.check_permissions(request)
        super().initial(request, *args, **kwargs)
        vm_snapshot_read_service.validate_scope(self.tenant, self.service, self.region_name)


class VMSnapshotListView(VMSnapshotReadView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        bean = vm_snapshot_read_service.list(self.tenant,
                                             self.service,
                                             self.region_name,
                                             page=request.query_params.get("page", 1),
                                             page_size=request.query_params.get("page_size", 20))
        return Response(general_message(200, "success", "查询成功", bean=bean))

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        bean = vm_snapshot_create_service.enqueue(self.tenant, self.service, self.region_name, self.user, request.data)
        operation_log_service.create_log(self.user,
                                         OperationType.COMPONENT_MANAGE,
                                         "提交了虚拟机快照任务",
                                         enterprise_id=self.tenant.enterprise_id or "",
                                         team_name=self.tenant.tenant_name,
                                         app_id=self.app.ID,
                                         service_alias=self.service.service_alias)
        return Response(general_message(202, "accepted", "快照任务已登记，等待处理", bean=bean), status=202)


class VMSnapshotCapabilityView(VMSnapshotReadView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # The Region scope comes only from the authenticated live component.
        bean = vm_snapshot_read_service.capability(self.tenant, self.service, self.region_name)
        return Response(general_message(200, "success", "查询成功", bean=bean))


class VMSnapshotDetailView(VMSnapshotReadView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        bean = vm_snapshot_read_service.detail(self.tenant, self.service, self.region_name, kwargs.get("snapshot_name"))
        return Response(general_message(200, "success", "查询成功", bean=bean))
