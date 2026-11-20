"""Retain data when generated migration history removes then restores live models."""
import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

from django.apps import apps
from django.core.management.base import CommandError
from django.db import connection, connections, migrations, models
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.writer import MigrationWriter
from django.test import override_settings

from console.utils.legacy_model_roundtrip import repair_generated_model_roundtrips


# capability_id: console.schema.preserve-generated-model-roundtrips
class LegacyModelRoundtripTests(TestCase):
    @contextmanager
    def database(self, incompatible=False, fresh=False):
        package = "roundtrip_" + uuid4().hex
        alias = "roundtrip_test"
        with TemporaryDirectory(prefix="schema-roundtrip-") as directory:
            root = Path(directory)
            folder = root / package
            folder.mkdir()
            (folder / "__init__.py").write_text("")
            initial = migrations.Migration("0001_initial", "console")
            initial.initial = True
            initial.operations = [
                migrations.CreateModel("Ledger", [("id", models.AutoField(primary_key=True)),
                                                  ("value", models.CharField(max_length=64))],
                                       options={"db_table": "roundtrip_ledger"}),
                migrations.CreateModel(
                    "LedgerEntry", [("id", models.AutoField(primary_key=True)),
                                    ("ledger", models.ForeignKey("console.Ledger", on_delete=models.CASCADE)),
                                    ("key", models.CharField(max_length=32))],
                    options={
                        "db_table": "roundtrip_entry",
                        "constraints": [models.UniqueConstraint(fields=["ledger", "key"], name="roundtrip_entry_unique")]
                    }),
                migrations.CreateModel("Preferences", [("id", models.AutoField(primary_key=True)),
                                                       ("name", models.CharField(max_length=64)),
                                                       ("enabled", models.BooleanField(default=False))],
                                       options={"db_table": "roundtrip_preferences"}),
            ]
            remove = migrations.Migration("0002_incomplete_models", "console")
            remove.dependencies = [("console", initial.name)]
            remove.operations = [
                migrations.RemoveConstraint("ledgerentry", "roundtrip_entry_unique"),
                migrations.RemoveField("ledgerentry", "ledger"),
                migrations.DeleteModel("LedgerEntry"),
                migrations.DeleteModel("Ledger"),
                migrations.RemoveField("preferences", "enabled"),
                migrations.AlterField("preferences", "name", models.CharField(max_length=64, unique=True))
            ]
            restore = migrations.Migration("0003_complete_models", "console")
            restore.dependencies = [("console", remove.name)]
            restore.operations = [
                initial.operations[0],
                migrations.CreateModel("LedgerEntry", [("id", models.AutoField(primary_key=True)),
                                                       ("key", models.CharField(max_length=32))],
                                       options={"db_table": "roundtrip_entry"}),
                migrations.AddField("ledgerentry", "ledger", models.ForeignKey("console.Ledger", on_delete=models.CASCADE)),
                migrations.AddConstraint("ledgerentry",
                                         models.UniqueConstraint(fields=["ledger", "key"], name="roundtrip_entry_unique")),
                migrations.AddField("preferences", "enabled", models.BooleanField(default=False)),
                migrations.AlterField("preferences", "name", models.CharField(max_length=64)),
                migrations.RunSQL("UPDATE roundtrip_ledger SET value = value || '-migrated'")
            ]
            for migration in (initial, remove, restore):
                (folder / (migration.name + ".py")).write_text(MigrationWriter(migration).as_string())
            modules = {config.label: None for config in apps.get_app_configs()}
            modules["console"] = package
            connections.databases[alias] = dict(connection.settings_dict, NAME=str(root / "database.sqlite3"))
            database = connections[alias]
            sys.path.insert(0, directory)
            try:
                with override_settings(MIGRATION_MODULES=modules):
                    if not fresh:
                        executor = MigrationExecutor(database)
                        executor.migrate([("console", initial.name)])
                        state = executor.loader.project_state(("console", initial.name))
                        state.apps.get_model("console", "Ledger").objects.using(alias).create(id=7, value="keep")
                        state.apps.get_model("console", "LedgerEntry").objects.using(alias).create(id=9,
                                                                                                   ledger_id=7,
                                                                                                   key="keep")
                        state.apps.get_model("console", "Preferences").objects.using(alias).create(name="keep", enabled=True)
                        if incompatible:
                            with database.cursor() as cursor:
                                cursor.execute("ALTER TABLE roundtrip_ledger RENAME COLUMN value TO incompatible_value")
                    yield database, folder
            finally:
                database.close()
                del connections[alias]
                del connections.databases[alias]
                sys.path.remove(directory)
                for key in list(sys.modules):
                    if key == package or key.startswith(package + "."):
                        del sys.modules[key]

    def executor(self, database, folder):
        for key in list(sys.modules):
            if key.startswith(folder.name + "."):
                del sys.modules[key]
        importlib.invalidate_caches()
        return MigrationExecutor(database)

    def test_restarts_preserve_model_rows_columns_and_normal_data_operations(self):
        with self.database() as (database, folder):
            self.assertTrue(repair_generated_model_roundtrips(database, ["console"]))
            self.assertNotIn(("console", "0002_incomplete_models"), MigrationRecorder(database).applied_migrations())
            executor = self.executor(database, folder)
            executor.migrate(executor.loader.graph.leaf_nodes())
            state = executor.loader.project_state()
            ledger = state.apps.get_model("console", "Ledger")
            preferences = state.apps.get_model("console", "Preferences")
            self.assertEqual(ledger.objects.using(database.alias).get(id=7).value, "keep-migrated")
            self.assertTrue(preferences.objects.using(database.alias).get(name="keep").enabled)
            self.assertEqual(
                state.apps.get_model("console", "LedgerEntry").objects.using(database.alias).get(id=9).ledger_id, 7)
            self.assertFalse(repair_generated_model_roundtrips(database, ["console"]))
            self.assertTrue(list(folder.glob("*.before-schema-repair")))

    def test_plan_is_read_only_and_incompatible_schema_rejects_before_any_rewrite(self):
        for incompatible in (False, True):
            with self.subTest(incompatible=incompatible), self.database(incompatible=incompatible) as (database, folder):
                before = {p.name: p.read_bytes() for p in folder.glob("*.py")}
                if incompatible:
                    with self.assertRaises(CommandError):
                        repair_generated_model_roundtrips(database, ["console"])
                else:
                    self.assertTrue(repair_generated_model_roundtrips(database, ["console"], dry_run=True))
                self.assertEqual(before, {p.name: p.read_bytes() for p in folder.glob("*.py")})
                self.assertEqual(list(folder.glob("*.before-schema-repair")), [])

    def test_fresh_database_materializes_initial_schema_before_preserved_roundtrips(self):
        with self.database(fresh=True) as (database, folder):
            self.assertTrue(repair_generated_model_roundtrips(database, ["console"]))
            executor = self.executor(database, folder)
            executor.migrate(executor.loader.graph.leaf_nodes())
            self.assertTrue({"roundtrip_ledger", "roundtrip_preferences"}.issubset(database.introspection.table_names()))
