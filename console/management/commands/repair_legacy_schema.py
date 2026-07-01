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


def repair_initial_migration(connection, recorder, app_label, migration, project_state):
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
    with connection.schema_editor() as schema_editor:
        for model, table_name in zip(target_models, target_tables):
            if table_name in existing_tables:
                skipped_tables.append(table_name)
                continue
            schema_editor.create_model(model)
            existing_tables.add(table_name)
            created_tables.append(table_name)

    recorder.record_applied(app_label, migration.name)
    return RepairResult(app_label, migration.name, skipped_tables, created_tables, True)


def repair_legacy_schema(connection, app_labels):
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    recorder = MigrationRecorder(connection)
    recorder.ensure_schema()
    applied_migrations = recorder.applied_migrations()
    results = []

    for key in get_initial_migration_keys(loader, app_labels):
        app_label, migration_name = key
        if key in applied_migrations:
            continue
        migration = loader.disk_migrations[key]
        project_state = loader.project_state(key, at_end=True)
        result = repair_initial_migration(connection, recorder, app_label, migration, project_state)
        if result.recorded:
            results.append(result)

    return results


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

    def handle(self, *args, **options):
        database = options["database"]
        if database not in connections.databases:
            raise CommandError('Unknown database alias "{}"'.format(database))

        app_labels = [label.strip() for label in options["apps"].split(",") if label.strip()]
        if not app_labels:
            raise CommandError("At least one app label is required")

        results = repair_legacy_schema(connections[database], app_labels)
        if not results:
            self.stdout.write("No legacy initial migrations needed repair")
            return

        for result in results:
            self.stdout.write(
                "Repaired {0}.{1}: skipped existing tables [{2}], created missing tables [{3}]".format(
                    result.app_label,
                    result.migration_name,
                    ", ".join(result.skipped_tables) or "-",
                    ", ".join(result.created_tables) or "-",
                ))
