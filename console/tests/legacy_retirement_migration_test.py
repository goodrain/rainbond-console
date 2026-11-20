"""Execute generated historical-retirement migrations with preserved SQL data."""
import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
from uuid import uuid4

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()
from django.apps import apps  # noqa: E402
from django.core.management.base import CommandError  # noqa: E402
from django.db import connection, connections, migrations, models  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402
from django.db.migrations.recorder import MigrationRecorder  # noqa: E402
from django.db.migrations.writer import MigrationWriter  # noqa: E402
from django.test import override_settings  # noqa: E402

from console.utils.legacy_retirement_migration import preserve_legacy_retirements  # noqa: E402


# capability_id: console.schema.preserve-legacy-retirements
class LegacyRetirementMigrationTests(TestCase):
    @contextmanager
    def database(self, applied=True, failure=False, historical_graph=True, database_settings=None):
        package = "retirement_" + uuid4().hex
        alias = "retirement_test"
        name = "0042_retire_legacy_and_more"
        with TemporaryDirectory(prefix="console-retirement-") as directory:
            root = Path(directory)
            folder = root / package
            folder.mkdir()
            (folder / "__init__.py").write_text("")

            def pk():
                return ("id", models.CharField(max_length=32, primary_key=True, serialize=False))

            def foreign(target, null=False):
                return models.ForeignKey("console." + target, on_delete=models.CASCADE, null=null)

            definitions = [
                ("DeliveryTemplate", "delivery_template", [pk(), ("label", models.TextField())], {}),
                ("DeliveryTemplateVersion", "delivery_template_version",
                 [pk(), ("template", foreign("DeliveryTemplate")), ("version", models.CharField(max_length=32))],
                 {"constraints": [models.UniqueConstraint(fields=("template", "version"), name="fixture_template_version")]}),
                ("DeliveryTask", "delivery_task",
                 [pk(), ("template", foreign("DeliveryTemplate")), ("version", foreign("DeliveryTemplateVersion", True))], {}),
                ("DeliveryTaskItem", "delivery_task_item",
                 [pk(), ("task", foreign("DeliveryTask")), ("key", models.CharField(max_length=32))],
                 {"constraints": [models.UniqueConstraint(fields=("task", "key"), name="fixture_task_key")]}),
                ("DeliveryListingRequest", "delivery_listing_request",
                 [pk(), ("publication_task", foreign("DeliveryTask", True)),
                  ("version", foreign("DeliveryTemplateVersion"))], {}),
                ("TeamApplication", "team_creation_application", [pk(), ("label", models.TextField())], {}),
                ("ServiceRecycleBin", "tenant_service_recycle_bin",
                 [pk(), ("recovery_metadata", models.JSONField(default=dict))], {}),
                ("RainbondCenterAppVersion", "rainbond_center_app_version",
                 [pk(), ("app_version_info", models.TextField())], {}),
                ("OrdinaryModel", "ordinary_model",
                 [pk(), ("obsolete", models.TextField()), ("label", models.TextField())], {}),
                ("OrdinaryRetiredModel", "ordinary_retired_model", [pk()], {}),
            ]
            initial = migrations.Migration("0001_initial", "console")
            initial.initial = True
            initial.operations = [migrations.CreateModel(name=n, fields=f, options={"db_table": table, **opts})
                                  for n, table, f, opts in definitions]
            pending = migrations.Migration(name, "console")
            pending.dependencies = [("console", initial.name)]
            pending.operations = [
                migrations.RemoveField("deliverylistingrequest", "publication_task"),
                migrations.RemoveField("deliverylistingrequest", "version"),
                migrations.RemoveField("deliverytask", "template"),
                migrations.RemoveField("deliverytask", "version"),
                migrations.RemoveField("deliverytaskitem", "task"),
                migrations.RemoveField("deliverytemplateversion", "template"),
                migrations.DeleteModel("TeamApplication"),
                migrations.RemoveField("servicerecyclebin", "recovery_metadata"),
                migrations.AlterField("rainbondcenterappversion", "app_version_info", models.CharField(max_length=255)),
                *[migrations.DeleteModel(n) for n in (
                    "DeliveryListingRequest", "DeliveryTask", "DeliveryTaskItem", "DeliveryTemplate",
                    "DeliveryTemplateVersion")],
                migrations.RemoveField("ordinarymodel", "obsolete"),
                migrations.DeleteModel("OrdinaryRetiredModel"),
                migrations.AddField("ordinarymodel", "marker", models.CharField(max_length=32, default="")),
                migrations.RunSQL("SELECT * FROM intentionally_missing_table" if failure else
                                  "UPDATE ordinary_model SET marker = 'executed'"),
            ]
            if not historical_graph:
                initial.operations = [op for op in initial.operations if op.name.startswith("Ordinary")]
                pending.operations = pending.operations[14:]
            (folder / "0001_initial.py").write_text(MigrationWriter(initial).as_string())
            path = folder / (name + ".py")
            path.write_text(MigrationWriter(pending).as_string())
            modules = {config.label: None for config in apps.get_app_configs()}
            modules["console"] = package
            settings = dict(connection.settings_dict, NAME=str(root / "database.sqlite3"))
            settings.update(database_settings or {})
            connections.databases[alias] = settings
            database = connections[alias]
            own_tables = {table for _, table, _, _ in definitions} | {"django_migrations"}
            empty_explicit_database = False
            sys.path.insert(0, directory)
            try:
                with override_settings(MIGRATION_MODULES=modules):
                    if database_settings:
                        self.assertEqual(database.introspection.table_names(), [], "explicit test database must be empty")
                        empty_explicit_database = True
                    if applied:
                        executor = MigrationExecutor(database)
                        executor.migrate([("console", initial.name)])
                        historical = executor.loader.project_state(("console", initial.name)).apps
                        historical.get_model("console", "DeliveryTemplate").objects.using(alias).create(id="t", label="kept")
                        historical.get_model("console", "DeliveryTemplateVersion").objects.using(alias).create(
                            id="v", template_id="t", version="1")
                        historical.get_model("console", "DeliveryTask").objects.using(alias).create(
                            id="task", template_id="t", version_id="v")
                        historical.get_model("console", "DeliveryTaskItem").objects.using(alias).create(
                            id="item", task_id="task", key="source")
                        historical.get_model("console", "DeliveryListingRequest").objects.using(alias).create(
                            id="listing", publication_task_id="task", version_id="v")
                        historical.get_model("console", "ServiceRecycleBin").objects.using(alias).create(
                            id="bin", recovery_metadata={"preserve": "original"})
                        historical.get_model("console", "RainbondCenterAppVersion").objects.using(alias).create(
                            id="version", app_version_info="x" * 1000)
                        historical.get_model("console", "OrdinaryModel").objects.using(alias).create(
                            id="ordinary", obsolete="delete normally", label="existing")
                    yield database, path, name
            finally:
                if empty_explicit_database:
                    with database.constraint_checks_disabled(), database.cursor() as cursor:
                        for table in sorted(own_tables.intersection(database.introspection.table_names())):
                            cursor.execute("DROP TABLE {}".format(database.ops.quote_name(table)))
                database.close()
                del connections[alias]
                del connections.databases[alias]
                sys.path.remove(directory)
                for key in list(sys.modules):
                    if key == package or key.startswith(package + "."):
                        del sys.modules[key]

    def reload_executor(self, database, path):
        sys.modules.pop(path.parent.name + "." + path.stem, None)
        importlib.invalidate_caches()
        return MigrationExecutor(database)

    def columns(self, database, table):
        with database.cursor() as cursor:
            return {field.name for field in database.introspection.get_table_description(cursor, table)}

    def test_preserves_rows_relations_json_and_long_text_and_executes_other_operations(self):
        with self.database() as (database, path, name):
            self.assertTrue(preserve_legacy_retirements(database))
            self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())
            executor = self.reload_executor(database, path)
            executor.migrate([("console", name)])
            self.assertIn(("console", name), MigrationRecorder(database).applied_migrations())
            with database.cursor() as cursor:
                cursor.execute("SELECT publication_task_id, version_id FROM delivery_listing_request WHERE id='listing'")
                self.assertEqual(cursor.fetchone(), ("task", "v"))
                cursor.execute("SELECT template_id, version_id FROM delivery_task WHERE id='task'")
                self.assertEqual(cursor.fetchone(), ("t", "v"))
                cursor.execute("SELECT recovery_metadata FROM tenant_service_recycle_bin")
                self.assertIn("original", cursor.fetchone()[0])
                cursor.execute("SELECT app_version_info FROM rainbond_center_app_version")
                self.assertEqual(cursor.fetchone()[0], "x" * 1000)
                cursor.execute("SELECT marker FROM ordinary_model")
                self.assertEqual(cursor.fetchone()[0], "executed")
                constraints = database.introspection.get_constraints(cursor, "delivery_task_item")
            self.assertTrue(any(c["foreign_key"] == ("delivery_task", "id") for c in constraints.values()))
            self.assertNotIn("obsolete", self.columns(database, "ordinary_model"))
            self.assertNotIn("ordinary_retired_model", database.introspection.table_names())
            final = executor.loader.project_state(("console", name))
            self.assertNotIn(("console", "deliverytask"), final.models)
            self.assertNotIn("recovery_metadata", final.models["console", "servicerecyclebin"].fields)
            self.assertFalse(preserve_legacy_retirements(database))
            self.reload_executor(database, path).migrate([("console", name)])

    def test_plan_is_zero_write_and_repeated_pending_repair_is_idempotent(self):
        with self.database() as (database, path, name):
            original = path.read_bytes()
            before = MigrationRecorder(database).applied_migrations()
            with mock.patch.object(database, "schema_editor", side_effect=AssertionError("plan performs DDL")):
                self.assertTrue(preserve_legacy_retirements(database, dry_run=True))
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(MigrationRecorder(database).applied_migrations(), before)
            self.assertTrue(preserve_legacy_retirements(database))
            wrapped = path.read_bytes()
            self.assertFalse(preserve_legacy_retirements(database))
            self.assertEqual(path.read_bytes(), wrapped)

    def test_missing_column_aborts_before_any_file_ddl_or_migration_record_change(self):
        with self.database() as (database, path, name):
            executor = MigrationExecutor(database)
            model = executor.loader.project_state(("console", "0001_initial")).apps.get_model(
                "console", "DeliveryListingRequest")
            with database.schema_editor() as editor:
                editor.remove_field(model, model._meta.get_field("publication_task"))
            original = path.read_bytes()
            before = MigrationRecorder(database).applied_migrations()
            for dry_run in (True, False):
                with self.subTest(plan=dry_run), self.assertRaisesRegex(CommandError, "restore.*delivery_listing_request"):
                    preserve_legacy_retirements(database, dry_run=dry_run)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(MigrationRecorder(database).applied_migrations(), before)

    def test_missing_foreign_key_is_not_hidden_even_after_file_was_wrapped(self):
        with self.database() as (database, path, name):
            preserve_legacy_retirements(database)
            original = path.read_bytes()
            introspect = database.introspection.get_constraints

            def without_foreign_key(cursor, table):
                return {key: value for key, value in introspect(cursor, table).items()
                        if not (table == "delivery_task_item" and value["foreign_key"])}

            with mock.patch.object(database.introspection, "get_constraints", side_effect=without_foreign_key):
                with self.assertRaisesRegex(CommandError, "restore.*delivery_task_item"):
                    preserve_legacy_retirements(database)
            self.assertEqual(path.read_bytes(), original)

    def test_fresh_database_uses_normal_migrate_without_requiring_legacy_tables(self):
        with self.database(applied=False, historical_graph=False) as (database, path, name):
            original = path.read_bytes()
            self.assertFalse(preserve_legacy_retirements(database))
            self.assertEqual(path.read_bytes(), original)
            self.reload_executor(database, path).migrate([("console", name)])
            self.assertNotIn("delivery_task", database.introspection.table_names())

    def test_empty_database_with_old_migration_files_preserves_future_historical_tables(self):
        with self.database(applied=False) as (database, path, name):
            self.assertTrue(preserve_legacy_retirements(database))
            self.reload_executor(database, path).migrate([("console", name)])
            self.assertIn("delivery_task", database.introspection.table_names())
            self.assertFalse(preserve_legacy_retirements(database))

    def test_later_real_operation_failure_does_not_fake_compound_migration(self):
        with self.database(failure=True) as (database, path, name):
            preserve_legacy_retirements(database)
            with self.assertRaisesRegex(Exception, "intentionally_missing_table"):
                self.reload_executor(database, path).migrate([("console", name)])
            self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())

    def test_failed_atomic_replace_keeps_original_file_and_cleans_temporary(self):
        with self.database() as (database, path, name):
            original = path.read_bytes()
            with mock.patch("console.utils.legacy_retirement_migration.os.replace", side_effect=OSError("fixture")):
                with self.assertRaises(CommandError):
                    preserve_legacy_retirements(database)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(".legacy-retirement-*")), [])

    def test_management_command_checks_damage_before_initial_or_oauth_repairs(self):
        from console.management.commands.repair_legacy_schema import Command

        with self.database() as (database, path, name):
            with database.cursor() as cursor:
                cursor.execute("DROP TABLE delivery_listing_request")
            with mock.patch("console.management.commands.repair_legacy_schema.repair_legacy_schema") as initial:
                with self.assertRaisesRegex(CommandError, "restore.*delivery_listing_request"):
                    Command().handle(database=database.alias, apps="console", plan=False)
                initial.assert_not_called()

    def test_existing_history_with_unapplied_prerequisite_stops_without_rewriting(self):
        with self.database() as (database, path, name):
            intermediate = migrations.Migration("0002_waiting_for_parent", "console")
            intermediate.dependencies = [("console", "0001_initial")]
            (path.parent / "0002_waiting_for_parent.py").write_text(MigrationWriter(intermediate).as_string())
            original = path.read_text().replace("0001_initial", "0002_waiting_for_parent")
            path.write_text(original)
            self.reload_executor(database, path)
            with self.assertRaisesRegex(CommandError, "applied dependencies"):
                preserve_legacy_retirements(database)
            self.assertEqual(path.read_text(), original)
            self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())

    def test_symlinked_migration_is_rejected_without_modifying_its_target(self):
        with self.database() as (database, path, name):
            original = path.read_bytes()
            target = path.parent.parent / "external.py"
            path.rename(target)
            path.symlink_to(target)
            with self.assertRaisesRegex(CommandError, "safely rewrite"):
                preserve_legacy_retirements(database)
            self.assertTrue(path.is_symlink())
            self.assertEqual(target.read_bytes(), original)

    def test_unexpected_source_edit_is_not_overwritten(self):
        with self.database() as (database, path, name):
            # The loader already imported this module while applying the initial
            # migration. Detect a later operation edit rather than using stale code.
            edited = path.read_text().replace("name='publication_task'", "name='unexpected_field'")
            path.write_text(edited)
            with self.assertRaisesRegex(CommandError, "source differs"):
                preserve_legacy_retirements(database)
            self.assertEqual(path.read_text(), edited)

    def test_already_narrowed_text_type_requires_recovery_before_preservation(self):
        with self.database() as (database, path, name):
            executor = MigrationExecutor(database)
            model = executor.loader.project_state(("console", "0001_initial")).apps.get_model(
                "console", "RainbondCenterAppVersion")
            old = model._meta.get_field("app_version_info")
            # Model an existing narrowed schema; strict MySQL would reject
            # creating that fixture while its original 1000-character value remains.
            model.objects.using(database.alias).update(app_version_info="already-short")
            narrowed = models.CharField(max_length=255)
            narrowed.set_attributes_from_name("app_version_info")
            narrowed.model = model
            with database.schema_editor() as editor:
                editor.alter_field(model, old, narrowed)
            original = path.read_bytes()
            with self.assertRaisesRegex(CommandError, "restore.*rainbond_center_app_version"):
                preserve_legacy_retirements(database)
            self.assertEqual(path.read_bytes(), original)

    def test_missing_historical_composite_uniqueness_is_not_hidden(self):
        with self.database() as (database, path, name):
            original = path.read_bytes()
            introspect = database.introspection.get_constraints

            def without_unique(cursor, table):
                return {key: value for key, value in introspect(cursor, table).items()
                        if not (table == "delivery_task_item" and value["unique"])}

            with mock.patch.object(database.introspection, "get_constraints", side_effect=without_unique):
                with self.assertRaisesRegex(CommandError, "restore.*delivery_task_item"):
                    preserve_legacy_retirements(database)
            self.assertEqual(path.read_bytes(), original)
