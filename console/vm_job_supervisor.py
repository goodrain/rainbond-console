"""Own and reap the web/VM worker processes; no shell or process-name kills."""
import os
import signal
import subprocess
import sys
import time
import uuid


def supervise(web_command, worker_command, grace=20):
    children = []
    stopping = [None]
    previous = {}

    def requested(signum, _frame):
        if stopping[0] is None:
            stopping[0] = signum

    def send(signum):
        for child in children:
            # start_new_session pins our group ID to this PID. The group can
            # outlive its leader; poll() is not proof that its descendants died.
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass
            except PermissionError:
                # Some hosts report EPERM while a terminating group is being
                # reaped. This never proves absence; the bounded group check
                # below must still observe cleanup before reporting success.
                pass

    def owned_groups_exist():
        for child in children:
            child.poll()
        for child in children:
            try:
                os.killpg(child.pid, 0)
                return True
            except ProcessLookupError:
                pass
            except PermissionError:
                return True
        return False

    def wait_direct_children():
        deadline = time.monotonic() + max(.5, min(grace, 2))
        for child in children:
            try:
                child.wait(timeout=max(.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                print('vm_supervisor_owned_child_cleanup_pending', file=sys.stderr)
                return False
        return True

    def reap_owned_descendants():
        # When this process is PID1 (or a subreaper), orphaned descendants are
        # ours to reap. Negative PGID restricts waitpid to our two owned groups.
        deadline = time.monotonic() + max(.5, min(grace, 2))
        while True:
            for child in children:
                try:
                    while os.waitpid(-child.pid, os.WNOHANG)[0] > 0:
                        pass
                except ChildProcessError:
                    pass
            if not owned_groups_exist():
                return True
            if time.monotonic() >= deadline:
                print('vm_supervisor_owned_group_cleanup_pending', file=sys.stderr)
                return False
            time.sleep(.01)

    try:
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, requested)
        environment = dict(os.environ, VM_JOB_INSTANCE_ID=uuid.uuid4().hex)
        for command in (web_command, worker_command):
            children.append(subprocess.Popen(command, env=environment, start_new_session=True))
        unexpected = False
        while stopping[0] is None:
            if any(child.poll() is not None for child in children):
                unexpected = True
                break
            time.sleep(.05)
        send(stopping[0] or signal.SIGTERM)
        deadline = time.monotonic() + max(0, grace)
        while owned_groups_exist() and time.monotonic() < deadline:
            time.sleep(.02)
        send(signal.SIGKILL)
        if not wait_direct_children() or not reap_owned_descendants():
            return 1
        return 1 if unexpected else 128 + (stopping[0] or signal.SIGTERM)
    except OSError:
        print('vm_supervisor_child_start_failed', file=sys.stderr)
        send(signal.SIGTERM)
        deadline = time.monotonic() + max(0, grace)
        while owned_groups_exist() and time.monotonic() < deadline:
            time.sleep(.02)
        send(signal.SIGKILL)
        if wait_direct_children():
            reap_owned_descendants()
        return 1
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def main():
    web = sys.argv[1:]
    if web[:1] == ['--']:
        web = web[1:]
    if not web:
        return 2
    worker = [sys.executable, 'manage.py', 'run_vm_restore_jobs']
    return supervise(web, worker)


if __name__ == '__main__':
    sys.exit(main())
