import re
import unittest
from pathlib import Path


class EntrypointGunicornTest(unittest.TestCase):

    def setUp(self):
        entrypoint = Path(__file__).resolve().parents[2] / "entrypoint.sh"
        self.source = entrypoint.read_text(encoding="utf-8")
        self.gunicorn_command = next(line for line in self.source.splitlines() if "exec gunicorn" in line)

    def test_production_server_has_enough_workers_without_reload(self):
        self.assertRegex(self.gunicorn_command, re.compile(r"--workers=\$\{WORKERS:-4\}"))
        self.assertNotIn("--reload", self.gunicorn_command)


if __name__ == "__main__":
    unittest.main()
