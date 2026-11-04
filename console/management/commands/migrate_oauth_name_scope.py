# -*- coding: utf-8 -*-
"""Upgrade OAuth naming even when startup fake-applies a generated initial migration."""
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections

from console.models.main import OAuthServices


def migrate_oauth_name_scope(connection, dry_run=False):
    table = OAuthServices._meta.db_table
    if table not in connection.introspection.table_names():
        raise CommandError("OAuth service table is missing")
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table)
        constraints = connection.introspection.get_constraints(cursor, table)
    scope_field = OAuthServices._meta.get_field("name_scope")
    missing_column = scope_field.column not in {column.name for column in columns}
    old_unique = any(item["unique"] and item["columns"] == ["name"] for item in constraints.values())
    scoped_unique = any(item["unique"] and item["columns"] == ["name_scope", "name"] for item in constraints.values())
    changed = missing_column or old_unique or not scoped_unique
    if missing_column:
        if dry_run:
            return True
        with connection.schema_editor() as schema:
            schema.add_field(OAuthServices, scope_field)

    rows = OAuthServices.objects.using(connection.alias)
    for row in rows.only("ID", "name_scope", "eid", "user_id", "system", "is_deleted", "oauth_type").iterator():
        scope = OAuthServices.get_name_scope(row.eid, row.user_id, row.system, row.is_deleted, row.oauth_type)
        if row.name_scope != scope:
            changed = True
            if not dry_run:
                rows.filter(pk=row.pk).update(name_scope=scope)
    if dry_run:
        return changed
    # Install scoped protection before removing the old global constraint.
    if not scoped_unique:
        with connection.schema_editor() as schema:
            schema.add_constraint(OAuthServices, OAuthServices._meta.constraints[0])
    if old_unique:
        field = OAuthServices._meta.get_field("name")
        old_field = field.clone()
        old_field.set_attributes_from_name(field.name)
        old_field.model = OAuthServices
        old_field._unique = True
        with connection.schema_editor() as schema:
            schema.alter_field(OAuthServices, old_field, field)
    return changed


class Command(BaseCommand):
    help = "Upgrade OAuth configuration names from global uniqueness to ownership scope."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--database", default=DEFAULT_DB_ALIAS)
        parser.add_argument("--plan", action="store_true")

    def handle(self, *args, **options):
        alias = options["database"]
        if alias not in connections.databases:
            raise CommandError('Unknown database alias "{}"'.format(alias))
        changed = migrate_oauth_name_scope(connections[alias], dry_run=options["plan"])
        self.stdout.write("OAuth name scope: {}".format(
            "upgrade planned" if changed and options["plan"] else "upgraded" if changed else "up to date"))
