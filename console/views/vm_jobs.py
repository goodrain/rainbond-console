"""Scoped durable status and explicit write readiness; no false acceptance."""
from typing import Any
from rest_framework.request import Request
from rest_framework.response import Response
from console.exception.main import ServiceHandleException
from console.services.vm_snapshot_admission import snapshot_write_capability
from console.services.vm_restore_journal import VMRestoreJournal, TrustedContext, JournalConflict
from console.services.vm_restore_submission import restore_submission_service
from console.services import vm_job_health
from console.views.vm_snapshot import VMSnapshotReadView
from www.utils.return_message import general_message


class VMJobCapabilityView(VMSnapshotReadView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(general_message(200, 'success', '查询成功', bean=snapshot_write_capability()))


class VMJobStatusView(VMSnapshotReadView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            journal = VMRestoreJournal()
            context = TrustedContext(self.service)
            operation = journal.read_operation(context, kwargs['operation_id'])
            if operation['kind'] == 'snapshot' and 'operator' in operation.get('request', {}):
                from console.services.vm_snapshot_jobs import SnapshotJobService
                value = SnapshotJobService(journal).status(context, operation['operation_id'])
            else:
                value = journal.public_operation(context, operation['operation_id'])
        except JournalConflict:
            raise ServiceHandleException('vm_job_conflict', '任务不存在或状态冲突', status_code=409) from None
        return Response(general_message(200, 'success', '查询成功', bean=value))


class VMRestoreSubmitView(VMSnapshotReadView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if not isinstance(request.data, dict) or set(
                request.data) != {'request_id', 'snapshot_uid', 'document_hash', 'power_after'}:
            raise ServiceHandleException('vm_restore_invalid_request', '恢复请求参数无效', status_code=400)
        if not vm_job_health.ready():
            raise ServiceHandleException('vm_restore_worker_unavailable', '恢复任务处理服务尚未就绪', status_code=503)
        try:
            context = TrustedContext(self.service)
            op = restore_submission_service.submit(context, dict(request.data))
            public = restore_submission_service.journal.public_operation(context, op['operation_id'])
        except JournalConflict:
            raise ServiceHandleException('vm_restore_conflict', '恢复来源或任务状态冲突', status_code=409) from None
        # Accepted means the original intent is durable, never restored/ready.
        return Response(general_message(202, 'restore_queued', '恢复请求已登记，等待处理', bean={**public, 'complete': False}), status=202)
