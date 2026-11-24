"""Non-sensitive, local process-instance heartbeat; never a Region capability."""
import json
import os
from pathlib import Path
import tempfile
import time


def runtime_path():
    return Path(os.environ.get('VM_JOB_RUNTIME_DIR', '/app/data/vm-jobs'))


def publish(state, now=None):
    instance = os.environ.get('VM_JOB_INSTANCE_ID', '')
    if not instance:
        return
    directory = runtime_path()
    if directory.is_symlink():
        raise ValueError('invalid VM worker runtime directory')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {'instance': instance, 'pid': os.getpid(), 'heartbeat': int(time.time() if now is None else now), 'state': state}
    descriptor, path = tempfile.mkstemp(prefix='.heartbeat-', dir=str(directory))
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(path, directory / 'worker.json')
    finally:
        if os.path.exists(path):
            os.unlink(path)


def ready(now=None, ttl=10):
    try:
        instance = os.environ.get('VM_JOB_INSTANCE_ID', '')
        directory = runtime_path()
        path = directory / 'worker.json'
        if not instance or directory.is_symlink() or path.is_symlink() or path.stat().st_size > 1024:
            return False
        value = json.loads(path.read_text())
        current = int(time.time() if now is None else now)
        if value.get('instance') != instance or value.get('state') != 'ready' or type(value.get('pid')) is not int:
            return False
        if type(value.get('heartbeat')) is not int or not 0 <= current - value['heartbeat'] <= ttl:
            return False
        os.kill(value['pid'], 0)
        return True
    except (OSError, ValueError, TypeError):
        return False
