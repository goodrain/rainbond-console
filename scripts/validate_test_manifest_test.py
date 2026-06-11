import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
