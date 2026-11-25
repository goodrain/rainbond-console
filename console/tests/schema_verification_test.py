# -*- coding: utf-8 -*-
from unittest import TestCase, mock
from types import SimpleNamespace

from django.apps import apps

from django.core.management.base import CommandError

from console.management.commands.verify_required_schema import (
    Command,
    REQUIRED_TABLES,
    find_missing_required_tables,
    find_missing_required_columns,
)


class RequiredSchemaVerificationTestCase(TestCase):
    # capability_id: console.database.required-schema-startup-gate
    def test_missing_required_tables_are_reported_in_stable_order(self):
        connection = mock.MagicMock()
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
            "delivery_template",
            "delivery_template_version",
            "delivery_task",
            "delivery_task_item",
            "delivery_listing_request",
            "team_creation_application",
        )
        for table in business_tables:
            with self.subTest(table=table):
                connection = mock.MagicMock()
                connection.introspection.table_names.return_value = [name for name in REQUIRED_TABLES if name != table]
                with mock.patch("console.management.commands.verify_required_schema.connections") as databases:
                    databases.databases = {"default": {}}
                    databases.__getitem__.return_value = connection
                    with self.assertRaisesRegex(CommandError, table):
                        Command().handle(database="default")

    def test_startup_accepts_complete_schema(self):
        connection = mock.MagicMock()
        connection.introspection.table_names.return_value = list(REQUIRED_TABLES)
        descriptions = {
            model._meta.db_table: [SimpleNamespace(name=field.column) for field in model._meta.local_fields]
            for model in apps.get_models()
        }
        connection.introspection.get_table_description.side_effect = lambda cursor, table: descriptions[table]
        with mock.patch("console.management.commands.verify_required_schema.connections") as databases:
            databases.databases = {"default": {}}
            databases.__getitem__.return_value = connection
            command = Command()
            command.stdout = mock.Mock()
            command.handle(database="default")
            command.stdout.write.assert_called_once_with("Required database schema verified")

    def test_missing_delivery_foreign_key_columns_fail_without_database_writes(self):
        for table, column in (("delivery_task", "template_id"), ("delivery_task", "version_id"),
                              ("delivery_listing_request", "publication_task_id"), ("delivery_listing_request", "version_id")):
            with self.subTest(table=table, column=column):
                database = mock.MagicMock()
                database.introspection.table_names.return_value = list(REQUIRED_TABLES)
                descriptions = {
                    model._meta.db_table: [SimpleNamespace(name=field.column) for field in model._meta.local_fields]
                    for model in apps.get_models()
                }
                descriptions[table] = [field for field in descriptions[table] if field.name != column]
                database.introspection.get_table_description.side_effect = lambda cursor, name: descriptions[name]
                self.assertEqual(find_missing_required_columns(database), [table + "." + column])
                with mock.patch("console.management.commands.verify_required_schema.connections") as databases:
                    databases.databases = {"default": {}}
                    databases.__getitem__.return_value = database
                    with self.assertRaisesRegex(CommandError, table + r"\." + column):
                        Command().handle(database="default")
                database.schema_editor.assert_not_called()
                database.cursor.return_value.__enter__.return_value.execute.assert_not_called()

    def test_model_preflight_rejects_missing_registration_without_accessing_database(self):
        with mock.patch("console.management.commands.verify_required_schema.apps.get_models", return_value=[]), \
                mock.patch("console.management.commands.verify_required_schema.connections") as databases:
            with self.assertRaisesRegex(CommandError, "models are not registered.*delivery_task"):
                Command().handle(database="default", models_only=True)
            databases.__getitem__.assert_not_called()

    def test_model_preflight_accepts_registered_models_without_accessing_database(self):
        with mock.patch("console.management.commands.verify_required_schema.connections") as databases:
            command = Command()
            command.stdout = mock.Mock()
            command.handle(database="default", models_only=True)
            command.stdout.write.assert_called_once_with("Required database models verified")
            databases.__getitem__.assert_not_called()
