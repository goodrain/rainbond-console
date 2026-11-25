# -*- coding: utf-8 -*-
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections

REQUIRED_TABLES = (
    "mcp_device_authorization",
    "mcp_device_authorization_rate_limit",
    "rainskills_skill_snapshot",
    "rainskills_operation",
    "rainskills_operation_event",
    "delivery_template",
    "delivery_template_version",
    "delivery_task",
    "delivery_task_item",
    "delivery_listing_request",
    "team_creation_application",
)


def find_missing_required_tables(connection):
    existing_tables = set(connection.introspection.table_names())
    return [table for table in REQUIRED_TABLES if table not in existing_tables]


def get_required_models():
    models = {model._meta.db_table: model for model in apps.get_models()}
    missing = [table for table in REQUIRED_TABLES if table not in models]
    if missing:
        raise CommandError("Required database models are not registered: {}. "
                           "Check model imports before generating migrations.".format(", ".join(missing)))
    return [models[table] for table in REQUIRED_TABLES]


def find_missing_required_columns(connection):
    models = get_required_models()
    tables = set(connection.introspection.table_names())
    missing = []
    with connection.cursor() as cursor:
        for model in models:
            table = model._meta.db_table
            if table not in tables:
                continue
            columns = {column.name for column in connection.introspection.get_table_description(cursor, table)}
            missing.extend(
                "{}.{}".format(table, field.column) for field in model._meta.local_fields if field.column not in columns)
    return missing


class Command(BaseCommand):
    help = "Verify required model registration before generating migrations, and tables and columns after migrating."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--models-only",
            action="store_true",
            help="Verify model imports without accessing the database, before generating migrations.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Database alias to verify.",
        )

    def handle(self, *args, **options):
        get_required_models()
        if options.get("models_only"):
            self.stdout.write("Required database models verified")
            return
        database = options["database"]
        if database not in connections.databases:
            raise CommandError('Unknown database alias "{}"'.format(database))
        missing_tables = find_missing_required_tables(connections[database])
        if missing_tables:
            raise CommandError("Missing required database tables after migration: {}".format(", ".join(missing_tables)))
        missing_columns = find_missing_required_columns(connections[database])
        if missing_columns:
            raise CommandError(
                "Missing required database columns after migration: {}. "
                "Restore missing data from a verified backup before retrying; do not fake migrations or drop tables.".format(
                    ", ".join(missing_columns)))
        self.stdout.write("Required database schema verified")
