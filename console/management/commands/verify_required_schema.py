# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections


REQUIRED_TABLES = (
    "mcp_device_authorization",
    "mcp_device_authorization_rate_limit",
    "rainskills_skill_snapshot",
    "rainskills_operation",
    "rainskills_operation_event",
)


def find_missing_required_tables(connection):
    existing_tables = set(connection.introspection.table_names())
    return [table for table in REQUIRED_TABLES if table not in existing_tables]


class Command(BaseCommand):
    help = "Fail startup when critical post-migration tables are missing."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Database alias to verify.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        if database not in connections.databases:
            raise CommandError('Unknown database alias "{}"'.format(database))
        missing_tables = find_missing_required_tables(connections[database])
        if missing_tables:
            raise CommandError(
                "Missing required database tables after migration: {}".format(
                    ", ".join(missing_tables)))
        self.stdout.write("Required database schema verified")
