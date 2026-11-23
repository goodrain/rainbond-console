# -*- coding: utf-8 -*-
import copy
import os
import re
import tempfile
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.core.management import CommandError, call_command  # noqa: E402
from django.db import connection, connections, models  # noqa: E402
from django.db.migrations.state import ModelState, ProjectState  # noqa: E402

from console.models.main import ServiceRecycleBin  # noqa: E402


# capability_id: console.component.recycle-schema-upgrade
class RecycleSchemaUpgradeTests(TestCase):
    OLD_LENGTHS = {"version": 20, "setting": 100, "extend_method": 15, "git_url": 200}
    ALIAS = "recycle_schema_upgrade"

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="rainbond-recycle-schema-")
        settings = copy.deepcopy(connection.settings_dict)
        settings["NAME"] = os.path.join(self.directory.name, "recycle.sqlite3")
        connections.databases[self.ALIAS] = settings
        self.connection = connections[self.ALIAS]
        self.addCleanup(self.cleanup_connection)

    def cleanup_connection(self):
        self.connection.close()
        del connections[self.ALIAS]
        connections.databases.pop(self.ALIAS, None)
        self.directory.cleanup()

    def create_schema(self, overrides=None):
        state = ModelState.from_model(ServiceRecycleBin)
        for name, length in self.OLD_LENGTHS.items():
            state.fields[name] = state.fields[name].clone()
            state.fields[name].max_length = length
        for name, field in (overrides or {}).items():
            if field is None:
                state.fields.pop(name)
            else:
                field.set_attributes_from_name(name)
                state.fields[name] = field
        project = ProjectState()
        project.add_model(state)
        model = project.apps.get_model("console", "ServiceRecycleBin")
        with self.connection.schema_editor() as schema:
            schema.create_model(model)
        return model

    def lengths(self):
        with self.connection.cursor() as cursor:
            columns = self.connection.introspection.get_table_description(cursor, ServiceRecycleBin._meta.db_table)
        return {column.name: int(re.fullmatch(r"varchar\((\d+)\)", column.type_code).group(1))
                for column in columns if re.fullmatch(r"varchar\((\d+)\)", column.type_code)}

    def upgrade(self, dry_run=False):
        from console.management.commands.migrate_service_recycle_fields import migrate_service_recycle_fields
        return migrate_service_recycle_fields(self.connection, dry_run=dry_run)

    def test_sqlite_old_schema_accepts_full_lengths_without_rebuilding(self):
        old_model = self.create_schema()
        old_model.objects.using(self.ALIAS).create(
            service_id="existing", tenant_id="tenant", service_key="key", service_alias="web",
            service_region="region", category="application", version="1.0", image="example.invalid/web:1.0",
            setting="settings", extend_method="stateless", git_url="https://example.invalid/repo.git")
        with mock.patch.object(self.connection, "schema_editor") as schema:
            self.assertEqual(self.upgrade(), [])
        schema.assert_not_called()
        self.assertEqual({name: self.lengths()[name] for name in self.OLD_LENGTHS}, self.OLD_LENGTHS)
        existing = ServiceRecycleBin.objects.using(self.ALIAS).get(service_id="existing")
        self.assertEqual((existing.version, existing.setting, existing.extend_method, existing.git_url),
                         ("1.0", "settings", "stateless", "https://example.invalid/repo.git"))
        values = {name: "x" * ServiceRecycleBin._meta.get_field(name).max_length for name in self.OLD_LENGTHS}
        ServiceRecycleBin.objects.using(self.ALIAS).filter(service_id="existing").update(**values)
        existing.refresh_from_db(using=self.ALIAS)
        for name, value in values.items():
            self.assertEqual(getattr(existing, name), value)
        with mock.patch.object(self.connection, "schema_editor") as schema:
            self.assertEqual(self.upgrade(), [])
        schema.assert_not_called()

    def test_plan_does_not_change_old_schema(self):
        self.create_schema()
        with mock.patch.object(self.connection, "schema_editor") as schema:
            self.assertEqual(self.upgrade(dry_run=True), [])
        schema.assert_not_called()
        self.assertEqual({name: self.lengths()[name] for name in self.OLD_LENGTHS}, self.OLD_LENGTHS)

    def test_larger_existing_column_is_not_shrunk(self):
        self.create_schema({"git_url": models.CharField(max_length=4096, null=True, blank=True)})
        self.assertEqual(self.upgrade(), [])
        self.assertEqual(self.lengths()["git_url"], 4096)

    def test_sqlite_unknown_columns_and_values_are_preserved(self):
        self.create_schema()
        with self.connection.cursor() as cursor:
            cursor.execute('ALTER TABLE "tenant_service_recycle_bin" ADD COLUMN "operator_note" TEXT')
        with mock.patch.object(self.connection, "schema_editor") as schema:
            self.assertEqual(self.upgrade(), [])
        schema.assert_not_called()
        with self.connection.cursor() as cursor:
            columns = self.connection.introspection.get_table_description(cursor, ServiceRecycleBin._meta.db_table)
        self.assertIn("operator_note", [column.name for column in columns])

    def test_sqlite_text_storage_does_not_need_ddl(self):
        self.create_schema({"git_url": models.TextField(null=True, blank=True)})
        with mock.patch.object(self.connection, "schema_editor") as schema:
            self.assertEqual(self.upgrade(), [])
        schema.assert_not_called()

    def test_command_accepts_database_alias_and_plan(self):
        self.create_schema()
        with mock.patch.object(self.connection, "schema_editor") as schema:
            call_command("migrate_service_recycle_fields", database=self.ALIAS, plan=True, verbosity=0)
        schema.assert_not_called()

    def test_command_rejects_unknown_database_alias(self):
        with self.assertRaises(CommandError):
            call_command("migrate_service_recycle_fields", database="missing-recycle-alias", verbosity=0)

    def test_missing_table_fails_without_creating_a_table(self):
        with self.assertRaises(CommandError):
            self.upgrade()
        self.assertNotIn(ServiceRecycleBin._meta.db_table, self.connection.introspection.table_names())

    def test_missing_column_is_rejected_before_any_alteration(self):
        self.create_schema({"git_url": None})
        with mock.patch.object(self.connection, "schema_editor") as schema:
            with self.assertRaises(CommandError):
                self.upgrade()
        schema.assert_not_called()

    def test_non_string_column_is_rejected_before_any_alteration(self):
        self.create_schema({"git_url": models.IntegerField(null=True)})
        with mock.patch.object(self.connection, "schema_editor") as schema:
            with self.assertRaises(CommandError):
                self.upgrade()
        schema.assert_not_called()

    def test_changed_nullability_is_rejected_before_any_alteration(self):
        self.create_schema({"git_url": models.CharField(max_length=200, null=False)})
        with mock.patch.object(self.connection, "schema_editor") as schema:
            with self.assertRaises(CommandError):
                self.upgrade()
        schema.assert_not_called()


