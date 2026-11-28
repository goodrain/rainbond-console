import subprocess


def test_install_rainbond_resource_requirements():
    subprocess.run(
        ["bash", "scripts/install_rainbond_resource_requirements_test.sh"],
        check=True,
    )
