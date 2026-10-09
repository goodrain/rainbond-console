import re
import unittest
from pathlib import Path


class EntrypointGunicornTest(unittest.TestCase):

    def setUp(self):
        repo_root = Path(__file__).resolve().parents[2]
        entrypoint = repo_root / "entrypoint.sh"
        self.source = entrypoint.read_text(encoding="utf-8")
        self.gunicorn_command = next(line for line in self.source.splitlines() if "exec gunicorn" in line)
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
        plan = "if ! python manage.py repair_legacy_schema --apps authtoken,www,console --plan; then"
        repair = "if ! python manage.py repair_legacy_schema --apps authtoken,www,console; then"
        migrate = "if ! python manage.py migrate --fake-initial --noinput; then"
        verify = "if ! python manage.py verify_required_schema; then"

        self.assertIn(plan, self.source)
        self.assertLess(self.source.index(plan), self.source.index(repair))
        self.assertLess(self.source.index(repair), self.source.index(migrate))
        self.assertLess(self.source.index(migrate), self.source.index(verify))


if __name__ == "__main__":
    unittest.main()