# capability_id: console.component.recycle-schema-upgrade
class RecycleMySQLUpgradePlanTests(TestCase):
    def setUp(self):
        self.connection = mock.MagicMock(vendor="mysql")
        self.connection.introspection.table_names.return_value = [ServiceRecycleBin._meta.db_table]
        self.columns = [SimpleNamespace(
            name=name, null_ok=ServiceRecycleBin._meta.get_field(name).null,
            data_type="varchar", internal_size=length, default=None, collation=None,
        ) for name, length in RecycleSchemaUpgradeTests.OLD_LENGTHS.items()]
        self.connection.introspection.get_table_description.return_value = self.columns

    def upgrade(self, dry_run=False):
        from console.management.commands.migrate_service_recycle_fields import migrate_service_recycle_fields
        return migrate_service_recycle_fields(self.connection, dry_run=dry_run)

    def test_mysql_plan_preflights_all_columns_without_schema_writes(self):
        self.assertEqual(set(self.upgrade(dry_run=True)), set(RecycleSchemaUpgradeTests.OLD_LENGTHS))
        self.connection.schema_editor.assert_not_called()

    def test_mysql_alters_only_narrow_columns_and_preserves_default_and_collation(self):
        self.columns[-1].internal_size = 4096
        self.columns[2].default = "stateless"
        self.columns[2].collation = "utf8mb4_bin"
        self.assertEqual(self.upgrade(), ["version", "setting", "extend_method"])
        calls = self.connection.schema_editor.return_value.__enter__.return_value.alter_field.call_args_list
        self.assertEqual(len(calls), 3)
        for call in calls:
            model, old, new = call.args
            self.assertIs(model, ServiceRecycleBin)
            self.assertLess(old.max_length, new.max_length)
            self.assertEqual(old.null, new.null)
            self.assertEqual(old.db_collation, new.db_collation)
            if old.name == "extend_method":
                self.assertEqual((old.db_default, new.db_default), ("stateless", "stateless"))

    def test_mysql_checks_every_column_before_applying_first_change(self):
        self.columns[-1].data_type = "integer"
        with self.assertRaises(CommandError):
            self.upgrade()
        self.connection.schema_editor.assert_not_called()

    def test_mysql_unbounded_text_or_sufficient_varchar_is_unchanged(self):
        for column in self.columns:
            column.internal_size = 65535
        self.columns[0].data_type = "text"
        self.assertEqual(self.upgrade(), [])
        self.connection.schema_editor.assert_not_called()

    def test_unsupported_backend_is_rejected_without_introspection(self):
        self.connection.vendor = "unsupported"
        with self.assertRaises(CommandError):
            self.upgrade()
        self.connection.introspection.table_names.assert_not_called()
