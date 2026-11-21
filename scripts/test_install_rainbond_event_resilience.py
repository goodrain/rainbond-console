import subprocess
from pathlib import Path


def test_install_rainbond_event_resilience_script():
    repository_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        ["bash", "scripts/install_rainbond_event_resilience_test.sh"],
        cwd=repository_root,
        check=True,
    )
