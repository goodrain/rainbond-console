"""Fail-closed write admission until the authoritative Region protocol exists."""
from console.exception.main import ServiceHandleException
from console.services import vm_job_health


def snapshot_write_capability():
    if not vm_job_health.ready():
        return {'available': False, 'reason': 'worker_unavailable'}
    # No current reviewed Go RPC proves source identity, epoch ownership and
    # terminal fence release. Never probe the legacy POST to discover support.
    return {'available': False, 'reason': 'region_authority_contract_unavailable'}


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
