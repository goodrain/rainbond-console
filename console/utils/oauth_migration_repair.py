"""Reconcile a pre-existing OAuth column in a startup-generated migration.

Keep the original operation's state transition and every other operation. The
normal migrate command remains responsible for dependencies and applied records.
"""
import ast
import importlib
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.management.base import CommandError
from django.db import migrations


def oauth_column_matches(connection, table, column, field):
    if column.null_ok != field.null:
        return False
    if connection.vendor == "mysql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
                [table, field.column],
            )
            row = cursor.fetchone()
        expected_type = field.db_type(connection).lower()
        # Django emits BOOL; MySQL reports its canonical TINYINT(1) alias.
        if expected_type in ("bool", "boolean"):
            expected_type = "tinyint(1)"
        return bool(row and str(row[0]).lower() == expected_type)
    return connection.introspection.get_field_type(column.type_code, column) == field.get_internal_type()


def make_oauth_add_field_state_only(migration, operation_index, dry_run=False):
    """Patch only the generated AddField expression, preserving custom code.

    Startup generates migration files before running repair in a separate
    process from migrate. Persist the standard SeparateDatabaseAndState wrapper
    so migrate reloads it. Never fake a compound migration or drop a live column.
    """
    module = sys.modules.get(type(migration).__module__)
    filename = getattr(module, "__file__", None)
    if not filename:
        raise CommandError("Cannot locate OAuth migration source: {}".format(migration.name))
    path = Path(filename)
    if path.suffix != ".py" or path.stem != migration.name or path.is_symlink():
        raise CommandError("Cannot safely rewrite OAuth migration: {}".format(migration.name))
    source = path.read_bytes()
    tree = ast.parse(source, filename=str(path))
    expressions = [
        assignment.value for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Migration"
        for assignment in node.body if isinstance(assignment, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "operations" for target in assignment.targets)
    ]
    if (len(expressions) != 1 or not isinstance(expressions[0], ast.List)
            or len(expressions[0].elts) != len(migration.operations)):
        raise CommandError("Cannot identify OAuth migration operations: {}".format(migration.name))
    node = expressions[0].elts[operation_index]
    if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute)
            or not isinstance(node.func.value, ast.Name) or node.func.value.id != "migrations"
            or node.func.attr != "AddField"):
        raise CommandError("Cannot identify generated OAuth AddField: {}".format(migration.name))
    values = {keyword.arg: keyword.value.value for keyword in node.keywords if isinstance(keyword.value, ast.Constant)}
    if values.get("model_name", "").lower() != "oauthservices" or values.get("name") != "auto_create_user":
        raise CommandError("OAuth migration source does not match its loaded operation")
    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
    end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
    replacement = b"migrations.SeparateDatabaseAndState(state_operations=[\n" + source[start:end] + b"\n])"
    repaired = source[:start] + replacement + source[end:]
    ast.parse(repaired, filename=str(path))
    if dry_run:
        return
    temporary = None
    try:
        with NamedTemporaryFile(dir=str(path.parent), prefix=".oauth-repair-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(repaired)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(str(temporary), str(path))
    except OSError as error:
        raise CommandError("Cannot write repaired OAuth migration: {}".format(migration.name)) from error
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    operation = migration.operations[operation_index]
    # The next loader in this process can reuse the imported module, while a
    # separate migrate process reads the same wrapper from disk.
    updated = list(migration.operations)
    updated[operation_index] = migrations.SeparateDatabaseAndState(state_operations=[operation])
    migration.operations = updated
    module.Migration.operations = updated
    importlib.invalidate_caches()
