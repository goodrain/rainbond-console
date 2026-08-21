from unittest import TestCase, mock

from console.repositories.base import BaseConnection
from www.db.base import BaseConnection as LegacyBaseConnection


class _Cursor(object):
    description = (("ID", None), ("GROUP_ID", None), ("SERVICE_IDS", None))

    def fetchall(self):
        return [(7, 1, '["service-1"]')]


class _LowercaseIDCursor(object):
    description = (("id", None), ("GROUP_ID", None))

    def fetchall(self):
        return [(7, 1)]


class _QueryCursor(object):
    description = (("SERVICE_ID", None),)

    def __init__(self):
        self.executed = None

    def execute(self, sql, args=None):
        self.executed = (sql, args)

    def fetchall(self):
        return [("service-1",)]


class BaseConnectionPortabilityTest(TestCase):
    # capability_id: console.database.normalized-cursor-columns
    def test_cursor_column_names_are_normalized_to_lowercase(self):
        rows = BaseConnection()._dict_fetch_all(_Cursor())

        self.assertEqual(rows[0].ID, 7)
        self.assertEqual(rows[0].group_id, 1)
        self.assertEqual(rows[0].service_ids, '["service-1"]')
        self.assertNotIn("GROUP_ID", rows[0])

    def test_legacy_connection_uses_the_same_normalization(self):
        rows = LegacyBaseConnection()._dict_fetch_all(_Cursor())

        self.assertEqual(rows[0].group_id, 1)

    def test_existing_lowercase_id_column_keeps_its_mysql_shape(self):
        rows = BaseConnection()._dict_fetch_all(_LowercaseIDCursor())

        self.assertEqual(rows[0].id, 7)
        self.assertNotIn("ID", rows[0])

    def test_query_forwards_bound_values_through_the_shared_connection(self):
        cursor = _QueryCursor()
        database = mock.Mock()
        database.cursor.return_value = cursor

        with mock.patch("console.repositories.base.connections", {"default": database}):
            rows = LegacyBaseConnection().query("select service_id where service_id=%s", ["service-1"])

        self.assertIs(LegacyBaseConnection, BaseConnection)
        self.assertEqual(cursor.executed, ("select service_id where service_id=%s", ["service-1"]))
        self.assertEqual(rows[0].service_id, "service-1")
