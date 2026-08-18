"""Regression coverage for the private Dameng driver bundle preparation script."""

import os
import shutil
import subprocess
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREPARE_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "prepare_dameng_python_driver.sh")
NORMAL_DOCKERFILE = os.path.join(PROJECT_ROOT, "Dockerfile")
DM_DOCKERFILE = os.path.join(PROJECT_ROOT, "Dockerfile.dm")
DOCKERIGNORE = os.path.join(PROJECT_ROOT, ".dockerignore")


# capability_id: console.database.dm-driver-bundle-preparation
class DamengDriverBundleScriptTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="rainbond-dameng-driver-")
        self.source_root = os.path.join(self.tempdir, "dmdbms")
        self.output_root = os.path.join(self.tempdir, "driver-bundle")
        self._create_driver_source()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def _create_driver_source(self):
        for relative_path in (
            "drivers/python/dmPython/setup.py",
            "drivers/python/dmDjango/dmDjango3.0/setup.py",
            "drivers/dpi/libdmdpi.so",
            "drivers/dpi/dependencies/libcrypto.so",
            "drivers/dpi/include/DPI.h",
            "include/not-required.h",
        ):
            path = os.path.join(self.source_root, relative_path)
            parent = os.path.dirname(path)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            with open(path, "w") as driver_file:
                driver_file.write("test driver artifact\n")

    def _run_prepare(self):
        return subprocess.run(
            ["bash", PREPARE_SCRIPT, self.source_root, self.output_root],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def test_copies_expected_private_driver_layout(self):
        result = self._run_prepare()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.output_root, "dpi", "libdmdpi.so")))
        self.assertTrue(os.path.isfile(os.path.join(self.output_root, "dpi", "dependencies", "libcrypto.so")))
        self.assertTrue(os.path.isfile(os.path.join(self.output_root, "dpi", "include", "DPI.h")))
        self.assertFalse(os.path.exists(os.path.join(self.output_root, "include")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.output_root, "drivers", "python", "dmPython", "setup.py"))
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.output_root, "drivers", "python", "dmDjango", "dmDjango3.0", "setup.py")
            )
        )

    def test_rejects_missing_dameng_runtime_library(self):
        os.remove(os.path.join(self.source_root, "drivers", "dpi", "libdmdpi.so"))

        result = self._run_prepare()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required source", result.stderr)
        self.assertFalse(os.path.exists(self.output_root))

    def test_rejects_missing_dameng_include_directory(self):
        shutil.rmtree(os.path.join(self.source_root, "drivers", "dpi", "include"))

        result = self._run_prepare()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required source", result.stderr)
        self.assertFalse(os.path.exists(self.output_root))

    def test_rejects_a_driver_path_that_is_not_a_directory(self):
        dm_python_path = os.path.join(self.source_root, "drivers", "python", "dmPython")
        shutil.rmtree(dm_python_path)
        with open(dm_python_path, "w") as driver_file:
            driver_file.write("not a driver directory")

        result = self._run_prepare()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required source", result.stderr)
        self.assertFalse(os.path.exists(self.output_root))

    def test_does_not_overwrite_an_existing_private_bundle(self):
        os.makedirs(self.output_root)
        sentinel_path = os.path.join(self.output_root, "sentinel")
        with open(sentinel_path, "w") as sentinel_file:
            sentinel_file.write("preserve existing bundle")

        result = self._run_prepare()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("destination already exists", result.stderr)
        self.assertTrue(os.path.isfile(sentinel_path))


# capability_id: console.database.dm-standard-image
class DamengDockerfileStructureTest(unittest.TestCase):
    def _read_file(self, path):
        with open(path) as source_file:
            return source_file.read()

    def test_standard_build_uses_the_named_dameng_context(self):
        dockerfile = self._read_file(NORMAL_DOCKERFILE)

        self.assertIn("COPY --from=dameng python/dpi/ /opt/dameng/dpi/", dockerfile)
        self.assertIn(
            "COPY --from=dameng python/drivers/python/dmPython/ /opt/dameng/drivers/python/dmPython/", dockerfile
        )
        self.assertIn(
            "COPY --from=dameng python/drivers/python/dmDjango/dmDjango3.0/ "
            "/opt/dameng/drivers/python/dmDjango/dmDjango3.0/",
            dockerfile,
        )
        self.assertIn("ENV DM_HOME=/opt/dameng", dockerfile)
        self.assertIn("ENV PATH=${DM_HOME}/dpi:/app/ui/py_venv/bin:${PATH}", dockerfile)
        self.assertIn("pip install --no-cache-dir /opt/dameng/drivers/python/dmPython", dockerfile)
        self.assertIn("pip install --no-cache-dir /opt/dameng/drivers/python/dmDjango/dmDjango3.0", dockerfile)
        self.assertIn("rm -rf /opt/dameng/drivers /opt/dameng/dpi/include", dockerfile)

        final_stage = dockerfile.split("FROM ${PYTHON_SLIM_BASE}", 1)[1]
        dameng_copy_lines = [
            line.strip()
            for line in final_stage.splitlines()
            if line.strip().startswith("COPY --from=build-console /opt/dameng")
        ]
        self.assertEqual(
            dameng_copy_lines,
            ["COPY --from=build-console /opt/dameng/dpi/ /opt/dameng/dpi/"],
        )
        self.assertNotIn("COPY --from=dameng", final_stage)
        self.assertNotIn("drivers/python", final_stage)
        self.assertNotIn("/opt/dameng/dpi/include", final_stage)
        self.assertIn("libaio1", final_stage)
        self.assertIn("/etc/ld.so.conf.d/dameng.conf", final_stage)
        self.assertIn("ldconfig", final_stage)

    def test_standard_build_preserves_mysql_support_and_removes_the_special_dockerfile(self):
        normal_dockerfile = self._read_file(NORMAL_DOCKERFILE)
        dockerignore = self._read_file(DOCKERIGNORE)

        self.assertIn("mariadb-client sqlite3 libmariadb3", normal_dockerfile)
        self.assertIn("third_party/dameng/", dockerignore)
        self.assertFalse(os.path.exists(DM_DOCKERFILE))
