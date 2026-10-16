# -*- coding: utf-8 -*-
# capability_id: console.build-source.single-transaction-boundary
import ast
from pathlib import Path
from unittest import TestCase


SOURCE_PATH = Path(__file__).resolve().parents[1] / "views" / "app_overview.py"


class BuildSourceTransactionTests(TestCase):

    def test_build_source_update_uses_atomic_rollback_without_manual_savepoints(self):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        build_source = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BuildSourceinfo")
        put = next(node for node in build_source.body if isinstance(node, ast.FunctionDef) and node.name == "put")

        transaction_calls = []
        message_attributes = []
        for node in ast.walk(put):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "transaction":
                    transaction_calls.append(node.func.attr)
            if isinstance(node, ast.Attribute) and node.attr == "message":
                message_attributes.append(node)

        self.assertNotIn("savepoint", transaction_calls)
        self.assertNotIn("savepoint_commit", transaction_calls)
        self.assertNotIn("savepoint_rollback", transaction_calls)
        self.assertIn("set_rollback", transaction_calls)
        self.assertEqual(message_attributes, [])
