"""Exercise the real loader and executor against startup-generated migration files."""
import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()
from django.apps import apps  # noqa: E402
from django.db import connection, connections, migrations  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402
from django.db.migrations.recorder import MigrationRecorder  # noqa: E402
from django.db.migrations.state import ModelState, ProjectState  # noqa: E402
from django.db.migrations.writer import MigrationWriter  # noqa: E402
from django.test import override_settings  # noqa: E402
from django.core.management.base import CommandError  # noqa: E402
from console.models.main import OAuthServices  # noqa: E402
from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column  # noqa: E402


# capability_id: console.oauth.gitlab-auto-provisioning
class OAuthCompoundMigrationTests(TestCase):
    @contextmanager
    def database(self, with_column=True, failing_sql=False):
        package = "oauth_migration_" + uuid4().hex
        alias = "oauth_compound_test"
        name = "0003_oauthservices_auto_create_user_and_more"
        with TemporaryDirectory(prefix="oauth-compound-") as directory:
            root = Path(directory)
            folder = root / package
            folder.mkdir()
            (folder / "__init__.py").write_text("")
            state = ProjectState()
            state.add_model(ModelState.from_model(OAuthServices))
            state.remove_field("console", "oauthservices", "auto_create_user")
            state.remove_field("console", "oauthservices", "name_scope")
            model = state.models["console", "oauthservices"]
            model.options["constraints"] = []
            model.fields["name"]._unique = True
            initial = migrations.Migration("0001_initial", "console")
            initial.initial = True
            initial.operations = [
                migrations.CreateModel(name="OAuthServices", fields=list(model.fields.items()), options=model.options)
            ]
            migration = migrations.Migration(name, "console")
            migration.dependencies = [("console", "0001_initial")]
            migration.operations = [
                migrations.AddField(model_name="oauthservices", name="name_scope",
                                    field=OAuthServices._meta.get_field("name_scope").clone()),
                migrations.AddField(model_name="oauthservices", name="auto_create_user",
                                    field=OAuthServices._meta.get_field("auto_create_user").clone()),
                migrations.AlterField(model_name="oauthservices", name="name",
                                      field=OAuthServices._meta.get_field("name").clone()),
                migrations.AddConstraint(model_name="oauthservices", constraint=OAuthServices._meta.constraints[0]),
                migrations.RunSQL("SELECT * FROM intentionally_missing_table" if failing_sql else
                                  "UPDATE oauth_service SET name_scope = 'migration-ran'"),
            ]
            (folder / "0001_initial.py").write_text(MigrationWriter(initial).as_string())
            path = folder / (name + ".py")
            path.write_text(MigrationWriter(migration).as_string())
            modules = {config.label: None for config in apps.get_app_configs()}
            modules["console"] = package
            connections.databases[alias] = dict(connection.settings_dict, NAME=str(root / "database.sqlite3"))
            database = connections[alias]
            sys.path.insert(0, directory)
            try:
                with override_settings(MIGRATION_MODULES=modules):
                    MigrationExecutor(database).migrate([("console", "0001_initial")])
                    old_model = state.apps.get_model("console", "OAuthServices")
                    old_model.objects.using(alias).create(name="existing", client_id="", client_secret="", redirect_uri="")
                    if with_column:
                        # Model the previous startup's one-column DDL without
                        # SQLite's table rebuild using today's full model.
                        with database.cursor() as cursor:
                            cursor.execute("ALTER TABLE oauth_service ADD COLUMN auto_create_user bool NOT NULL DEFAULT 0")
                            cursor.execute("UPDATE oauth_service SET auto_create_user = 1")
                    yield database, path, name
            finally:
                database.close()
                del connections[alias]
                del connections.databases[alias]
                sys.path.remove(directory)
                for key in list(sys.modules):
                    if key == package or key.startswith(package + "."):
                        del sys.modules[key]

    def fresh_executor(self, database, path):
        # Drop the loaded module: a fresh migrate process must see the repaired file.
        sys.modules.pop(path.parent.name + "." + path.stem, None)
        importlib.invalidate_caches()
        return MigrationExecutor(database)

    def test_existing_column_preserves_values_and_runs_every_other_operation(self):
        with self.database() as (database, path, name):
            self.assertTrue(repair_oauth_auto_create_user_column(database))
            self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())
            executor = self.fresh_executor(database, path)
            executor.migrate([("console", name)])
            self.assertIn(("console", name), MigrationRecorder(database).applied_migrations())
            model = executor.loader.project_state(("console", name)).apps.get_model("console", "OAuthServices")
            row = model.objects.using(database.alias).get(name="existing")
            self.assertTrue(row.auto_create_user)
            self.assertEqual(row.name_scope, "migration-ran")
            with database.cursor() as cursor:
                constraints = database.introspection.get_constraints(cursor, "oauth_service")
            self.assertTrue(constraints["uk_oauth_name_scope"]["unique"])
            # AlterField must also remove the previous global name constraint.
            another = model.objects.using(database.alias).create(
                name="existing", name_scope="other-scope", client_id="", client_secret="", redirect_uri="")
            self.assertFalse(another.auto_create_user)
            self.assertFalse(repair_oauth_auto_create_user_column(database))
            self.fresh_executor(database, path).migrate([("console", name)])

    def test_plan_does_not_modify_file_or_record_and_missing_column_uses_normal_migrate(self):
        for with_column in (True, False):
            with self.subTest(with_column=with_column), self.database(with_column=with_column) as (database, path, name):
                original = path.read_bytes()
                self.assertEqual(repair_oauth_auto_create_user_column(database, dry_run=True), with_column)
                self.assertEqual(path.read_bytes(), original)
                self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())
                if with_column:
                    repair_oauth_auto_create_user_column(database)
                executor = self.fresh_executor(database, path)
                executor.migrate([("console", name)])
                model = executor.loader.project_state(("console", name)).apps.get_model("console", "OAuthServices")
                row = model.objects.using(database.alias).get(name="existing")
                self.assertEqual(row.auto_create_user, with_column)
                self.assertEqual(row.name_scope, "migration-ran")

    def test_later_failure_never_marks_the_compound_migration_applied(self):
        with self.database(failing_sql=True) as (database, path, name):
            repair_oauth_auto_create_user_column(database)
            with self.assertRaisesRegex(Exception, "intentionally_missing_table"):
                self.fresh_executor(database, path).migrate([("console", name)])
            self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())

    def test_incompatible_column_is_rejected_without_modifying_the_migration(self):
        with self.database(with_column=False) as (database, path, name):
            with database.cursor() as cursor:
                cursor.execute("ALTER TABLE oauth_service ADD COLUMN auto_create_user varchar(32) NOT NULL DEFAULT ''")
            original = path.read_bytes()
            with self.assertRaises(CommandError):
                repair_oauth_auto_create_user_column(database)
            self.assertEqual(path.read_bytes(), original)
            self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())

    def test_mysql_column_check_uses_the_exact_database_type_and_bound_identifiers(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.utils.oauth_migration_repair import oauth_column_matches

        cursor = mock.MagicMock()
        database = mock.MagicMock(vendor="mysql")
        database.cursor.return_value.__enter__.return_value = cursor
        field = mock.Mock(column="auto_create_user", null=False)
        field.db_type.return_value = "bool"
        column = SimpleNamespace(null_ok=False)
        for data_type, expected in (("tinyint(1)", True), ("varchar(32)", False), ("int", False)):
            with self.subTest(data_type=data_type):
                cursor.fetchone.return_value = (data_type,)
                self.assertEqual(oauth_column_matches(database, "oauth_service", column, field), expected)
        self.assertEqual(cursor.execute.call_args.args[1], ["oauth_service", "auto_create_user"])

    def test_failed_file_write_preserves_the_original_migration_and_cleans_up(self):
        from unittest import mock

        with self.database() as (database, path, name):
            original = path.read_bytes()
            with mock.patch("console.utils.oauth_migration_repair.os.replace", side_effect=OSError("read-only filesystem")):
                with self.assertRaises(CommandError):
                    repair_oauth_auto_create_user_column(database)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(".oauth-repair-*")), [])
            self.assertNotIn(("console", name), MigrationRecorder(database).applied_migrations())
