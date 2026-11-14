"""Scoped durable snapshot enqueue. Region transport belongs only to the worker."""
import re
from typing import Any, Dict, Tuple

from django.db import DatabaseError

from console.exception.main import ServiceHandleException
from console.services import vm_job_health
from console.services.vm_restore_journal import JournalConflict, TrustedContext
from console.services.vm_snapshot_jobs import snapshot_job_service
from console.services.vm_snapshot_read import snapshot_error, vm_snapshot_read_service


def enqueue_unknown() -> ServiceHandleException:
    return ServiceHandleException('vm_snapshot_enqueue_outcome_unknown',
                                  '快照任务提交结果尚未确认，请保留原请求并读取任务状态，不要重新提交。',
                                  503,
                                  503,
                                  bean={'error': {
                                      'code': 'vm_snapshot_enqueue_outcome_unknown',
                                      'retryable': False
                                  }})


class VMSnapshotCreateService:
    @staticmethod
    def selection(tenant: Any, service: Any, region: str, actor: Any, payload: Any) -> Tuple[Dict[str, Any], str]:
        vm_snapshot_read_service.validate_scope(tenant, service, region)
        allowed = {'name', 'description', 'request_id', 'power_after', 'team_name', 'region_name'}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise snapshot_error('vm_snapshot_invalid_request')
        if payload.get('team_name', tenant.tenant_name) != tenant.tenant_name or payload.get('region_name', region) != region:
            raise snapshot_error('vm_snapshot_invalid_request')
        name, request_id = payload.get('name'), payload.get('request_id')
        name_pattern = r'[a-z0-9](?:[-a-z0-9]*[a-z0-9])?(?:\.[a-z0-9](?:[-a-z0-9]*[a-z0-9])?)*'
        if (not isinstance(name, str) or len(name) > 253 or re.fullmatch(name_pattern, name) is None
                or not isinstance(request_id, str) or re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', request_id) is None):
            raise snapshot_error('vm_snapshot_invalid_request')
        description, power = payload.get('description', ''), payload.get('power_after')
        try:
            valid_description = isinstance(description, str) and len(description.encode('utf-8')) <= 2048
        except UnicodeError:
            valid_description = False
        if not valid_description or power not in {'previous', 'stopped'}:
            raise snapshot_error('vm_snapshot_invalid_request')
        actor_id = getattr(actor, 'user_id', None)
        if type(actor_id) is not int or actor_id <= 0 or len(str(actor_id).encode('utf-8')) > 40:
            raise snapshot_error('vm_snapshot_forbidden')
        return dict(name=name, description=description, request_id=request_id, power_after=power), str(actor_id)

    def enqueue(self, tenant: Any, service: Any, region: str, actor: Any, payload: Any) -> Dict[str, Any]:
        selection, operator = self.selection(tenant, service, region, actor, payload)
        if not vm_job_health.ready():
            raise ServiceHandleException('vm_snapshot_worker_unavailable',
                                         '快照任务处理服务尚未就绪，请稍后再试。',
                                         503,
                                         503,
                                         bean={'error': {
                                             'code': 'vm_snapshot_worker_unavailable',
                                             'retryable': False
                                         }})
        try:
            public = snapshot_job_service.submit(TrustedContext(service), selection, operator=operator)
        except JournalConflict:
            raise ServiceHandleException('vm_snapshot_job_conflict',
                                         '本次请求与已有任务或组件状态冲突，请保留原请求并读取状态。',
                                         409,
                                         409,
                                         bean={'error': {
                                             'code': 'vm_snapshot_job_conflict',
                                             'retryable': False
                                         }}) from None
        except DatabaseError:
            raise enqueue_unknown() from None
        except Exception:
            raise enqueue_unknown() from None
        if (not isinstance(public, dict) or public.get('kind') != 'snapshot'
                or public.get('operation_id') != selection['request_id'] or public.get('request_id') != selection['request_id']
                or public.get('complete') is not False):
            raise enqueue_unknown()
        return public


vm_snapshot_create_service = VMSnapshotCreateService()
