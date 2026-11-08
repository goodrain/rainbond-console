"""Run lifecycle tests in a separate SQLite process without changing suite-wide Django settings."""
import subprocess
import sys
import unittest
from pathlib import Path


class TeamApplicationWorkflowTest(unittest.TestCase):
    def test_isolated_lifecycle_and_http_contract(self):
        result = subprocess.run([sys.executable, "-m", "console.tests.isolated_team_application_workflow"],
                                cwd=Path(__file__).parents[2], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
