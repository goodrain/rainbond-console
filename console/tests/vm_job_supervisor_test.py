# capability_id: console.vm-jobs.supervised-runtime
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from unittest import TestCase


class VMJobSupervisorTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vm-supervisor-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.child = self.root / 'child.py'
        self.child.write_text('''import os,signal,sys,time
from pathlib import Path
Path(sys.argv[1]).write_text(str(os.getpid()))
if 'exit' in sys.argv: sys.exit(0)
if 'ignore' in sys.argv: signal.signal(signal.SIGTERM,signal.SIG_IGN)
while True: time.sleep(.02)
''')

    def wait_file(self, name, process):
        path = self.root / name
        deadline = time.monotonic() + 4
        while not path.exists() and time.monotonic() < deadline and process.poll() is None:
            time.sleep(.02)
        self.assertTrue(path.exists(), '{} missing, supervisor exit {}'.format(name, process.poll()))
        return int(path.read_text())

    def launch(self, worker_mode='', web_mode=''):
        web = [sys.executable, str(self.child), str(self.root / 'web'), web_mode]
        worker = [sys.executable, str(self.child), str(self.root / 'worker'), worker_mode]
        code = 'import sys;from console.vm_job_supervisor import supervise;sys.exit(supervise({}, {}, grace=.3))'.format(
            repr(web), repr(worker))
        process = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: self.stop(process))
        return process

    @staticmethod
    def stop(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    def absent(self, pid):
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_term_reaps_both_owned_children(self):
        process = self.launch()
        web = self.wait_file('web', process)
        worker = self.wait_file('worker', process)
        process.send_signal(signal.SIGTERM)
        self.assertEqual(process.wait(timeout=4), 128 + signal.SIGTERM)
        self.absent(web)
        self.absent(worker)

    def test_even_successful_unexpected_worker_exit_fails_container_and_stops_web(self):
        process = self.launch(worker_mode='exit')
        web = self.wait_file('web', process)
        self.assertEqual(process.wait(timeout=4), 1)
        self.absent(web)

    def test_unexpected_web_exit_stops_worker(self):
        process = self.launch(web_mode='exit')
        self.wait_file('web', process)
        self.assertEqual(process.wait(timeout=4), 1)
        if (self.root / 'worker').exists():
            self.absent(int((self.root / 'worker').read_text()))

    def test_timeout_kills_only_owned_process_groups(self):
        unrelated = subprocess.Popen([sys.executable, str(self.child), str(self.root / 'unrelated'), 'ignore'])
        self.addCleanup(lambda: self.stop(unrelated))
        process = self.launch(worker_mode='ignore', web_mode='ignore')
        web = self.wait_file('web', process)
        worker = self.wait_file('worker', process)
        process.send_signal(signal.SIGTERM)
        self.assertEqual(process.wait(timeout=4), 128 + signal.SIGTERM)
        self.absent(web)
        self.absent(worker)
        self.assertIsNone(unrelated.poll())

    def launch_family(self, leader_exits=False):
        leader = self.root / 'leader.py'
        grandchild = [sys.executable, str(self.child), str(self.root / 'grandchild'), 'ignore']
        leader.write_text('import os,subprocess,time\nfrom pathlib import Path\n' +
                          'Path({}).write_text(str(os.getpid()))\n'.format(repr(str(self.root / 'leader'))) +
                          'subprocess.Popen({})\n'.format(repr(grandchild)) +
                          'while not Path({}).exists():time.sleep(.01)\n'.format(repr(str(self.root / 'grandchild'))) +
                          ('' if leader_exits else 'while True:time.sleep(.02)\n'))
        worker = [sys.executable, str(self.child), str(self.root / 'worker')]
        code = 'from console.vm_job_supervisor import supervise;raise SystemExit(supervise({}, {}, grace=.2))'.format(
            repr([sys.executable, str(leader)]), repr(worker))
        process = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: self.stop(process))
        grandchild_pid = self.wait_file('grandchild', process)
        group = int((self.root / 'leader').read_text())

        def cleanup():
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass

        self.addCleanup(cleanup)
        return process, grandchild_pid

    def test_exited_leader_still_terminates_its_sigterm_ignoring_grandchild(self):
        unrelated = subprocess.Popen([sys.executable, str(self.child), str(self.root / 'unrelated'), 'ignore'])
        self.addCleanup(lambda: self.stop(unrelated))
        process, grandchild = self.launch_family(leader_exits=True)
        self.assertEqual(process.wait(timeout=4), 1)
        self.absent(grandchild)
        self.assertIsNone(unrelated.poll())
        # A subsequent supervisor starts without the first incarnation's child.
        restarted = self.launch()
        self.wait_file('web', restarted)
        restarted.terminate()
        self.assertEqual(restarted.wait(timeout=4), 143)
        self.absent(grandchild)
        self.assertIsNone(unrelated.poll())

    def test_sigterm_and_sigint_stop_owned_descendants_as_well_as_leaders(self):
        for signum in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=signum):
                for name in ('leader', 'grandchild', 'worker'):
                    (self.root / name).unlink(missing_ok=True)
                process, grandchild = self.launch_family()
                worker = self.wait_file('worker', process)
                process.send_signal(signum)
                self.assertEqual(process.wait(timeout=4), 128 + signum)
                self.absent(grandchild)
                self.absent(worker)

    def test_entrypoint_keeps_schema_order_and_original_web_arguments(self):
        source = Path('entrypoint.sh').read_text()
        self.assertLess(source.index('init_database\n  fi'), source.index('console.vm_job_supervisor'))
        self.assertIn('--timeout=${GUNICORN_TIMEOUT:-3700}', source)
        self.assertIn('geventwebsocket.gunicorn.workers.GeventWebSocketWorker', source)
        self.assertIn('--workers=${WORKERS:-4}', source)
        self.assertIn('exec /bin/bash', source)

    def test_actual_entrypoint_runs_schema_then_both_supervised_commands(self):
        import shlex
        binary = self.root / 'bin'
        binary.mkdir()
        events = self.root / 'schema-events'
        python = binary / 'python'
        python.write_text('''#!/bin/sh
if [ "$1" = "manage.py" ]; then
 if [ "$2" = "run_vm_restore_jobs" ]; then
  exec {python} {child} {worker}
 fi
 echo "$2" >> {events}
 exit 0
fi
exec {python} "$@"
'''.format(python=shlex.quote(sys.executable),
           child=shlex.quote(str(self.child)),
           worker=shlex.quote(str(self.root / 'worker')),
           events=shlex.quote(str(events))))
        (binary / 'sqlite3').write_text('#!/bin/sh\necho 1\n')
        (binary / 'gunicorn').write_text('#!/bin/sh\nexec {} {} {}\n'.format(shlex.quote(sys.executable),
                                                                             shlex.quote(str(self.child)),
                                                                             shlex.quote(str(self.root / 'web'))))
        for path in binary.iterdir():
            path.chmod(0o755)
        (self.root / 'manage.py'
         ).write_text('import os,sys\nassert sys.argv[1]=="run_vm_restore_jobs"\nos.execv(sys.executable,' +
                      repr([sys.executable, str(self.child), str(self.root / 'worker')]) + ')\n')
        environment = dict(os.environ,
                           PATH=str(binary) + os.pathsep + os.environ['PATH'],
                           PYTHONPATH=str(Path.cwd()),
                           DB_TYPE='sqlite3')
        process = subprocess.Popen(['bash', str(Path('entrypoint.sh').resolve())],
                                   cwd=self.root,
                                   env=environment,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: self.stop(process))
        web = self.wait_file('web', process)
        worker = self.wait_file('worker', process)
        self.assertEqual(events.read_text().splitlines(), [
            'makemigrations', 'makemigrations', 'repair_legacy_schema', 'repair_legacy_schema', 'migrate',
            'migrate_oauth_name_scope', 'verify_required_schema'
        ])
        process.terminate()
        self.assertEqual(process.wait(timeout=4), 128 + signal.SIGTERM)
        self.absent(web)
        self.absent(worker)
