import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import validate_test_manifest as validator
from validate_test_manifest import collect_marked_tests


class ValidateTestManifestTests(unittest.TestCase):

    # capability_id: console.test-manifest.ignore-worktrees
    def test_collect_marked_tests_ignores_nested_worktrees(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            real_test = repo_root / "console" / "tests" / "real_test.py"
            worktree_test = repo_root / ".worktrees" / "old-work" / "console" / "tests" / "stale_test.py"
            real_test.parent.mkdir(parents=True)
            worktree_test.parent.mkdir(parents=True)

            marker_prefix = "# capability" + "_id:"
            real_test.write_text(marker_prefix + " console.real\n", encoding="utf-8")
            worktree_test.write_text(marker_prefix + " console.stale\n", encoding="utf-8")

            marked = collect_marked_tests(repo_root)

        self.assertEqual(marked, {"console/tests/real_test.py": ["console.real"]})


def create_fixture(root, registered):
    test_file = root / "console" / "tests" / "sample_test.py"
    test_file.parent.mkdir(parents=True)
    prefix = "# capability" + "_id:"
    test_file.write_text(prefix + " console.sample\n", encoding="utf-8")
    (root / "sample.py").write_text("value = 1\n", encoding="utf-8")
    capability = {
        "id": "console.sample",
        "title": "Sample",
        "interface_type": "other",
        "interface": "sample.value",
        "code_paths": ["sample.py"],
        "tests": [{
            "path": "console/tests/sample_test.py"
        }],
        "test_type": "regression",
        "status": "active",
    }
    manifest = root / "test-manifest.json"
    manifest.write_text(json.dumps({
        "version": 1,
        "repo": "sample",
        "capabilities": [capability] if registered else []
    }),
                        encoding="utf-8")
    return manifest


# capability_id: console.test-manifest.repo-relative-scan
class ManifestRootBoundaryTests(unittest.TestCase):
    def test_external_ignored_ancestor_does_not_hide_real_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for ancestor in ("ordinary", ".worktrees", ".git", ".claude", "vendor", "_output", "node_modules", "dist"):
                with self.subTest(ancestor=ancestor):
                    root = Path(temp_dir) / ancestor / "repo"
                    create_fixture(root, registered=True)
                    hidden = root / "vendor" / "ignored_test.py"
                    hidden.parent.mkdir()
                    hidden.write_text(("# capability" + "_id: console.ignored\n"), encoding="utf-8")
                    self.assertEqual(collect_marked_tests(root), {"console/tests/sample_test.py": ["console.sample"]})

    def test_public_cli_returns_the_same_unknown_marker_error_in_both_locations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            errors = []
            for ancestor in ("ordinary", ".worktrees"):
                root = Path(temp_dir) / ancestor / "repo"
                create_fixture(root, registered=False)
                result = subprocess.run([sys.executable, validator.__file__, "--repo-root",
                                         str(root)],
                                        capture_output=True,
                                        text=True)
                self.assertEqual(result.returncode, 1)
                errors.append(result.stderr)
            self.assertEqual(errors[0], errors[1])
            self.assertIn("managed test references unknown", errors[0])

    def test_success_cli_reports_a_nonzero_marker_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / ".worktrees" / "repo"
            create_fixture(root, registered=True)
            result = subprocess.run([sys.executable, validator.__file__, "--repo-root",
                                     str(root)],
                                    capture_output=True,
                                    text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("marked test files: 1", result.stdout)


# capability_id: console.test-manifest.nonempty-marker-control
class ManifestScanCompletenessTests(unittest.TestCase):
    def test_present_managed_marker_cannot_pass_an_unexpected_empty_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = create_fixture(root, registered=True)
            with mock.patch.object(validator, "collect_marked_tests", return_value={}):
                errors = validator.validate_manifest(root, manifest)
            self.assertTrue(any("scan returned no files" in error for error in errors))

    def test_truly_empty_repository_is_not_falsely_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "test-manifest.json"
            manifest.write_text(json.dumps({"version": 1, "repo": "empty", "capabilities": []}), encoding="utf-8")
            self.assertEqual(validator.validate_manifest(root, manifest), [])


if __name__ == "__main__":
    unittest.main()
