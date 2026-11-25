# -*- coding: utf-8 -*-
from unittest import TestCase, mock

from django.core.management.base import CommandError

from console.management.commands.verify_required_schema import (
    Command,
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

    def test_startup_rejects_missing_delivery_and_team_application_tables(self):
        business_tables = (
            "delivery_template", "delivery_template_version", "delivery_task",
            "delivery_task_item", "delivery_listing_request", "team_creation_application",
        )
        for table in business_tables:
            with self.subTest(table=table):
                connection = mock.Mock()
                connection.introspection.table_names.return_value = [name for name in REQUIRED_TABLES if name != table]
                with mock.patch("console.management.commands.verify_required_schema.connections") as databases:
                    databases.databases = {"default": {}}
                    databases.__getitem__.return_value = connection
                    with self.assertRaisesRegex(CommandError, table):
                        Command().handle(database="default")

    def test_startup_accepts_complete_schema(self):
        connection = mock.Mock()
        connection.introspection.table_names.return_value = list(REQUIRED_TABLES)
        with mock.patch("console.management.commands.verify_required_schema.connections") as databases:
            databases.databases = {"default": {}}
            databases.__getitem__.return_value = connection
            command = Command()
            command.stdout = mock.Mock()
            command.handle(database="default")
            command.stdout.write.assert_called_once_with("Required database schema verified")
