import subprocess
from pathlib import Path


def test_install_timeout_diagnostics_shell_checks():
    script = Path(__file__).with_suffix(".sh")
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
