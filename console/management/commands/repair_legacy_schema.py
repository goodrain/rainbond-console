# -*- coding: utf-8 -*-
from __future__ import print_function

from collections import namedtuple

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, migrations
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


DEFAULT_APP_LABELS = ("authtoken", "www", "console")
RepairResult = namedtuple("RepairResult", ("app_label", "migration_name", "skipped_tables", "created_tables", "recorded"))


def is_initial_migration(app_label, migration):
    initial = getattr(migration, "initial", None)
    if initial is True:
        return True
    if initial is False:
        return False
    return not any(dependency[0] == app_label for dependency in migration.dependencies)


def get_initial_migration_keys(loader, app_labels):
    app_label_set = set(app_labels)
    migration_keys = []
    for key, migration in loader.disk_migrations.items():
        app_label, _ = key
        if app_label in app_label_set and is_initial_migration(app_label, migration):
            migration_keys.append(key)
    return sorted(migration_keys)


def get_create_model_operations(migration):
    return [operation for operation in migration.operations if isinstance(operation, migrations.CreateModel)]


def repair_initial_migration(connection,
                             recorder,
                             app_label,
                             migration,
                             project_state,
                             record_migration=True,
                             dry_run=False):
    create_model_operations = get_create_model_operations(migration)
    if not create_model_operations:
        return RepairResult(app_label, migration.name, [], [], False)

    existing_tables = set(connection.introspection.table_names())
    target_models = []
    target_tables = []
    for operation in create_model_operations:
        model = project_state.apps.get_model(app_label, operation.name)
        target_models.append(model)
        target_tables.append(model._meta.db_table)

    if not existing_tables.intersection(target_tables):
        return RepairResult(app_label, migration.name, [], [], False)

    skipped_tables = []
    created_tables = []
    missing_models = []
    for model, table_name in zip(target_models, target_tables):
        if table_name in existing_tables:
            skipped_tables.append(table_name)
            continue
        missing_models.append((model, table_name))
        created_tables.append(table_name)

    if not dry_run and missing_models:
        with connection.schema_editor() as schema_editor:
            for model, table_name in missing_models:
                schema_editor.create_model(model)
                existing_tables.add(table_name)

    recorded = bool(record_migration and not dry_run)
    if recorded:
        recorder.record_applied(app_label, migration.name)
    return RepairResult(app_label, migration.name, skipped_tables, created_tables, recorded)


def repair_legacy_schema(connection, app_labels, dry_run=False):
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    recorder = MigrationRecorder(connection)
    if not dry_run:
        recorder.ensure_schema()
    applied_migrations = recorder.applied_migrations()
    results = []

    for key in get_initial_migration_keys(loader, app_labels):
        app_label, migration_name = key
        migration = loader.disk_migrations[key]
        project_state = loader.project_state(key, at_end=True)
        result = repair_initial_migration(
            connection,
            recorder,
            app_label,
            migration,
            project_state,
            record_migration=key not in applied_migrations,
            dry_run=dry_run,
        )
        if result.recorded or result.created_tables:
            results.append(result)

    return results


def repair_oauth_auto_create_user_column(connection, dry_run=False):
    """Reconcile the OAuth field without racing startup's generated AddField migration."""
    from console.models.main import OAuthServices

    table = OAuthServices._meta.db_table
    if table not in connection.introspection.table_names():
        return False
    field = OAuthServices._meta.get_field("auto_create_user")
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table)
    existing_column = next((column for column in columns if column.name == field.column), None)
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    pending = [
        (key, migration) for key, migration in loader.disk_migrations.items()
        if key[0] == "console" and key not in loader.applied_migrations
        and any(isinstance(operation, migrations.AddField) and operation.model_name.lower() == "oauthservices"
                and operation.name == field.name for operation in migration.operations)
    ]
    if pending:
        if existing_column is None:
            # Normal migrate owns this column; pre-adding it would fail with duplicate column.
            return False
        # Recover a prior startup that added the column but did not record its migration.
        # Never mark a compound migration, a changed definition, or missing dependencies as applied.
        for key, migration in pending:
            operation = migration.operations[0]
            if (len(pending) != 1 or len(migration.operations) != 1
                    or operation.field.deconstruct()[1:] != field.deconstruct()[1:]
                    or not set(migration.dependencies).issubset(loader.applied_migrations)
                    or existing_column.null_ok != field.null):
                raise CommandError("Cannot safely reconcile existing OAuth column for migration {}.{}".format(*key))
        if not dry_run:
            MigrationRecorder(connection).record_applied(*pending[0][0])
        return True
    if existing_column is not None:
        return False
    if not dry_run:
        with connection.schema_editor() as schema_editor:
            schema_editor.add_field(OAuthServices, field)
    return True


class Command(BaseCommand):
    help = "Repair legacy databases whose initial tables exist but django_migrations records are missing."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--apps",
            default=",".join(DEFAULT_APP_LABELS),
            help="Comma-separated app labels to repair. Defaults to authtoken,www,console.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Database alias to inspect and repair.",
        )
        parser.add_argument(
            "--plan",
            action="store_true",
            help="Report missing initial-migration tables without changing the database.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        if database not in connections.databases:
            raise CommandError('Unknown database alias "{}"'.format(database))

        app_labels = [label.strip() for label in options["apps"].split(",") if label.strip()]
        if not app_labels:
            raise CommandError("At least one app label is required")

        plan = bool(options["plan"])
        results = repair_legacy_schema(connections[database], app_labels, dry_run=plan)
        if "console" in app_labels and repair_oauth_auto_create_user_column(connections[database], dry_run=plan):
            self.stdout.write("{} console.oauth_service.auto_create_user".format("Would repair" if plan else "Repaired"))
        if not results:
            self.stdout.write("No legacy initial migrations needed repair")
            return

        for result in results:
            self.stdout.write(
                "{0} {1}.{2}: skipped existing tables [{3}], {4} missing tables [{5}]".format(
                    "Planned" if plan else "Repaired",
                    result.app_label,
                    result.migration_name,
                    ", ".join(result.skipped_tables) or "-",
                    "would create" if plan else "created",
                    ", ".join(result.created_tables) or "-",
                ))
