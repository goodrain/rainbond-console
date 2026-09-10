# -*- coding: utf-8 -*-
from unittest import TestCase, mock

from django.db import migrations, models

from console.management.commands.repair_legacy_schema import repair_initial_migration, repair_legacy_schema


class DummyModel(object):
    def __init__(self, table_name):
        self._meta = mock.Mock()
        self._meta.db_table = table_name


class DummyApps(object):
    def __init__(self, models_by_name):
        self.models_by_name = models_by_name

    def get_model(self, app_label, model_name):
        return self.models_by_name[model_name]


class DummyProjectState(object):
    def __init__(self, models_by_name):
        self.apps = DummyApps(models_by_name)


class DummySchemaEditor(object):
    def __init__(self, tables):
        self.created_tables = []
        self.tables = tables

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def create_model(self, model):
        self.created_tables.append(model._meta.db_table)
        self.tables.add(model._meta.db_table)


class DummyIntrospection(object):
    def __init__(self, tables):
        self.tables = tables

    def table_names(self):
        return list(self.tables)


class DummyConnection(object):
    def __init__(self, tables):
        self.introspection = DummyIntrospection(tables)
        self.editor = DummySchemaEditor(tables)

    def schema_editor(self):
        return self.editor


class DummyRecorder(object):
    def __init__(self):
        self.applied = []

    def record_applied(self, app_label, migration_name):
        self.applied.append((app_label, migration_name))


class RepairInitialMigrationTests(TestCase):

    # capability_id: console.rainskills-audit-migration-repair

    def test_existing_tables_are_skipped_and_missing_tables_are_created_before_recording_initial_migration(self):
        migration = mock.Mock()
        migration.name = "0001_initial"
        migration.operations = [
            migrations.CreateModel(
                name="Announcement",
                fields=[("id", models.AutoField(primary_key=True, serialize=False))],
                options={"db_table": "announcement"},
            ),
            migrations.CreateModel(
                name="RuntimeToken",
                fields=[("id", models.AutoField(primary_key=True, serialize=False))],
                options={"db_table": "runtime_token"},
            ),
        ]
        project_state = DummyProjectState({
            "Announcement": DummyModel("announcement"),
            "RuntimeToken": DummyModel("runtime_token"),
        })
        connection = DummyConnection({"announcement"})
        recorder = DummyRecorder()

        result = repair_initial_migration(connection, recorder, "console", migration, project_state)

        self.assertEqual(["announcement"], result.skipped_tables)
        self.assertEqual(["runtime_token"], result.created_tables)
        self.assertEqual(["runtime_token"], connection.editor.created_tables)
        self.assertEqual([("console", "0001_initial")], recorder.applied)

    def test_initial_migration_without_existing_target_tables_is_left_for_normal_migrate(self):
        migration = mock.Mock()
        migration.name = "0001_initial"
        migration.operations = [
            migrations.CreateModel(
                name="Token",
                fields=[("key", models.CharField(max_length=40, primary_key=True, serialize=False))],
                options={"db_table": "authtoken_token"},
            ),
        ]
        project_state = DummyProjectState({"Token": DummyModel("authtoken_token")})
        connection = DummyConnection(set())
        recorder = DummyRecorder()

        result = repair_initial_migration(connection, recorder, "authtoken", migration, project_state)

        self.assertEqual([], result.skipped_tables)
        self.assertEqual([], result.created_tables)
        self.assertEqual([], recorder.applied)

    def test_applied_compressed_initial_migration_repairs_missing_audit_tables_idempotently(self):
        migration = mock.Mock()
        migration.name = "0001_initial"
        migration.operations = [
            migrations.CreateModel(
                name="ExistingModel",
                fields=[("id", models.AutoField(primary_key=True, serialize=False))],
                options={"db_table": "existing_model"},
            ),
            migrations.CreateModel(
                name="RainSkillsSkillSnapshot",
                fields=[("id", models.BigAutoField(primary_key=True, serialize=False))],
                options={"db_table": "rainskills_skill_snapshot"},
            ),
            migrations.CreateModel(
                name="RainSkillsOperation",
                fields=[("id", models.BigAutoField(primary_key=True, serialize=False))],
                options={"db_table": "rainskills_operation"},
            ),
            migrations.CreateModel(
                name="RainSkillsOperationEvent",
                fields=[("id", models.BigAutoField(primary_key=True, serialize=False))],
                options={"db_table": "rainskills_operation_event"},
            ),
        ]
        project_state = DummyProjectState({
            "ExistingModel": DummyModel("existing_model"),
            "RainSkillsSkillSnapshot": DummyModel("rainskills_skill_snapshot"),
            "RainSkillsOperation": DummyModel("rainskills_operation"),
            "RainSkillsOperationEvent": DummyModel("rainskills_operation_event"),
        })
        connection = DummyConnection({"existing_model"})
        recorder = DummyRecorder()

        first = repair_initial_migration(connection, recorder, "console", migration, project_state, record_migration=False)
        second = repair_initial_migration(connection, recorder, "console", migration, project_state, record_migration=False)

        self.assertEqual([
            "rainskills_skill_snapshot",
            "rainskills_operation",
            "rainskills_operation_event",
        ], first.created_tables)
        self.assertEqual([], second.created_tables)
        self.assertEqual([], recorder.applied)

    def test_repair_plan_reports_missing_tables_without_writing_or_recording(self):
        migration = mock.Mock()
        migration.name = "0001_initial"
        migration.operations = [
            migrations.CreateModel(
                name="ExistingModel",
                fields=[("id", models.AutoField(primary_key=True, serialize=False))],
                options={"db_table": "existing_console_table"},
            ),
            migrations.CreateModel(
                name="RainSkillsOperation",
                fields=[("id", models.BigAutoField(primary_key=True, serialize=False))],
                options={"db_table": "rainskills_operation"},
            ),
        ]
        project_state = DummyProjectState({
            "ExistingModel": DummyModel("existing_console_table"),
            "RainSkillsOperation": DummyModel("rainskills_operation"),
        })
        connection = DummyConnection({"existing_console_table"})
        recorder = DummyRecorder()

        result = repair_initial_migration(
            connection,
            recorder,
            "console",
            migration,
            project_state,
            record_migration=False,
            dry_run=True,
        )

        self.assertEqual(["rainskills_operation"], result.created_tables)
        self.assertEqual([], connection.editor.created_tables)
        self.assertEqual([], recorder.applied)

    @mock.patch("console.management.commands.repair_legacy_schema.MigrationRecorder")
    @mock.patch("console.management.commands.repair_legacy_schema.MigrationLoader")
    def test_repair_plan_does_not_create_migration_recorder_schema(self, loader_class, recorder_class):
        loader_class.return_value.disk_migrations = {}
        recorder = recorder_class.return_value
        recorder.applied_migrations.return_value = {}

        self.assertEqual([], repair_legacy_schema(mock.Mock(), ["console"], dry_run=True))

        recorder.ensure_schema.assert_not_called()
