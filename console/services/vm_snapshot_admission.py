"""Console enqueue readiness; scoped Region validation still owns snapshot admission."""
from console.exception.main import ServiceHandleException
from console.services import vm_job_health


def snapshot_write_capability():
    if not vm_job_health.ready():
        return {'available': False, 'reason': 'worker_unavailable'}
    # The default worker now implements the managed Prepare/ACK/finalize protocol.
    # This is process readiness, not proof of storage support or task completion.
    return {'available': True, 'reason': 'ready'}


def require_snapshot_writer():
    capability = snapshot_write_capability()
    if not capability['available']:
        raise ServiceHandleException('vm_snapshot_write_unavailable',
                                     '快照写入服务尚未就绪',
                                     status_code=503,
                                     bean={'error': {
                                         'code': capability['reason'],
                                         'retryable': True
                                     }})
