import re
import os
import subprocess
from tempfile import TemporaryDirectory
import unittest
from pathlib import Path


class EntrypointGunicornTest(unittest.TestCase):
    def setUp(self):
        repo_root = Path(__file__).resolve().parents[2]
        entrypoint = repo_root / "entrypoint.sh"
        self.source = entrypoint.read_text(encoding="utf-8")
        self.gunicorn_command = next(line for line in self.source.splitlines() if "gunicorn goodrain_web.wsgi" in line)
        self.procfile_command = (repo_root / "Procfile").read_text(encoding="utf-8")

    def test_production_server_has_enough_workers_without_reload(self):
        self.assertRegex(self.gunicorn_command, re.compile(r"--workers=\$\{WORKERS:-4\}"))
        self.assertNotIn("--reload", self.gunicorn_command)

    # capability_id: console.runtime.sse-gunicorn-timeout
    def test_gunicorn_timeout_outlives_one_hour_sse_streams(self):
        timeout_option = "--timeout=${GUNICORN_TIMEOUT:-3700}"

        self.assertIn(timeout_option, self.gunicorn_command)
        self.assertIn(timeout_option, self.procfile_command)

    # capability_id: console.rainskills-audit-strict-startup
    # capability_id: console.database.required-schema-startup-gate
    def test_database_startup_plans_repairs_before_applying_and_migrating(self):
        models = "if ! python manage.py verify_required_schema --models-only; then"
        self.assertIn(models, self.source)
        self.assertLess(self.source.index(models), self.source.index("python manage.py makemigrations"))
        plan = "if ! python manage.py repair_legacy_schema --apps authtoken,www,console --plan; then"
        repair = "if ! python manage.py repair_legacy_schema --apps authtoken,www,console; then"
        migrate = "if ! python manage.py migrate --fake-initial --noinput; then"
        verify = "if ! python manage.py verify_required_schema; then"

        self.assertIn(plan, self.source)
        self.assertLess(self.source.index(plan), self.source.index(repair))
        self.assertLess(self.source.index(repair), self.source.index(migrate))
        self.assertLess(self.source.index(migrate), self.source.index(verify))

    def test_missing_models_stop_real_entrypoint_before_migration_generation(self):
        with TemporaryDirectory(prefix="schema-model-preflight-") as directory:
            root = Path(directory)
            events = root / "commands"
            python = root / "python"
            python.write_text('#!/bin/sh\necho "$*" >> "$SCHEMA_TEST_EVENTS"\nexit 1\n')
            sqlite = root / "sqlite3"
            sqlite.write_text('#!/bin/sh\necho 1\n')
            python.chmod(0o755)
            sqlite.chmod(0o755)
            environment = dict(os.environ,
                               PATH=str(root) + os.pathsep + os.environ["PATH"],
                               DB_TYPE="sqlite3",
                               SCHEMA_TEST_EVENTS=str(events))
            script = Path(__file__).resolve().parents[2] / "entrypoint.sh"
            result = subprocess.run(["bash", str(script)],
                                    cwd=directory,
                                    env=environment,
                                    capture_output=True,
                                    text=True,
                                    timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(events.read_text().splitlines(), ["manage.py verify_required_schema --models-only"])
            self.assertIn("required database models are not registered", result.stdout)


if __name__ == "__main__":
    unittest.main()
