# -*- coding: utf-8 -*-
"""Widen legacy recycle fields after a generated initial migration is fake-applied."""
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections

from console.models.main import ServiceRecycleBin


FIELD_NAMES = ("version", "setting", "extend_method", "git_url")


def migrate_service_recycle_fields(connection, dry_run=False):
    if connection.vendor not in ("mysql", "sqlite"):
        raise CommandError("Unsupported backend for service recycle fields")
    table = ServiceRecycleBin._meta.db_table
    if table not in connection.introspection.table_names():
        raise CommandError("Service recycle table is missing")
    with connection.cursor() as cursor:
        columns = {column.name: column for column in connection.introspection.get_table_description(cursor, table)}
    changes = []
    for name in FIELD_NAMES:
        field = ServiceRecycleBin._meta.get_field(name)
        column = columns.get(field.column)
        if column is None:
            raise CommandError("Service recycle column is missing: " + name)
        if column.null_ok != field.null:
            raise CommandError("Service recycle column nullability differs: " + name)
        if connection.vendor == "sqlite":
            declared_type = column.type_code.lower().strip()
            if declared_type == "text":
                continue
            if not re.fullmatch(r"varchar\((\d+)\)", declared_type):
                raise CommandError("Service recycle column is not varchar: " + name)
            # SQLite does not enforce varchar lengths. Avoid rebuilding the
            # whole table, which could shrink wider or remove unknown columns.
            continue
        else:
            declared_type = column.data_type.lower()
            if (declared_type.endswith("text") and isinstance(column.internal_size, int)
                    and column.internal_size >= field.max_length):
                continue
            if declared_type != "varchar" or not isinstance(column.internal_size, int):
                raise CommandError("Service recycle column is not varchar: " + name)
            length = column.internal_size
        if length >= field.max_length:
            continue
        old_field = field.clone()
        new_field = field.clone()
        for candidate in (old_field, new_field):
            candidate.set_attributes_from_name(field.name)
            candidate.model = ServiceRecycleBin
            candidate.db_collation = getattr(column, "collation", None)
            if column.default is not None:
                candidate.db_default = column.default
        old_field.max_length = length
        changes.append((name, old_field, new_field))
    if changes and not dry_run:
        with connection.schema_editor() as schema:
            for _, old_field, new_field in changes:
                schema.alter_field(ServiceRecycleBin, old_field, new_field)
    return [name for name, _, _ in changes]


class Command(BaseCommand):
    help = "Widen service recycle fields to match supported component string lengths."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--database", default=DEFAULT_DB_ALIAS)
        parser.add_argument("--plan", action="store_true")

    def handle(self, *args, **options):
        alias = options["database"]
        if alias not in connections.databases:
            raise CommandError('Unknown database alias "{}"'.format(alias))
        changed = migrate_service_recycle_fields(connections[alias], dry_run=options["plan"])
        self.stdout.write("Service recycle fields: {}".format(
            "upgrade planned" if changed and options["plan"] else "upgraded" if changed else "up to date"))
