"""Keep delivery SQLite settings isolated from the rest of the Django suite."""
import subprocess
import sys
import unittest
from pathlib import Path


class DeliveryWorkflowTest(unittest.TestCase):
    def test_independent_delivery_workflow(self):
        result = subprocess.run([sys.executable, "-m", "console.tests.isolated_delivery_workflow"],
                                cwd=Path(__file__).parents[2],
                                capture_output=True,
                                text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
