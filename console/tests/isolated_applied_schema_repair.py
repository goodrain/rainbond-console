"""Exercise recorded migrations whose required tables are absent from the database."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock


def main():
    with TemporaryDirectory(prefix="applied-schema-") as directory:
        root = Path(directory)
        package = root / "schema_fixture"
        (package / "migrations").mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "migrations/__init__.py").write_text("")
        (package / "apps.py").write_text("from django.apps import AppConfig\n"
                                         "class Config(AppConfig):\n"
                                         "    name = 'schema_fixture'\n"
                                         "    label = 'console'\n")
        sys.path.insert(0, directory)
        from django.conf import settings
        settings.configure(INSTALLED_APPS=["schema_fixture.apps.Config"],
                           DATABASES={"default": {
                               "ENGINE": "django.db.backends.sqlite3",
                               "NAME": ":memory:"
                           }},
                           SECRET_KEY="test-placeholder")
        import django
        django.setup()
        from django.db import connection, connections, migrations, models
        from django.db.migrations.executor import MigrationExecutor
        from django.db.migrations.recorder import MigrationRecorder
        from django.db.migrations.writer import MigrationWriter
        from console.management.commands.repair_legacy_schema import Command, repair_missing_required_tables

        initial = migrations.Migration("0001_initial", "console")
        initial.initial = True
        initial.operations = [
            migrations.CreateModel("Legacy", [("id", models.AutoField(primary_key=True)),
                                              ("value", models.CharField(max_length=64))],
                                   options={"db_table": "legacy_preserved"}),
        ]
        feature = migrations.Migration("0002_required_features", "console")
        feature.dependencies = [("console", initial.name)]

        def foreign(target, nullable=False):
            return models.ForeignKey("console." + target, on_delete=models.PROTECT, null=nullable)

        definitions = (
            ("DeliveryTemplate", "delivery_template", [("name", models.CharField(max_length=64))]),
            ("DeliveryTemplateVersion", "delivery_template_version", [("template", foreign("DeliveryTemplate"))]),
            ("DeliveryTask", "delivery_task", [("version", foreign("DeliveryTemplateVersion"))]),
            ("DeliveryTaskItem", "delivery_task_item", [("task", foreign("DeliveryTask"))]),
            ("DeliveryListingRequest", "delivery_listing_request", [("version", foreign("DeliveryTemplateVersion")),
                                                                    ("task", foreign("DeliveryTask", True))]),
            ("TeamApplication", "team_creation_application", [("name", models.CharField(max_length=64))]),
            ("Unrelated", "unrelated_feature", []),
        )
        feature.operations = [
            migrations.CreateModel(name, [("id", models.AutoField(primary_key=True))] + fields, options={"db_table": table})
            for name, table, fields in definitions
        ]
        later = migrations.Migration("0003_template_details", "console")
        later.dependencies = [("console", feature.name)]
        later.operations = [migrations.AddField("deliverytemplate", "details", models.TextField(default=""))]
        for migration in (initial, feature, later):
            (package / "migrations" / (migration.name + ".py")).write_text(MigrationWriter(migration).as_string())
        required = [table for _, table, _ in definitions[:-1]]

        class AppliedSchemaRepairTests(unittest.TestCase):
            def setUp(self):
                self.alias = "applied_schema_test"
                connections.databases[self.alias] = dict(connection.settings_dict, NAME=":memory:")
                self.database = connections[self.alias]

            def tearDown(self):
                self.database.close()
                del connections[self.alias]
                del connections.databases[self.alias]

            def seed(self, target=feature.name, keep_template=False):
                executor = MigrationExecutor(self.database)
                executor.migrate([("console", target)])
                state = executor.loader.project_state(("console", target))
                state.apps.get_model("console", "Legacy").objects.using(self.alias).create(id=7, value="preserved")
                if target != initial.name:
                    if keep_template:
                        state.apps.get_model("console",
                                             "DeliveryTemplate").objects.using(self.alias).create(id=9,
                                                                                                  name="preserved template")
                    with self.database.schema_editor() as editor:
                        for name, _, _ in reversed(definitions):
                            if keep_template and name == "DeliveryTemplate":
                                continue
                            editor.delete_model(state.apps.get_model("console", name))
                return state

            def test_missing_applied_tables_are_restored_without_changing_records_or_legacy_rows(self):
                state = self.seed()
                before = MigrationRecorder(self.database).applied_migrations()
                self.assertEqual(repair_missing_required_tables(self.database, ["console"]), required)
                self.assertEqual(repair_missing_required_tables(self.database, ["console"]), [])
                self.assertEqual(MigrationRecorder(self.database).applied_migrations(), before)
                self.assertEqual(
                    state.apps.get_model("console", "Legacy").objects.using(self.alias).get(id=7).value, "preserved")
                self.assertNotIn("unrelated_feature", self.database.introspection.table_names())
                template = state.apps.get_model("console", "DeliveryTemplate").objects.using(self.alias).create(name="new")
                version = state.apps.get_model("console",
                                               "DeliveryTemplateVersion").objects.using(self.alias).create(template=template)
                task = state.apps.get_model("console", "DeliveryTask").objects.using(self.alias).create(version=version)
                state.apps.get_model("console", "DeliveryTaskItem").objects.using(self.alias).create(task=task)
                state.apps.get_model("console", "DeliveryListingRequest").objects.using(self.alias).create(version=version,
                                                                                                           task=task)
                self.database.check_constraints()

            def test_existing_feature_rows_survive_repair(self):
                state = self.seed(keep_template=True)
                self.assertEqual(repair_missing_required_tables(self.database, ["console"]), required[1:])
                self.assertEqual(
                    state.apps.get_model("console", "DeliveryTemplate").objects.using(self.alias).get(id=9).name,
                    "preserved template")

            def test_plan_does_not_create_tables_or_modify_migration_records(self):
                self.seed()
                before = MigrationRecorder(self.database).applied_migrations()
                tables = self.database.introspection.table_names()
                self.assertEqual(repair_missing_required_tables(self.database, ["console"], dry_run=True), required)
                self.assertEqual(self.database.introspection.table_names(), tables)
                self.assertEqual(MigrationRecorder(self.database).applied_migrations(), before)

            def test_pending_field_change_is_left_to_normal_migrate(self):
                self.seed()
                repair_missing_required_tables(self.database, ["console"])
                with self.database.cursor() as cursor:
                    columns = self.database.introspection.get_table_description(cursor, "delivery_template")
                self.assertNotIn("details", [column.name for column in columns])
                executor = MigrationExecutor(self.database)
                executor.migrate([("console", later.name)])
                with self.database.cursor() as cursor:
                    columns = self.database.introspection.get_table_description(cursor, "delivery_template")
                self.assertIn("details", [column.name for column in columns])

            def test_unapplied_features_and_other_apps_are_not_repaired(self):
                self.seed(target=initial.name)
                self.assertEqual(repair_missing_required_tables(self.database, ["console"]), [])
                MigrationExecutor(self.database).migrate([("console", feature.name)])
                state = MigrationExecutor(self.database).loader.project_state(("console", feature.name))
                with self.database.schema_editor() as editor:
                    editor.delete_model(state.apps.get_model("console", "DeliveryListingRequest"))
                self.assertEqual(repair_missing_required_tables(self.database, ["www"]), [])
                self.assertNotIn("delivery_listing_request", self.database.introspection.table_names())

            def test_startup_command_repairs_applied_feature_tables(self):
                self.seed()
                before = MigrationRecorder(self.database).applied_migrations()
                with mock.patch("console.management.commands.repair_legacy_schema.repair_oauth_auto_create_user_column",
                                return_value=False):
                    command = Command()
                    command.stdout = mock.Mock()
                    command.handle(database=self.alias, apps="console", plan=False)
                self.assertTrue(set(required).issubset(self.database.introspection.table_names()))
                self.assertEqual(MigrationRecorder(self.database).applied_migrations(), before)

            def test_fresh_database_is_left_for_normal_migrate(self):
                self.assertEqual(repair_missing_required_tables(self.database, ["console"]), [])
                self.assertEqual(self.database.introspection.table_names(), [])

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AppliedSchemaRepairTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.exit(main())
