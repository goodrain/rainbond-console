"""Run real migration/schema reconciliation in an isolated Django process."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class AppliedSchemaRepairTests(unittest.TestCase):
    # capability_id: console.database.repair-missing-applied-required-tables
    def test_applied_migration_schema_drift_preserves_data_and_pending_operations(self):
        result = subprocess.run([sys.executable, "-m", "console.tests.isolated_applied_schema_repair"],
                                cwd=str(Path(__file__).resolve().parents[2]),
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                                capture_output=True,
                                text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
