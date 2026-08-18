# -*- coding: utf-8 -*-
import importlib.util
import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "database_state.py"
SPEC = importlib.util.spec_from_file_location("database_state", SCRIPT_PATH)
database_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(database_state)


# capability_id: console.database.backend-neutral-readiness
class DatabaseStateTests(unittest.TestCase):

    def test_entrypoint_uses_django_database_state_helper(self):
        entrypoint = Path(__file__).resolve().parents[2] / "entrypoint.sh"
        source = entrypoint.read_text(encoding="utf-8")

        self.assertIn("python scripts/database_state.py empty", source)
        self.assertIn("python scripts/database_state.py ready", source)
        self.assertNotIn("mysql -h", source)

    def test_returns_not_ready_when_connection_is_unavailable(self):
        unavailable_connection = mock.Mock()
        unavailable_connection.ensure_connection.side_effect = RuntimeError("not ready")

        with mock.patch.object(database_state, "get_connection", return_value=unavailable_connection), \
                redirect_stderr(io.StringIO()):
            exit_code = database_state.main(["ready"])

        self.assertEqual(exit_code, 1)

    def test_reports_an_empty_database_from_django_introspection(self):
        connection = mock.Mock()
        connection.introspection.table_names.return_value = []

        with mock.patch.object(database_state, "get_connection", return_value=connection):
            exit_code = database_state.main(["empty"])

        connection.ensure_connection.assert_called_once_with()
        connection.introspection.table_names.assert_called_once_with()
        self.assertEqual(exit_code, 0)

    def test_reports_a_populated_database_from_django_introspection(self):
        connection = mock.Mock()
        connection.introspection.table_names.return_value = ["console_users"]

        with mock.patch.object(database_state, "get_connection", return_value=connection):
            exit_code = database_state.main(["empty"])

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
