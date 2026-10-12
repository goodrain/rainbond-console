# -*- coding: utf-8 -*-
from unittest import TestCase, mock

from console.management.commands.verify_required_schema import (
    REQUIRED_TABLES,
    find_missing_required_tables,
)


class RequiredSchemaVerificationTestCase(TestCase):
    # capability_id: console.database.required-schema-startup-gate
    def test_missing_required_tables_are_reported_in_stable_order(self):
        connection = mock.Mock()
        connection.introspection.table_names.return_value = [
            "mcp_device_authorization",
            "unrelated_table",
        ]

        missing = find_missing_required_tables(connection)

        self.assertEqual(
            missing,
            [table for table in REQUIRED_TABLES if table != "mcp_device_authorization"],
        )
