"""The strict gate must distinguish legacy errors from a broken mypy run."""
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.parametrize("status,output,expected", [
    (0, "Success: no issues found", 0),
    (1, "www/models/main.py:1: error: legacy issue", 0),
    (1, "console/services/example.py:1: error: regression", 1),
    (2, "ModuleNotFoundError: No module named 'corsheaders'", 2),
    (127, "mypy: command not found", 127),
])
def test_typecheck_gate_exit_status(tmp_path, status, output, expected):
    executable = tmp_path / "mypy"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' \"$MYPY_TEST_OUTPUT\"\nexit \"$MYPY_TEST_STATUS\"\n")
    executable.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               MYPY_TEST_OUTPUT=output, MYPY_TEST_STATUS=str(status))
    script = Path(__file__).with_name("typecheck_gate.sh")
    result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected:
        assert "typecheck-gate OK" not in result.stdout
