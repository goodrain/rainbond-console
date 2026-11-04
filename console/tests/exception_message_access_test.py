import ast
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRECTORIES = ("console", "openapi", "www")
EXCEPTION_VARIABLE_NAMES = {"e", "err", "ex", "exc"}


class ExceptionMessageAccessTests(TestCase):
    def test_exception_message_attribute_access_is_not_used(self):
        violations = []

        for source_directory in SOURCE_DIRECTORIES:
            for path in (REPO_ROOT / source_directory).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Attribute) and node.attr == "message" and isinstance(node.value, ast.Name)
                            and node.value.id in EXCEPTION_VARIABLE_NAMES):
                        violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

        self.assertEqual([], violations, "Use a safe exception message lookup instead:\n" + "\n".join(violations))
