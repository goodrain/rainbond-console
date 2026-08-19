# -*- coding: utf-8 -*-
import os
import unittest
from unittest import mock

from console.repositories.base import BaseConnection as ConsoleBaseConnection
from www.db.base import BaseConnection as WebBaseConnection


class Cursor(object):
    def __init__(self, columns, rows):
        self.description = [(column,) for column in columns]
        self._rows = rows
        self.executed = None

    def execute(self, sql, args=None):
        self.executed = (sql, args)

    def fetchall(self):
        return self._rows


# capability_id: console.database.dm-result-column-normalization
class DatabaseConnectionTests(unittest.TestCase):
    def test_dm_result_columns_are_normalized_before_addict_attribute_access(self):
        cursor = Cursor(["SERVICE_ID", "GROUP_NAME"], [("service-1", "demo")])

        with mock.patch.dict(os.environ, {"DB_TYPE": "dm"}, clear=False):
            for connection_class in (ConsoleBaseConnection, WebBaseConnection):
                row = connection_class()._dict_fetch_all(cursor)[0]

                self.assertEqual(row.service_id, "service-1")
                self.assertEqual(row.group_name, "demo")
                self.assertNotIn("SERVICE_ID", row)

    def test_mysql_result_column_keys_are_unchanged(self):
        cursor = Cursor(["service_id", "group_name"], [("service-1", "demo")])

        with mock.patch.dict(os.environ, {"DB_TYPE": "mysql"}, clear=False):
            for connection_class in (ConsoleBaseConnection, WebBaseConnection):
                row = connection_class()._dict_fetch_all(cursor)[0]

                self.assertEqual(dict(row), {"service_id": "service-1", "group_name": "demo"})

    def test_raw_query_forwards_bound_values_to_both_connection_wrappers(self):
        for module_name, connection_class in (
            ("console.repositories.base", ConsoleBaseConnection),
            ("www.db.base", WebBaseConnection),
        ):
            cursor = Cursor(["service_id"], [("service-1",)])
            database = mock.Mock()
            database.cursor.return_value = cursor
            with mock.patch(module_name + ".connections", {"default": database}):
                connection_class().query("select service_id where service_id=%s", ["service-1"])
            self.assertEqual(cursor.executed, ("select service_id where service_id=%s", ["service-1"]))


if __name__ == "__main__":
    unittest.main()
