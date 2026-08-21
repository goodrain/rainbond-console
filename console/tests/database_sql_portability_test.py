import ast
import re
from pathlib import Path
from unittest import TestCase


class DatabaseSQLPortabilityTest(TestCase):
    # capability_id: console.database.portable-runtime-sql
    def test_runtime_sql_does_not_use_mysql_only_constructs(self):
        repo_root = Path(__file__).resolve().parents[2]
        violations = []
        for source_root in (repo_root / "console", repo_root / "www", repo_root / "openapi"):
            for path in source_root.rglob("*.py"):
                if "tests" in path.parts or "migrations" in path.parts:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                        continue
                    sql = node.value.upper()
                    is_sql = bool(
                        re.search(r"\bSELECT\b[\s\S]*\bFROM\b", sql) or
                        re.search(r"\bINSERT\b[\s\S]*\bINTO\b", sql) or
                        re.search(r"\bUPDATE\b[\s\S]*\bSET\b", sql) or
                        re.search(r"\bDELETE\b[\s\S]*\bFROM\b", sql)
                    )
                    is_sql_fragment = bool(re.search(r"\bLIMIT\s+\{?[^,;\n]+\}?,", sql))
                    if not is_sql and not is_sql_fragment:
                        continue
                    if ("GROUP_CONCAT" in sql or " AS SIGNED" in sql or " AS UNSIGNED" in sql or
                            "COLLATE UTF8" in sql or "CONCAT(" in sql or "`" in sql or is_sql_fragment or
                            re.search(r'\{(?:\d+|[A-Z_][A-Z0-9_]*)\}', sql) or
                            re.search(r'(?:=|<>|!=|LIKE)\s*"', sql) or
                            re.search(r'\bIN\s*\(\s*"', sql)):
                        violations.append("{}:{}".format(path.relative_to(repo_root), node.lineno))

        self.assertEqual(violations, [], "MySQL-only runtime SQL must be replaced by ORM/application logic")
